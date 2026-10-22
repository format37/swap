"""Deals (ADR-0018): proposals, acceptance, the legs, remainders and payment details.
Refusals first (kickoff rule 6): outside a deal, nobody sees or moves it."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from swap.deals import expire_due
from swap.models import Deal, DealLeg, Notification, Order, User
from tests.test_links import ALEX, GIO, NINO, WRITTEN, Headers, linked, person
from tests.test_orders import publish

Sessions = async_sessionmaker[AsyncSession]
TODAY = datetime.now(UTC).date()
GRANDMA = "Сбербанк, карта 2202 2061 1234 5678, Иванова Мария"


class World:
    """Alex's order of up to 150 000 RUB for GEL or USD, open to Nino; Gio is a stranger."""

    def __init__(self, client: AsyncClient, sessions: Sessions) -> None:
        self.client = client
        self.sessions = sessions

    async def build(self, **order: Any) -> "World":
        self.alex = await person(self.client, ALEX)
        self.nino = await person(self.client, NINO)
        self.gio = await person(self.client, GIO)
        self.link = await linked(self.client, self.sessions, self.alex, NINO)
        self.order = await publish(
            self.client, self.alex, payout_methods=["card", "phone", "cash"], **order
        )
        self.nino_rub = await self.details(self.nino, asset="RUB", kind="card", text=GRANDMA)
        self.alex_gel = await self.details(
            self.alex, asset="GEL", kind="bank", text="TBC, GE29TB7777777777777777"
        )
        return self

    async def details(self, headers: Headers, **entry: Any) -> str:
        body = {"title": "Saved", **entry}
        response = await self.client.post("/api/v1/payment-methods", json=body, headers=headers)
        assert response.status_code == 201, response.text
        return str(response.json()["id"])

    def proposal(self, **changes: Any) -> dict[str, Any]:
        return {
            "amount": "50000.00",
            "want_currency": "GEL",
            "give_method": "card",
            "receive_with": self.nino_rub,
            "counter_method": "cash",
            "my_due": str(TODAY + timedelta(days=3)),
            "their_due": str(TODAY + timedelta(days=2)),
            **changes,
        }

    async def propose(
        self, headers: Headers | None = None, order_id: str | None = None, **changes: Any
    ) -> dict[str, Any]:
        response = await self.client.post(
            f"/api/v1/orders/{order_id or self.order['id']}/deals",
            json=self.proposal(**changes),
            headers=headers or self.nino,
        )
        assert response.status_code == 201, response.text
        body: dict[str, Any] = response.json()
        return body

    async def act(
        self, headers: Headers, deal: dict[str, Any] | str, path: str, **body: Any
    ) -> Any:
        deal_id = deal if isinstance(deal, str) else deal["id"]
        return await self.client.post(
            f"/api/v1/deals/{deal_id}/{path}", json=body or None, headers=headers
        )

    async def ok(self, headers: Headers, deal: dict[str, Any] | str, path: str, **body: Any) -> Any:
        response = await self.act(headers, deal, path, **body)
        assert response.status_code == 200, (path, response.text)
        return response.json()

    async def remaining(self) -> str:
        async with self.sessions() as db:
            order = await db.get(Order, uuid.UUID(self.order["id"]))
        assert order is not None
        return f"{order.amount_remaining}:{order.status}"

    async def told(self, kind: str) -> list[tuple[str, dict[str, str], str | None]]:
        async with self.sessions() as db:
            rows = await db.execute(
                select(User.first_name, Notification.params, Notification.target)
                .join(User, User.id == Notification.recipient_id)
                .where(Notification.type == kind)
                .order_by(Notification.created_at, WRITTEN)
            )
            return [(name, params, card) for name, params, card in rows]


@pytest.fixture
async def world(client: AsyncClient, sessionmaker: Sessions) -> World:
    return await World(client, sessionmaker).build()


