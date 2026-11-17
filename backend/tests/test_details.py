"""Payment details (QUESTIONS Q1, ADR-0043): where a payee takes a transfer, sealed, and
seen by the deal's two sides alone. Refusals first: nobody but the payee writes them, and
nobody outside the deal, nor anyone who merely sees the order, reads them."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from swap.crypto import seal_details
from swap.errors import DomainError
from swap.models import DealLeg, Order, OrderWant
from swap.repeats import repeat_due
from tests.test_deals import World, settle
from tests.test_links import Headers
from tests.test_orders import fixed, want

Sessions = async_sessionmaker[AsyncSession]

ALEX_GEL = "TBC 4276 1234 5678 9012, Alex"
NINO_RUB = "Сбер 2202 2003 4005 6007, Нино Б."


@pytest.fixture
async def world(client: AsyncClient, sessionmaker: Sessions) -> World:
    """Alex's order takes GEL to his TBC card, or USD with no details."""
    return await World(client, sessionmaker).build(
        wants=[
            {**want("GEL", "GE", fixed("GEL", "RUB", "29.20")), "details": ALEX_GEL},
            want("USD", "GE", fixed("USD", "RUB", "81.50"), ways=("bank",)),
        ]
    )


async def put(world: World, headers: Headers, deal: dict[str, Any], seq: int, text: Any) -> Any:
    return await world.client.put(
        f"/api/v1/deals/{deal['id']}/legs/{seq}/details", json={"details": text}, headers=headers
    )


async def legs(world: World, headers: Headers, deal: dict[str, Any]) -> dict[int, str | None]:
    shown = await world.client.get(f"/api/v1/deals/{deal['id']}", headers=headers)
    assert shown.status_code == 200
    return {leg["seq"]: leg["details"] for leg in shown.json()["legs"]}


# --- refused ---------------------------------------------------------------------------


async def test_nobody_outside_the_deal_writes_details(world: World) -> None:
    deal = await world.propose()
    refused = await put(world, world.gio, deal, 2, "моя карта")
    assert (refused.status_code, refused.json()["code"]) == (404, "deal.not_found")


async def test_only_the_payee_writes_a_legs_details(world: World) -> None:
    # Leg 1 is Nino's GEL to Alex: hers to pay, so not hers to say where.
    deal = await world.propose()
    refused = await put(world, world.nino, deal, 1, "куда угодно")
    assert (refused.status_code, refused.json()["code"]) == (403, "deal.not_your_move")
    refused = await put(world, world.alex, deal, 2, "куда угодно")
    assert (refused.status_code, refused.json()["code"]) == (403, "deal.not_your_move")


async def test_details_are_fixed_once_sent_and_once_the_deal_is_over(world: World) -> None:
    deal = await world.propose()
    await world.ok(world.alex, deal, "accept")
    await world.ok(world.nino, deal, "legs/1/sent")
    refused = await put(world, world.alex, deal, 1, "другая карта")
    assert (refused.status_code, refused.json()["code"]) == (409, "deal.invalid_transition")
    await settle_rest(world, deal)
    refused = await put(world, world.nino, deal, 2, "другая карта")
    assert (refused.status_code, refused.json()["code"]) == (409, "deal.invalid_transition")


async def settle_rest(world: World, deal: dict[str, Any]) -> None:
    await world.ok(world.alex, deal, "legs/1/received")
    await world.ok(world.alex, deal, "legs/2/sent")
    await world.ok(world.nino, deal, "legs/2/received")


async def test_whoever_sees_the_order_doesnt_see_its_details(world: World) -> None:
    order_id = world.order["id"]
    card = (await world.client.get(f"/api/v1/orders/{order_id}", headers=world.nino)).json()
    assert [w["details"] for w in card["wants"]] == [None, None]
    feed = (await world.client.get("/api/v1/orders", headers=world.nino)).json()
    assert [w["details"] for order in feed for w in order["wants"]] == [None, None]
    # Nor a proposer, until the author accepts.
    deal = await world.propose()
    assert await legs(world, world.nino, deal) == {1: None, 2: None}


def test_without_a_key_details_are_refused_not_dropped() -> None:
    with pytest.raises(DomainError) as refused:
        seal_details(None, uuid.uuid4(), ALEX_GEL)
    assert (refused.value.status, refused.value.code) == (503, "details.off")
    # Nothing to seal needs no key.
    assert seal_details(None, uuid.uuid4(), "   ") is None


# --- allowed ---------------------------------------------------------------------------


