"""Request dependencies shared by the routers."""

from collections.abc import AsyncIterator
from typing import Annotated, cast

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from swap.api.errors import ApiError
from swap.config import Settings
from swap.db import Sessionmaker
from swap.market import Market
from swap.models import AuthSession, User
from swap.sessions import hash_token


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    sessionmaker = cast(Sessionmaker, request.app.state.sessionmaker)
    async with sessionmaker() as session:
        yield session


def get_app_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_market(request: Request) -> Market:
    return cast(Market, request.app.state.market)


Db = Annotated[AsyncSession, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_app_settings)]
MarketRates = Annotated[Market, Depends(get_market)]

# auto_error=False: a missing header is our own 401 problem, not FastAPI's 403.
_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    db: Db, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]
) -> User:
    if credentials is None:
        raise ApiError(401, "unauthorized")
    user = await db.scalar(
        select(User)
        .join(AuthSession, AuthSession.user_id == User.id)
        .where(
            AuthSession.token_hash == hash_token(credentials.credentials),
            AuthSession.expires_at > func.now(),
        )
    )
    if user is None:
        raise ApiError(401, "unauthorized")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
