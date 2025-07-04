"""File defining all the routes for the module, to configure the router"""

from fastapi import APIRouter

from app.module import all_modules

api_router = APIRouter()


for core_module in all_modules:
    api_router.include_router(core_module.router)
