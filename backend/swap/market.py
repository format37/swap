"""The market rate that fills in the wizard: Coinbase's public rates (QUESTIONS F5, ADR-0020).

It is a suggestion. The author keeps it or types another, and what the order stores is a
fixed rate (ADR-0004), so nothing here touches a deal. Coinbase's table holds every
currency against USD, so one answer covers every pair, through USD where it isn't one
side (FR-3.3), and it is kept for ten minutes. While Coinbase can't be reached, an
answer up to a day old is still given, with its time; after that, none.
"""

import asyncio
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Context, Decimal, InvalidOperation, localcontext

import httpx
import structlog

SOURCE = "coinbase"
URL = "https://api.coinbase.com/v2/exchange-rates"
FRESH = timedelta(minutes=10)
STALE = timedelta(days=1)
TIMEOUT_S = 5.0

log = structlog.get_logger(__name__)


class MarketError(Exception):
    """Coinbase didn't answer, or answered something that isn't its table of rates."""


@dataclass(frozen=True)
class MarketRate:
    """1 `base` = `value` `quote`, as Coinbase had it at `fetched_at`."""

    base: str
    quote: str
    value: Decimal
    fetched_at: datetime


def parse(payload: object) -> dict[str, Decimal]:
    """Coinbase's answer, {"data": {"currency": "USD", "rates": {"RUB": "81.38…", …}}}.

    A rate is a decimal string. One that is anything else, or not a positive number,
    is left out: the table is what Coinbase says, not what JSON's floats make of it.
    """
    data = payload.get("data") if isinstance(payload, Mapping) else None
    rates = data.get("rates") if isinstance(data, Mapping) else None
    if not isinstance(data, Mapping) or data.get("currency") != "USD":
        raise MarketError("not a table of rates against USD")
    if not isinstance(rates, Mapping):
        raise MarketError("no rates in the table")
    table: dict[str, Decimal] = {}
    for code, text in rates.items():
        if not isinstance(code, str) or not isinstance(text, str):
            continue
        try:
            value = Decimal(text)
        except InvalidOperation:
            continue
        if value.is_finite() and value > 0:
            table[code] = value
    table["USD"] = Decimal(1)
    return table


def suggested(value: Decimal) -> Decimal:
    """The rate as a person would type it: «31.40» to the cent, «0.03185» to 4 figures."""
    with localcontext(Context(prec=28)):
        step = Decimal("0.01") if value >= 1 else Decimal(1).scaleb(value.adjusted() - 3)
        return value.quantize(step, rounding=ROUND_HALF_UP)


class Market:
    """Coinbase's table, fetched at most every ten minutes, by whoever asks first."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        url: str = URL,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._client = client
        self._url = url
        self._now = now
        self._lock = asyncio.Lock()
        self._table: dict[str, Decimal] = {}
        self._fetched_at: datetime | None = None

    async def _fetch(self) -> None:
        response = await self._client.get(self._url, params={"currency": "USD"})
        response.raise_for_status()
        self._table = parse(response.json())
        self._fetched_at = self._now()

    async def rate(self, base: str, quote: str) -> MarketRate | None:
        """1 `base` in `quote`, rounded the way people type it; None if there is none."""
        async with self._lock:
            age = self._now() - self._fetched_at if self._fetched_at else None
            if age is None or age >= FRESH:
                try:
                    await self._fetch()
                except (httpx.HTTPError, ValueError, MarketError) as error:
                    # The last table serves for a day; the wizard says how old it is.
                    log.warning("market.unavailable", error=str(error))
            fetched_at = self._fetched_at
        if fetched_at is None or self._now() - fetched_at >= STALE:
            return None
        if base not in self._table or quote not in self._table:
            return None
        with localcontext(Context(prec=28)):
            value = self._table[quote] / self._table[base]
        return MarketRate(base, quote, suggested(value), fetched_at)
