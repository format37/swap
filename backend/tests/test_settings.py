"""Notification settings (QUESTIONS K1, FR-7.2): everything off, kinds off, and one
person's new orders muted. Refusals first: nobody mutes through someone else's link."""

import uuid
from typing import Any

import pytest
from aiogram import Bot
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from swap.config import Settings
from swap.i18n import MESSAGES
from swap.models import Notification, NotificationStatus, User
from swap.notifications import KIND_OF
from swap.worker.outbox import send_due
from tests.conftest import TEST_BOT_TOKEN
from tests.telegram import RecordingSession
from tests.test_links import ALEX, GIO, NINO, linked, person
from tests.test_orders import publish

Sessions = async_sessionmaker[AsyncSession]


async def told(sessions: Sessions, name: str, kind: str) -> int:
    async with sessions() as db:
        found = await db.scalars(
            select(Notification.id)
            .join(User, User.id == Notification.recipient_id)
            .where(User.first_name == name, Notification.type == kind)
        )
        return len(list(found))


# --- refused ---------------------------------------------------------------------------


async def test_nobody_mutes_through_someone_elses_link(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    gio = await person(client, GIO)
    await person(client, NINO)
    link_id = await linked(client, sessionmaker, alex, NINO)
    for method in ("PUT", "DELETE"):
        refused = await client.request(method, f"/api/v1/links/{link_id}/mute", headers=gio)
        assert refused.status_code == 404, method
        missing = await client.request(method, f"/api/v1/links/{uuid.uuid4()}/mute", headers=alex)
        assert missing.status_code == 404, method
    assert (await client.put(f"/api/v1/links/{link_id}/mute")).status_code == 401


@pytest.mark.parametrize(
    "body", [{"muted_kinds": ["pigeons"]}, {"muted_kinds": "orders"}, {"notifications_off": "x"}]
)
async def test_unknown_switches_are_refused(client: AsyncClient, body: dict[str, Any]) -> None:
    alex = await person(client, ALEX)
    response = await client.patch("/api/v1/me", json=body, headers=alex)
    assert response.status_code == 422


# --- allowed ---------------------------------------------------------------------------


async def test_the_switches_are_kept_and_said_back(client: AsyncClient) -> None:
    alex = await person(client, ALEX)
    me = (await client.get("/api/v1/me", headers=alex)).json()
    assert (me["notifications_off"], me["muted_kinds"]) == (False, [])
    body = {"notifications_off": True, "muted_kinds": ["orders", "transfers", "orders"]}
    changed = (await client.patch("/api/v1/me", json=body, headers=alex)).json()
    assert (changed["notifications_off"], changed["muted_kinds"]) == (True, ["orders", "transfers"])
    # Only what is sent changes.
    kept = (await client.patch("/api/v1/me", json={"tz": "Asia/Tbilisi"}, headers=alex)).json()
    assert kept["muted_kinds"] == ["orders", "transfers"]


async def test_a_muted_authors_new_orders_still_show_but_tell_nothing(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    link_id = await linked(client, sessionmaker, alex, NINO)
    muted = await client.put(f"/api/v1/links/{link_id}/mute", headers=nino)
    assert muted.status_code == 200, muted.text
    assert muted.json()["muted"] is True
    # Muting is one side's own: Alex's view of the link says nothing about it.
    theirs = (await client.get(f"/api/v1/links/{link_id}", headers=alex)).json()
    assert theirs["muted"] is False
    order = await publish(client, alex)
    assert await told(sessionmaker, "Nino", "order.opened") == 0
    feed = (await client.get("/api/v1/orders", headers=nino)).json()
    assert [found["id"] for found in feed] == [order["id"]]
    again = await client.delete(f"/api/v1/links/{link_id}/mute", headers=nino)
    assert again.json()["muted"] is False
    await publish(client, alex)
    assert await told(sessionmaker, "Nino", "order.opened") == 1


@pytest.mark.parametrize(
    ("settings_", "sent"),
    [
        ({}, {"order.opened", "deal.settled"}),
        ({"notifications_off": True}, set()),
        ({"muted_kinds": ["orders"]}, {"deal.settled"}),
        ({"muted_kinds": ["transfers", "links"]}, {"order.opened"}),
    ],
)
async def test_the_outbox_skips_what_its_recipient_switched_off(
    client: AsyncClient,
    sessionmaker: Sessions,
    settings: Settings,
    settings_: dict[str, Any],
    sent: set[str],
) -> None:
    nino = await person(client, NINO)
    if settings_:
        await client.patch("/api/v1/me", json=settings_, headers=nino)
    async with sessionmaker() as db:
        user = await db.scalar(select(User).where(User.first_name == "Nino"))
        assert user is not None
        await db.execute(update(User).where(User.id == user.id).values(can_message=True))
        for kind in ("order.opened", "deal.settled"):
            db.add(Notification(recipient_id=user.id, type=kind, params=PARAMS[kind]))
        await db.commit()
    telegram = RecordingSession()
    await send_due(sessionmaker, Bot(TEST_BOT_TOKEN, session=telegram), settings)
    async with sessionmaker() as db:
        rows = list(await db.execute(select(Notification.type, Notification.tg_status)))
    assert {kind for kind, status in rows if status == NotificationStatus.SENT} == sent
    skipped = {kind for kind, status in rows if status == NotificationStatus.SKIPPED}
    assert skipped == {"order.opened", "deal.settled"} - sent


PARAMS = {
    "order.opened": {"name": "Alex", "amount": "1000.00", "currency": "RUB", "wants": "GEL"},
    "deal.settled": {"name": "Alex", "amount": "1000.00", "currency": "RUB"},
}


def test_every_message_answers_to_a_switch() -> None:
    sent_by_the_outbox = {key for key in MESSAGES["en"] if "." in key} - {
        key for key in MESSAGES["en"] if key.split(".")[0] in ("start", "button", "invite", "bot")
    }
    assert sent_by_the_outbox == set(KIND_OF)
