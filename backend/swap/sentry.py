"""Error reports to Sentry (ADR-0025), cleaned by the same redactor as the logs.

Nothing personal goes: no IP addresses, no request bodies (a sign-in's is someone's
initData, a relay's is someone's message), no local variables. The bot token is in
every Bot API URL, so each event and breadcrumb passes through `Redactor` last.
"""

from collections.abc import Callable, Mapping
from logging import LogRecord
from typing import Any, cast

import sentry_sdk
from sentry_sdk.transport import Transport
from sentry_sdk.types import Breadcrumb, BreadcrumbHint, Event, Hint

from swap.config import Settings
from swap.logs import Redactor


def _structlog_message(
    record: LogRecord | None, redactor: Redactor
) -> tuple[str, dict[str, Any]] | None:
    """Our records carry structlog's event dict as their message: its event and its
    redacted fields. Without this a report's title would be the dict's repr."""
    if record is None or not isinstance(record.msg, Mapping):
        return None
    fields = {
        k: v
        for k, v in redactor.clean(record.msg).items()
        if k not in {"event", "exc_info"} and not k.startswith("_")
    }
    return str(record.msg.get("event", "")), fields


def _sampler(rate: float) -> Callable[[dict[str, Any]], float]:
    def sample(context: dict[str, Any]) -> float:
        # Docker's health checks call /healthz every ten seconds.
        path = (context.get("asgi_scope") or {}).get("path")
        return 0.0 if path == "/healthz" else rate

    return sample


def init_sentry(settings: Settings, service: str, *, transport: Transport | None = None) -> None:
    """Start reporting, once per process. Without `SENTRY_DSN` this does nothing."""
    if not settings.sentry_dsn:
        return
    redactor = Redactor(settings.secrets())

    def before_send(event: Event, hint: Hint) -> Event:
        if logged := _structlog_message(hint.get("log_record"), redactor):
            event["logentry"] = {"message": logged[0], "params": []}
            event["extra"] = {**event.get("extra", {}), **logged[1]}
        return cast(Event, redactor.clean(event))

    def before_send_transaction(event: Event, hint: Hint) -> Event:
        return cast(Event, redactor.clean(event))

    def before_breadcrumb(crumb: Breadcrumb, hint: BreadcrumbHint) -> Breadcrumb:
        if logged := _structlog_message(hint.get("log_record"), redactor):
            crumb["message"] = logged[0]
            crumb["data"] = {**crumb.get("data", {}), **logged[1]}
        return cast(Breadcrumb, redactor.clean(crumb))

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env,
        # The release comes from SENTRY_RELEASE, which the deploy sets to the commit.
        data_collection={
            "user_info": False,
            "cookies": {"mode": "off"},
            "http_bodies": [],
            "url_query_params": {"mode": "off"},
            # SQL parameters are amounts, names and hashes.
            "database_query_data": False,
            "stack_frame_variables": False,
        },
        traces_sampler=_sampler(settings.sentry_traces_sample_rate),
        before_send=before_send,
        before_send_transaction=before_send_transaction,
        before_breadcrumb=before_breadcrumb,
        transport=transport,
    )
    sentry_sdk.set_tag("service", service)
