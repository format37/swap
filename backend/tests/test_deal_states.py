"""The deal state machine (ADR-0018, ADR-0024): every transition, and every illegal one.

Kickoff rule 6. Each of 13 actions is tried from each of 8 situations: the six states,
and an accepted deal with something marked on leg 1. A legal one moves the deal and
journals it; any other is refused with nothing changed. The database refuses a status
change that skips the journal, and any edit of the journal itself.
"""

import uuid
from datetime import UTC, datetime, timedelta
from itertools import product
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from swap.deals import expire_due
from swap.models import Deal, Event
from tests.test_deals import World

Sessions = async_sessionmaker[AsyncSession]

# Where a deal can be, and the status it shows there. Leg 1 is Nino's own transfer, GEL to
# Alex; leg 2 is Alex's, RUB to Nino. They move in any order (QUESTIONS H2).
SITUATIONS: dict[str, str] = {
    "proposed": "proposed",
    "accepted": "accepted",
    "sent1": "accepted",
    "received1": "accepted",
    "disputed": "disputed",
    "settled": "settled",
    "cancelled": "cancelled",
    "expired": "expired",
}
RUNNING = ["accepted", "sent1", "received1"]
MOVED = ["sent1", "received1"]

# Who does it, where, and with what.
ACTIONS: dict[str, tuple[str, str, dict[str, Any]]] = {
    "accept": ("alex", "accept", {}),
    "decline": ("alex", "decline", {}),
    "withdraw": ("nino", "withdraw", {}),
    "cancel": ("nino", "cancel", {}),
    "sent1": ("nino", "legs/1/sent", {}),
    "received1": ("alex", "legs/1/received", {}),
    "sent2": ("alex", "legs/2/sent", {}),
    "received2": ("nino", "legs/2/received", {}),
    "cancel_request": ("nino", "cancel-request", {}),
    "cancel_approve": ("alex", "cancel-request/approve", {}),
    "cancel_reject": ("alex", "cancel-request/reject", {}),
    "dispute": ("nino", "dispute", {"note": "деньги не пришли"}),
    "resolve": ("nino", "resolve", {"outcome": "settled"}),
}

# ADR-0024, as (action, situation) → status.
LEGAL: dict[tuple[str, str], str] = {
    ("accept", "proposed"): "accepted",
    ("decline", "proposed"): "cancelled",
    ("withdraw", "proposed"): "cancelled",
    # Alone, only while nothing has moved (FR-4.5).
    ("cancel", "accepted"): "cancelled",
    # Each mark once, in any order; a receipt needs no «sent» before it.
    ("sent1", "accepted"): "accepted",
    ("received1", "accepted"): "accepted",
    ("received1", "sent1"): "accepted",
    **{("sent2", state): "accepted" for state in RUNNING},
    ("received2", "accepted"): "accepted",
    ("received2", "sent1"): "accepted",
    # The receipt that leaves nothing outstanding settles it.
    ("received2", "received1"): "settled",
    **{("cancel_request", state): "accepted" for state in MOVED},
    **{("dispute", state): "disputed" for state in RUNNING},
    # One side's word on how a dispute ended; the other's confirmation closes it.
    ("resolve", "disputed"): "disputed",
}
# Answering a cancel request once something has moved, when nobody has asked.
NOBODY_ASKED = set(product(["cancel_approve", "cancel_reject"], MOVED))


async def deal_in(world: World, situation: str) -> dict[str, Any]:
    """A deal of Nino's on Alex's order, walked to `situation` the way people would."""
    deal = await world.propose()
    steps = {
        "proposed": [],
        "accepted": ["accept"],
        "sent1": ["accept", "sent1"],
        "received1": ["accept", "sent1", "received1"],
        "settled": ["accept", "sent2", "received1", "received2"],
        "disputed": ["accept", "dispute"],
        "cancelled": ["decline"],
        "expired": [],
    }[situation]
    for step in steps:
        who, path, body = ACTIONS[step]
        await world.ok(getattr(world, who), deal, path, **body)
    if situation == "expired":
        async with world.sessions() as db:
            await db.execute(update(Deal).values(expires_at=datetime.now(UTC) - timedelta(1)))
            assert await expire_due(db) == 1
            await db.commit()
    shown = await world.client.get(f"/api/v1/deals/{deal['id']}", headers=world.nino)
    assert shown.json()["status"] == SITUATIONS[situation]
    return dict(shown.json())


