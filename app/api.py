"""File defining all the routes for the module, to configure the router"""

from fastapi import APIRouter

from app.core.core_module_list import core_module_list
from app.modules.module_list import module_list

api_router = APIRouter()


for core_module in core_module_list:
    api_router.include_router(core_module.router)

for module in module_list:
    api_router.include_router(module.router)
