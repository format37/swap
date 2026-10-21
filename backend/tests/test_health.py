from datetime import UTC, datetime, timedelta

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from swap.api.app import create_app
from swap.config import Settings
from swap.models import ServiceHeartbeat


async def test_ok_without_a_worker_heartbeat(client: AsyncClient) -> None:
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "worker_heartbeat_age_s": None}


async def test_reports_the_age_of_the_worker_heartbeat(
    client: AsyncClient, sessionmaker: async_sessionmaker[AsyncSession]
) -> None:
    async with sessionmaker() as db:
        db.add(ServiceHeartbeat(name="worker", beat_at=datetime.now(UTC) - timedelta(seconds=40)))
        await db.commit()

    age = (await client.get("/healthz")).json()["worker_heartbeat_age_s"]
    assert 39 < age < 60


async def test_a_dead_database_is_a_503_problem(settings: Settings) -> None:
    # Port 1 refuses at once, which is all a dead database looks like from here.
    engine = create_async_engine("postgresql+asyncpg://swap:swap@127.0.0.1:1/swap")
    app = create_app(settings, sessionmaker=async_sessionmaker(engine))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/healthz")
    await engine.dispose()

    assert response.status_code == 503
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["code"] == "database_unavailable"