async def journal_length(world: World, deal: dict[str, Any]) -> int:
    async with world.sessions() as db:
        count = await db.scalar(
            select(func.count()).select_from(Event).where(Event.deal_id == uuid.UUID(deal["id"]))
        )
    return count or 0


@pytest.fixture
async def world(client: AsyncClient, sessionmaker: Sessions) -> World:
    return await World(client, sessionmaker).build()


@pytest.mark.parametrize(("action", "state"), list(product(ACTIONS, SITUATIONS)))
async def test_every_action_from_every_state(world: World, action: str, state: str) -> None:
    deal = await deal_in(world, state)
    before = await journal_length(world, deal)
    who, path, body = ACTIONS[action]
    response = await world.act(getattr(world, who), deal, path, **body)

    if (action, state) in LEGAL:
        assert response.status_code == 200, response.text
        moved = response.json()
        assert moved["status"] == LEGAL[action, state]
        # Every legal action is journaled, from where to where.
        assert await journal_length(world, deal) == before + 1
        last = moved["events"][-1]
        assert last["to"] == LEGAL[action, state]
        return

    assert response.status_code == 409, response.text
    expected = (
        "deal.no_cancel_request" if (action, state) in NOBODY_ASKED else "deal.invalid_transition"
    )
    assert response.json()["code"] == expected
    # A refused action changes nothing at all.
    unchanged = await world.client.get(f"/api/v1/deals/{deal['id']}", headers=world.nino)
    assert unchanged.json() == deal
    assert await journal_length(world, deal) == before


@pytest.mark.parametrize(
    ("action", "state", "wrong"),
    [
        ("accept", "proposed", "nino"),
        ("decline", "proposed", "nino"),
        ("withdraw", "proposed", "alex"),
        ("sent1", "accepted", "alex"),
        ("received1", "sent1", "nino"),
        ("sent2", "accepted", "nino"),
        ("received2", "accepted", "alex"),
    ],
)
async def test_only_the_right_side_takes_each_step(
    world: World, action: str, state: str, wrong: str
) -> None:
    deal = await deal_in(world, state)
    _, path, body = ACTIONS[action]
    response = await world.act(getattr(world, wrong), deal, path, **body)
    assert response.status_code == 403
    assert response.json()["code"] == "deal.not_your_move"
    assert (
        await world.client.get(f"/api/v1/deals/{deal['id']}", headers=world.nino)
    ).json() == deal


async def test_a_cancel_after_the_first_transfer_needs_the_other_side(world: World) -> None:
    deal = await deal_in(world, "sent1")
    asked = await world.ok(world.nino, deal, "cancel-request")
    assert asked["status"] == "accepted"
    assert asked["cancel_requested_by"] == asked["proposer"]["id"]
    # One request at a time, and nobody answers their own.
    twice = await world.act(world.alex, deal, "cancel-request")
    assert (twice.status_code, twice.json()["code"]) == (409, "deal.cancel_pending")
    own = await world.act(world.nino, deal, "cancel-request/approve")
    assert (own.status_code, own.json()["code"]) == (403, "deal.not_your_move")

    # Declined: nothing else changes (Q-B1), and it may be asked again.
    rejected = await world.ok(world.alex, deal, "cancel-request/reject")
    assert (rejected["status"], rejected["cancel_requested_by"]) == ("accepted", None)
    await world.ok(world.nino, deal, "cancel-request")
    cancelled = await world.ok(world.alex, deal, "cancel-request/approve")
    assert cancelled["status"] == "cancelled"
    assert cancelled["cancel_requested_by"] is None
    # The accepted amount goes back to the order (FR-2.3).
    assert await world.remaining() == "150000.00:open"
    assert [e["type"] for e in cancelled["events"]][-4:] == [
        "cancel_requested",
        "cancel_rejected",
        "cancel_requested",
        "cancel_approved",
    ]


async def test_a_dispute_needs_a_word_and_ends_when_both_agree(world: World) -> None:
    deal = await deal_in(world, "received1")
    blank = await world.act(world.alex, deal, "dispute", note="   ")
    assert (blank.status_code, blank.json()["code"]) == (422, "validation_error")
    disputed = await world.ok(world.alex, deal, "dispute", note="RUB не пришли")
    assert (disputed["status"], disputed["dispute_note"]) == ("disputed", "RUB не пришли")
    assert disputed["events"][-1]["note"] == "RUB не пришли"

    # One side proposes, the other answers with something else, and the first agrees.
    await world.ok(world.alex, deal, "resolve", outcome="settled")
    again = await world.ok(world.alex, deal, "resolve", outcome="settled")
    assert (again["status"], again["resolution"]) == ("disputed", "settled")
    other = await world.ok(world.nino, deal, "resolve", outcome="cancelled")
    assert (other["status"], other["resolution"]) == ("disputed", "cancelled")
    assert other["resolution_by"] == other["proposer"]["id"]
    ended = await world.ok(world.alex, deal, "resolve", outcome="cancelled")
    assert (ended["status"], ended["resolution"]) == ("cancelled", None)
    assert ended["events"][-1]["outcome"] == "cancelled"
    assert await world.remaining() == "150000.00:open"


