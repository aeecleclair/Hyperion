"""File defining all the routes for the module, to configure the router"""

from fastapi import APIRouter

from app.endpoints import (
    admin,
    advert,
    amap,
    associations,
    auth,
    booking,
    calendar,
    campaign,
    cinema,
    core,
    groups,
    loan,
    notification,
    raffle,
    todos,
    users,
)

api_router = APIRouter()

api_router.include_router(admin.router)
api_router.include_router(advert.router)
api_router.include_router(amap.router)
api_router.include_router(associations.router)
api_router.include_router(auth.router)
api_router.include_router(booking.router)
api_router.include_router(calendar.router)
api_router.include_router(campaign.router)
api_router.include_router(cinema.router)
api_router.include_router(core.router)
api_router.include_router(groups.router)
api_router.include_router(loan.router)
api_router.include_router(notification.router)
api_router.include_router(raffle.router)
api_router.include_router(todos.router)
api_router.include_router(users.router)
