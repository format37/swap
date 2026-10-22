"""Signing in and /me. Refusals first (kickoff rule 6)."""

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote, urlencode

from httpx import AsyncClient
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from swap.init_data import sign
from swap.models import AuthSession, User
from swap.sessions import hash_token
from tests.conftest import TEST_BOT_TOKEN

Sessions = async_sessionmaker[AsyncSession]


def launch(
    user: dict[str, Any] | None = None,
    *,
    age: timedelta = timedelta(0),
    token: str = TEST_BOT_TOKEN,
) -> str:
    """initData as Telegram would hand it to the Mini App."""
    profile = {
        "id": 1001,
        "first_name": "Alex",
        "username": "format37",
        "language_code": "ru",
        "allows_write_to_pm": True,
        **(user or {}),
    }
    fields = {
        "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
        "user": json.dumps(profile, ensure_ascii=False),
        "auth_date": str(int((datetime.now(UTC) - age).timestamp())),
    }
    return urlencode({**fields, "hash": sign(fields, token)}, quote_via=quote)


async def sign_in(client: AsyncClient, **kwargs: Any) -> dict[str, Any]:
    response = await client.post("/api/v1/auth/telegram", json={"init_data": launch(**kwargs)})
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def bearer(signed_in: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {signed_in['token']}"}


# --- refused ---------------------------------------------------------------------


async def test_me_needs_a_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/me")
    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


async def test_an_unknown_token_is_refused(client: AsyncClient) -> None:
    response = await client.get("/api/v1/me", headers={"Authorization": "Bearer not-a-session"})
    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


async def test_an_expired_session_is_refused(client: AsyncClient, sessionmaker: Sessions) -> None:
    signed_in = await sign_in(client)
    async with sessionmaker() as db:
        await db.execute(
            update(AuthSession).values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )
        await db.commit()
    assert (await client.get("/api/v1/me", headers=bearer(signed_in))).status_code == 401


async def test_forged_init_data_signs_nobody_in(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    forged = launch(token="987654321:" + "O" * 35)
    response = await client.post("/api/v1/auth/telegram", json={"init_data": forged})
    assert response.status_code == 401
    assert response.json()["code"] == "init_data_bad_signature"
    async with sessionmaker() as db:
        assert await db.scalar(select(func.count()).select_from(User)) == 0


async def test_stale_init_data_has_its_own_code(client: AsyncClient) -> None:
    stale = launch(age=timedelta(hours=2))
    response = await client.post("/api/v1/auth/telegram", json={"init_data": stale})
    assert response.status_code == 401
    # The UI tells the user to reopen the app for this one, not that something broke.
    assert response.json()["code"] == "init_data_expired"


async def test_an_empty_body_is_a_validation_problem(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/telegram", json={})
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


async def test_an_unknown_time_zone_is_refused(client: AsyncClient) -> None:
    signed_in = await sign_in(client)
    response = await client.patch(
        "/api/v1/me", json={"tz": "Mars/Olympus_Mons"}, headers=bearer(signed_in)
    )
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


async def test_an_unknown_locale_is_refused(client: AsyncClient) -> None:
    signed_in = await sign_in(client)
    response = await client.patch("/api/v1/me", json={"locale": "de"}, headers=bearer(signed_in))
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


# --- accepted --------------------------------------------------------------------


async def test_signing_in_creates_the_user_and_a_session(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    signed_in = await sign_in(client)
    assert signed_in["me"]["first_name"] == "Alex"
    assert signed_in["me"]["username"] == "format37"
    assert signed_in["me"]["locale"] == "ru"
    assert signed_in["me"]["locale_chosen"] is False

    async with sessionmaker() as db:
        user = await db.scalar(select(User).where(User.telegram_id == 1001))
        session = await db.scalar(select(AuthSession))
    assert user is not None
    assert user.can_message is True
    assert session is not None
    # The token itself is never stored, only its hash.
    assert session.token_hash == hash_token(signed_in["token"])

    me = await client.get("/api/v1/me", headers=bearer(signed_in))
    assert me.status_code == 200
    assert me.json() == signed_in["me"]


async def test_signing_in_again_refreshes_the_profile(client: AsyncClient) -> None:
    await sign_in(client)
    again = await sign_in(
        client, user={"first_name": "Alexey", "username": None, "language_code": "ka"}
    )
    assert again["me"]["first_name"] == "Alexey"
    assert again["me"]["username"] is None
    assert again["me"]["locale"] == "ka"


async def test_each_sign_in_brings_the_photo_link_of_its_launch(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    photo = "https://t.me/i/userpic/320/abc.jpg"
    first = await sign_in(client, user={"photo_url": photo})
    assert first["me"]["photo_url"] == photo
    # A launch without one means the photo is gone, or hidden now (ADR-0027).
    again = await sign_in(client)
    assert again["me"]["photo_url"] is None
    async with sessionmaker() as db:
        user = await db.scalar(select(User).where(User.telegram_id == 1001))
    assert user is not None
    assert user.photo_url is None


async def test_a_username_moves_to_its_new_owner(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    await sign_in(client, user={"id": 1, "username": "Swapper"})
    await sign_in(client, user={"id": 2, "username": "swapper"})
    async with sessionmaker() as db:
        rows = dict((await db.execute(select(User.telegram_id, User.username))).all())
    assert rows == {1: None, 2: "swapper"}


async def test_the_chosen_language_sticks(client: AsyncClient) -> None:
    signed_in = await sign_in(client)  # Telegram says ru
    response = await client.patch("/api/v1/me", json={"locale": "ka"}, headers=bearer(signed_in))
    assert response.status_code == 200
    assert response.json()["locale"] == "ka"
    assert response.json()["locale_chosen"] is True
    again = await sign_in(client)  # Telegram still says ru
    assert again["me"]["locale"] == "ka"


async def test_letting_the_choice_go_follows_telegram_again(client: AsyncClient) -> None:
    signed_in = await sign_in(client, user={"language_code": "en"})
    me = "/api/v1/me"
    await client.patch(me, json={"locale": "ru"}, headers=bearer(signed_in))
    # Sending something else leaves the choice alone (ADR-0039).
    kept = await client.patch(me, json={"tz": "Asia/Tbilisi"}, headers=bearer(signed_in))
    assert (kept.json()["locale"], kept.json()["locale_chosen"]) == ("ru", True)
    assert kept.json()["telegram_locale"] == "en"
    response = await client.patch(me, json={"locale": None}, headers=bearer(signed_in))
    assert response.status_code == 200
    assert (response.json()["locale"], response.json()["locale_chosen"]) == ("en", False)
    again = await sign_in(client, user={"language_code": "ka"})
    assert (again["me"]["locale"], again["me"]["telegram_locale"]) == ("ka", "ka")


async def test_other_languages_fall_back_to_english(client: AsyncClient) -> None:
    signed_in = await sign_in(client, user={"language_code": "pt-br"})
    assert signed_in["me"]["locale"] == "en"


async def test_the_device_time_zone_is_kept_and_the_language_left_alone(
    client: AsyncClient,
) -> None:
    signed_in = await sign_in(client)
    assert signed_in["me"]["tz"] is None
    response = await client.patch(
        "/api/v1/me", json={"tz": "Asia/Tbilisi"}, headers=bearer(signed_in)
    )
    assert response.status_code == 200
    assert response.json()["tz"] == "Asia/Tbilisi"
    assert response.json()["locale_chosen"] is False
