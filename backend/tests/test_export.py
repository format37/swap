"""CSV export (FR-6.3, QUESTIONS K4): every deal someone took part in, sent by the bot.
Refusals first: no chat to send it to, and a second tap at once."""

import csv
import io

from aiogram import Bot
from aiogram.methods import SendDocument
from aiogram.types import BufferedInputFile
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from swap.config import Settings
from swap.models import Notification, NotificationStatus, User
from swap.worker.outbox import send_due
from tests.conftest import TEST_BOT_TOKEN
from tests.telegram import RecordingSession
from tests.test_deals import World
from tests.test_score import settle

Sessions = async_sessionmaker[AsyncSession]


async def test_without_a_chat_there_is_nothing_to_send_to(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    world = await World(client, sessionmaker).build()
    async with sessionmaker() as db:
        await db.execute(update(User).where(User.first_name == "Nino").values(can_message=False))
        await db.commit()
    refused = await client.post("/api/v1/me/export", headers=world.nino)
    assert refused.status_code == 409
    assert refused.json()["code"] == "export.no_chat"
    assert (await client.post("/api/v1/me/export")).status_code == 401


async def test_a_second_tap_at_once_sends_nothing_more(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    world = await World(client, sessionmaker).build()
    assert (await client.post("/api/v1/me/export", headers=world.nino)).status_code == 202
    again = await client.post("/api/v1/me/export", headers=world.nino)
    assert again.status_code == 429
    assert again.json()["code"] == "export.too_soon"


async def test_the_bot_sends_every_deal_as_csv_in_the_recipients_words(
    client: AsyncClient, sessionmaker: Sessions, settings: Settings
) -> None:
    world = await World(client, sessionmaker).build()
    await settle(world, world.nino)
    declined = await world.propose()
    await world.ok(world.alex, declined, "decline")
    # Switching messages off doesn't silence what was asked for.
    await client.patch("/api/v1/me", json={"notifications_off": True}, headers=world.nino)
    assert (await client.post("/api/v1/me/export", headers=world.nino)).status_code == 202
    async with sessionmaker() as db:
        # The deals' own messages are out of the way: only the export is due.
        await db.execute(
            update(Notification)
            .where(Notification.type != "export.deals")
            .values(tg_status=NotificationStatus.SENT)
        )
        await db.commit()
    telegram = RecordingSession()
    await send_due(sessionmaker, Bot(TEST_BOT_TOKEN, session=telegram), settings)

    [sent] = telegram.calls
    assert isinstance(sent, SendDocument)
    assert isinstance(sent.document, BufferedInputFile)
    assert sent.document.filename.startswith("swap-deals-")
    assert sent.caption is not None
    assert sent.caption.startswith("Ваши сделки в Swap: 2.")
    data = sent.document.data
    # A byte-order mark, so Excel reads it as UTF-8.
    assert data.startswith(b"\xef\xbb\xbf")
    rows = list(csv.reader(io.StringIO(data.decode("utf-8-sig"))))
    assert rows[0][:6] == ["Предложена", "Принята", "Закрыта", "Заявка №", "Статус", "С кем"]
    settled, declined_row = rows[1], rows[2]
    assert settled[3:6] == [str(world.order["number"]), "завершена", "Alex (@format37)"]
    # Nino paid 342,47 GEL in cash and got 10 000 RUB by bank, at the author's 29,20.
    assert settled[6:14] == ["342.47", "GEL", "GE", "наличные", "10000.00", "RUB", "RU", "банк"]
    assert settled[14:] == ["1 GEL = 29.2 RUB", "курс автора заявки"]
    assert declined_row[4] == "отменена"
    async with sessionmaker() as db:
        note = await db.scalar(select(Notification).where(Notification.type == "export.deals"))
    assert note is not None
    assert note.tg_status == NotificationStatus.SENT
