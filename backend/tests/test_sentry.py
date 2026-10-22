from collections.abc import Iterator
from typing import Any

import pytest
import sentry_sdk
import structlog
from sentry_sdk.envelope import Envelope
from sentry_sdk.transport import Transport

from swap.api.headers import content_security_policy
from swap.config import Settings
from swap.logs import REDACTED, configure_logging
from swap.sentry import _sampler, init_sentry
from tests.conftest import TEST_BOT_TOKEN

DSN = "https://public@o1.ingest.us.sentry.io/2"
SECRET_HALF = TEST_BOT_TOKEN.partition(":")[2]


class Recorder(Transport):
    """Keeps the events the SDK would have sent."""

    def __init__(self) -> None:
        super().__init__()
        self.events: list[dict[str, Any]] = []

    def capture_envelope(self, envelope: Envelope) -> None:
        if (event := envelope.get_event()) is not None:
            self.events.append(event)


@pytest.fixture
def sent(settings: Settings) -> Iterator[list[dict[str, Any]]]:
    recorder = Recorder()
    configure_logging("INFO", "console", settings.secrets())
    init_sentry(settings.model_copy(update={"sentry_dsn": DSN}), "worker", transport=recorder)
    yield recorder.events
    # Later tests build apps without a DSN, which leaves the client alone: drop it.
    sentry_sdk.init()


def test_nothing_starts_without_a_dsn(settings: Settings) -> None:
    init_sentry(settings, "api")
    assert sentry_sdk.get_client().transport is None


def test_a_logged_failure_is_reported_without_the_token(sent: list[dict[str, Any]]) -> None:
    url = f"http://127.0.0.1:8081/bot{TEST_BOT_TOKEN}/sendMessage"
    try:
        raise RuntimeError(f"POST {url} failed")
    except RuntimeError as error:
        structlog.get_logger("swap.worker").error(
            "update failed", exc_info=error, url=url, init_data="user=%7B%22id%22%3A1%7D"
        )

    [event] = sent
    text = repr(event)
    assert TEST_BOT_TOKEN not in text
    assert SECRET_HALF not in text
    # The title is the log's event, not the repr of structlog's dict.
    assert event["logentry"]["message"] == "update failed"
    assert event["extra"]["url"] == f"http://127.0.0.1:8081/bot{REDACTED}/sendMessage"
    assert event["extra"]["init_data"] == REDACTED
    [exception] = event["exception"]["values"]
    assert exception["type"] == "RuntimeError"
    assert exception["stacktrace"]["frames"]
    assert event["tags"]["service"] == "worker"


def test_breadcrumbs_from_our_logs_are_redacted(sent: list[dict[str, Any]]) -> None:
    log = structlog.get_logger("swap.worker")
    log.info("bot request", url=f"http://127.0.0.1:8081/bot{TEST_BOT_TOKEN}/getMe", token="x")
    log.error("outbox stuck")

    [event] = sent
    assert TEST_BOT_TOKEN not in repr(event)
    crumb = event["breadcrumbs"]["values"][-1]
    assert crumb["message"] == "bot request"
    assert crumb["data"]["token"] == REDACTED


def test_no_local_variables_or_bodies_are_sent(sent: list[dict[str, Any]]) -> None:
    def handler() -> None:
        init_data = "user=someone"  # noqa: F841
        raise ValueError("boom")

    try:
        handler()
    except ValueError:
        sentry_sdk.capture_exception()

    [event] = sent
    frames = event["exception"]["values"][0]["stacktrace"]["frames"]
    assert all("vars" not in frame for frame in frames)
    collected = sentry_sdk.get_client().options["data_collection"]
    assert collected["user_info"] is False
    assert collected["http_bodies"] == []


def test_health_checks_are_not_traced() -> None:
    sample = _sampler(0.1)
    assert sample({"asgi_scope": {"path": "/healthz"}}) == 0.0
    assert sample({"asgi_scope": {"path": "/api/v1/me"}}) == 0.1
    assert sample({}) == 0.1


def test_the_browser_may_reach_the_dsn_host_only_when_there_is_one() -> None:
    assert "connect-src 'self';" in content_security_policy(None)
    assert "connect-src 'self' https://o1.ingest.us.sentry.io;" in content_security_policy(DSN)
