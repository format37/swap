"""Money, rates, assets and countries as they cross the api (ADR-0002, ADR-0004, ADR-0007).

An amount is a decimal string, never a JSON number: JavaScript and Python's json both
read a number as a float. Values built in Python pass as Decimals.
"""

import re
from collections.abc import Callable
from decimal import Decimal
from typing import Annotated

from pydantic import BeforeValidator, Field, WithJsonSchema

AMOUNT_PATTERN = r"^\d{1,16}(\.\d{1,2})?$"
RATE_PATTERN = r"^\d{1,10}(\.\d{1,10})?$"


def _decimal_string(pattern: str, example: str) -> Callable[[object], object]:
    compiled = re.compile(pattern)

    def check(value: object) -> object:
        if isinstance(value, Decimal) or (isinstance(value, str) and compiled.fullmatch(value)):
            return value
        raise ValueError(f"must be a decimal string such as {example!r}")

    return check


# numeric(18,2): up to 16 digits before the point and 2 after (ADR-0002).
Money = Annotated[
    Decimal,
    BeforeValidator(_decimal_string(AMOUNT_PATTERN, "1500.00")),
    Field(gt=0, max_digits=18, decimal_places=2),
    WithJsonSchema({"type": "string", "pattern": AMOUNT_PATTERN, "examples": ["1500.00"]}),
]

# The same, with 0 allowed: an order's minimum, where 0 means any amount (QUESTIONS F4).
MoneyOrZero = Annotated[
    Decimal,
    BeforeValidator(_decimal_string(AMOUNT_PATTERN, "0")),
    Field(ge=0, max_digits=18, decimal_places=2),
    WithJsonSchema({"type": "string", "pattern": AMOUNT_PATTERN, "examples": ["0"]}),
]

# Rates are not money: RUB→GEL ≈ 0.0339 doesn't survive two decimals. numeric(20,10).
RateValue = Annotated[
    Decimal,
    BeforeValidator(_decimal_string(RATE_PATTERN, "29.20")),
    Field(gt=0, max_digits=20, decimal_places=10),
    WithJsonSchema({"type": "string", "pattern": RATE_PATTERN, "examples": ["29.20"]}),
]

# ISO 4217 codes, plus the stablecoins USDT and USDC (ADR-0010).
Asset = Annotated[str, Field(pattern=r"^[A-Z]{3,5}$", examples=["GEL"])]
# ISO 3166-1 alpha-2.
Country = Annotated[str, Field(pattern=r"^[A-Z]{2}$", examples=["GE"])]
