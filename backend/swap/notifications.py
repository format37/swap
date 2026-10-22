"""Notifications: written with the change they report, worded and sent by the worker (ADR-0014)."""

import uuid
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from swap.models import Notification, NotificationKind

# Each type is also the key of its words in swap/i18n.py.
type NotificationType = Literal[
    "link.requested",
    "link.established",
    "order.opened",
    "deal.proposed",
    "deal.accepted",
    "deal.declined",
    "deal.withdrawn",
    "deal.expired",
    "deal.cancelled",
    "deal.proposal_closed",
    "deal.sent",
    "deal.received",
    "deal.settled",
    # Asked for by its recipient, so no switch silences it (QUESTIONS K4).
    "export.deals",
]


# Which switch in the settings each message answers to (QUESTIONS K1).
KIND_OF: dict[str, NotificationKind] = {
    "order.opened": NotificationKind.ORDERS,
    "link.requested": NotificationKind.LINKS,
    "link.established": NotificationKind.LINKS,
    "deal.proposed": NotificationKind.PROPOSALS,
    "deal.accepted": NotificationKind.PROPOSALS,
    "deal.declined": NotificationKind.PROPOSALS,
    "deal.withdrawn": NotificationKind.PROPOSALS,
    "deal.expired": NotificationKind.PROPOSALS,
    "deal.proposal_closed": NotificationKind.PROPOSALS,
    "deal.sent": NotificationKind.TRANSFERS,
    "deal.received": NotificationKind.TRANSFERS,
    "deal.settled": NotificationKind.TRANSFERS,
    "deal.cancelled": NotificationKind.CANCELLATIONS,
}


def notify(
    db: AsyncSession,
    recipient: uuid.UUID,
    type_: NotificationType,
    *,
    target: str | None = None,
    **params: str,
) -> None:
    """Queue a message in the caller's transaction, so it goes out only if the change commits.

    A value whose name holds `amount` is a decimal string, which the worker formats in the
    recipient's language.
    """
    db.add(
        Notification(
            id=uuid.uuid4(), recipient_id=recipient, type=type_, params=params, target=target
        )
    )
