"""What the wizard and the proposal need about money: the assets, and live previews of a
counter-amount (ADR-0004). The UI never does money arithmetic, so it asks here, debounced.
"""

from decimal import Decimal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from swap.api.deps import AppSettings, CurrentUser
from swap.api.errors import Problem
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


@router.get("/assets")
async def list_assets(user: CurrentUser, settings: AppSettings) -> list[str]:
    """What orders may give and want (FR-2.2). Config, so the app asks rather than knows."""
    return settings.assets
