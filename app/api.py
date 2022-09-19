"""File defining all the routes for the module, to configure the router"""

from fastapi import APIRouter

from app.endpoints import (
    admin,
    amap,
    associations,
    auth,
    bdebooking,
    calendar,
    campaign,
    core,
    groups,
    loans,
    users,
)

api_router = APIRouter()
api_router.include_router(admin.router)
api_router.include_router(amap.router)
api_router.include_router(associations.router)
api_router.include_router(auth.router)
api_router.include_router(bdebooking.router)
api_router.include_router(calendar.router)
api_router.include_router(campaign.router)
api_router.include_router(groups.router)
api_router.include_router(core.router)
api_router.include_router(users.router)
api_router.include_router(loans.router)
api_router.include_router(campaign.router)
