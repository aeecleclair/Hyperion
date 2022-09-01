"""File defining all the routes for the module, to configure the router"""

from fastapi import APIRouter

from app.endpoints import family

api_router = APIRouter()

api_router.include_router(family.router)
