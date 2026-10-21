"""The Mini App's REST API, version 1."""

from fastapi import APIRouter

from swap.api.v1 import auth, links, me

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(me.router)
router.include_router(links.router)