# --- refused: outside a deal -----------------------------------------------------------


async def test_every_deal_endpoint_needs_a_session(client: AsyncClient) -> None:
    some = uuid.uuid4()
    paths = [
        ("POST", f"/api/v1/orders/{some}/deals"),
        ("GET", "/api/v1/deals"),
        ("GET", f"/api/v1/deals/{some}"),
        *(
            ("POST", f"/api/v1/deals/{some}/{action}")
            for action in (
                "accept",
                "decline",
                "withdraw",
                "cancel",
                "legs/1/sent",
                "legs/1/received",
                "cancel-request",
                "cancel-request/approve",
                "cancel-request/reject",
                "dispute",
                "resolve",
            )
        ),
    ]
    for method, path in paths:
        assert (await client.request(method, path)).status_code == 401, path


async def test_a_stranger_can_neither_see_nor_move_a_deal(world: World) -> None:
    deal = await world.propose()
    response = await world.client.get(f"/api/v1/deals/{deal['id']}", headers=world.gio)
    assert response.status_code == 404
    assert response.json()["code"] == "deal.not_found"
    for path, body in [
        ("accept", {}),
        ("decline", {}),
        ("withdraw", {}),
        ("cancel", {}),
        ("legs/1/sent", {}),
        ("legs/1/received", {}),
        ("cancel-request", {}),
        ("cancel-request/approve", {}),
        ("dispute", {"note": "?"}),
        ("resolve", {"outcome": "settled"}),
    ]:
        refused = await world.act(world.gio, deal, path, **body)
        assert refused.status_code == 404, path
        assert refused.json()["code"] == "deal.not_found"
    listed = await world.client.get("/api/v1/deals", headers=world.gio)
    assert listed.json() == []
    async with world.sessions() as db:
        stored = await db.get(Deal, uuid.UUID(deal["id"]))
    assert stored is not None
    assert stored.status == "proposed"


async def test_nobody_proposes_on_an_order_they_cant_see(world: World) -> None:
    response = await world.client.post(
        f"/api/v1/orders/{world.order['id']}/deals", json=world.proposal(), headers=world.gio
    )
    assert response.status_code == 404
    assert response.json()["code"] == "order.not_found"


async def test_nobody_proposes_on_their_own_order(world: World) -> None:
    response = await world.client.post(
        f"/api/v1/orders/{world.order['id']}/deals",
        json=world.proposal(receive_with=None, give_method="cash"),
        headers=world.alex,
    )
    assert response.status_code == 409
    assert response.json()["code"] == "deal.own_order"


async def test_a_closed_order_takes_no_proposals(world: World) -> None:
    await world.client.post(f"/api/v1/orders/{world.order['id']}/close", headers=world.alex)
    response = await world.client.post(
        f"/api/v1/orders/{world.order['id']}/deals", json=world.proposal(), headers=world.nino
    )
    assert response.status_code == 404


# --- refused: what a proposal may say --------------------------------------------------


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"amount": "9999.99"}, "deal.amount_range"),
        ({"amount": "150000.01"}, "deal.amount_range"),
        ({"want_currency": "EUR"}, "deal.unknown_want"),
        ({"give_method": "crypto"}, "deal.method_not_offered"),
        ({"receive_with": None}, "deal.details_required"),
        ({"receive_with": str(uuid.uuid4())}, "deal.details_unknown"),
        ({"my_due": str(TODAY - timedelta(days=1))}, "deal.due_past"),
        ({"their_due": str(TODAY - timedelta(days=1))}, "deal.due_past"),
        ({"amount": 50000}, "validation_error"),
        ({"amount": "50000.001"}, "validation_error"),
        ({"first": "nobody"}, "validation_error"),
        ({"extra": 1}, "validation_error"),
    ],
)
async def test_a_malformed_proposal_is_refused(
    world: World, changes: dict[str, Any], code: str
) -> None:
    response = await world.client.post(
        f"/api/v1/orders/{world.order['id']}/deals",
        json=world.proposal(**changes),
        headers=world.nino,
    )
    assert response.status_code == 422, response.text
    assert response.json()["code"] == code
    async with world.sessions() as db:
        assert list(await db.scalars(select(Deal))) == []


