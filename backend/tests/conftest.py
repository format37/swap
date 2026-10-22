"""Shared fixtures: real Postgres, migrated from scratch once per run, and a
transaction per test that is rolled back afterwards."""

import asyncio
import os
from collections.abc import AsyncIterator

import asyncpg
import httpx
import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy import make_url
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from swap.api.app import create_app
from swap.config import Settings
from swap.market import Market

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://swap:swap@127.0.0.1:5436/swap_test"
)
# Built at run time, so the repository holds nothing a secret scanner reads as a token.
TEST_BOT_TOKEN = "123456789:" + "T" * 35
# Coinbase's table as it was on 2026-10-22, cut short: tests never call out (ADR-0020).
COINBASE = {
    "data": {
        "currency": "USD",
        "rates": {
            "RUB": "81.386641",
            "GEL": "2.5924766666666667",
            "EUR": "0.889521046386925",
            "USDT": "1.001081167661074",
            "USD": "1.0",
        },
    }
}


async def _ensure_database(url: str) -> None:
    target = make_url(url)
    conn = await asyncpg.connect(
        user=target.username,
        password=target.password,
        host=target.host,
        port=target.port,
        database="postgres",
    )
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", target.database
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{target.database}"')
    finally:
        await conn.close()


def _migrate(url: str) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    # From scratch on every run, so a model edited without a migration can't hide
    # behind a schema left over from an earlier run.
    command.downgrade(config, "base")
    command.upgrade(config, "head")


@pytest.fixture(scope="session")
async def engine() -> AsyncIterator[AsyncEngine]:
    await _ensure_database(TEST_DATABASE_URL)
    # env.py runs its own event loop, so it gets a thread of its own.
    await asyncio.to_thread(_migrate, TEST_DATABASE_URL)
    engine = create_async_engine(TEST_DATABASE_URL)
    yield engine
    await engine.dispose()


@pytest.fixture
async def connection(engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
    async with engine.connect() as conn:
        transaction = await conn.begin()
        yield conn
        await transaction.rollback()


@pytest.fixture
def sessionmaker(connection: AsyncConnection) -> async_sessionmaker[AsyncSession]:
    # A commit in the code under test only releases a savepoint. The test's own
    # transaction is rolled back at the end, so no test sees another's rows.
    return async_sessionmaker(
        bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_env="test",
        database_url=TEST_DATABASE_URL,
        telegram_bot_token=SecretStr(TEST_BOT_TOKEN),
        log_format="console",
    )


@pytest.fixture
async def client(
    settings: Settings, sessionmaker: async_sessionmaker[AsyncSession]
) -> AsyncIterator[AsyncClient]:
    coinbase = httpx.MockTransport(lambda request: httpx.Response(200, json=COINBASE))
    async with httpx.AsyncClient(transport=coinbase) as outside:
        app = create_app(settings, sessionmaker=sessionmaker, market=Market(outside))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client
