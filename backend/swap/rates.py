"""Rates, and the one formula that turns an amount into its counter-amount (ADR-0004).

The UI never does this arithmetic: previews come from the api, and a deal stores the
amounts it agreed on.
"""

from decimal import ROUND_HALF_UP, Context, Decimal, localcontext
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from swap.errors import DomainError
from swap.money import Asset, RateValue

CENT = Decimal("0.01")
WHOLE = Decimal("1")


class Quote(BaseModel):
    """1 `base` = `value` `quote`, in the direction the author typed it: «1 GEL = 29,20 RUB»."""

    model_config = ConfigDict(extra="forbid")

    base: Asset
    quote: Asset
    value: RateValue


class FixedRate(BaseModel):
    """`rate_spec` v1 of type fixed: one quote per wanted currency (ADR-0004)."""

    model_config = ConfigDict(extra="forbid")

    v: Literal[1] = 1
    type: Literal["fixed"] = "fixed"
    quotes: list[Quote] = Field(min_length=1, max_length=8)

    def quote_for(self, give: str, want: str) -> Quote:
        for quote in self.quotes:
            if {quote.base, quote.quote} == {give, want}:
                return quote
        raise DomainError(422, "rate.missing", f"no rate between {give} and {want}")


def convert(
    amount: Decimal, spec: FixedRate, give: str, want: str, *, whole: bool = False
) -> Decimal:
    """What `amount` of `give` is worth in `want`, rounded half up once, at the end.

    `whole` rounds to whole units, for cash (Q-B4); otherwise to cents.
    """
    quote = spec.quote_for(give, want)
    with localcontext(Context(prec=28)):
        exact = amount * quote.value if quote.base == give else amount / quote.value
        return exact.quantize(WHOLE if whole else CENT, rounding=ROUND_HALF_UP)
