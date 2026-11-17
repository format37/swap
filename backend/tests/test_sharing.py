"""Sharing an order (QUESTIONS O1, ADR-0041). Refusals first: only its author shares an
open order, and its link shows it to nobody before they are within its reach."""

import uuid
from typing import Any

from httpx import AsyncClient

from swap.links import MAX_OUTSTANDING_INVITES, Opened
from tests.test_links import (
    ALEX,
    GIO,
    NINO,
    Headers,
    Sessions,
    invite,
    linked,
    lists,
    person,
    press_start,
)
from tests.test_orders import publish, user_id

PREFIX = "https://t.me/peertopeerswapbot?start=inv_"


async def share(client: AsyncClient, headers: Headers, order_id: str) -> str:
    """The shared link's token, read the way the recipient's Telegram would."""
    response = await client.post(f"/api/v1/orders/{order_id}/share", headers=headers)
    assert response.status_code == 201, response.text
    url: str = response.json()["url"]
    assert url.startswith(PREFIX)
    return url.removeprefix(PREFIX)


async def sees(client: AsyncClient, headers: Headers, order_id: str) -> bool:
    response = await client.get(f"/api/v1/orders/{order_id}", headers=headers)
    assert response.status_code in (200, 404), response.text
    return response.status_code == 200


async def link_card(client: AsyncClient, headers: Headers, link_id: str) -> Any:
    response = await client.get(f"/api/v1/links/{link_id}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


# --- refused ---------------------------------------------------------------------


async def test_only_its_author_shares_an_order(client: AsyncClient, sessionmaker: Sessions) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    await linked(client, sessionmaker, alex, NINO)
    order = await publish(client, alex)
    # Nino sees it, yet can't pass it on: its words would travel past the author's reach.
    for order_id in (order["id"], str(uuid.uuid4())):
        response = await client.post(f"/api/v1/orders/{order_id}/share", headers=nino)
        assert response.status_code == 404
        assert response.json()["code"] == "order.not_found"


async def test_an_order_that_is_over_is_not_shared(client: AsyncClient) -> None:
    alex = await person(client, ALEX)
    order = await publish(client, alex)
    await client.post(f"/api/v1/orders/{order['id']}/close", headers=alex)
    response = await client.post(f"/api/v1/orders/{order['id']}/share", headers=alex)
    assert response.status_code == 409
    assert response.json()["code"] == "order.not_open"


async def test_shared_links_count_against_the_invite_cap(client: AsyncClient) -> None:
    alex = await person(client, ALEX)
    order = await publish(client, alex)
    for _ in range(MAX_OUTSTANDING_INVITES):
        await share(client, alex, order["id"])
    for path in (f"/api/v1/orders/{order['id']}/share", "/api/v1/links/invites"):
        response = await client.post(path, headers=alex)
        assert response.status_code == 429
        assert response.json()["code"] == "invite.limit"


async def test_a_spent_shared_link_shows_nobody_else_the_order(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    await person(client, NINO)
    gio = await person(client, GIO)
    order = await publish(client, alex)
    token = await share(client, alex, order["id"])
    # Its author opening it spends nothing.
    assert (await press_start(sessionmaker, ALEX, token)).outcome is Opened.OWN
    assert (await press_start(sessionmaker, NINO, token)).outcome is Opened.REQUESTED
    opened = await press_start(sessionmaker, GIO, token)
    assert opened.outcome is Opened.INVALID
    assert opened.order is None
    assert not await sees(client, gio, order["id"])
    assert (await lists(client, gio))["incoming"] == []


async def test_the_request_names_the_order_to_its_receiver_alone(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    order = await publish(client, alex)
    opened = await press_start(sessionmaker, NINO, await share(client, alex, order["id"]))
    assert opened.link is not None
    link_id = str(opened.link.id)
    assert (await link_card(client, alex, link_id))["shared_order"] is None
    named = (await link_card(client, nino, link_id))["shared_order"]
    assert named == {"id": order["id"], "number": order["number"]}
    # A plain invite between others names nothing.
    gio = await person(client, GIO)
    plain = await press_start(sessionmaker, GIO, await invite(client, alex))
    assert plain.link is not None
    assert (await link_card(client, gio, str(plain.link.id)))["shared_order"] is None


# --- allowed ---------------------------------------------------------------------


async def test_a_stranger_links_up_and_then_sees_the_order(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    order = await publish(client, alex)
    token = await share(client, alex, order["id"])
    assert not await sees(client, nino, order["id"])

    opened = await press_start(sessionmaker, NINO, token)
    assert opened.outcome is Opened.REQUESTED
    assert opened.order is not None
    assert str(opened.order.id) == order["id"]
    assert opened.sees_order is False
    assert opened.link is not None
    # Nothing shows before Nino agrees to the link.
    assert not await sees(client, nino, order["id"])
    assert (await lists(client, alex))["invites"] == []  # spent

    accepted = await client.post(f"/api/v1/links/{opened.link.id}/accept", headers=nino)
    assert accepted.status_code == 200
    assert await sees(client, nino, order["id"])
    # Opening the link again now goes straight to the order.
    again = await press_start(sessionmaker, NINO, token)
    assert again.outcome is Opened.SHARED
    assert again.sees_order is True


async def test_someone_who_already_sees_it_is_only_shown_it(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    gio = await person(client, GIO)
    await linked(client, sessionmaker, alex, NINO)
    await linked(client, sessionmaker, nino, GIO)
    # Gio is two handshakes away, within a new order's reach of 2 (QUESTIONS J2).
    order = await publish(client, alex)
    assert await sees(client, gio, order["id"])

    opened = await press_start(sessionmaker, GIO, await share(client, alex, order["id"]))
    assert opened.outcome is Opened.SHARED
    assert opened.sees_order is True
    assert opened.link is None
    # No request was made, and the link is spent all the same.
    assert (await lists(client, gio))["incoming"] == []
    assert (await lists(client, alex))["invites"] == []


async def test_at_reach_0_whoever_opens_it_joins_its_list(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    gio = await person(client, GIO)
    await linked(client, sessionmaker, alex, NINO)
    await linked(client, sessionmaker, alex, GIO)
    order = await publish(client, alex, reach=0, visible_to=[await user_id(client, nino)])
    assert not await sees(client, gio, order["id"])

    # Gio is linked already, so the order shows at once.
    opened = await press_start(sessionmaker, GIO, await share(client, alex, order["id"]))
    assert opened.outcome is Opened.ALREADY_LINKED
    assert opened.sees_order is True
    assert await sees(client, gio, order["id"])
    card = (await client.get(f"/api/v1/orders/{order['id']}", headers=alex)).json()
    assert sorted(p["first_name"] for p in card["visibility"]["people"]) == ["Gio", "Nino"]


async def test_at_reach_0_a_stranger_sees_it_once_linked(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    gio = await person(client, GIO)
    await linked(client, sessionmaker, alex, GIO)
    order = await publish(client, alex, reach=0, visible_to=[await user_id(client, gio)])
    opened = await press_start(sessionmaker, NINO, await share(client, alex, order["id"]))
    assert opened.outcome is Opened.REQUESTED
    assert opened.link is not None
    assert not await sees(client, nino, order["id"])
    await client.post(f"/api/v1/links/{opened.link.id}/accept", headers=nino)
    assert await sees(client, nino, order["id"])


async def test_once_the_order_is_over_the_link_is_a_plain_invite(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    order = await publish(client, alex)
    token = await share(client, alex, order["id"])
    await client.post(f"/api/v1/orders/{order['id']}/close", headers=alex)
    opened = await press_start(sessionmaker, NINO, token)
    assert opened.outcome is Opened.REQUESTED
    assert opened.order is None
    assert opened.link is not None
    assert (await link_card(client, nino, str(opened.link.id)))["shared_order"] is None


async def test_the_invitations_list_names_the_order_it_carries(client: AsyncClient) -> None:
    alex = await person(client, ALEX)
    order = await publish(client, alex)
    await share(client, alex, order["id"])
    await invite(client, alex)
    body = (await client.get("/api/v1/links", headers=alex)).json()
    assert sorted(item["order_number"] or 0 for item in body["invites"]) == [0, order["number"]]
