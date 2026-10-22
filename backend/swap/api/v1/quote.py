"""What the wizard and the proposal need about money: the assets, live previews of a
counter-amount (ADR-0004), and the market rate to start from (ADR-0020). The UI never does
money arithmetic, so it asks here, debounced.
"""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from swap.api.deps import AppSettings, CurrentUser, MarketRates
from swap.api.errors import Problem
from swap.errors import DomainError
from swap.money import Asset, Money
from swap.rates import FixedRate, convert

router = APIRouter(tags=["rates"], responses={401: {"model": Problem}})


class QuoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: Money
    give_currency: Asset
    want_currency: Asset
    rate_spec: FixedRate
    # Round to whole units, for cash (Q-B4).
    whole: bool = False


class QuoteResult(BaseModel):
    amount: Decimal


@router.post("/quote", responses={422: {"model": Problem}})
async def quote(body: QuoteRequest, user: CurrentUser) -> QuoteResult:
    """What `amount` of the give currency comes to in the want currency."""
    amount = convert(
        body.amount, body.rate_spec, body.give_currency, body.want_currency, whole=body.whole
    )
    return QuoteResult(amount=amount)


class MarketQuote(BaseModel):
    """1 `base` = `value` `quote` on the market, rounded the way people type a rate."""

    base: str
    quote: str
    value: Decimal
    source: Literal["coinbase"]
    # When the source said so: shown beside the rate (§11).
    fetched_at: datetime


@router.get("/rates/market", responses={422: {"model": Problem}, 503: {"model": Problem}})
async def market_rate(
    base: str, quote: str, user: CurrentUser, settings: AppSettings, market: MarketRates
) -> MarketQuote:
    """The market's rate, which the wizard fills in for the author to keep or change (F5)."""
    if base not in settings.assets or quote not in settings.assets:
        raise DomainError(422, "rate.unknown_currency")
    if base == quote:
        raise DomainError(422, "rate.same_currency")
    found = await market.rate(base, quote)
    if found is None:
        raise DomainError(503, "rate.unavailable")
    return MarketQuote(
        base=base, quote=quote, value=found.value, source="coinbase", fetched_at=found.fetched_at
    )


@router.get("/assets")
async def list_assets(user: CurrentUser, settings: AppSettings) -> list[str]:
    """What orders may give and want (FR-2.2). Config, so the app asks rather than knows."""
    return settings.assets
