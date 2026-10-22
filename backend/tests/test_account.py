"""Deleting all history, and the account (QUESTIONS K2, Q-B10). Refusals first: nothing
goes while a deal runs, and what still runs stays."""

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from swap.models import AuthSession, Deal, Invite, Link, Mute, Notification, User
from tests.test_auth import sign_in
from tests.test_deals import World
from tests.test_links import NINO
from tests.test_score import settle

Sessions = async_sessionmaker[AsyncSession]


@pytest.fixture
async def world(client: AsyncClient, sessionmaker: Sessions) -> World:
    return await World(client, sessionmaker).build()


async def count(sessions: Sessions, model: Any, *where: Any) -> int:
    async with sessions() as db:
        return int(await db.scalar(select(func.count()).select_from(model).where(*where)) or 0)


async def nino(sessions: Sessions) -> User:
    async with sessions() as db:
        found = await db.scalar(select(User).where(User.first_name == "Nino"))
    assert found is not None
    return found


# --- refused ---------------------------------------------------------------------------


@pytest.mark.parametrize("stage", ["accepted", "disputed"])
async def test_an_account_with_a_running_deal_stays(world: World, stage: str) -> None:
    deal = await world.propose()
    await world.ok(world.alex, deal, "accept")
    if stage == "disputed":
        await world.ok(world.nino, deal, "dispute", note="не пришло")
    for headers in (world.nino, world.alex):
        refused = await world.client.delete("/api/v1/me", headers=headers)
        assert refused.status_code == 409
        assert refused.json()["code"] == "account.deals_running"
    assert (await world.client.get("/api/v1/me", headers=world.nino)).status_code == 200


async def test_deleting_all_history_leaves_what_runs(world: World) -> None:
    done = await settle(world, world.nino)
    running = await world.propose()
    await world.ok(world.alex, running, "accept")
    deleted = await world.client.delete("/api/v1/me/history", headers=world.nino)
    assert deleted.status_code == 200, deleted.text
    assert deleted.json() == {"deals": 1, "orders": 0, "running": 1}
    mine = (await world.client.get("/api/v1/deals?scope=all", headers=world.nino)).json()
    assert [deal["id"] for deal in mine] == [running["id"]]
    # The author keeps both, and their open order can't go yet.
    theirs = (await world.client.get("/api/v1/deals?scope=all", headers=world.alex)).json()
    assert {deal["id"] for deal in theirs} == {done["id"], running["id"]}
    authors = (await world.client.delete("/api/v1/me/history", headers=world.alex)).json()
    assert authors == {"deals": 0, "orders": 0, "running": 2}


# --- allowed ---------------------------------------------------------------------------


async def test_deleting_all_history_erases_what_the_other_side_deleted(
    world: World, sessionmaker: Sessions
) -> None:
    deal = await settle(world, world.nino)
    await world.client.post(f"/api/v1/orders/{world.order['id']}/close", headers=world.alex)
    assert (await world.client.delete("/api/v1/me/history", headers=world.alex)).json() == {
        "deals": 0,
        "orders": 1,
        "running": 0,
    }
    assert await count(sessionmaker, Deal, Deal.id == uuid.UUID(deal["id"])) == 1
    assert (await world.client.delete("/api/v1/me/history", headers=world.nino)).json() == {
        "deals": 1,
        "orders": 0,
        "running": 0,
    }
    assert await count(sessionmaker, Deal, Deal.id == uuid.UUID(deal["id"])) == 0


async def test_a_deleted_account_is_scrubbed_and_starts_afresh(
    world: World, sessionmaker: Sessions
) -> None:
    deal = await settle(world, world.nino)
    pending = await world.propose()
    await world.client.put(f"/api/v1/links/{world.link}/mute", headers=world.nino)
    await world.client.post("/api/v1/links/invites", headers=world.nino)
    before = await nino(sessionmaker)

    gone = await world.client.delete("/api/v1/me", headers=world.nino)
    assert gone.status_code == 204, gone.text
    # Signed out: the session went with the account.
    assert (await world.client.get("/api/v1/me", headers=world.nino)).status_code == 401
    async with sessionmaker() as db:
        row = await db.get(User, before.id)
    assert row is not None
    assert (row.telegram_id, row.first_name, row.username, row.photo_url) == (None, "", None, None)
    assert row.deleted_at is not None
    for model, where in [
        (Link, (Link.user_lo_id == before.id) | (Link.user_hi_id == before.id)),
        (Invite, Invite.created_by == before.id),
        (AuthSession, AuthSession.user_id == before.id),
        (Mute, Mute.user_id == before.id),
        (Notification, Notification.recipient_id == before.id),
    ]:
        assert await count(sessionmaker, model, where) == 0, model.__name__
    # Their proposal was taken back; the settled deal stays with Alex, under no name.
    taken = (await world.client.get(f"/api/v1/deals/{pending['id']}", headers=world.alex)).json()
    assert taken["status"] == "cancelled"
    kept = (await world.client.get(f"/api/v1/deals/{deal['id']}", headers=world.alex)).json()
    assert kept["proposer"]["deleted"] is True
    assert kept["proposer"]["first_name"] == ""
    # The same Telegram account starting Swap again is someone new.
    again = await sign_in(world.client, user=NINO)
    assert again["me"]["id"] != str(before.id)
    assert again["me"]["score"] == 0
