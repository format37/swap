"""Orders (ADR-0016). Visibility first (kickoff rule 6): with no chain of links to the
author, and off the order's list, nobody sees it. Reach itself is tests/test_reach.py."""

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from swap.models import Notification, Order, User
from swap.orders import today
from tests.test_links import ALEX, GIO, NINO, Headers, linked, person, requested

Sessions = async_sessionmaker[AsyncSession]

TODAY = datetime.now(UTC).date()
# What the wizard sends for a currency whose rate isn't fixed (QUESTIONS G2, J1).
MARKET = {"v": 1, "type": "reference", "source": "coinbase"}


def fixed(base: str, quote: str, value: str) -> dict[str, Any]:
    """The author's own rate for one wanted currency, «1 base = value quote» (ADR-0026)."""
    return {"v": 1, "type": "fixed", "quotes": [{"base": base, "quote": quote, "value": value}]}


def want(
    currency: str,
    country: str,
    rate_spec: dict[str, Any] = MARKET,
    ways: tuple[str, ...] = ("cash", "bank"),
) -> dict[str, Any]:
    """A wanted currency with its rate and how the author takes it (ADR-0026, ADR-0037)."""
    return {
        "currency": currency,
        "country": country,
        "rate_spec": rate_spec,
        "receive_methods": list(ways),
    }


def draft(**changes: Any) -> dict[str, Any]:
    """The wizard's order: up to 150 000 RUB in Russia, for GEL in cash or by bank, or USD
    by bank alone, in Georgia (QUESTIONS L1)."""
    return {
        "give_currency": "RUB",
        "give_country": "RU",
        "amount_min": "10000.00",
        "amount_max": "150000.00",
        "available_from": str(TODAY),
        "available_until": str(TODAY + timedelta(days=14)),
        "payout_methods": ["bank", "crypto"],
        "wants": [
            want("GEL", "GE", fixed("GEL", "RUB", "29.20")),
            want("USD", "GE", fixed("USD", "RUB", "81.50"), ways=("bank",)),
        ],
        **changes,
    }


async def publish(client: AsyncClient, headers: Headers, **changes: Any) -> dict[str, Any]:
    response = await client.post("/api/v1/orders", json=draft(**changes), headers=headers)
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


async def sees(client: AsyncClient, headers: Headers, order_id: str) -> bool:
    """Whether the order is in their feed. Its card must agree, and refuse as a stranger's."""
    feed = await client.get("/api/v1/orders", headers=headers)
    assert feed.status_code == 200
    listed = order_id in [order["id"] for order in feed.json()]
    card = await client.get(f"/api/v1/orders/{order_id}", headers=headers)
    if listed:
        assert card.status_code == 200
    else:
        assert card.status_code == 404
        assert card.json()["code"] == "order.not_found"
    return listed


async def user_id(client: AsyncClient, headers: Headers) -> str:
    me: dict[str, Any] = (await client.get("/api/v1/me", headers=headers)).json()
    return str(me["id"])


# --- refused: who sees what -----------------------------------------------------------


async def test_every_order_endpoint_needs_a_session(client: AsyncClient) -> None:
    some = uuid.uuid4()
    for method, path in [
        ("POST", "/api/v1/orders"),
        ("GET", "/api/v1/orders"),
        ("GET", f"/api/v1/orders/{some}"),
        ("POST", f"/api/v1/orders/{some}/close"),
        ("POST", f"/api/v1/orders/{some}/reopen"),
        ("DELETE", f"/api/v1/orders/{some}"),
        ("POST", "/api/v1/quote"),
    ]:
        response = await client.request(method, path)
        assert response.status_code == 401, (method, path)


async def test_a_stranger_sees_no_order(client: AsyncClient) -> None:
    alex = await person(client, ALEX)
    gio = await person(client, GIO)
    order = await publish(client, alex)
    assert not await sees(client, gio, order["id"])