async def test_payment_details_must_be_the_proposers_own_and_in_the_right_currency(
    world: World,
) -> None:
    usd = await world.details(world.nino, asset="USD", kind="card", text="4111 1111 1111 1111")
    for receive_with, code in [
        (world.alex_gel, "deal.details_unknown"),
        (usd, "deal.details_mismatch"),
    ]:
        response = await world.client.post(
            f"/api/v1/orders/{world.order['id']}/deals",
            json=world.proposal(receive_with=receive_with),
            headers=world.nino,
        )
        assert response.status_code == 422, receive_with
        assert response.json()["code"] == code


# --- allowed: a whole deal --------------------------------------------------------------


async def test_a_deal_from_proposal_to_settled(world: World) -> None:
    deal = await world.propose()
    assert deal["status"] == "proposed"
    assert deal["role"] == "proposer"
    assert deal["rate"] == {"base": "GEL", "quote": "RUB", "value": "29.20"}
    first, second = deal["legs"]
    # The proposer sends first by default (Q-B16): GEL cash to Alex, then RUB to the card.
    assert (first["payer"]["first_name"], first["currency"], first["amount"]) == (
        "Nino",
        "GEL",
        "1712.33",
    )
    assert first["method"] == "cash"
    assert first["recipient"] is None  # Alex chooses when accepting
    assert (second["payer"]["first_name"], second["currency"], second["amount"]) == (
        "Alex",
        "RUB",
        "50000.00",
    )
    assert second["recipient"]["full"] == GRANDMA  # the payee reads their own
    assert await world.told("deal.proposed") == [
        (
            "Alex",
            {
                "name": "Nino B (@nino)",
                "amount": "50000.00",
                "currency": "RUB",
                "counter_amount": "1712.33",
                "counter_currency": "GEL",
            },
            f"deal_{deal['id']}",
        )
    ]
    assert await world.remaining() == "150000.00:open"

    accepted = await world.ok(world.alex, deal, "accept", receive_with=None)
    assert accepted["status"] == "accepted"
    assert accepted["accepted_at"] is not None
    assert await world.remaining() == "100000.00:open"  # FR-2.3
    assert [name for name, _, _ in await world.told("deal.accepted")] == ["Nino"]

    assert (await world.ok(world.nino, deal, "legs/1/sent"))["status"] == "leg1_sent"
    assert [name for name, _, _ in await world.told("deal.sent")] == ["Alex"]
    assert (await world.ok(world.alex, deal, "legs/1/received"))["status"] == "leg1_received"
    assert (await world.ok(world.alex, deal, "legs/2/sent"))["status"] == "leg2_sent"
    settled = await world.ok(world.nino, deal, "legs/2/received")
    assert settled["status"] == "settled"
    assert settled["closed_at"] is not None
    assert all(leg["sent_at"] and leg["received_at"] for leg in settled["legs"])
    assert [name for name, _, _ in await world.told("deal.settled")] == ["Alex"]
    assert [event["type"] for event in settled["events"]] == [
        "proposed",
        "accepted",
        "sent",
        "received",
        "sent",
        "received",
    ]
    assert await world.remaining() == "100000.00:open"


async def test_the_author_may_go_first_and_round_to_whole_units(world: World) -> None:
    deal = await world.propose(first="author", whole=True)
    first, second = deal["legs"]
    assert (first["payer"]["first_name"], first["currency"]) == ("Alex", "RUB")
    assert (second["currency"], second["amount"]) == ("GEL", "1712.00")
    assert deal["whole"] is True


