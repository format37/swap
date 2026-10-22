"""Deleting for oneself, and erasing once all have (QUESTIONS J3, ADR-0030). Refusals
first: a stranger, the wrong side, and anything still running.

Nino proposes on Alex's order, as in tests/test_deals.py; Gio is a stranger to both.
"""

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from swap.deeplinks import target
from swap.models import Deal, DealLeg, Event, Notification, Order
from tests.test_deals import World
from tests.test_score import score, settle

Sessions = async_sessionmaker[AsyncSession]


async def delete_deal(world: World, headers: dict[str, str], deal: dict[str, Any]) -> Any:
    return await world.client.delete(f"/api/v1/deals/{deal['id']}", headers=headers)


async def delete_order(world: World) -> Any:
    order = f"/api/v1/orders/{world.order['id']}"
    await world.client.post(f"{order}/close", headers=world.alex)
    return await world.client.delete(order, headers=world.alex)


async def delete_mine(world: World, headers: dict[str, str]) -> Any:
    """«Удалить у себя» on Alex's order, by someone who isn't its author (QUESTIONS L4)."""
    return await world.client.delete(f"/api/v1/orders/{world.order['id']}", headers=headers)


async def rows(sessions: Sessions, deal: dict[str, Any]) -> dict[str, int]:
    """What the server still holds of a deal and its order."""
    deal_id = uuid.UUID(deal["id"])
    async with sessions() as db:
        order_id = await db.scalar(select(Deal.order_id).where(Deal.id == deal_id))

        async def count(model: Any, *where: Any) -> int:
            return int(await db.scalar(select(func.count()).select_from(model).where(*where)) or 0)

        return {
            "deal": await count(Deal, Deal.id == deal_id),
            "legs": await count(DealLeg, DealLeg.deal_id == deal_id),
            "journal": await count(Event, Event.deal_id == deal_id),
            "messages": await count(Notification, Notification.target == target("deal", deal_id)),
            "order": 0 if order_id is None else await count(Order, Order.id == order_id),
        }


@pytest.fixture
async def world(client: AsyncClient, sessionmaker: Sessions) -> World:
    return await World(client, sessionmaker).build()


def seen(response: Any) -> bool:
    assert response.status_code in (200, 404), response.text
    return bool(response.status_code == 200)


# --- refused ---------------------------------------------------------------------------


async def test_a_stranger_cannot_delete_a_deal(world: World) -> None:
    deal = await settle(world, world.nino)
    response = await delete_deal(world, world.gio, deal)
    assert response.status_code == 404
    assert response.json()["code"] == "deal.not_found"


async def test_the_author_deletes_the_whole_order_not_a_deal(world: World) -> None:
    deal = await settle(world, world.nino)
    response = await delete_deal(world, world.alex, deal)
    assert response.status_code == 409
    assert response.json()["code"] == "deal.delete_with_order"


@pytest.mark.parametrize("stage", ["proposed", "accepted"])
async def test_a_running_deal_cannot_be_deleted(world: World, stage: str) -> None:
    deal = await world.propose()
    if stage == "accepted":
        await world.ok(world.alex, deal, "accept")
    response = await delete_deal(world, world.nino, deal)
    assert response.status_code == 409
    assert response.json()["code"] == "deal.running"


async def test_an_open_order_or_one_with_a_running_deal_cannot_be_deleted(world: World) -> None:
    order = f"/api/v1/orders/{world.order['id']}"
    still_open = await world.client.delete(order, headers=world.alex)
    assert still_open.json()["code"] == "order.open"
    deal = await world.propose()
    await world.ok(world.alex, deal, "accept")
    running = await delete_order(world)
    assert running.status_code == 409
    assert running.json()["code"] == "order.deals_running"


async def test_nobody_without_a_deal_on_it_deletes_someone_elses_order(world: World) -> None:
    # Nino may see the open order, and Gio may not: both get the same answer.
    for headers in (world.nino, world.gio):
        response = await delete_mine(world, headers)
        assert response.status_code == 404
        assert response.json()["code"] == "order.not_found"


async def test_a_participant_keeps_the_order_while_any_of_their_deals_runs(
    world: World, sessionmaker: Sessions
) -> None:
    settled = await settle(world, world.nino)
    running = await world.propose(world.nino)
    await world.ok(world.alex, running, "accept")
    response = await delete_mine(world, world.nino)
    assert response.status_code == 409
    assert response.json()["code"] == "deal.running"
    # Nothing was deleted, the finished deal included.
    assert seen(await world.client.get(f"/api/v1/deals/{settled['id']}", headers=world.nino))


# --- allowed ---------------------------------------------------------------------------


async def test_a_deleted_deal_is_gone_for_its_deleter_alone(
    world: World, sessionmaker: Sessions
) -> None:
    deal = await settle(world, world.nino)
    assert (await delete_deal(world, world.nino, deal)).status_code == 204
    path = f"/api/v1/deals/{deal['id']}"
    assert not seen(await world.client.get(path, headers=world.nino))
    listed = (await world.client.get("/api/v1/deals?scope=all", headers=world.nino)).json()
    assert listed == []
    # Deleted is deleted: nothing more can be done with it, by its deleter.
    assert (await delete_deal(world, world.nino, deal)).status_code == 404
    # The other side keeps it whole, journal and all.
    kept = (await world.client.get(path, headers=world.alex)).json()
    assert kept["status"] == "settled"
    assert len(kept["events"]) == 4
    assert (await rows(sessionmaker, deal))["deal"] == 1


