"""Security headers on every response, set here rather than in the shared Caddyfile.

A change to them then ships with a deploy, not with a hand edit of a file the
VPS's other sites depend on (ADR-0001).
"""

from urllib.parse import urlsplit

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


def content_security_policy(sentry_dsn: str | None = None) -> str:
    # The browser sends its error reports to the DSN's host (ADR-0025).
    connect = "connect-src 'self'"
    if sentry_dsn:
        dsn = urlsplit(sentry_dsn)
        connect += f" {dsn.scheme}://{dsn.hostname}"
    return "; ".join(
        [
            "default-src 'self'",
            "script-src 'self'",
            # React and the Telegram SDK set inline styles and CSS variables.
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: blob:",
            "font-src 'self'",
            connect,
            "object-src 'none'",
            "base-uri 'none'",
            "form-action 'self'",
            # Telegram Web shows the Mini App in an iframe. This is also why there is no
            # X-Frame-Options here: DENY would leave that frame blank.
            "frame-ancestors https://web.telegram.org https://webk.telegram.org"
            " https://weba.telegram.org",
        ]
    )


def security_headers(sentry_dsn: str | None = None) -> dict[str, str]:
    return {
        "Content-Security-Policy": content_security_policy(sentry_dsn),
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    }


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp, sentry_dsn: str | None = None) -> None:
        self.app = app
        self.headers = security_headers(sentry_dsn)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in self.headers.items():
                    headers[name] = value
            await send(message)

        await self.app(scope, receive, send_with_headers)
