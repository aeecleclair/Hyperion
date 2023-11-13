"""File defining all the routes for the module, to configure the router"""

from fastapi import APIRouter

from app.core import endpoints_core
from app.core.auth import endpoints_auth
from app.core.groups import endpoints_groups
from app.core.notification import endpoints_notification
from app.core.users import endpoints_users
from app.modules.advert import endpoints_advert
from app.modules.amap import endpoints_amap
from app.modules.booking import endpoints_booking
from app.modules.calendar import endpoints_calendar
from app.modules.campaign import endpoints_campaign
from app.modules.cinema import endpoints_cinema
from app.modules.loan import endpoints_loan
from app.modules.raffle import endpoints_raffle

api_router = APIRouter()

api_router.include_router(endpoints_advert.router)
api_router.include_router(endpoints_amap.router)
api_router.include_router(endpoints_auth.router)
api_router.include_router(endpoints_booking.router)
api_router.include_router(endpoints_calendar.router)
api_router.include_router(endpoints_campaign.router)
api_router.include_router(endpoints_cinema.router)
api_router.include_router(endpoints_core.router)
api_router.include_router(endpoints_groups.router)
api_router.include_router(endpoints_loan.router)
api_router.include_router(endpoints_notification.router)
api_router.include_router(endpoints_raffle.router)
api_router.include_router(endpoints_users.router)
