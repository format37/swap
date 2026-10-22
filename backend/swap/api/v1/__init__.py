"""The Mini App's REST API, version 1."""

from fastapi import APIRouter

from swap.api.v1 import auth, deals, links, me, network, orders, quote

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(me.router)
router.include_router(links.router)
router.include_router(network.router)
router.include_router(orders.router)
router.include_router(quote.router)
router.include_router(deals.router)
