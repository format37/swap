"""Links and invites (ADR-0012). Refusals first: outside a pair, nobody sees or changes it."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from swap.links import MAX_OUTSTANDING_INVITES, Opened, OpenedInvite, open_invite
from swap.models import Invite, Link, LinkStatus, Notification, User
from swap.sessions import hash_token
from tests.test_auth import bearer, sign_in

Sessions = async_sessionmaker[AsyncSession]
Headers = dict[str, str]

ALEX = {"id": 1001, "first_name": "Alex", "username": "format37"}
NINO = {"id": 2002, "first_name": "Nino", "last_name": "B", "username": "nino"}
GIO = {"id": 3003, "first_name": "Gio", "username": "gio"}


async def person(client: AsyncClient, profile: dict[str, Any]) -> Headers:
    return bearer(await sign_in(client, user=profile))


async def invite(client: AsyncClient, headers: Headers) -> str:
    """A new invite's token, read from its link the way the invitee's Telegram would."""
    response = await client.post("/api/v1/links/invites", headers=headers)
    assert response.status_code == 201, response.text
    url: str = response.json()["url"]
    prefix = "https://t.me/peertopeerswapbot?start=inv_"
    assert url.startswith(prefix)
    return url.removeprefix(prefix)


async def press_start(sessions: Sessions, profile: dict[str, Any], token: str) -> OpenedInvite:
    """What the bot does when `profile` presses /start inv_<token>."""
    async with sessions() as db:
        user = await db.scalar(select(User).where(User.telegram_id == profile["id"]))
        assert user is not None
        opened = await open_invite(db, user, token)
        await db.commit()
    return opened


async def requested(
    client: AsyncClient, sessions: Sessions, inviter: Headers, invitee: dict[str, Any]
) -> str:
    """The id of a pending request from `inviter` to `invitee`, made by an invite."""
    opened = await press_start(sessions, invitee, await invite(client, inviter))
    assert opened.outcome is Opened.REQUESTED
    assert opened.link is not None
    return str(opened.link.id)


async def linked(
    client: AsyncClient, sessions: Sessions, inviter: Headers, invitee: dict[str, Any]
) -> str:
    link_id = await requested(client, sessions, inviter, invitee)
    invitee_headers = await person(client, invitee)
    response = await client.post(f"/api/v1/links/{link_id}/accept", headers=invitee_headers)
    assert response.status_code == 200, response.text
    return link_id


async def ask_by_username(client: AsyncClient, headers: Headers, username: str) -> Any:
    return await client.post("/api/v1/links/requests", json={"username": username}, headers=headers)


async def told(sessions: Sessions) -> list[tuple[str, str, dict[str, str], str | None]]:
    """Every queued message: to whom (first name), its type, its words' values, its card."""
    async with sessions() as db:
        rows = await db.execute(
            select(User.first_name, Notification.type, Notification.params, Notification.target)
            .join(User, User.id == Notification.recipient_id)
            .order_by(Notification.created_at)
        )
        return [(name, type_, params, target) for name, type_, params, target in rows]


