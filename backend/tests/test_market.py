"""The market rate that fills in the wizard (ADR-0020): Coinbase's table, parsed without a
float, kept for ten minutes, and served for a day while Coinbase is away."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
import pytest
from httpx import AsyncClient

from swap.market import FRESH, STALE, Market, MarketError, parse, suggested
from tests.conftest import COINBASE
from tests.test_links import ALEX, person

T0 = datetime(2026, 10, 22, 7, 30, tzinfo=UTC)


class Clock:
    def __init__(self) -> None:
        self.now = T0

    def __call__(self) -> datetime:
        return self.now


class Coinbase:
    """Answers with the recorded table, or fails as told, and counts the calls."""

    def __init__(self) -> None:
        self.calls = 0
        self.down = False

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        assert request.url.params["currency"] == "USD"
        return httpx.Response(503) if self.down else httpx.Response(200, json=COINBASE)


@pytest.fixture
async def world() -> Any:
    coinbase, clock = Coinbase(), Clock()
    async with httpx.AsyncClient(transport=httpx.MockTransport(coinbase)) as client:
        yield coinbase, clock, Market(client, now=clock)


# --- parsing --------------------------------------------------------------------------


def test_the_table_is_read_as_decimals() -> None:
    table = parse(COINBASE)
    assert table["RUB"] == Decimal("81.386641")
    assert table["GEL"] == Decimal("2.5924766666666667")
    assert table["USD"] == 1


def test_anything_but_a_positive_decimal_string_is_left_out() -> None:
    rates = {
        "RUB": "81.38",
        "FLOAT": 81.38,
        "ZERO": "0",
        "NEGATIVE": "-1",
        "NAN": "NaN",
        "INF": "Infinity",
        "WORDS": "много",
        "EMPTY": "",
        "NULL": None,
    }
    table = parse({"data": {"currency": "USD", "rates": rates}})
    assert table == {"RUB": Decimal("81.38"), "USD": Decimal(1)}


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        {"errors": [{"id": "not_found"}]},
        {"data": None},
        {"data": {"currency": "EUR", "rates": {"RUB": "91.5"}}},
        {"data": {"currency": "USD"}},
        {"data": {"currency": "USD", "rates": ["RUB", "81.38"]}},
    ],
)
def test_anything_but_coinbases_table_is_refused(payload: object) -> None:
    with pytest.raises(MarketError):
        parse(payload)


@pytest.mark.parametrize(
    ("value", "shown"),
    [
        ("31.39318401", "31.39"),
        ("31.395", "31.40"),
        ("361.044107", "361.04"),
        ("1.001081167", "1.00"),
        ("0.031853791", "0.03185"),
        ("0.38574905", "0.3857"),
        ("0.0022319900", "0.002232"),
    ],
)
def test_a_rate_is_suggested_the_way_people_type_one(value: str, shown: str) -> None:
    assert str(suggested(Decimal(value))) == shown


# --- the cache ------------------------------------------------------------------------


async def test_one_answer_serves_every_pair_for_ten_minutes(world: Any) -> None:
    coinbase, clock, market = world
    gel = await market.rate("GEL", "RUB")
    assert (gel.value, gel.fetched_at) == (Decimal("31.39"), T0)
    # Through USD, the other way round, and USD itself: still the one answer.
    assert (await market.rate("RUB", "GEL")).value == Decimal("0.03185")
    assert (await market.rate("USD", "RUB")).value == Decimal("81.39")
    clock.now = T0 + FRESH - timedelta(seconds=1)
    await market.rate("EUR", "RUB")
    assert coinbase.calls == 1
    clock.now = T0 + FRESH
    assert (await market.rate("GEL", "RUB")).fetched_at == T0 + FRESH
    assert coinbase.calls == 2


async def test_while_coinbase_is_away_the_last_answer_serves_for_a_day(world: Any) -> None:
    coinbase, clock, market = world
    await market.rate("GEL", "RUB")
    coinbase.down = True
    clock.now = T0 + timedelta(hours=5)
    stale = await market.rate("GEL", "RUB")
    # Its time goes with it, so the wizard can say how old it is.
    assert (stale.value, stale.fetched_at) == (Decimal("31.39"), T0)
    clock.now = T0 + STALE
    assert await market.rate("GEL", "RUB") is None


async def test_nothing_is_suggested_without_an_answer_or_a_currency(world: Any) -> None:
    coinbase, _, market = world
    coinbase.down = True
    assert await market.rate("GEL", "RUB") is None
    coinbase.down = False
    # KZT isn't in the recorded table.
    assert await market.rate("KZT", "RUB") is None


# --- the endpoint ---------------------------------------------------------------------


async def test_the_wizard_gets_the_market_rate(client: AsyncClient) -> None:
    alex = await person(client, ALEX)
    query = {"base": "GEL", "quote": "RUB"}
    response = await client.get("/api/v1/rates/market", params=query, headers=alex)
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["base"], body["quote"], body["value"], body["source"]) == (
        "GEL",
        "RUB",
        "31.39",
        "coinbase",
    )
    assert datetime.fromisoformat(body["fetched_at"]) <= datetime.now(UTC)
    assert (await client.get("/api/v1/rates/market", params=query)).status_code == 401


@pytest.mark.parametrize(
    ("base", "quote", "status", "code"),
    [
        ("XYZ", "RUB", 422, "rate.unknown_currency"),
        ("GEL", "BTC", 422, "rate.unknown_currency"),
        ("RUB", "RUB", 422, "rate.same_currency"),
        ("KZT", "RUB", 503, "rate.unavailable"),
    ],
)
async def test_a_rate_that_cant_be_had_is_refused(
    client: AsyncClient, base: str, quote: str, status: int, code: str
) -> None:
    alex = await person(client, ALEX)
    response = await client.get(
        "/api/v1/rates/market", params={"base": base, "quote": quote}, headers=alex
    )
    assert response.status_code == status
    assert response.json()["code"] == code
