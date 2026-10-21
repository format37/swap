import json
import logging

import pytest
import structlog

from swap.logs import REDACTED, configure_logging
from tests.conftest import TEST_BOT_TOKEN

SECRET_HALF = TEST_BOT_TOKEN.partition(":")[2]


def _logged(capsys: pytest.CaptureFixture[str]) -> str:
    return capsys.readouterr().err


def test_a_bot_api_url_is_scrubbed_in_our_logs(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO", "json", secrets=(TEST_BOT_TOKEN, SECRET_HALF))
    structlog.get_logger("swap").warning(
        "send failed", url=f"http://127.0.0.1:8081/bot{TEST_BOT_TOKEN}/sendMessage"
    )
    out = _logged(capsys)
    assert TEST_BOT_TOKEN not in out
    assert SECRET_HALF not in out
    assert json.loads(out)["url"] == f"http://127.0.0.1:8081/bot{REDACTED}/sendMessage"


def test_library_records_and_tracebacks_are_scrubbed(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO", "json", secrets=(TEST_BOT_TOKEN, SECRET_HALF))
    try:
        raise RuntimeError(f"cannot open /{SECRET_HALF}/documents/file_0.pdf")
    except RuntimeError:
        logging.getLogger("aiogram").exception("request to /bot%s/getFile failed", TEST_BOT_TOKEN)
    out = _logged(capsys)
    assert TEST_BOT_TOKEN not in out
    assert SECRET_HALF not in out
    assert "getFile failed" in out
    assert "documents/file_0.pdf" in out


def test_sensitive_keys_lose_their_values(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO", "json")
    structlog.get_logger("swap").info(
        "auth",
        init_data="query_id=AAH&user=%7B%7D&hash=abc",
        nested={"details": "GE29TB0000000000000001", "kind": "bank"},
        Authorization="Bearer abc",
    )
    record = json.loads(_logged(capsys))
    assert record["init_data"] == REDACTED
    assert record["Authorization"] == REDACTED
    assert record["nested"] == {"details": REDACTED, "kind": "bank"}


def test_ordinary_text_is_left_alone(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO", "json", secrets=(TEST_BOT_TOKEN,))
    structlog.get_logger("swap").info("deal settled", amount="1712.33", deal_id=42)
    record = json.loads(_logged(capsys))
    assert record["event"] == "deal settled"
    assert record["amount"] == "1712.33"
    assert record["deal_id"] == 42