async def lists(client: AsyncClient, headers: Headers) -> dict[str, list[str]]:
    """Who sits in each list of the «Связи» tab, by first name, and how many invites."""
    response = await client.get("/api/v1/links", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    names = {
        key: [item["person"]["first_name"] for item in body[key]]
        for key in ("active", "incoming", "outgoing")
    }
    return {**names, "invites": [item["id"] for item in body["invites"]]}


# --- refused ---------------------------------------------------------------------


async def test_every_endpoint_needs_a_session(client: AsyncClient) -> None:
    some = uuid.uuid4()
    calls = [
        ("GET", "/api/v1/links"),
        ("POST", "/api/v1/links/invites"),
        ("DELETE", f"/api/v1/links/invites/{some}"),
        ("GET", f"/api/v1/links/{some}"),
        ("POST", f"/api/v1/links/{some}/accept"),
        ("POST", f"/api/v1/links/{some}/decline"),
        ("DELETE", f"/api/v1/links/{some}"),
        ("POST", "/api/v1/links/requests"),
    ]
    for method, path in calls:
        response = await client.request(method, path)
        assert response.status_code == 401, (method, path)
        assert response.json()["code"] == "unauthorized"


async def test_a_stranger_can_neither_see_nor_touch_a_pairs_link(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    await person(client, NINO)
    gio = await person(client, GIO)
    link_id = await requested(client, sessionmaker, alex, NINO)

    async def refused() -> None:
        for method, path in [
            ("GET", f"/api/v1/links/{link_id}"),
            ("POST", f"/api/v1/links/{link_id}/accept"),
            ("POST", f"/api/v1/links/{link_id}/decline"),
            ("DELETE", f"/api/v1/links/{link_id}"),
        ]:
            response = await client.request(method, path, headers=gio)
            # The same answer as for a link that doesn't exist.
            assert response.status_code == 404, (method, path)
            assert response.json()["code"] == "link.not_found"
        assert await lists(client, gio) == {
            "active": [],
            "incoming": [],
            "outgoing": [],
            "invites": [],
        }

    await refused()
    nino = await person(client, NINO)
    assert (await client.post(f"/api/v1/links/{link_id}/accept", headers=nino)).status_code == 200
    await refused()
    async with sessionmaker() as db:
        link = await db.get(Link, uuid.UUID(link_id))
    assert link is not None
    assert link.status == LinkStatus.ACTIVE


async def test_an_unknown_link_is_not_found(client: AsyncClient) -> None:
    alex = await person(client, ALEX)
    response = await client.get(f"/api/v1/links/{uuid.uuid4()}", headers=alex)
    assert response.status_code == 404
    assert response.json()["code"] == "link.not_found"


async def test_a_stranger_cannot_revoke_an_invite(client: AsyncClient) -> None:
    alex = await person(client, ALEX)
    gio = await person(client, GIO)
    await invite(client, alex)
    [invite_id] = (await lists(client, alex))["invites"]

    response = await client.delete(f"/api/v1/links/invites/{invite_id}", headers=gio)
    assert response.status_code == 404
    assert response.json()["code"] == "invite.not_found"
    assert (await lists(client, alex))["invites"] == [invite_id]


async def test_the_requester_cannot_answer_their_own_request(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    await person(client, NINO)
    link_id = await requested(client, sessionmaker, alex, NINO)
    for action in ("accept", "decline"):
        response = await client.post(f"/api/v1/links/{link_id}/{action}", headers=alex)
        assert response.status_code == 409, action
        assert response.json()["code"] == "link.invalid_state"


async def test_only_a_pending_request_can_be_answered(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    link_id = await linked(client, sessionmaker, alex, NINO)
    for action in ("accept", "decline"):
        response = await client.post(f"/api/v1/links/{link_id}/{action}", headers=nino)
        assert response.status_code == 409, action
        assert response.json()["code"] == "link.invalid_state"


async def test_the_receiver_declines_rather_than_withdraws(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    link_id = await requested(client, sessionmaker, alex, NINO)
    response = await client.delete(f"/api/v1/links/{link_id}", headers=nino)
    assert response.status_code == 409
    assert response.json()["code"] == "link.invalid_state"


async def test_a_declined_request_cannot_be_withdrawn_or_broken(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    link_id = await requested(client, sessionmaker, alex, NINO)
    await client.post(f"/api/v1/links/{link_id}/decline", headers=nino)
    for headers in (alex, nino):
        response = await client.delete(f"/api/v1/links/{link_id}", headers=headers)
        assert response.status_code == 409
        assert response.json()["code"] == "link.invalid_state"


async def test_outstanding_invites_are_capped(client: AsyncClient) -> None:
    alex = await person(client, ALEX)
    for _ in range(MAX_OUTSTANDING_INVITES):
        await invite(client, alex)
    response = await client.post("/api/v1/links/invites", headers=alex)
    assert response.status_code == 429
    assert response.json()["code"] == "invite.limit"

    oldest = (await lists(client, alex))["invites"][-1]
    revoked = await client.delete(f"/api/v1/links/invites/{oldest}", headers=alex)
    assert revoked.status_code == 204
    await invite(client, alex)


async def test_a_dead_invite_links_nobody(client: AsyncClient, sessionmaker: Sessions) -> None:
    alex = await person(client, ALEX)
    await person(client, NINO)
    await person(client, GIO)

    expired = await invite(client, alex)
    async with sessionmaker() as db:
        await db.execute(
            update(Invite)
            .where(Invite.token_hash == hash_token(expired))
            .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )
        await db.commit()
    revoked = await invite(client, alex)
    [revoked_id, *_] = (await lists(client, alex))["invites"]
    await client.delete(f"/api/v1/links/invites/{revoked_id}", headers=alex)
    spent = await invite(client, alex)
    assert (await press_start(sessionmaker, GIO, spent)).outcome is Opened.REQUESTED

    for token in (expired, revoked, spent, "not-a-token"):
        opened = await press_start(sessionmaker, NINO, token)
        assert opened == OpenedInvite(Opened.INVALID), token
    async with sessionmaker() as db:
        pairs = await db.scalar(select(func.count()).select_from(Link))
    assert pairs == 1  # Alex and Gio, from the spent invite


async def test_opening_ones_own_invite_spends_nothing(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    token = await invite(client, alex)
    assert await press_start(sessionmaker, ALEX, token) == OpenedInvite(Opened.OWN)
    assert len((await lists(client, alex))["invites"]) == 1


async def test_an_invite_between_linked_people_is_not_spent(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    await person(client, NINO)
    await linked(client, sessionmaker, alex, NINO)
    token = await invite(client, alex)
    opened = await press_start(sessionmaker, NINO, token)
    assert opened.outcome is Opened.ALREADY_LINKED
    assert len((await lists(client, alex))["invites"]) == 1


@pytest.mark.parametrize("username", ["nobody_here", "@nobody_here", "a b", "@", "x" * 40, "ni"])
async def test_a_username_nobody_has_is_not_found(client: AsyncClient, username: str) -> None:
    alex = await person(client, ALEX)
    await person(client, NINO)
    response = await ask_by_username(client, alex, username)
    assert response.status_code == 404
    assert response.json()["code"] == "user.not_found"


async def test_one_cannot_ask_oneself(client: AsyncClient) -> None:
    alex = await person(client, ALEX)
    response = await ask_by_username(client, alex, "@Format37")
    assert response.status_code == 409
    assert response.json()["code"] == "link.self"


async def test_after_a_decline_the_requester_waits_a_week(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    link_id = (await ask_by_username(client, alex, "nino")).json()["id"]
    await client.post(f"/api/v1/links/{link_id}/decline", headers=nino)

    response = await ask_by_username(client, alex, "nino")
    assert response.status_code == 429
    assert response.json()["code"] == "link.cooldown"
    assert [type_ for _, type_, _, _ in await told(sessionmaker)] == ["link.requested"]

    async with sessionmaker() as db:
        await db.execute(
            update(Link).values(declined_at=datetime.now(UTC) - timedelta(days=7, seconds=1))
        )
        await db.commit()
    again = await ask_by_username(client, alex, "nino")
    assert again.status_code == 200
    assert again.json()["status"] == "pending"


async def test_the_decliner_may_ask_at_once(client: AsyncClient, sessionmaker: Sessions) -> None:
    # The cooldown protects the one who declined, so it doesn't bind them.
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    link_id = (await ask_by_username(client, alex, "nino")).json()["id"]
    await client.post(f"/api/v1/links/{link_id}/decline", headers=nino)
    response = await ask_by_username(client, nino, "format37")
    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    assert response.json()["direction"] == "outgoing"


# --- allowed ---------------------------------------------------------------------


async def test_an_invite_becomes_a_request_and_then_a_link(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)

    created = await client.post("/api/v1/links/invites", headers=alex)
    body = created.json()
    token = body["url"].removeprefix("https://t.me/peertopeerswapbot?start=inv_")
    assert len(token) == 22
    async with sessionmaker() as db:
        stored = await db.get(Invite, uuid.UUID(body["id"]))
    assert stored is not None
    # Only the hash is kept: a read of the table hands out no working invite.
    assert stored.token_hash == hash_token(token)
    assert token.encode() not in stored.token_hash
    assert datetime.fromisoformat(body["expires_at"]) - stored.created_at > timedelta(hours=71)

    opened = await press_start(sessionmaker, NINO, token)
    assert opened.outcome is Opened.REQUESTED
    assert opened.inviter is not None
    assert opened.inviter.first_name == "Alex"
    assert opened.link is not None
    link_id = str(opened.link.id)

    assert await lists(client, alex) == {
        "active": [],
        "incoming": [],
        "outgoing": ["Nino"],
        "invites": [],  # spent
    }
    assert await lists(client, nino) == {
        "active": [],
        "incoming": ["Alex"],
        "outgoing": [],
        "invites": [],
    }
    shown = (await client.get(f"/api/v1/links/{link_id}", headers=nino)).json()
    assert shown["status"] == "pending"
    assert shown["direction"] == "incoming"
    assert shown["person"] == {
        "id": shown["person"]["id"],
        "first_name": "Alex",
        "last_name": None,
        "username": "format37",
    }
    assert shown["mutual_links"] == 0
    assert shown["accepted_at"] is None
    from_alex = (await client.get(f"/api/v1/links/{link_id}", headers=alex)).json()
    assert from_alex["direction"] == "outgoing"
    assert from_alex["person"]["first_name"] == "Nino"

    accepted = await client.post(f"/api/v1/links/{link_id}/accept", headers=nino)
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "active"
    assert accepted.json()["accepted_at"] is not None
    assert (await lists(client, alex))["active"] == ["Nino"]
    assert (await lists(client, nino))["active"] == ["Alex"]


async def test_a_decline_leaves_both_lists_and_starts_the_cooldown(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    link_id = await requested(client, sessionmaker, alex, NINO)
    response = await client.post(f"/api/v1/links/{link_id}/decline", headers=nino)
    assert response.status_code == 200
    assert response.json()["status"] == "declined"
    for headers in (alex, nino):
        assert await lists(client, headers) == {
            "active": [],
            "incoming": [],
            "outgoing": [],
            "invites": [],
        }
    async with sessionmaker() as db:
        link = await db.get(Link, uuid.UUID(link_id))
    assert link is not None
    assert link.declined_at is not None


async def test_the_decliner_may_still_open_an_invite(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    # Q-E1: opening an invite is the invitee's own doing, so the cooldown doesn't apply.
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    link_id = await requested(client, sessionmaker, alex, NINO)
    await client.post(f"/api/v1/links/{link_id}/decline", headers=nino)
    again = await requested(client, sessionmaker, alex, NINO)
    assert again == link_id  # the pair keeps its row
    assert (await lists(client, nino))["incoming"] == ["Alex"]


async def test_withdrawing_and_breaking_reuse_the_pairs_row(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    link_id = await requested(client, sessionmaker, alex, NINO)
    assert (await client.delete(f"/api/v1/links/{link_id}", headers=alex)).status_code == 204
    assert (await lists(client, nino))["incoming"] == []

    assert await linked(client, sessionmaker, alex, NINO) == link_id
    assert (await client.delete(f"/api/v1/links/{link_id}", headers=nino)).status_code == 204
    for headers in (alex, nino):
        assert (await lists(client, headers))["active"] == []
    shown = (await client.get(f"/api/v1/links/{link_id}", headers=alex)).json()
    assert shown["status"] == "removed"


async def test_when_both_have_asked_they_are_linked(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    link_id = await requested(client, sessionmaker, alex, NINO)
    opened = await press_start(sessionmaker, ALEX, await invite(client, nino))
    assert opened.outcome is Opened.LINKED
    assert opened.link is not None
    assert str(opened.link.id) == link_id
    assert (await lists(client, alex))["active"] == ["Nino"]
    assert (await lists(client, nino))["invites"] == []  # Nino's invite did its job


async def test_opening_a_spent_invite_again_shows_where_it_led(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    token = await invite(client, alex)
    first = await press_start(sessionmaker, NINO, token)
    again = await press_start(sessionmaker, NINO, token)
    assert again.outcome is Opened.REQUESTED
    assert again.link is not None
    assert first.link is not None
    assert again.link.id == first.link.id

    await client.post(f"/api/v1/links/{first.link.id}/accept", headers=nino)
    assert (await press_start(sessionmaker, NINO, token)).outcome is Opened.ALREADY_LINKED
    assert (await lists(client, alex))["active"] == ["Nino"]


async def test_mutual_links_are_counted_never_named(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    await person(client, GIO)
    await linked(client, sessionmaker, alex, GIO)
    await linked(client, sessionmaker, nino, GIO)
    link_id = await requested(client, sessionmaker, alex, NINO)

    response = await client.get(f"/api/v1/links/{link_id}", headers=nino)
    assert response.json()["mutual_links"] == 1
    assert "Gio" not in response.text
    assert "gio" not in response.text


@pytest.mark.parametrize("status", list(LinkStatus))
async def test_the_list_shows_only_pending_and_active(
    client: AsyncClient, sessionmaker: Sessions, status: LinkStatus
) -> None:
    alex = await person(client, ALEX)
    await person(client, NINO)
    link_id = await requested(client, sessionmaker, alex, NINO)
    async with sessionmaker() as db:
        await db.execute(update(Link).where(Link.id == uuid.UUID(link_id)).values(status=status))
        await db.commit()
    shown = await lists(client, alex)
    expected = {"active": ["Nino"], "pending": ["Nino"]}.get(status, [])
    assert shown["active"] + shown["outgoing"] == expected


async def test_a_request_by_username_tells_its_receiver(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    response = await ask_by_username(client, alex, " @NINO ")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert body["direction"] == "outgoing"
    assert body["person"]["first_name"] == "Nino"
    assert await told(sessionmaker) == [
        ("Nino", "link.requested", {"name": "Alex (@format37)"}, f"link_{body['id']}")
    ]
    assert (await lists(client, nino))["incoming"] == ["Alex"]

    # Asking again is not news.
    await ask_by_username(client, alex, "nino")
    assert len(await told(sessionmaker)) == 1


async def test_when_both_ask_by_username_they_are_linked_and_the_first_is_told(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    await ask_by_username(client, nino, "format37")
    response = await ask_by_username(client, alex, "nino")
    assert response.json()["status"] == "active"
    assert [(to, type_, params) for to, type_, params, _ in await told(sessionmaker)] == [
        ("Alex", "link.requested", {"name": "Nino B (@nino)"}),
        ("Nino", "link.established", {"name": "Alex (@format37)"}),
    ]


async def test_accepting_tells_the_requester(client: AsyncClient, sessionmaker: Sessions) -> None:
    alex = await person(client, ALEX)
    await person(client, NINO)
    link_id = await linked(client, sessionmaker, alex, NINO)
    # The invite itself told nobody: the bot answered the invitee there and then.
    assert await told(sessionmaker) == [
        ("Alex", "link.established", {"name": "Nino B (@nino)"}, f"link_{link_id}")
    ]


async def test_declining_withdrawing_and_breaking_tell_nobody(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    link_id = await requested(client, sessionmaker, alex, NINO)
    await client.post(f"/api/v1/links/{link_id}/decline", headers=nino)
    await requested(client, sessionmaker, alex, NINO)
    await client.delete(f"/api/v1/links/{link_id}", headers=alex)
    async with sessionmaker() as db:
        await db.execute(update(Link).values(status=LinkStatus.ACTIVE))
        await db.commit()
    await client.delete(f"/api/v1/links/{link_id}", headers=nino)
    assert await told(sessionmaker) == []


async def test_an_invite_to_someone_who_had_asked_tells_the_inviter(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    await ask_by_username(client, nino, "format37")
    opened = await press_start(sessionmaker, NINO, await invite(client, alex))
    assert opened.outcome is Opened.LINKED
    assert [(to, type_) for to, type_, _, _ in await told(sessionmaker)] == [
        ("Alex", "link.requested"),
        ("Alex", "link.established"),
    ]
