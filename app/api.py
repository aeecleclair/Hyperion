"""File defining all the routes for the module, to configure the router"""

from fastapi import APIRouter

from app.endpoints import amap, associations, bdebooking, bdecalendar, groups, users

api_router = APIRouter()
api_router.include_router(amap.router)
api_router.include_router(associations.router)
api_router.include_router(bdebooking.router)
api_router.include_router(bdecalendar.router)
api_router.include_router(groups.router)
api_router.include_router(users.router)
