"""Saved payment details (ADR-0010). Refusals first: nobody but their owner reads or deletes
them, and the database and the logs never hold their text (ADR-0004)."""

import logging
import uuid
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from swap.api.app import create_app
from swap.config import Settings
from swap.payment_methods import MAX_SAVED
from tests.test_links import ALEX, NINO, person

Sessions = async_sessionmaker[AsyncSession]
SECRET_TEXT = "TBC Bank, IBAN GE29TB7777777777777777, Нино Б."


def card(**changes: Any) -> dict[str, Any]:
    return {"asset": "GEL", "kind": "bank", "title": "TBC", "text": SECRET_TEXT, **changes}


async def save(client: AsyncClient, headers: dict[str, str], **changes: Any) -> dict[str, Any]:
    response = await client.post("/api/v1/payment-methods", json=card(**changes), headers=headers)
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


# --- refused ---------------------------------------------------------------------------


async def test_every_endpoint_needs_a_session(client: AsyncClient) -> None:
    for method, path in [
        ("GET", "/api/v1/payment-methods"),
        ("POST", "/api/v1/payment-methods"),
        ("DELETE", f"/api/v1/payment-methods/{uuid.uuid4()}"),
    ]:
        assert (await client.request(method, path)).status_code == 401, (method, path)


async def test_nobody_else_lists_or_deletes_them(client: AsyncClient) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    saved = await save(client, nino)
    assert (await client.get("/api/v1/payment-methods", headers=alex)).json() == []
    response = await client.delete(f"/api/v1/payment-methods/{saved['id']}", headers=alex)
    assert response.status_code == 404
    assert response.json()["code"] == "payment.not_found"
    assert len((await client.get("/api/v1/payment-methods", headers=nino)).json()) == 1


async def test_the_database_holds_ciphertext_only(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    nino = await person(client, NINO)
    await save(client, nino)
    async with sessionmaker() as db:
        stored = await db.scalar(text("SELECT details::text FROM payment_methods"))
    assert stored is not None
    for fragment in ("GE29TB7777", "TBC Bank", "Нино"):
        assert fragment not in stored
    assert "•••• 7777" in stored


async def test_no_log_line_holds_the_text(
    client: AsyncClient, caplog: pytest.LogCaptureFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    caplog.set_level(logging.DEBUG)
    nino = await person(client, NINO)
    saved = await save(client, nino)
    await client.get("/api/v1/payment-methods", headers=nino)
    await client.delete(f"/api/v1/payment-methods/{saved['id']}", headers=nino)
    logged = caplog.text + capsys.readouterr().err
    assert "GE29TB7777" not in logged


async def test_without_keys_nothing_is_saved(settings: Settings, sessionmaker: Sessions) -> None:
    keyless = settings.model_copy(update={"recipient_keys": None})
    app = create_app(keyless, sessionmaker=sessionmaker)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        nino = await person(client, NINO)
        response = await client.post("/api/v1/payment-methods", json=card(), headers=nino)
    assert response.status_code == 503
    assert response.json()["code"] == "payment.unavailable"


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"asset": "XYZ"}, "payment.unknown_asset"),
        ({"kind": "bank", "text": "  "}, "payment.text_required"),
        ({"kind": "card"}, "validation_error"),
        ({"kind": "crypto", "text": ""}, "payment.text_required"),
        ({"title": "  "}, "validation_error"),
        ({"title": "x" * 61}, "validation_error"),
        ({"text": "x" * 501}, "validation_error"),
        ({"kind": "pigeon"}, "validation_error"),
        ({"extra": 1}, "validation_error"),
    ],
)
async def test_a_malformed_entry_is_refused(
    client: AsyncClient, changes: dict[str, Any], code: str
) -> None:
    nino = await person(client, NINO)
    response = await client.post("/api/v1/payment-methods", json=card(**changes), headers=nino)
    assert response.status_code == 422, response.text
    assert response.json()["code"] == code


async def test_entries_are_capped(client: AsyncClient) -> None:
    nino = await person(client, NINO)
    for _ in range(MAX_SAVED):
        await save(client, nino, kind="cash", text="")
    response = await client.post("/api/v1/payment-methods", json=card(), headers=nino)
    assert response.status_code == 429
    assert response.json()["code"] == "payment.limit"


# --- allowed -----------------------------------------------------------------------------


async def test_the_owner_reads_their_own_in_full(client: AsyncClient) -> None:
    nino = await person(client, NINO)
    saved = await save(client, nino, title="  TBC  ")
    assert saved["title"] == "TBC"
    assert saved["details"] == {"masked": "•••• 7777", "full": SECRET_TEXT}
    [listed] = (await client.get("/api/v1/payment-methods", headers=nino)).json()
    assert listed == saved


async def test_cash_needs_no_text(client: AsyncClient) -> None:
    nino = await person(client, NINO)
    saved = await save(client, nino, kind="cash", title="Наличные", text="")
    assert saved["details"] is None
    noted = await save(client, nino, kind="cash", title="Наличные", text="У метро Руставели")
    assert noted["details"] == {"masked": "•••", "full": "У метро Руставели"}


async def test_deleting_is_for_real(client: AsyncClient, sessionmaker: Sessions) -> None:
    nino = await person(client, NINO)
    saved = await save(client, nino)
    response = await client.delete(f"/api/v1/payment-methods/{saved['id']}", headers=nino)
    assert response.status_code == 204
    async with sessionmaker() as db:
        assert await db.scalar(text("SELECT count(*) FROM payment_methods")) == 0
