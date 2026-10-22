"""Validation of the Mini App's `initData`, as in Telegram's "Validating data received
via the Mini App".

This is our own function rather than aiogram's. aiogram checks the signature only and
never looks at `auth_date`, so a captured `initData` would work forever.
"""

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qsl

# Telegram's clock and ours may disagree a little. More than this is a forgery or a
# broken clock.
CLOCK_SKEW = timedelta(seconds=60)
# Where Telegram serves profile photos. A link anywhere else is dropped, so a stored URL
# can only ever point a browser at Telegram (ADR-0027).
PHOTO_PREFIX = "https://t.me/"


class InitDataError(Exception):
    """Why `initData` was refused. `code` reaches the client as the problem's code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class TelegramUser:
    id: int
    first_name: str
    last_name: str | None
    username: str | None
    language_code: str | None
    allows_write_to_pm: bool
    # Telegram's link to their photo, when their privacy settings let it come.
    photo_url: str | None = None


@dataclass(frozen=True, slots=True)
class InitData:
    user: TelegramUser
    auth_date: datetime
    start_param: str | None


def sign(fields: dict[str, str], bot_token: str) -> str:
    """The `hash` Telegram computes over `fields`: every field but `hash` itself, sorted
    by key and joined with newlines. That includes `signature` (Bot API 8.0)."""
    check_string = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    return hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()


def validate_init_data(
    raw: str, bot_token: str, *, max_age: timedelta, now: datetime | None = None
) -> InitData:
    """Check the signature first, then the age, then read the user."""
    try:
        pairs = parse_qsl(raw, keep_blank_values=True, strict_parsing=True)
    except ValueError as exc:
        raise InitDataError("init_data_malformed") from exc
    fields = dict(pairs)
    if len(fields) != len(pairs):
        # A repeated key: which copy did Telegram sign?
        raise InitDataError("init_data_malformed")

    received = fields.pop("hash", None)
    if not received:
        raise InitDataError("init_data_unsigned")
    if not hmac.compare_digest(sign(fields, bot_token), received):
        raise InitDataError("init_data_bad_signature")

    try:
        auth_date = datetime.fromtimestamp(int(fields["auth_date"]), tz=UTC)
    except (KeyError, ValueError, OverflowError, OSError) as exc:
        raise InitDataError("init_data_malformed") from exc
    now = now or datetime.now(UTC)
    if auth_date > now + CLOCK_SKEW:
        raise InitDataError("init_data_from_future")
    if now - auth_date > max_age:
        raise InitDataError("init_data_expired")

    return InitData(
        user=_user(fields.get("user")),
        auth_date=auth_date,
        start_param=fields.get("start_param") or None,
    )


def _user(raw: str | None) -> TelegramUser:
    if not raw:
        raise InitDataError("init_data_no_user")
    try:
        data = json.loads(raw)
        return TelegramUser(
            id=int(data["id"]),
            first_name=str(data["first_name"]),
            last_name=data.get("last_name") or None,
            username=data.get("username") or None,
            language_code=data.get("language_code") or None,
            allows_write_to_pm=bool(data.get("allows_write_to_pm", False)),
            photo_url=_photo(data.get("photo_url")),
        )
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise InitDataError("init_data_no_user") from exc


def _photo(url: object) -> str | None:
    """Telegram's link to a profile photo, or None for anything that isn't one."""
    if (
        isinstance(url, str)
        and url.startswith(PHOTO_PREFIX)
        and len(url) <= 512
        and url.isprintable()
        and " " not in url
    ):
        return url
    return None
