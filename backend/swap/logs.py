"""Structured logs with one redaction step (ADR-0011).

Every record, ours or a library's, is rendered by one stdlib handler. Its
formatter runs `Redactor` just before rendering, which blanks the values of
denylisted keys, anything shaped like a bot token, and the configured secrets.
Bot API URLs carry the token in their path, so a logged URL or a traceback would
otherwise leak it.
"""

import logging
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any

import structlog
from structlog.typing import EventDict, Processor, WrappedLogger

REDACTED = "[redacted]"
SENSITIVE_KEYS = frozenset(
    {
        "authorization",
        "details",
        "hash",
        "init_data",
        "password",
        "recipient_details",
        "secret",
        "token",
    }
)
_BOT_TOKEN = re.compile(r"(?<!\d)\d{6,12}:[A-Za-z0-9_-]{30,}")
# Shorter strings would blank innocent text, and real secrets are long.
_MIN_SECRET_LENGTH = 16


def _sensitive(key: object) -> bool:
    return str(key).lower() in SENSITIVE_KEYS


class Redactor:
    """A structlog processor that blanks secrets in keys, values and free text."""

    def __init__(self, secrets: Iterable[str] = ()) -> None:
        # Longest first, so the whole token goes before its secret half.
        self._secrets = sorted(
            {s for s in secrets if len(s) >= _MIN_SECRET_LENGTH}, key=len, reverse=True
        )

    def scrub(self, text: str) -> str:
        for secret in self._secrets:
            text = text.replace(secret, REDACTED)
        return _BOT_TOKEN.sub(REDACTED, text)

    def clean(self, value: Any) -> Any:
        if isinstance(value, str):
            return self.scrub(value)
        if isinstance(value, Mapping):
            return {k: REDACTED if _sensitive(k) else self.clean(v) for k, v in value.items()}
        if isinstance(value, list | tuple | set | frozenset):
            return [self.clean(v) for v in value]
        return value

    def __call__(self, logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
        return {k: REDACTED if _sensitive(k) else self.clean(v) for k, v in event_dict.items()}


def configure_logging(level: str = "INFO", fmt: str = "json", secrets: Iterable[str] = ()) -> None:
    """Send structlog and the standard library through one redacting handler on stderr.

    stderr keeps stdout free for tools that print data, such as `swap.tools.openapi`.
    """
    shared: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]
    renderer: Processor = (
        structlog.processors.JSONRenderer()
        if fmt == "json"
        else structlog.dev.ConsoleRenderer(colors=False)
    )
    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                # Tracebacks become text here, so the redactor sees them too.
                structlog.processors.format_exc_info,
                Redactor(secrets),
                renderer,
            ],
        )
    )
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
    # uvicorn installs handlers of its own; route its records through ours instead.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = True
    # Two INFO lines per run of every job, every 30 seconds, say nothing a failure won't.
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