async def test_a_request_not_yet_accepted_shows_nothing(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    await requested(client, sessionmaker, alex, NINO)
    order = await publish(client, alex)
    assert not await sees(client, nino, order["id"])


async def test_breaking_a_link_hides_orders_at_once(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    link_id = await linked(client, sessionmaker, alex, NINO)
    order = await publish(client, alex)
    assert await sees(client, nino, order["id"])
    await client.delete(f"/api/v1/links/{link_id}", headers=nino)
    assert not await sees(client, nino, order["id"])
    # And the other way round: the author no longer sees the broken link's orders.
    mine = await publish(client, nino)
    assert not await sees(client, alex, mine["id"])


async def test_an_order_for_chosen_links_hides_from_the_others(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    gio = await person(client, GIO)
    await linked(client, sessionmaker, alex, NINO)
    await linked(client, sessionmaker, alex, GIO)
    order = await publish(client, alex, reach=0, visible_to=[await user_id(client, nino)])
    assert await sees(client, nino, order["id"])
    assert not await sees(client, gio, order["id"])


async def test_a_closed_order_is_its_authors_alone(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    await linked(client, sessionmaker, alex, NINO)
    order = await publish(client, alex)
    closed = await client.post(f"/api/v1/orders/{order['id']}/close", headers=alex)
    assert closed.json()["status"] == "closed"
    assert not await sees(client, nino, order["id"])
    assert (await client.get(f"/api/v1/orders/{order['id']}", headers=alex)).status_code == 200


async def test_an_order_past_its_dates_is_its_authors_alone(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    await linked(client, sessionmaker, alex, NINO)
    order = await publish(client, alex)
    async with sessionmaker() as db:
        await db.execute(
            update(Order).values(
                available_from=TODAY - timedelta(days=10),
                available_until=TODAY - timedelta(days=2),
            )
        )
        await db.commit()
    assert not await sees(client, nino, order["id"])
    mine = await client.get("/api/v1/orders", params={"scope": "mine"}, headers=alex)
    assert [found["id"] for found in mine.json()] == [order["id"]]


async def test_only_the_author_closes_an_order(client: AsyncClient, sessionmaker: Sessions) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    gio = await person(client, GIO)
    await linked(client, sessionmaker, alex, NINO)
    order = await publish(client, alex)
    for headers in (nino, gio):
        response = await client.post(f"/api/v1/orders/{order['id']}/close", headers=headers)
        assert response.status_code == 404
        assert response.json()["code"] == "order.not_found"
    assert await sees(client, nino, order["id"])


async def test_only_the_author_reopens_or_deletes_an_order(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    gio = await person(client, GIO)
    await linked(client, sessionmaker, alex, NINO)
    order = await publish(client, alex)
    await client.post(f"/api/v1/orders/{order['id']}/close", headers=alex)
    for headers in (nino, gio):
        for method, path in [
            ("POST", f"/api/v1/orders/{order['id']}/reopen"),
            ("DELETE", f"/api/v1/orders/{order['id']}"),
        ]:
            response = await client.request(method, path, headers=headers)
            assert response.status_code == 404, (method, path)
            assert response.json()["code"] == "order.not_found"
    card = await client.get(f"/api/v1/orders/{order['id']}", headers=alex)
    assert card.json()["status"] == "closed"


async def test_a_deleted_order_is_gone_for_everyone_its_author_too(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    await linked(client, sessionmaker, alex, NINO)
    order = await publish(client, alex)
    await client.post(f"/api/v1/orders/{order['id']}/close", headers=alex)
    deleted = await client.delete(f"/api/v1/orders/{order['id']}", headers=alex)
    assert deleted.status_code == 204
    for headers in (alex, nino):
        assert not await sees(client, headers, order["id"])
    mine = await client.get("/api/v1/orders", params={"scope": "mine"}, headers=alex)
    assert mine.json() == []
    # Nothing more can be done with it: it answers as one that never existed.
    for method, path in [
        ("POST", f"/api/v1/orders/{order['id']}/close"),
        ("POST", f"/api/v1/orders/{order['id']}/reopen"),
        ("DELETE", f"/api/v1/orders/{order['id']}"),
    ]:
        response = await client.request(method, path, headers=alex)
        assert response.status_code == 404, (method, path)


async def test_who_else_may_see_it_is_the_authors_to_know(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    await linked(client, sessionmaker, alex, NINO)
    order = await publish(client, alex, reach=0, visible_to=[await user_id(client, nino)])
    seen = (await client.get(f"/api/v1/orders/{order['id']}", headers=nino)).json()
    assert seen["visibility"] is None
    assert seen["mine"] is False
    own = (await client.get(f"/api/v1/orders/{order['id']}", headers=alex)).json()
    assert own["visibility"]["reach"] == 0
    assert [p["first_name"] for p in own["visibility"]["people"]] == ["Nino"]


async def test_an_order_cannot_be_shown_to_someone_unlinked(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    gio = await person(client, GIO)
    await linked(client, sessionmaker, alex, NINO)
    nino_id, gio_id = await user_id(client, nino), await user_id(client, gio)
    for reach, visible_to, code in [
        (0, [gio_id], "order.visible_to_unlinked"),
        (0, [nino_id, gio_id], "order.visible_to_unlinked"),
        (0, [str(uuid.uuid4())], "order.visible_to_unlinked"),
        # «Только выбранным» needs someone chosen: the slider has no broken state (J2).
        (0, [], "order.visible_to_nobody"),
        (0, None, "order.visible_to_nobody"),
        # A list belongs to reach 0 alone.
        (1, [nino_id], "order.visible_to_needs_reach_0"),
        (None, [nino_id], "order.visible_to_needs_reach_0"),
    ]:
        response = await client.post(
            "/api/v1/orders", json=draft(reach=reach, visible_to=visible_to), headers=alex
        )
        assert response.status_code == 422, (reach, visible_to)
        assert response.json()["code"] == code
    async with sessionmaker() as db:
        assert list(await db.scalars(select(Order))) == []


# --- refused: what an order may say -------------------------------------------------


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"give_currency": "XYZ"}, "order.unknown_currency"),
        ({"wants": [want("XYZ", "GE")]}, "order.unknown_currency"),
        ({"wants": [want("RUB", "GE")]}, "order.wants_own_currency"),
        ({"wants": [want("GEL", "GE"), want("GEL", "GE")]}, "order.wants_repeated"),
        # Once each, whatever the country: a proposal names one rate (ADR-0026).
        ({"wants": [want("GEL", "GE"), want("GEL", "TR")]}, "order.wants_repeated"),
        # A fixed rate is between the given currency and this one, and is one quote.
        ({"wants": [want("EUR", "GE", fixed("GEL", "RUB", "29.20"))]}, "rate.missing"),
        ({"wants": [want("GEL", "GE", fixed("USD", "GEL", "2.70"))]}, "rate.missing"),
        (
            {
                "wants": [
                    want(
                        "GEL",
                        "GE",
                        {
                            "v": 1,
                            "type": "fixed",
                            "quotes": [
                                {"base": "GEL", "quote": "RUB", "value": "29.20"},
                                {"base": "USD", "quote": "RUB", "value": "81.50"},
                            ],
                        },
                    )
                ]
            },
            "rate.unused",
        ),
        ({"amount_min": "200000.00"}, "order.amount_range"),
        (
            {"available_from": str(TODAY + timedelta(days=3)), "available_until": str(TODAY)},
            "order.window",
        ),
        (
            {
                "available_from": str(TODAY - timedelta(days=9)),
                "available_until": str(TODAY - timedelta(days=2)),
            },
            "order.window_past",
        ),
        ({"amount_max": 150000}, "validation_error"),
        ({"amount_max": "150000.001"}, "validation_error"),
        ({"amount_max": "0"}, "validation_error"),
        ({"amount_min": "-5"}, "validation_error"),
        ({"amount_min": 0}, "validation_error"),
        ({"amount_min": "1e3"}, "validation_error"),
        ({"payout_methods": []}, "validation_error"),
        ({"payout_methods": ["pigeon"]}, "validation_error"),
        # A card is a bank account now (QUESTIONS G3).
        ({"payout_methods": ["card"]}, "validation_error"),
        # How the author is paid is each currency's own now (QUESTIONS L1).
        ({"receive_methods": ["cash"]}, "validation_error"),
        ({"wants": [want("GEL", "GE", ways=("phone",))]}, "validation_error"),
        ({"wants": [want("GEL", "GE", ways=())]}, "validation_error"),
        ({"wants": [want("GEL", "GE", ways=("pigeon",))]}, "validation_error"),
        ({"wants": [{**want("GEL", "GE"), "receive_methods": None}]}, "validation_error"),
        (
            {"wants": [{"currency": "GEL", "country": "GE", "rate_spec": MARKET}]},
            "validation_error",
        ),
        ({"give_country": "Russia"}, "validation_error"),
        ({"wants": []}, "validation_error"),
        # Each wanted currency says its rate; the order no longer has one of its own.
        ({"wants": [{"currency": "GEL", "country": "GE"}]}, "validation_error"),
        ({"rate_spec": MARKET}, "validation_error"),
        ({"note": "x" * 501}, "validation_error"),
        ({"reach": 4}, "validation_error"),
        ({"reach": -1}, "validation_error"),
        ({"reach": "far"}, "validation_error"),
        ({"extra": "field"}, "validation_error"),
    ],
)
async def test_a_malformed_order_is_refused(
    client: AsyncClient, sessionmaker: Sessions, changes: dict[str, Any], code: str
) -> None:
    alex = await person(client, ALEX)
    response = await client.post("/api/v1/orders", json=draft(**changes), headers=alex)
    assert response.status_code == 422, response.text
    assert response.json()["code"] == code
    async with sessionmaker() as db:
        assert list(await db.scalars(select(Order))) == []


# --- allowed --------------------------------------------------------------------------


async def test_an_order_is_published_and_everyone_who_can_see_it_is_told(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    gio = await person(client, GIO)
    await linked(client, sessionmaker, alex, NINO)
    await linked(client, sessionmaker, alex, GIO)
    async with sessionmaker() as db:
        before = len(list(await db.scalars(select(Notification))))

    order = await publish(client, alex, note="  карта Сбер или СБП  ")
    assert order["mine"] is True
    assert order["status"] == "open"
    assert order["amount_remaining"] == "150000.00"
    assert order["amount_min"] == "10000.00"
    assert order["note"] == "карта Сбер или СБП"
    assert order["payout_methods"] == ["bank", "crypto"]
    assert order["wants"] == [
        want("GEL", "GE", fixed("GEL", "RUB", "29.20")),
        want("USD", "GE", fixed("USD", "RUB", "81.50"), ways=("bank",)),
    ]
    # «Мои связи и их связи» unless the author says otherwise (QUESTIONS J2).
    assert order["visibility"] == {"reach": 2, "people": []}

    async with sessionmaker() as db:
        told = (
            await db.execute(
                select(User.first_name, Notification.type, Notification.params, Notification.target)
                .join(User, User.id == Notification.recipient_id)
                .where(Notification.type == "order.opened")
                .order_by(User.first_name)
            )
        ).all()
        assert len(list(await db.scalars(select(Notification)))) == before + 2
    params = {
        "name": "Alex (@format37)",
        "number": str(order["number"]),
        "amount": "150000.00",
        "currency": "RUB",
        "wants": "GEL, USD",
    }
    assert [tuple(row) for row in told] == [
        ("Gio", "order.opened", params, f"order_{order['id']}"),
        ("Nino", "order.opened", params, f"order_{order['id']}"),
    ]
    assert await sees(client, nino, order["id"])
    assert await sees(client, gio, order["id"])


async def test_an_order_for_chosen_links_tells_only_them(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    await person(client, GIO)
    await linked(client, sessionmaker, alex, NINO)
    await linked(client, sessionmaker, alex, GIO)
    await publish(client, alex, reach=0, visible_to=[await user_id(client, nino)])
    async with sessionmaker() as db:
        told = list(
            await db.scalars(
                select(User.first_name)
                .join(Notification, Notification.recipient_id == User.id)
                .where(Notification.type == "order.opened")
            )
        )
    assert told == ["Nino"]


async def test_a_link_made_later_sees_an_order_for_all_links(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    order = await publish(client, alex)
    assert not await sees(client, nino, order["id"])
    await linked(client, sessionmaker, alex, NINO)
    assert await sees(client, nino, order["id"])


async def test_the_feeds(client: AsyncClient, sessionmaker: Sessions) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    await linked(client, sessionmaker, alex, NINO)
    later = await publish(
        client,
        alex,
        available_from=str(TODAY + timedelta(days=5)),
        available_until=str(TODAY + timedelta(days=9)),
    )
    sooner = await publish(client, alex)
    own = await publish(
        client,
        nino,
        give_currency="GEL",
        give_country="GE",
        wants=[want("RUB", "RU", fixed("GEL", "RUB", "29.00"))],
    )

    visible = (await client.get("/api/v1/orders", headers=nino)).json()
    # Open to me, by the date they become available (FR-2.4); never my own.
    assert [o["id"] for o in visible] == [sooner["id"], later["id"]]
    assert visible[0]["author"]["first_name"] == "Alex"
    assert visible[0]["visibility"] is None
    mine = (await client.get("/api/v1/orders", params={"scope": "mine"}, headers=nino)).json()
    assert [o["id"] for o in mine] == [own["id"]]


async def test_closing_an_order_twice_is_refused(client: AsyncClient) -> None:
    alex = await person(client, ALEX)
    order = await publish(client, alex)
    first = await client.post(f"/api/v1/orders/{order['id']}/close", headers=alex)
    assert first.status_code == 200
    again = await client.post(f"/api/v1/orders/{order['id']}/close", headers=alex)
    assert again.status_code == 409
    assert again.json()["code"] == "order.not_open"


async def test_an_order_says_how_its_author_pays_and_is_paid(client: AsyncClient) -> None:
    alex = await person(client, ALEX)
    wants = [want("GEL", "GE", ways=("cash", "bank", "cash")), want("USD", "GE", ways=("bank",))]
    order = await publish(client, alex, wants=wants)
    # In the order chosen, once each (QUESTIONS F2), and for each currency its own (L1).
    assert order["payout_methods"] == ["bank", "crypto"]
    assert [w["receive_methods"] for w in order["wants"]] == [["cash", "bank"], ["bank"]]
    assert "receive_methods" not in order
    card = (await client.get(f"/api/v1/orders/{order['id']}", headers=alex)).json()
    assert [w["receive_methods"] for w in card["wants"]] == [["cash", "bank"], ["bank"]]


async def test_an_order_needs_no_minimum_and_no_last_day(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    await linked(client, sessionmaker, alex, NINO)
    # What the wizard sends when both are left empty (QUESTIONS F3, F4).
    order = await publish(client, alex, amount_min="0", available_until=None)
    assert order["amount_min"] == "0.00"
    assert order["available_until"] is None
    assert await sees(client, nino, order["id"])
    # An order without a last day never passes its dates, however long ago it began.
    async with sessionmaker() as db:
        await db.execute(update(Order).values(available_from=TODAY - timedelta(days=400)))
        await db.commit()
    assert await sees(client, nino, order["id"])
    # Leaving the last day out is the same as sending none.
    default = draft()
    del default["available_until"]
    response = await client.post("/api/v1/orders", json=default, headers=alex)
    assert response.json()["available_until"] is None


async def test_a_closed_order_reopens_as_it_was_and_tells_nobody(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    gio = await person(client, GIO)
    await linked(client, sessionmaker, alex, NINO)
    await linked(client, sessionmaker, alex, GIO)
    order = await publish(client, alex, reach=0, visible_to=[await user_id(client, nino)])
    await client.post(f"/api/v1/orders/{order['id']}/close", headers=alex)
    async with sessionmaker() as db:
        before = len(list(await db.scalars(select(Notification))))
    reopened = await client.post(f"/api/v1/orders/{order['id']}/reopen", headers=alex)
    assert reopened.status_code == 200, reopened.text
    body = reopened.json()
    assert body["status"] == "open"
    assert body["amount_remaining"] == order["amount_remaining"]
    assert [p["first_name"] for p in body["visibility"]["people"]] == ["Nino"]
    # Its list holds as before: Nino sees it again, Gio still doesn't.
    assert await sees(client, nino, order["id"])
    assert not await sees(client, gio, order["id"])
    async with sessionmaker() as db:
        assert len(list(await db.scalars(select(Notification)))) == before


async def test_only_a_closed_order_reopens_and_only_one_not_open_is_deleted(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    order = await publish(client, alex)
    reopen = f"/api/v1/orders/{order['id']}/reopen"
    again = await client.post(reopen, headers=alex)
    assert (again.status_code, again.json()["code"]) == (409, "order.not_closed")
    # An open order is closed first, so its proposals go the one way they do (Q-E2).
    gone = await client.delete(f"/api/v1/orders/{order['id']}", headers=alex)
    assert (gone.status_code, gone.json()["code"]) == (409, "order.open")
    async with sessionmaker() as db:
        await db.execute(update(Order).values(status="fulfilled"))
        await db.commit()
    used_up = await client.post(reopen, headers=alex)
    assert (used_up.status_code, used_up.json()["code"]) == (409, "order.not_closed")
    assert (await client.delete(f"/api/v1/orders/{order['id']}", headers=alex)).status_code == 204


async def test_an_order_past_its_last_day_doesnt_reopen(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    order = await publish(client, alex)
    await client.post(f"/api/v1/orders/{order['id']}/close", headers=alex)
    async with sessionmaker() as db:
        await db.execute(
            update(Order).values(
                available_from=TODAY - timedelta(days=10),
                available_until=TODAY - timedelta(days=1),
            )
        )
        await db.commit()
    response = await client.post(f"/api/v1/orders/{order['id']}/reopen", headers=alex)
    assert (response.status_code, response.json()["code"]) == (409, "order.window_past")


async def test_exactly_one_amount_is_an_order_too(client: AsyncClient) -> None:
    alex = await person(client, ALEX)
    order = await publish(client, alex, amount_min="50000.00", amount_max="50000.00")
    assert order["amount_min"] == order["amount_max"] == order["amount_remaining"] == "50000.00"


# --- the quote -------------------------------------------------------------------------


async def test_a_quote_previews_the_counter_amount(client: AsyncClient) -> None:
    alex = await person(client, ALEX)
    body = {
        "amount": "50000.00",
        "give_currency": "RUB",
        "want_currency": "GEL",
        "rate_spec": fixed("GEL", "RUB", "29.20"),
    }
    response = await client.post("/api/v1/quote", json=body, headers=alex)
    # The amount, and the rate it came from, the author's own (ADR-0004).
    assert response.json() == {
        "amount": "1712.33",
        "rate": {
            "base": "GEL",
            "quote": "RUB",
            "value": "29.20",
            "source": None,
            "fetched_at": None,
        },
    }
    whole = await client.post("/api/v1/quote", json={**body, "whole": True}, headers=alex)
    assert whole.json()["amount"] == "1712.00"

    missing = await client.post(
        "/api/v1/quote", json={**body, "want_currency": "EUR"}, headers=alex
    )
    assert missing.status_code == 422
    assert missing.json()["code"] == "rate.missing"
    number = await client.post("/api/v1/quote", json={**body, "amount": 50000}, headers=alex)
    assert number.status_code == 422


async def test_an_order_follows_the_market_unless_its_rate_is_fixed(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    await linked(client, sessionmaker, alex, NINO)
    # What the wizard sends for a currency whose rate the author doesn't fix (G2, J1).
    market = MARKET
    order = await publish(client, alex, wants=[want("GEL", "GE")])
    assert order["wants"][0]["rate_spec"] == market
    assert await sees(client, nino, order["id"])
    # Whoever looks gets the rate of the moment: Coinbase's recorded table in the tests.
    body = {
        "amount": "50000.00",
        "give_currency": "RUB",
        "want_currency": "GEL",
        "rate_spec": market,
    }
    response = await client.post("/api/v1/quote", json=body, headers=nino)
    result = response.json()
    assert result["amount"] == "1592.86"
    assert {k: result["rate"][k] for k in ("base", "quote", "value", "source")} == {
        "base": "GEL",
        "quote": "RUB",
        "value": "31.39",
        "source": "coinbase",
    }
    assert result["rate"]["fetched_at"] is not None
    # Read «1 strong = so many weak», whichever side is given.
    other_way = await client.post(
        "/api/v1/quote",
        json={**body, "amount": "100.00", "give_currency": "GEL", "want_currency": "RUB"},
        headers=nino,
    )
    assert other_way.json()["amount"] == "3139.00"
    assert other_way.json()["rate"]["base"] == "GEL"


@pytest.mark.parametrize(
    "spec",
    [
        {"v": 1, "type": "reference", "source": "cbr"},
        {"v": 1, "type": "reference", "source": "coinbase", "markup_pct": "1"},
        {"v": 2, "type": "reference", "source": "coinbase"},
        {"type": "floating"},
        {"quotes": [{"base": "GEL", "quote": "RUB", "value": "29.20"}]},
    ],
)
async def test_a_rate_spec_of_no_known_kind_is_refused(
    client: AsyncClient, spec: dict[str, Any]
) -> None:
    alex = await person(client, ALEX)
    response = await client.post(
        "/api/v1/orders", json=draft(wants=[want("GEL", "GE", spec)]), headers=alex
    )
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


async def test_orders_are_numbered_from_one_sequence(client: AsyncClient) -> None:
    alex = await person(client, ALEX)
    first = await publish(client, alex)
    second = await publish(client, alex)
    # «№ 17» (QUESTIONS K8): every order its own, one after another.
    assert second["number"] == first["number"] + 1
    card = (await client.get(f"/api/v1/orders/{first['id']}", headers=alex)).json()
    assert card["number"] == first["number"]


async def test_each_wanted_currency_keeps_its_own_rate(client: AsyncClient) -> None:
    alex = await person(client, ALEX)
    order = await publish(
        client,
        alex,
        wants=[want("GEL", "GE", fixed("GEL", "RUB", "29.20")), want("USD", "GE")],
    )
    card = (await client.get(f"/api/v1/orders/{order['id']}", headers=alex)).json()
    assert [w["rate_spec"] for w in card["wants"]] == [fixed("GEL", "RUB", "29.20"), MARKET]


def test_today_is_in_the_authors_time_zone() -> None:
    # A day apart: it is always tomorrow on Kiritimati compared with Pago Pago.
    for tz in ("Pacific/Kiritimati", "Pacific/Pago_Pago", None):
        user: Any = SimpleNamespace(tz=tz)
        assert today(user) == datetime.now(ZoneInfo(tz or "UTC")).date()


async def test_the_assets_come_from_config(client: AsyncClient) -> None:
    alex = await person(client, ALEX)
    response = await client.get("/api/v1/assets", headers=alex)
    assert response.json() == ["RUB", "GEL", "USD", "EUR", "TRY", "KZT", "AMD", "USDT", "USDC"]
    assert (await client.get("/api/v1/assets")).status_code == 401