async def test_a_card_for_the_counter_leg_needs_the_authors_details(world: World) -> None:
    deal = await world.propose(counter_method="bank")
    missing = await world.act(world.alex, deal, "accept")
    assert missing.status_code == 422
    assert missing.json()["code"] == "deal.details_required"
    accepted = await world.ok(world.alex, deal, "accept", receive_with=world.alex_gel)
    assert accepted["legs"][0]["recipient"]["full"] == "TBC, GE29TB7777777777777777"


# --- payment details in a deal (ADR-0010, Q-B8) ----------------------------------------


async def test_the_payer_reads_the_details_only_once_the_deal_is_accepted(world: World) -> None:
    deal = await world.propose()
    before = await world.client.get(f"/api/v1/deals/{deal['id']}", headers=world.alex)
    card_leg = before.json()["legs"][1]
    assert card_leg["recipient"] == {"title": "Saved", "masked": "•••• 5678", "full": None}
    await world.ok(world.alex, deal, "accept")
    after = await world.client.get(f"/api/v1/deals/{deal['id']}", headers=world.alex)
    assert after.json()["legs"][1]["recipient"]["full"] == GRANDMA


async def test_a_deal_keeps_its_own_sealed_copy_of_the_details(world: World) -> None:
    deal = await world.propose()
    await world.client.delete(f"/api/v1/payment-methods/{world.nino_rub}", headers=world.nino)
    shown = await world.client.get(f"/api/v1/deals/{deal['id']}", headers=world.nino)
    assert shown.json()["legs"][1]["recipient"]["full"] == GRANDMA
    async with world.sessions() as db:
        stored = await db.scalar(
            text("SELECT recipient_details::text FROM deal_legs WHERE seq = 2")
        )
    assert stored is not None
    assert "2202" not in stored
    assert "Иванова" not in stored


# --- remainders (FR-2.3, Q-B5, Q-E2, Q-B9) ----------------------------------------------


async def test_accepting_until_too_little_is_left_fulfils_the_order(world: World) -> None:
    big = await world.propose(amount="145000.00")
    other = await world.propose(amount="10000.00")
    await world.ok(world.alex, big, "accept")
    # 5 000 RUB left, below the 10 000 minimum: the order is used up (Q-B5)...
    assert await world.remaining() == "5000.00:fulfilled"
    # ...and a proposal it can no longer cover is cancelled, and its proposer told (Q-E2).
    shown = await world.client.get(f"/api/v1/deals/{other['id']}", headers=world.nino)
    assert shown.json()["status"] == "cancelled"
    assert shown.json()["events"][-1]["reason"] == "order_short"
    assert [name for name, _, _ in await world.told("deal.proposal_closed")] == ["Nino"]


async def test_cancelling_an_accepted_deal_gives_its_amount_back(world: World) -> None:
    deal = await world.propose(amount="145000.00")
    await world.ok(world.alex, deal, "accept")
    assert await world.remaining() == "5000.00:fulfilled"
    await world.ok(world.nino, deal, "cancel")
    # Back to open, since 150 000 is above the minimum again (FR-2.3).
    assert await world.remaining() == "150000.00:open"
    assert [name for name, _, _ in await world.told("deal.cancelled")] == ["Alex"]


