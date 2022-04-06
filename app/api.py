from fastapi import APIRouter
from app.endpoints import amap, associations, bdebooking, bdecalendar, groups, users


api_router = (
    APIRouter()
)  # Create a router for the API endpoints (see https://fastapi.tiangolo.com/tutorial/routing/)
api_router.include_router(amap.router, prefix="/amap")
api_router.include_router(associations.router)
api_router.include_router(bdebooking.router, prefix="/bdebooking")
api_router.include_router(bdecalendar.router, prefix="/bdecalendar")
api_router.include_router(groups.router)
api_router.include_router(users.router)
