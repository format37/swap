"""Reach by handshakes (QUESTIONS J2, ADR-0028). Refusals first: one ring too far, a chain
broken in the middle, an order at 0 and someone off its list, and the viewer's filter.

The people stand in a line: Alex – Nino – Gio – Ana – Dato – Elene, so Gio is two
handshakes from Alex, Ana three, Dato four and Elene five. Zura is on an island of his own.
"""

import random
import uuid
from itertools import pairwise
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from swap.models import Link, LinkStatus, Notification, User
from swap.network import FAR, Graph, distances
from tests.test_links import ALEX, GIO, NINO, Headers, linked, person
from tests.test_orders import publish, sees, user_id

Sessions = async_sessionmaker[AsyncSession]

ANA = {"id": 4004, "first_name": "Ana", "username": "ana"}
DATO = {"id": 5005, "first_name": "Dato", "username": "dato"}
ELENE = {"id": 6006, "first_name": "Elene", "username": "elene"}
ZURA = {"id": 7007, "first_name": "Zura", "username": "zura"}
LINE = [ALEX, NINO, GIO, ANA, DATO, ELENE]


class Line:
    """Everyone signed in, and the line linked up; `links[i]` joins LINE[i] and LINE[i+1]."""

    def __init__(self, client: AsyncClient, sessions: Sessions) -> None:
        self.client = client
        self.sessions = sessions

    async def build(self) -> "Line":
        self.people: dict[str, Headers] = {}
        for profile in [*LINE, ZURA]:
            self.people[str(profile["first_name"])] = await person(self.client, profile)
        self.links: list[str] = []
        for left, right in pairwise(LINE):
            inviter = self.people[str(left["first_name"])]
            self.links.append(await linked(self.client, self.sessions, inviter, right))
        return self

    def __getitem__(self, name: str) -> Headers:
        return self.people[name]

    async def who_sees(self, order: dict[str, Any], **params: Any) -> list[str]:
        """Everyone but the author whose feed lists the order, its card agreeing."""
        seen = []
        for name, headers in self.people.items():
            if name == order["author"]["first_name"]:
                continue
            if params:
                feed = await self.client.get(
                    "/api/v1/orders", params={"scope": "visible", **params}, headers=headers
                )
                assert feed.status_code == 200, feed.text
                if order["id"] in [found["id"] for found in feed.json()]:
                    seen.append(name)
            elif await sees(self.client, headers, order["id"]):
                seen.append(name)
        return seen


@pytest.fixture
async def line(client: AsyncClient, sessionmaker: Sessions) -> Line:
    return await Line(client, sessionmaker).build()


# --- refused ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("reach", "seen"),
    [
        (1, ["Nino"]),
        (2, ["Nino", "Gio"]),
        (3, ["Nino", "Gio", "Ana"]),
        # Any chain at all, however long; never the island.
        (None, ["Nino", "Gio", "Ana", "Dato", "Elene"]),
    ],
)
async def test_one_ring_too_far_sees_nothing(
    line: Line, reach: int | None, seen: list[str]
) -> None:
    order = await publish(line.client, line["Alex"], reach=reach)
    assert await line.who_sees(order) == seen


async def test_a_broken_link_in_the_middle_of_a_chain_hides_the_order(line: Line) -> None:
    order = await publish(line.client, line["Alex"], reach=None)
    # Gio breaks with Nino: the line splits into two islands.
    broken = await line.client.delete(f"/api/v1/links/{line.links[1]}", headers=line["Gio"])
    assert broken.status_code == 204, broken.text
    assert await line.who_sees(order) == ["Nino"]


async def test_an_order_at_0_shows_only_to_its_list_while_linked(
    client: AsyncClient, sessionmaker: Sessions, line: Line
) -> None:
    # Ana links to Alex too, so two of Alex's links can be told apart.
    await linked(client, sessionmaker, line["Alex"], ANA)
    nino = await user_id(client, line["Nino"])
    order = await publish(client, line["Alex"], reach=0, visible_to=[nino])
    assert await line.who_sees(order) == ["Nino"]
    await client.delete(f"/api/v1/links/{line.links[0]}", headers=line["Nino"])
    assert await line.who_sees(order) == []


async def test_the_viewers_filter_narrows_what_the_reach_allows(line: Line) -> None:
    order = await publish(line.client, line["Alex"], reach=None)
    assert await line.who_sees(order, within=1) == ["Nino"]
    assert await line.who_sees(order, within=2) == ["Nino", "Gio"]
    assert await line.who_sees(order, within=3) == ["Nino", "Gio", "Ana"]
    # The filter never widens a reach.
    near = await publish(line.client, line["Alex"], reach=1)
    assert await line.who_sees(near, within=3) == ["Nino"]
    # Its 0, favourites, doesn't exist yet; ∞ is no filter at all.
    for within in (0, 4, "far"):
        response = await line.client.get(
            "/api/v1/orders", params={"within": within}, headers=line["Gio"]
        )
        assert response.status_code == 422, within