async def test_a_dispute_can_end_settled(world: World) -> None:
    deal = await deal_in(world, "disputed")
    await world.ok(world.nino, deal, "resolve", outcome="settled")
    settled = await world.ok(world.alex, deal, "resolve", outcome="settled")
    assert settled["status"] == "settled"
    # A settled deal keeps its amount out of the order.
    assert await world.remaining() == "100000.00:open"


# --- the database's own guards (ADR-0002, ADR-0018) -----------------------------------


async def test_a_status_change_without_its_event_is_refused(world: World) -> None:
    deal = await deal_in(world, "accepted")
    async with world.sessions() as db:
        with pytest.raises(DBAPIError, match="without its event"):
            await db.execute(
                text("UPDATE deals SET status = 'settled' WHERE id = :id"), {"id": deal["id"]}
            )
        await db.rollback()
    # Nor does pointing at an event that says something else.
    async with world.sessions() as db:
        other = await db.scalar(
            select(Event.id).where(Event.deal_id == uuid.UUID(deal["id"])).order_by(Event.id)
        )
        with pytest.raises(DBAPIError, match="without its event"):
            await db.execute(
                text("UPDATE deals SET status = 'settled', last_event_id = :e WHERE id = :id"),
                {"id": deal["id"], "e": other},
            )
        await db.rollback()


async def test_a_deal_starts_as_proposed(world: World, sessionmaker: Sessions) -> None:
    deal = await deal_in(world, "proposed")
    async with sessionmaker() as db:
        with pytest.raises(DBAPIError, match="starts as proposed"):
            await db.execute(
                text(
                    "INSERT INTO deals (id, order_id, proposer_id, acceptor_id, status, rate_spec,"
                    " rate_base, rate_quote, rate_value, rate_locked_at, expires_at)"
                    " SELECT :new, order_id, proposer_id, acceptor_id, 'settled', rate_spec,"
                    " rate_base, rate_quote, rate_value, now(), now() FROM deals WHERE id = :id"
                ),
                {"new": uuid.uuid4(), "id": deal["id"]},
            )
        await db.rollback()


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE events SET type = 'forged' WHERE deal_id = :id",
        "DELETE FROM events WHERE deal_id = :id",
    ],
)
async def test_the_journal_is_append_only(world: World, statement: str) -> None:
    deal = await deal_in(world, "accepted")
    async with world.sessions() as db:
        with pytest.raises(DBAPIError, match="append-only"):
            await db.execute(text(statement), {"id": deal["id"]})
        await db.rollback()
    assert await journal_length(world, deal) == 2


async def test_either_side_moves_first_and_both_receipts_settle(world: World) -> None:
    deal = await deal_in(world, "accepted")
    # Alex pays before Nino, and Nino confirms it before Alex marks it sent (H2).
    got = await world.ok(world.nino, deal, "legs/2/received")
    assert got["status"] == "accepted"
    leg2 = next(leg for leg in got["legs"] if leg["seq"] == 2)
    # Money that arrived was sent: the receipt dates both.
    assert leg2["received_at"] is not None
    assert leg2["sent_at"] == leg2["received_at"]
    # Too late to mark it sent: it arrived already.
    late = await world.act(world.alex, deal, "legs/2/sent")
    assert (late.status_code, late.json()["code"]) == (409, "deal.invalid_transition")
    sent = await world.ok(world.nino, deal, "legs/1/sent")
    assert sent["status"] == "accepted"
    settled = await world.ok(world.alex, deal, "legs/1/received")
    assert settled["status"] == "settled"
    assert [(e["type"], e.get("seq")) for e in settled["events"]][1:] == [
        ("accepted", None),
        ("received", 2),
        ("sent", 1),
        ("received", 1),
    ]
    assert [name for name, _, _ in await world.told("deal.settled")] == ["Nino"]
    assert [name for name, _, _ in await world.told("deal.received")] == ["Alex"]
