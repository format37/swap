"""Amounts from rate_spec (kickoff rule 6): the one formula, rounded half up once."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from swap.errors import DomainError
from swap.rates import FixedRate, convert

GEL_RUB = FixedRate.model_validate_json(
    '{"v": 1, "type": "fixed", "quotes": [{"base": "GEL", "quote": "RUB", "value": "29.20"},'
    ' {"base": "USD", "quote": "RUB", "value": "81.50"}]}'
)


@pytest.mark.parametrize(
    ("amount", "give", "want", "whole", "expected"),
    [
        # Q-B4's example: 50 000 RUB at «1 GEL = 29,20 RUB».
        ("50000", "RUB", "GEL", False, "1712.33"),
        ("50000", "RUB", "GEL", True, "1712"),
        ("100000", "RUB", "USD", False, "1226.99"),
        # The quote's own direction multiplies.
        ("1100", "GEL", "RUB", False, "32120.00"),
        ("0.01", "GEL", "RUB", False, "0.29"),
        ("150000.00", "RUB", "GEL", False, "5136.99"),
    ],
)
def test_the_counter_amount(
    amount: str, give: str, want: str, *, whole: bool, expected: str
) -> None:
    result = convert(Decimal(amount), GEL_RUB, give, want, whole=whole)
    assert result == Decimal(expected)
    assert str(result) == expected  # exactly two decimals, or none when whole


def test_halves_round_up_not_to_even() -> None:
    spec = FixedRate.model_validate({"quotes": [{"base": "AAA", "quote": "BBB", "value": "0.125"}]})
    # Banker's rounding would give 0.12 and 2.
    assert convert(Decimal("1"), spec, "AAA", "BBB") == Decimal("0.13")
    two_and_a_half = FixedRate.model_validate(
        {"quotes": [{"base": "AAA", "quote": "BBB", "value": "2.5"}]}
    )
    assert convert(Decimal("1"), two_and_a_half, "AAA", "BBB", whole=True) == Decimal("3")


def test_a_rate_keeps_ten_decimals() -> None:
    spec = FixedRate.model_validate(
        {"quotes": [{"base": "RUB", "quote": "GEL", "value": "0.0342465753"}]}
    )
    assert convert(Decimal("50000"), spec, "RUB", "GEL") == Decimal("1712.33")


def test_a_currency_without_a_rate_is_refused() -> None:
    with pytest.raises(DomainError) as refused:
        convert(Decimal("1"), GEL_RUB, "RUB", "EUR")
    assert refused.value.code == "rate.missing"


@pytest.mark.parametrize(
    "spec",
    [
        # A JSON number is a float on the way in.
        '{"quotes": [{"base": "GEL", "quote": "RUB", "value": 29.2}]}',
        '{"quotes": [{"base": "GEL", "quote": "RUB", "value": "29.2e0"}]}',
        '{"quotes": [{"base": "GEL", "quote": "RUB", "value": "0"}]}',
        '{"quotes": [{"base": "GEL", "quote": "RUB", "value": "-1"}]}',
        '{"quotes": [{"base": "gel", "quote": "RUB", "value": "29.20"}]}',
        '{"quotes": []}',
        '{"quotes": [{"base": "GEL", "quote": "RUB", "value": "29.20"}], "markup_pct": "1"}',
        '{"type": "reference", "quotes": [{"base": "GEL", "quote": "RUB", "value": "29.20"}]}',
    ],
)
def test_a_malformed_rate_is_refused(spec: str) -> None:
    with pytest.raises(ValidationError):
        FixedRate.model_validate_json(spec)