async def test_an_order_without_a_minimum_is_used_up_only_when_nothing_is_left(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    world = await World(client, sessionmaker).build(amount_min="0")
    # Any amount is a deal, a single rouble included (QUESTIONS F4).
    small = await world.propose(amount="1.00")
    await world.ok(world.alex, small, "accept")
    assert await world.remaining() == "149999.00:open"
    rest = await world.propose(amount="149999.00")
    await world.ok(world.alex, rest, "accept")
    assert await world.remaining() == "0.00:fulfilled"
    await world.ok(world.nino, rest, "cancel")
    assert await world.remaining() == "149999.00:open"


async def test_closing_an_order_cancels_its_proposals_but_not_its_deals(world: World) -> None:
    proposed = await world.propose()
    accepted = await world.propose(amount="20000.00")
    await world.ok(world.alex, accepted, "accept")
    await world.client.post(f"/api/v1/orders/{world.order['id']}/close", headers=world.alex)
    deals = {
        d["id"]: d["status"]
        for d in (
            await world.client.get("/api/v1/deals", params={"scope": "history"}, headers=world.nino)
        ).json()
    }
    assert deals == {proposed["id"]: "cancelled"}
    still = await world.client.get(f"/api/v1/deals/{accepted['id']}", headers=world.nino)
    assert still.json()["status"] == "accepted"


async def test_breaking_the_link_cancels_its_proposals_quietly(world: World) -> None:
    proposed = await world.propose()
    accepted = await world.propose(amount="20000.00")
    await world.ok(world.alex, accepted, "accept")
    await world.client.delete(f"/api/v1/links/{world.link}", headers=world.alex)
    # Both still see their deal, but nobody can propose again (Q-B9).
    gone = await world.client.get(f"/api/v1/deals/{proposed['id']}", headers=world.nino)
    assert gone.json()["status"] == "cancelled"
    assert gone.json()["events"][-1]["reason"] == "link_removed"
    kept = await world.client.get(f"/api/v1/deals/{accepted['id']}", headers=world.nino)
    assert kept.json()["status"] == "accepted"
    assert await world.told("deal.proposal_closed") == []  # a break tells nobody (ADR-0012)
    refused = await world.client.post(
        f"/api/v1/orders/{world.order['id']}/deals", json=world.proposal(), headers=world.nino
    )
    assert refused.status_code == 404


async def test_a_proposal_lapses_after_48_hours(world: World) -> None:
    deal = await world.propose()
    async with world.sessions() as db:
        await db.execute(update(Deal).values(expires_at=datetime.now(UTC) - timedelta(seconds=1)))
        await db.commit()
    late = await world.act(world.alex, deal, "accept")
    assert late.status_code == 409
    assert late.json()["code"] == "deal.expired"
    async with world.sessions() as db:
        assert await expire_due(db) == 1
        await db.commit()
    shown = await world.client.get(f"/api/v1/deals/{deal['id']}", headers=world.alex)
    assert shown.json()["status"] == "expired"
    assert shown.json()["events"][-1]["actor_id"] is None  # the system did it
    assert [name for name, _, _ in await world.told("deal.expired")] == ["Nino"]


async def test_lists_show_ones_own_deals(world: World) -> None:
    active = await world.propose()
    done = await world.propose(amount="20000.00")
    await world.ok(world.alex, done, "decline")
    for headers in (world.alex, world.nino):
        open_ = await world.client.get("/api/v1/deals", headers=headers)
        assert [d["id"] for d in open_.json()] == [active["id"]]
        history = await world.client.get(
            "/api/v1/deals", params={"scope": "history"}, headers=headers
        )
        assert [d["id"] for d in history.json()] == [done["id"]]
    by_order = await world.client.get(
        "/api/v1/deals", params={"order_id": world.order["id"]}, headers=world.alex
    )
    assert [d["id"] for d in by_order.json()] == [active["id"]]


async def test_legs_are_stored_as_the_proposal_said(world: World) -> None:
    deal = await world.propose()
    async with world.sessions() as db:
        legs = list(
            await db.scalars(
                select(DealLeg)
                .where(DealLeg.deal_id == uuid.UUID(deal["id"]))
                .order_by(DealLeg.seq)
            )
        )
    assert [(leg.seq, leg.currency, str(leg.amount), leg.method) for leg in legs] == [
        (1, "GEL", "1712.33", "cash"),
        (2, "RUB", "50000.00", "card"),
    ]
    assert [str(leg.due_date) for leg in legs] == [
        str(TODAY + timedelta(days=3)),
        str(TODAY + timedelta(days=2)),
    ]