async def test_too_far_to_see_is_too_far_to_propose(line: Line) -> None:
    order = await publish(line.client, line["Alex"], payout_methods=["bank"])
    proposal = {"amount": "50000.00", "want_currency": "GEL", "give_method": "bank"}
    response = await line.client.post(
        f"/api/v1/orders/{order['id']}/deals",
        json={**proposal, "counter_method": "cash"},
        headers=line["Ana"],
    )
    assert response.status_code == 404
    assert response.json()["code"] == "order.not_found"


# --- allowed ---------------------------------------------------------------------------


async def test_anyone_who_sees_an_order_may_propose_on_it(line: Line) -> None:
    # Gio is two handshakes from Alex, and a new order reaches two (QUESTIONS J2).
    order = await publish(line.client, line["Alex"], payout_methods=["bank"])
    response = await line.client.post(
        f"/api/v1/orders/{order['id']}/deals",
        json={
            "amount": "50000.00",
            "want_currency": "GEL",
            "give_method": "bank",
            "counter_method": "cash",
        },
        headers=line["Gio"],
    )
    assert response.status_code == 201, response.text
    deal = response.json()
    # A deal outlives a broken chain: Gio and Nino part, and both sides still have it.
    await line.client.delete(f"/api/v1/links/{line.links[1]}", headers=line["Gio"])
    for headers in (line["Gio"], line["Alex"]):
        shown = await line.client.get(f"/api/v1/deals/{deal['id']}", headers=headers)
        assert shown.json()["status"] == "proposed"
    accepted = await line.client.post(f"/api/v1/deals/{deal['id']}/accept", headers=line["Alex"])
    assert accepted.status_code == 200, accepted.text


async def test_the_bot_tells_direct_links_only(line: Line, sessionmaker: Sessions) -> None:
    async with sessionmaker() as db:
        before = set(await db.scalars(select(Notification.id)))
    await publish(line.client, line["Nino"], reach=None)
    async with sessionmaker() as db:
        told = list(
            await db.scalars(
                select(User.first_name)
                .join(Notification, Notification.recipient_id == User.id)
                .where(Notification.type == "order.opened", Notification.id.not_in(before))
                .order_by(User.first_name)
            )
        )
    # Farther rings find it in their feed (QUESTIONS J2).
    assert told == ["Alex", "Gio"]


async def test_the_card_names_one_shortest_chain(
    client: AsyncClient, sessionmaker: Sessions, line: Line
) -> None:
    order = await publish(client, line["Alex"], reach=3)

    async def chain(name: str) -> list[str] | None:
        card = (await client.get(f"/api/v1/orders/{order['id']}", headers=line[name])).json()
        return None if card["chain"] is None else [p["first_name"] for p in card["chain"]]

    assert await chain("Alex") is None
    assert await chain("Nino") == []
    assert await chain("Gio") == ["Nino"]
    # From the viewer's side: Ana's own link first, «через Gio → Nino».
    assert await chain("Ana") == ["Gio", "Nino"]
    # A shortcut makes the chain shorter.
    await linked(client, sessionmaker, line["Alex"], GIO)
    assert await chain("Ana") == ["Gio"]
    # Lists show no chains.
    feed = (await client.get("/api/v1/orders", headers=line["Ana"])).json()
    assert [found["chain"] for found in feed] == [None]


async def test_the_network_names_three_rings_and_counts_the_rest(line: Line) -> None:
    response = await line.client.get("/api/v1/network", headers=line["Alex"])
    assert response.status_code == 200, response.text
    network = response.json()
    assert [
        (ring["distance"], [p["first_name"] for p in ring["people"]]) for ring in network["rings"]
    ] == [(1, ["Nino"]), (2, ["Gio"]), (3, ["Ana"])]
    assert network["farther"] == 2
    # The island has an empty network.
    alone = (await line.client.get("/api/v1/network", headers=line["Zura"])).json()
    assert alone == {
        "rings": [
            {"distance": 1, "people": []},
            {"distance": 2, "people": []},
            {"distance": 3, "people": []},
        ],
        "farther": 0,
    }
    assert (await line.client.get("/api/v1/network")).status_code == 401


async def test_sql_and_python_agree_on_every_distance(sessionmaker: Sessions) -> None:
    """The feeds ask SQL and the screens ask Python; a random network keeps them honest."""
    # Not for secrets: a seeded network that is the same on every run.
    chance = random.Random(37)  # noqa: S311
    async with sessionmaker() as db:
        people = [
            User(id=uuid.uuid4(), telegram_id=900_000 + n, first_name=f"P{n}") for n in range(40)
        ]
        db.add_all(people)
        await db.flush()
        pairs = {tuple(sorted(chance.sample([p.id for p in people], 2))) for _ in range(55)}
        for lo, hi in pairs:
            status = chance.choice([LinkStatus.ACTIVE] * 4 + [LinkStatus.REMOVED])
            db.add(Link(user_lo_id=lo, user_hi_id=hi, status=status, requested_by=lo))
        await db.flush()
        graph = await Graph.load(db)
        for someone in people[:12]:
            ring = distances(someone.id)
            rows = await db.execute(
                select(ring.c.user_id, func.min(ring.c.depth))
                .where(ring.c.user_id != someone.id)
                .group_by(ring.c.user_id)
            )
            assert dict(rows.all()) == graph.rings(someone.id)
        assert max(distance for p in people for distance in graph.rings(p.id).values()) == FAR
