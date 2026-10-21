"""Links between users, and the invites that start them (ADR-0012).

A request is the pair's `links` row in `pending`, whichever way it came: an invite
opened through the bot, or a request to an @username. The receiver accepts or
declines it, the requester may withdraw it, and either side breaks an active link.
Only the two people of a pair ever see its row; anyone else gets 404.
"""

import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from sqlalchemy import ColumnElement, Select, case, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from swap.deeplinks import target
from swap.errors import DomainError
from swap.models import Invite, Link, LinkStatus, User
from swap.notifications import notify
from swap.sessions import hash_token
from swap.users import person_label

# The rate limit on invites that §7 asks for (ADR-0012).
MAX_OUTSTANDING_INVITES = 10
# After a decline, how long the declined person can't ask again by @username (FR-1.2).
COOLDOWN = timedelta(days=7)
# Telegram usernames are 5 to 32 of these; a few bought ones are 4.
_USERNAME = re.compile(r"[A-Za-z0-9_]{4,32}")


def pair(a: uuid.UUID, b: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    """The pair in the row's order. Python and Postgres order uuids the same way."""
    return (a, b) if a < b else (b, a)


def other_side(link: Link, me: uuid.UUID) -> uuid.UUID:
    return link.user_hi_id if link.user_lo_id == me else link.user_lo_id


def _other_side_of(me: uuid.UUID) -> ColumnElement[uuid.UUID]:
    return case((Link.user_lo_id == me, Link.user_hi_id), else_=Link.user_lo_id)


def _involves(me: uuid.UUID) -> ColumnElement[bool]:
    return or_(Link.user_lo_id == me, Link.user_hi_id == me)


def linked_ids(me: uuid.UUID) -> Select[uuid.UUID]:
    """Everyone `me` is actively linked to. Links are not transitive (§3)."""
    return select(_other_side_of(me)).where(_involves(me), Link.status == LinkStatus.ACTIVE)


async def mutual_count(db: AsyncSession, a: uuid.UUID, b: uuid.UUID) -> int:
    """How many people are linked to both; never who they are (§3)."""
    both = linked_ids(a).intersect(linked_ids(b)).subquery()
    return await db.scalar(select(func.count()).select_from(both)) or 0


class Asked(StrEnum):
    # A new pending request now waits for the receiver.
    REQUESTED = "requested"
    # The same request was already waiting.
    ALREADY_ASKED = "already_asked"
    # The receiver had already asked the requester: both consented, so they are linked.
    LINKED = "linked"
    # Nothing to ask.
    ALREADY_LINKED = "already_linked"


async def ask(
    db: AsyncSession,
    requester: uuid.UUID,
    receiver: uuid.UUID,
    *,
    cooldown: timedelta | None = None,
) -> tuple[Link, Asked]:
    """Make `requester` ask `receiver` to link, reusing the pair's row if it has one.

    With `cooldown`, a requester whom the receiver declined that recently is refused.
    """
    lo, hi = pair(requester, receiver)
    # Create the row if the pair has none, then lock it, so two requests at once agree.
    created = await db.scalar(
        insert(Link)
        .values(
            id=uuid.uuid4(),
            user_lo_id=lo,
            user_hi_id=hi,
            status=LinkStatus.PENDING,
            requested_by=requester,
        )
        .on_conflict_do_nothing(index_elements=[Link.user_lo_id, Link.user_hi_id])
        .returning(Link.id)
    )
    link = await db.scalar(
        select(Link)
        .where(Link.user_lo_id == lo, Link.user_hi_id == hi)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if link is None:  # pragma: no cover - the insert above guarantees the row
        raise RuntimeError("the pair's row vanished")
    if created is not None:
        return link, Asked.REQUESTED
    now = datetime.now(UTC)
    if link.status == LinkStatus.ACTIVE:
        return link, Asked.ALREADY_LINKED
    if link.status == LinkStatus.PENDING:
        if link.requested_by == receiver:
            link.status = LinkStatus.ACTIVE
            link.accepted_at = now
            return link, Asked.LINKED
        return link, Asked.ALREADY_ASKED
    if (
        cooldown is not None
        and link.status == LinkStatus.DECLINED
        and link.requested_by == requester
        and link.declined_at is not None
        and now - link.declined_at < cooldown
    ):
        raise DomainError(429, "link.cooldown")
    # Declined or removed: a new request, on the same row.
    link.status = LinkStatus.PENDING
    link.requested_by = requester
    link.requested_at = now
    link.accepted_at = None
    link.declined_at = None
    return link, Asked.REQUESTED


async def _lock_own(db: AsyncSession, me: uuid.UUID, link_id: uuid.UUID) -> Link:
    link = await db.scalar(select(Link).where(Link.id == link_id, _involves(me)).with_for_update())
    if link is None:
        # The same answer whether the row is someone else's or doesn't exist.
        raise DomainError(404, "link.not_found")
    return link


def _answerable(link: Link, me: uuid.UUID) -> None:
    """Only the receiver answers a request, and only while it is pending."""
    if link.status != LinkStatus.PENDING or link.requested_by == me:
        raise DomainError(409, "link.invalid_state")


async def accept(db: AsyncSession, me: User, link_id: uuid.UUID) -> Link:
    link = await _lock_own(db, me.id, link_id)
    _answerable(link, me.id)
    link.status = LinkStatus.ACTIVE
    link.accepted_at = datetime.now(UTC)
    _established(db, link, tell=link.requested_by, about=me)
    return link


def _established(db: AsyncSession, link: Link, *, tell: uuid.UUID, about: User) -> None:
    notify(db, tell, "link.established", target=target("link", link.id), name=person_label(about))


async def request_by_username(db: AsyncSession, me: User, username: str) -> Link:
    """Ask someone who has used Swap to link, by their @username (FR-1.1, Q-B11)."""
    name = username.strip().removeprefix("@")
    receiver = None
    if _USERNAME.fullmatch(name):
        receiver = await db.scalar(select(User).where(func.lower(User.username) == name.lower()))
    if receiver is None:
        raise DomainError(404, "user.not_found")
    if receiver.id == me.id:
        raise DomainError(409, "link.self")
    link, asked = await ask(db, me.id, receiver.id, cooldown=COOLDOWN)
    if asked is Asked.REQUESTED:
        notify(
            db, receiver.id, "link.requested", target=target("link", link.id), name=person_label(me)
        )
    elif asked is Asked.LINKED:
        _established(db, link, tell=receiver.id, about=me)
    return link


async def decline(db: AsyncSession, me: uuid.UUID, link_id: uuid.UUID) -> Link:
    link = await _lock_own(db, me, link_id)
    _answerable(link, me)
    link.status = LinkStatus.DECLINED
    link.declined_at = datetime.now(UTC)
    return link


async def remove(db: AsyncSession, me: uuid.UUID, link_id: uuid.UUID) -> Link:
    """Break an active link, or withdraw one's own pending request.

    The pair's orders disappear for both at once, because visibility is a query
    over active links.
    """
    link = await _lock_own(db, me, link_id)
    withdrawing = link.status == LinkStatus.PENDING and link.requested_by == me
    if link.status != LinkStatus.ACTIVE and not withdrawing:
        raise DomainError(409, "link.invalid_state")
    link.status = LinkStatus.REMOVED
    return link


@dataclass(frozen=True, slots=True)
class LinkWith:
    """A link and the person on its other side."""

    link: Link
    person: User


@dataclass(frozen=True, slots=True)
class Overview:
    active: list[LinkWith]
    incoming: list[LinkWith]
    outgoing: list[LinkWith]
    invites: list[Invite]


async def overview(db: AsyncSession, me: uuid.UUID) -> Overview:
    """Everything the «Связи» tab lists."""
    rows = await db.execute(
        select(Link, User)
        .join(User, User.id == _other_side_of(me))
        .where(_involves(me), Link.status.in_([LinkStatus.ACTIVE, LinkStatus.PENDING]))
        .order_by(Link.accepted_at.desc().nulls_last(), Link.requested_at.desc())
    )
    result = Overview(active=[], incoming=[], outgoing=[], invites=[])
    for link, person in rows:
        if link.status == LinkStatus.ACTIVE:
            result.active.append(LinkWith(link, person))
        elif link.requested_by == me:
            result.outgoing.append(LinkWith(link, person))
        else:
            result.incoming.append(LinkWith(link, person))
    invites = await db.scalars(
        _outstanding_invites(me).order_by(Invite.created_at.desc(), Invite.id)
    )
    result.invites.extend(invites)
    return result


async def view(db: AsyncSession, me: uuid.UUID, link_id: uuid.UUID) -> tuple[LinkWith, int]:
    """One link with the person on its other side, and their mutual links."""
    row = (
        await db.execute(
            select(Link, User)
            .join(User, User.id == _other_side_of(me))
            .where(Link.id == link_id, _involves(me))
        )
    ).first()
    if row is None:
        raise DomainError(404, "link.not_found")
    link, person = row
    return LinkWith(link, person), await mutual_count(db, me, person.id)


def _outstanding_invites(me: uuid.UUID) -> Select[Invite]:
    return select(Invite).where(
        Invite.created_by == me,
        Invite.used_at.is_(None),
        Invite.revoked_at.is_(None),
        Invite.expires_at > func.now(),
    )


async def create_invite(db: AsyncSession, me: uuid.UUID, ttl: timedelta) -> tuple[Invite, str]:
    """A new one-time invite and its token. The token is never stored, only its hash."""
    outstanding = await db.scalar(
        select(func.count()).select_from(_outstanding_invites(me).subquery())
    )
    if (outstanding or 0) >= MAX_OUTSTANDING_INVITES:
        raise DomainError(429, "invite.limit")
    # 128 random bits: 22 characters of base64url, well inside `start`'s 64.
    token = secrets.token_urlsafe(16)
    invite = Invite(
        id=uuid.uuid4(),
        created_by=me,
        token_hash=hash_token(token),
        expires_at=datetime.now(UTC) + ttl,
    )
    db.add(invite)
    await db.flush()
    return invite, token


async def revoke_invite(db: AsyncSession, me: uuid.UUID, invite_id: uuid.UUID) -> None:
    invite = await db.scalar(
        select(Invite).where(Invite.id == invite_id, Invite.created_by == me).with_for_update()
    )
    if invite is None:
        raise DomainError(404, "invite.not_found")
    if invite.used_at is not None:
        raise DomainError(409, "invite.used")
    if invite.revoked_at is None:
        invite.revoked_at = datetime.now(UTC)


class Opened(StrEnum):
    """What opening an invite led to. The bot words each one."""

    REQUESTED = "requested"
    LINKED = "linked"
    ALREADY_LINKED = "already_linked"
    # The inviter opened their own link. It stays unspent.
    OWN = "own"
    # Unknown, revoked, expired, or spent by someone else.
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class OpenedInvite:
    outcome: Opened
    inviter: User | None = None
    link: Link | None = None


async def open_invite(db: AsyncSession, invitee: User, token: str) -> OpenedInvite:
    """The invitee pressed /start with an invite: it becomes a request from the inviter.

    The invite is spent unless the two are already linked. Opening a spent invite
    again, as the person who spent it, shows where it led.
    """
    invite = await db.scalar(
        select(Invite).where(Invite.token_hash == hash_token(token)).with_for_update()
    )
    if invite is None or invite.revoked_at is not None:
        return OpenedInvite(Opened.INVALID)
    if invite.created_by == invitee.id:
        return OpenedInvite(Opened.OWN)
    if invite.used_by is None:
        if invite.expires_at <= datetime.now(UTC):
            return OpenedInvite(Opened.INVALID)
    elif invite.used_by != invitee.id:
        return OpenedInvite(Opened.INVALID)

    inviter = await db.get(User, invite.created_by)
    if inviter is None:  # pragma: no cover - the foreign key guarantees the row
        return OpenedInvite(Opened.INVALID)
    # Opening it is the invitee's own doing, so the cooldown doesn't apply (Q-E1).
    link, asked = await ask(db, inviter.id, invitee.id)
    if invite.used_by is None and asked is not Asked.ALREADY_LINKED:
        invite.used_by = invitee.id
        invite.used_at = datetime.now(UTC)
    if asked is Asked.LINKED:
        # The invitee had asked first. The bot answers them; the inviter learns here.
        _established(db, link, tell=inviter.id, about=invitee)
    outcome = Opened.REQUESTED if asked is Asked.ALREADY_ASKED else Opened(asked.value)
    return OpenedInvite(outcome, inviter, link)
