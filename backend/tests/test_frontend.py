from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from swap.api.app import create_app
from swap.config import Settings


@pytest.fixture
async def site(
    tmp_path: Path, settings: Settings, sessionmaker: async_sessionmaker[AsyncSession]
) -> AsyncIterator[AsyncClient]:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>Swap</title>")
    (dist / "assets" / "index-abc123.js").write_text("console.log('swap')")
    (dist / "icon.svg").write_text("<svg/>")
    (dist / "privacy.html").write_text("<!doctype html><title>Swap: privacy</title>")
    (tmp_path / "secret.txt").write_text("outside the build")
    app = create_app(
        settings.model_copy(update={"static_dir": str(dist)}), sessionmaker=sessionmaker
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


async def test_client_routes_get_the_shell_revalidated(site: AsyncClient) -> None:
    for path in ("/", "/deals/123", "/settings/language"):
        response = await site.get(path)
        assert response.status_code == 200
        assert "<title>Swap</title>" in response.text
        assert response.headers["cache-control"] == "no-cache"


async def test_hashed_assets_are_immutable(site: AsyncClient) -> None:
    response = await site.get("/assets/index-abc123.js")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "public, max-age=31536000, immutable"


async def test_root_files_are_served_as_they_are(site: AsyncClient) -> None:
    response = await site.get("/icon.svg")
    assert response.status_code == 200
    assert response.text == "<svg/>"


async def test_a_page_of_its_own_opens_outside_the_app(site: AsyncClient) -> None:
    # The privacy page, for a plain browser and BotFather (QUESTIONS K3).
    for path in ("/privacy", "/privacy.html"):
        response = await site.get(path)
        assert response.status_code == 200
        assert "<title>Swap: privacy</title>" in response.text
    assert "<title>Swap</title>" in (await site.get("/privacy/more")).text


async def test_unknown_api_paths_stay_problems_not_the_shell(site: AsyncClient) -> None:
    response = await site.get("/api/v1/nothing-here")
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


async def test_no_file_outside_the_build_is_reachable(site: AsyncClient) -> None:
    for path in ("/../secret.txt", "/%2e%2e/secret.txt", "/assets/../../secret.txt"):
        response = await site.get(path)
        assert "outside the build" not in response.text