async def test_an_orders_details_are_its_authors_and_stored_sealed(world: World) -> None:
    order_id = world.order["id"]
    assert [w["details"] for w in world.order["wants"]] == [ALEX_GEL, None]
    card = (await world.client.get(f"/api/v1/orders/{order_id}", headers=world.alex)).json()
    assert [w["details"] for w in card["wants"]] == [ALEX_GEL, None]
    async with world.sessions() as db:
        stored = await db.scalar(
            select(OrderWant.details).where(
                OrderWant.order_id == uuid.UUID(order_id), OrderWant.currency == "GEL"
            )
        )
    assert stored is not None
    assert "4276" not in str(stored)
    assert "TBC" not in str(stored)
    assert stored["mask"] == "•••• 9012"


async def test_accepting_puts_the_authors_details_on_his_leg(world: World) -> None:
    deal = await world.propose()
    await world.ok(world.alex, deal, "accept")
    # Leg 1 pays Alex GEL: his card, for both sides to read.
    for headers in (world.alex, world.nino):
        assert await legs(world, headers, deal) == {1: ALEX_GEL, 2: None}
    # A deal in USD finds none, since that currency has none.
    usd = await world.propose(want_currency="USD", amount="10000.00", counter_method="bank")
    await world.ok(world.alex, usd, "accept")
    assert await legs(world, world.nino, usd) == {1: None, 2: None}


async def test_the_payee_writes_changes_and_clears_their_details(world: World) -> None:
    deal = await world.propose()
    # Nino says where Alex should send her RUB, even before he accepts.
    shown = await put(world, world.nino, deal, 2, f"  {NINO_RUB}  ")
    assert shown.status_code == 200
    assert {leg["seq"]: leg["details"] for leg in shown.json()["legs"]} == {1: None, 2: NINO_RUB}
    await world.ok(world.alex, deal, "accept")
    assert await legs(world, world.alex, deal) == {1: ALEX_GEL, 2: NINO_RUB}
    # Alex corrects his own, then Nino clears hers.
    assert (await put(world, world.alex, deal, 1, "BoG 1111 2222 3333 4444")).status_code == 200
    assert (await put(world, world.nino, deal, 2, "")).status_code == 200
    assert await legs(world, world.nino, deal) == {1: "BoG 1111 2222 3333 4444", 2: None}
    async with world.sessions() as db:
        stored = list(await db.scalars(select(DealLeg.details).where(DealLeg.details.is_not(None))))
    assert stored
    assert all("1111" not in str(sealed) for sealed in stored)


async def test_details_stay_once_the_deal_is_settled(world: World) -> None:
    deal = await world.propose()
    await put(world, world.nino, deal, 2, NINO_RUB)
    await world.ok(world.alex, deal, "accept")
    await settle(world, deal)
    assert await legs(world, world.alex, deal) == {1: ALEX_GEL, 2: NINO_RUB}


async def test_deleting_an_account_takes_its_details_with_it(world: World) -> None:
    deal = await world.propose()
    await put(world, world.nino, deal, 2, NINO_RUB)
    await world.ok(world.alex, deal, "accept")
    await settle(world, deal)
    assert (await world.client.delete("/api/v1/me", headers=world.nino)).status_code == 204
    # Alex keeps the deal, without her card number.
    assert await legs(world, world.alex, deal) == {1: ALEX_GEL, 2: None}
    assert (await world.client.delete("/api/v1/me", headers=world.alex)).status_code == 204
    async with world.sessions() as db:
        left = list(
            await db.scalars(select(OrderWant.details).where(OrderWant.details.is_not(None)))
        )
        left += list(await db.scalars(select(DealLeg.details).where(DealLeg.details.is_not(None))))
    assert left == []


async def test_a_monthly_copy_keeps_its_details(
    client: AsyncClient, sessionmaker: Sessions, settings: Any
) -> None:
    world = await World(client, sessionmaker).build(
        wants=[{**want("GEL", "GE", fixed("GEL", "RUB", "29.20")), "details": ALEX_GEL}],
        repeat_day=5,
    )
    first = datetime.now(UTC).date().replace(day=1) + timedelta(days=32)
    async with sessionmaker() as db:
        assert (
            await repeat_due(
                db, settings.assets, datetime(first.year, first.month, 5, 12, tzinfo=UTC)
            )
            == 1
        )
        await db.commit()
        copy = await db.scalar(
            select(Order)
            .where(Order.id != uuid.UUID(world.order["id"]))
            .order_by(Order.number.desc())
        )
    assert copy is not None
    card = (await world.client.get(f"/api/v1/orders/{copy.id}", headers=world.alex)).json()
    assert [w["details"] for w in card["wants"]] == [ALEX_GEL]
