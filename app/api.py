from fastapi import APIRouter

from app.endpoints import amap, associations, bdebooking, bdecalendar, users, auth

api_router = APIRouter()
api_router.include_router(amap.router, prefix="/amap")
api_router.include_router(associations.router)
api_router.include_router(bdebooking.router, prefix="/bdebooking")
api_router.include_router(bdecalendar.router, prefix="/bdecalendar")
api_router.include_router(users.router)
api_router.include_router(auth.router)
