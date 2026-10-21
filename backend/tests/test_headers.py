from httpx import AsyncClient


async def test_every_response_carries_the_security_headers(client: AsyncClient) -> None:
    for path in ("/healthz", "/no-such-page"):
        headers = (await client.get(path)).headers
        assert headers["x-content-type-options"] == "nosniff"
        assert headers["referrer-policy"] == "no-referrer"
        assert headers["strict-transport-security"].startswith("max-age=")
        assert "default-src 'self'" in headers["content-security-policy"]


async def test_telegram_web_may_frame_the_app(client: AsyncClient) -> None:
    headers = (await client.get("/healthz")).headers
    # X-Frame-Options: DENY would leave Telegram Web's iframe blank; the CSP's
    # frame-ancestors names who may frame us instead.
    assert "x-frame-options" not in headers
    assert "frame-ancestors https://web.telegram.org" in headers["content-security-policy"]
