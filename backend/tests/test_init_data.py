"""initData validation (kickoff rule 6). Refusals first, then what is accepted."""

import json
from datetime import UTC, datetime, timedelta
from urllib.parse import quote, urlencode

import pytest
from aiogram.utils.web_app import check_webapp_signature

from swap.init_data import CLOCK_SKEW, InitDataError, sign, validate_init_data
from tests.conftest import TEST_BOT_TOKEN

NOW = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)
HOUR = timedelta(hours=1)
USER = {
    "id": 279058397,
    "first_name": "Alex",
    "last_name": "",
    "username": "format37",
    "language_code": "ru",
    "allows_write_to_pm": True,
}


def fields(**overrides: object) -> dict[str, str]:
    values: dict[str, object] = {
        "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
        "user": json.dumps(USER, ensure_ascii=False, separators=(",", ":")),
        "auth_date": str(int(NOW.timestamp())),
        "signature": "6fbdaaGuA7fz5fyVBG9A41s0uW1NUnCC-SMuSbwrrEDhOKIzdO13-TgYZzuiaS1gaBTpqWrG",
    }
    values.update(overrides)
    return {key: str(value) for key, value in values.items() if value is not None}


def signed(data: dict[str, str], token: str = TEST_BOT_TOKEN) -> str:
    # Encoded as Telegram does: percent-encoding, spaces as %20.
    return urlencode({**data, "hash": sign(data, token)}, quote_via=quote)


def refusal(raw: str, *, now: datetime = NOW) -> str:
    with pytest.raises(InitDataError) as caught:
        validate_init_data(raw, TEST_BOT_TOKEN, max_age=HOUR, now=now)
    return caught.value.code


# --- refused ---------------------------------------------------------------------


def test_a_tampered_field_is_refused() -> None:
    raw = signed(fields())
    forged = raw.replace("format37", "someone_else")
    assert refusal(forged) == "init_data_bad_signature"


def test_another_bots_signature_is_refused() -> None:
    other_token = "987654321:" + "O" * 35
    assert refusal(signed(fields(), token=other_token)) == "init_data_bad_signature"


def test_a_missing_hash_is_refused() -> None:
    assert refusal(urlencode(fields(), quote_via=quote)) == "init_data_unsigned"
    assert refusal("") == "init_data_unsigned"


def test_a_repeated_key_is_refused() -> None:
    raw = signed(fields()) + "&auth_date=" + str(int(NOW.timestamp()))
    assert refusal(raw) == "init_data_malformed"


def test_garbage_is_refused() -> None:
    assert refusal("not a query string") == "init_data_malformed"


def test_the_signature_field_is_part_of_what_is_signed() -> None:
    data = fields()
    raw = signed(data)
    without_signature = raw.replace("signature=" + quote(data["signature"]) + "&", "")
    assert without_signature != raw
    assert refusal(without_signature) == "init_data_bad_signature"


def test_older_than_max_age_is_refused() -> None:
    raw = signed(fields(auth_date=int((NOW - HOUR - timedelta(seconds=1)).timestamp())))
    assert refusal(raw) == "init_data_expired"


def test_from_the_future_is_refused() -> None:
    later = NOW + CLOCK_SKEW + timedelta(seconds=1)
    assert refusal(signed(fields(auth_date=int(later.timestamp())))) == "init_data_from_future"


def test_a_signed_but_broken_auth_date_is_refused() -> None:
    assert refusal(signed(fields(auth_date="yesterday"))) == "init_data_malformed"


def test_signed_data_without_a_user_is_refused() -> None:
    assert refusal(signed(fields(user=None))) == "init_data_no_user"
    assert refusal(signed(fields(user="{not json"))) == "init_data_no_user"
    assert refusal(signed(fields(user=json.dumps({"id": 1})))) == "init_data_no_user"


# --- accepted --------------------------------------------------------------------


def test_a_valid_launch_is_accepted() -> None:
    data = validate_init_data(
        signed(fields(start_param="inv_abc")), TEST_BOT_TOKEN, max_age=HOUR, now=NOW
    )
    assert data.user.id == 279058397
    assert data.user.first_name == "Alex"
    assert data.user.last_name is None
    assert data.user.username == "format37"
    assert data.user.language_code == "ru"
    assert data.user.allows_write_to_pm is True
    assert data.auth_date == NOW
    assert data.start_param == "inv_abc"


PHOTO = "https://t.me/i/userpic/320/4FPEE4tmP3ATHa57u6MqTDih13LTOiMoKoLDRG4PnSA.svg"


@pytest.mark.parametrize(
    ("sent", "kept"),
    [
        (PHOTO, PHOTO),
        (None, None),
        # Only Telegram's own links are kept, so a stored one points nowhere else (ADR-0027).
        ("https://evil.example/i/userpic/320/x.svg", None),
        ("http://t.me/i/userpic/320/x.svg", None),
        ("https://t.me.evil.example/x.svg", None),
        ("https://t.me/x y.svg", None),
        ("https://t.me/" + "x" * 600, None),
        (42, None),
    ],
)
def test_only_telegrams_own_photo_link_is_kept(sent: object, kept: str | None) -> None:
    user = json.dumps({**USER, "photo_url": sent}, ensure_ascii=False)
    data = validate_init_data(signed(fields(user=user)), TEST_BOT_TOKEN, max_age=HOUR, now=NOW)
    assert data.user.photo_url == kept


def test_our_signature_agrees_with_aiograms() -> None:
    assert check_webapp_signature(TEST_BOT_TOKEN, signed(fields()))


def test_the_age_limit_and_the_skew_are_inclusive() -> None:
    at_limit = signed(fields(auth_date=int((NOW - HOUR).timestamp())))
    assert validate_init_data(at_limit, TEST_BOT_TOKEN, max_age=HOUR, now=NOW)
    slightly_ahead = signed(fields(auth_date=int((NOW + CLOCK_SKEW).timestamp())))
    assert validate_init_data(slightly_ahead, TEST_BOT_TOKEN, max_age=HOUR, now=NOW)


@pytest.mark.parametrize(
    "first_name",
    [
        "Анна-Мария",
        "ანა",  # Georgian
        "Jo + Mo & Co = 100%",
        "  spaces  ",
        "emoji 💱",
    ],
)
def test_names_survive_url_encoding(first_name: str) -> None:
    user = json.dumps({**USER, "first_name": first_name}, ensure_ascii=False)
    data = validate_init_data(signed(fields(user=user)), TEST_BOT_TOKEN, max_age=HOUR, now=NOW)
    assert data.user.first_name == first_name
