"""Every deal someone took part in, as CSV for their own records (FR-6.3, QUESTIONS K4).

One row per deal they still keep (ADR-0030), oldest first, worded in their language and
dated in their time zone. Amounts stay decimal strings with a point, as a machine reads
them. The file starts with a byte-order mark, so Excel opens the Cyrillic and Georgian
right. The bot sends it to their chat (ADR-0035).
"""

import csv
import io
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from swap.deals import kept_by
from swap.i18n import Locale, t
from swap.models import Deal, DealLeg, Order, User
from swap.rates import FixedRate
from swap.users import person_label


def _when(moment: datetime | None, zone: ZoneInfo) -> str:
    return moment.astimezone(zone).strftime("%Y-%m-%d %H:%M") if moment else ""


def _leg(leg: DealLeg | None, locale: Locale) -> list[str]:
    if leg is None:  # pragma: no cover - a deal has both legs
        return ["", "", "", ""]
    return [str(leg.amount), leg.currency, leg.country, t(locale, f"export.way.{leg.method}")]


async def deals_csv(db: AsyncSession, user: User, locale: Locale) -> tuple[bytes, int]:
    """The CSV of `user`'s deals, and how many rows it has."""
    zone = ZoneInfo(user.tz or "UTC")
    deals = list(await db.scalars(select(Deal).where(kept_by(user.id)).order_by(Deal.created_at)))
    numbers = dict(
        (
            await db.execute(
                select(Order.id, Order.number).where(Order.id.in_({d.order_id for d in deals}))
            )
        ).all()
    )
    others = {d.acceptor_id if d.proposer_id == user.id else d.proposer_id for d in deals}
    people = {
        person.id: person for person in await db.scalars(select(User).where(User.id.in_(others)))
    }

    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(t(locale, "export.header").split("|"))
    for deal in deals:
        other = people.get(deal.acceptor_id if deal.proposer_id == user.id else deal.proposer_id)
        gave = next((leg for leg in deal.legs if leg.payer_id == user.id), None)
        got = next((leg for leg in deal.legs if leg.payee_id == user.id), None)
        quote = FixedRate.model_validate(deal.rate_spec).quote_for(deal.rate_base, deal.rate_quote)
        source = (
            t(locale, "export.rate.market", time=_when(deal.rate_fetched_at, zone))
            if deal.rate_source
            else t(locale, "export.rate.author")
        )
        name = ""
        if other is not None:
            name = t(locale, "export.deleted") if other.deleted_at else person_label(other)
        writer.writerow(
            [
                _when(deal.created_at, zone),
                _when(deal.accepted_at, zone),
                _when(deal.closed_at, zone),
                numbers.get(deal.order_id, ""),
                t(locale, f"export.status.{deal.status}"),
                name,
                *_leg(gave, locale),
                *_leg(got, locale),
                f"1 {quote.base} = {quote.value.normalize():f} {quote.quote}",
                source,
            ]
        )
    # With a byte-order mark, so Excel reads it as UTF-8.
    return out.getvalue().encode("utf-8-sig"), len(deals)
