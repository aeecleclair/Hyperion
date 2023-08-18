"""File defining all the routes for the module, to configure the router"""

from fastapi import APIRouter

from app.utils.types.module_list import CoreRouter, ModuleList

api_router = APIRouter()
for module in ModuleList:
    api_router.include_router(module.value.router)

for core_module in CoreRouter:
    api_router.include_router(module.value.router)
