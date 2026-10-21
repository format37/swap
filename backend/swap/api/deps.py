"""Request dependencies shared by the routers."""

from collections.abc import AsyncIterator
from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from swap.config import Settings
from swap.db import Sessionmaker


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    sessionmaker = cast(Sessionmaker, request.app.state.sessionmaker)
    async with sessionmaker() as session:
        yield session


def get_app_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


Db = Annotated[AsyncSession, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_app_settings)]
