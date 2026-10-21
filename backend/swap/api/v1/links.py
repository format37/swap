"""Links and invites (ADR-0012): the «Связи» tab, the request screen and the invite sheet."""

import uuid
from datetime import datetime, timedelta
from typing import Literal, Self

from fastapi import APIRouter
from pydantic import BaseModel, Field

from swap import links
from swap.api.deps import AppSettings, CurrentUser, Db
from swap.api.errors import Problem
from swap.api.v1.people import Person
from swap.deeplinks import invite_url
from swap.models import Invite as InviteRow
from swap.models import Link as LinkRow
from swap.models import LinkStatus, User

router = APIRouter(prefix="/links", tags=["links"], responses={401: {"model": Problem}})


class Link(BaseModel):
    id: uuid.UUID
    # The other side of the pair.
    person: Person
    status: LinkStatus
    # Who asked: "outgoing" if the signed-in user did, "incoming" if the other side did.
    direction: Literal["incoming", "outgoing"]
    requested_at: datetime
    # When the link was established; null until then.
    accepted_at: datetime | None

    @classmethod
    def of(cls, link: LinkRow, person: User) -> Self:
        return cls(
            id=link.id,
            person=Person.of(person),
            status=LinkStatus(link.status),
            direction="incoming" if link.requested_by == person.id else "outgoing",
            requested_at=link.requested_at,
            accepted_at=link.accepted_at,
        )


class LinkDetail(Link):
    # How many people are linked to both; never who (§3).
    mutual_links: int


class Invite(BaseModel):
    """An outstanding invite. Its link can't be shown again: only a hash is kept."""

    id: uuid.UUID
    created_at: datetime
    expires_at: datetime

    @classmethod
    def of(cls, invite: InviteRow) -> Self:
        return cls(id=invite.id, created_at=invite.created_at, expires_at=invite.expires_at)


class NewInvite(Invite):
    # t.me/<bot>?start=inv_<token>, shown once.
    url: str


class Links(BaseModel):
    active: list[Link]
    incoming: list[Link]
    outgoing: list[Link]
    invites: list[Invite]


@router.get("")
async def list_links(user: CurrentUser, db: Db) -> Links:
    found = await links.overview(db, user.id)
    return Links(
        active=[Link.of(item.link, item.person) for item in found.active],
        incoming=[Link.of(item.link, item.person) for item in found.incoming],
        outgoing=[Link.of(item.link, item.person) for item in found.outgoing],
        invites=[Invite.of(invite) for invite in found.invites],
    )


@router.post("/invites", status_code=201, responses={429: {"model": Problem}})
async def create_invite(user: CurrentUser, db: Db, settings: AppSettings) -> NewInvite:
    invite, token = await links.create_invite(db, user.id, timedelta(seconds=settings.invite_ttl_s))
    await db.commit()
    return NewInvite(
        id=invite.id,
        created_at=invite.created_at,
        expires_at=invite.expires_at,
        url=invite_url(settings.telegram_bot_username, token),
    )


class LinkRequest(BaseModel):
    # With or without the @; Telegram's own limit is 32 characters.
    username: str = Field(min_length=1, max_length=64)


@router.post(
    "/requests",
    responses={404: {"model": Problem}, 409: {"model": Problem}, 429: {"model": Problem}},
)
async def request_link(body: LinkRequest, user: CurrentUser, db: Db) -> Link:
    """Ask someone to link by their @username. When they had already asked, it links."""
    link = await links.request_by_username(db, user, body.username)
    return await _answered(db, link, user.id)


@router.delete(
    "/invites/{invite_id}",
    status_code=204,
    responses={404: {"model": Problem}, 409: {"model": Problem}},
)
async def revoke_invite(invite_id: uuid.UUID, user: CurrentUser, db: Db) -> None:
    await links.revoke_invite(db, user.id, invite_id)
    await db.commit()


@router.get("/{link_id}", responses={404: {"model": Problem}})
async def get_link(link_id: uuid.UUID, user: CurrentUser, db: Db) -> LinkDetail:
    item, mutual = await links.view(db, user.id, link_id)
    return LinkDetail(**Link.of(item.link, item.person).model_dump(), mutual_links=mutual)


async def _answered(db: Db, link: LinkRow, me: uuid.UUID) -> Link:
    person = await db.get(User, links.other_side(link, me))
    if person is None:  # pragma: no cover - the foreign key guarantees the row
        raise RuntimeError("the other side of a link vanished")
    await db.commit()
    return Link.of(link, person)


@router.post("/{link_id}/accept", responses={404: {"model": Problem}, 409: {"model": Problem}})
async def accept_link(link_id: uuid.UUID, user: CurrentUser, db: Db) -> Link:
    return await _answered(db, await links.accept(db, user, link_id), user.id)


@router.post("/{link_id}/decline", responses={404: {"model": Problem}, 409: {"model": Problem}})
async def decline_link(link_id: uuid.UUID, user: CurrentUser, db: Db) -> Link:
    return await _answered(db, await links.decline(db, user.id, link_id), user.id)


@router.delete(
    "/{link_id}", status_code=204, responses={404: {"model": Problem}, 409: {"model": Problem}}
)
async def remove_link(link_id: uuid.UUID, user: CurrentUser, db: Db) -> None:
    """Break an active link, or withdraw one's own pending request."""
    await links.remove(db, user.id, link_id)
    await db.commit()