async def test_the_author_deletes_the_order_and_its_deals_for_themselves(
    world: World, sessionmaker: Sessions
) -> None:
    deal = await settle(world, world.nino)
    assert (await delete_order(world)).status_code == 204
    order = f"/api/v1/orders/{world.order['id']}"
    assert not seen(await world.client.get(order, headers=world.alex))
    assert not seen(await world.client.get(f"/api/v1/deals/{deal['id']}", headers=world.alex))
    history = await world.client.get("/api/v1/orders?scope=history", headers=world.alex)
    assert history.json() == []
    # Whoever dealt on it keeps the deal, and the order with it (QUESTIONS J3).
    assert seen(await world.client.get(order, headers=world.nino))
    assert seen(await world.client.get(f"/api/v1/deals/{deal['id']}", headers=world.nino))
    theirs = await world.client.get("/api/v1/orders?scope=history", headers=world.nino)
    assert [found["id"] for found in theirs.json()] == [world.order["id"]]
    assert await rows(sessionmaker, deal) == {
        "deal": 1,
        "legs": 2,
        "journal": 4,
        "messages": 4,
        "order": 1,
    }


@pytest.mark.parametrize("first", ["proposer", "author"])
async def test_once_both_sides_have_deleted_the_deal_is_erased(
    world: World, sessionmaker: Sessions, first: str
) -> None:
    deal = await settle(world, world.nino)
    assert await score(world.client, world.nino) == 1
    if first == "proposer":
        assert (await delete_deal(world, world.nino, deal)).status_code == 204
        assert (await rows(sessionmaker, deal))["deal"] == 1
        assert (await delete_order(world)).status_code == 204
    else:
        assert (await delete_order(world)).status_code == 204
        assert (await rows(sessionmaker, deal))["deal"] == 1
        assert (await delete_deal(world, world.nino, deal)).status_code == 204
    # Legs, journal lines and messages go with it, and the order with its last deal.
    assert await rows(sessionmaker, deal) == {
        "deal": 0,
        "legs": 0,
        "journal": 0,
        "messages": 0,
        "order": 0,
    }
    # Its point goes too (ADR-0029).
    assert await score(world.client, world.nino) == 0


async def test_an_order_stays_while_any_of_its_deals_does(
    world: World, sessionmaker: Sessions
) -> None:
    gone = await settle(world, world.nino)
    kept = await settle(world, world.nino)
    await delete_deal(world, world.nino, gone)
    assert (await delete_order(world)).status_code == 204
    assert (await rows(sessionmaker, gone))["deal"] == 0
    left = await rows(sessionmaker, kept)
    assert left["deal"] == 1
    assert left["order"] == 1
    # The last deal deleted takes the order with it.
    await delete_deal(world, world.nino, kept)
    assert await rows(sessionmaker, kept) == {
        "deal": 0,
        "legs": 0,
        "journal": 0,
        "messages": 0,
        "order": 0,
    }


async def test_a_participant_deletes_all_their_deals_on_an_order_at_once(
    world: World, sessionmaker: Sessions
) -> None:
    first = await settle(world, world.nino)
    second = await settle(world, world.nino)
    order = f"/api/v1/orders/{world.order['id']}"
    await world.client.post(f"{order}/close", headers=world.alex)
    assert (await delete_mine(world, world.nino)).status_code == 204
    # Gone from their history and their deals, as if they had deleted each (QUESTIONS L4).
    assert not seen(await world.client.get(order, headers=world.nino))
    history = await world.client.get("/api/v1/orders?scope=history", headers=world.nino)
    assert history.json() == []
    assert (await world.client.get("/api/v1/deals?scope=all", headers=world.nino)).json() == []
    # The author keeps the order and both deals.
    on_it = {"scope": "all", "order_id": world.order["id"]}
    kept = await world.client.get("/api/v1/deals", params=on_it, headers=world.alex)
    assert {deal["id"] for deal in kept.json()} == {first["id"], second["id"]}
    assert (await rows(sessionmaker, first))["deal"] == 1
    # Once the author deletes the order too, nothing of it is left.
    assert (await world.client.delete(order, headers=world.alex)).status_code == 204
    for deal in (first, second):
        assert await rows(sessionmaker, deal) == {
            "deal": 0,
            "legs": 0,
            "journal": 0,
            "messages": 0,
            "order": 0,
        }


async def test_after_the_author_deleted_the_order_a_participant_erases_it(
    world: World, sessionmaker: Sessions
) -> None:
    deal = await settle(world, world.nino)
    assert (await delete_order(world)).status_code == 204
    assert (await delete_mine(world, world.nino)).status_code == 204
    assert await rows(sessionmaker, deal) == {
        "deal": 0,
        "legs": 0,
        "journal": 0,
        "messages": 0,
        "order": 0,
    }
