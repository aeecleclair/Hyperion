"""File defining all the routes for the module, to configure the router"""

import glob
import importlib
import logging

from fastapi import APIRouter

from app.core import endpoints_core
from app.core.auth import endpoints_auth
from app.core.groups import endpoints_groups
from app.core.module import Module
from app.core.notification import endpoints_notification
from app.core.users import endpoints_users

hyperion_error_logger = logging.getLogger("hyperion.error")

module_list: list[Module] = []
api_router = APIRouter()

api_router.include_router(endpoints_auth.router)
api_router.include_router(endpoints_core.router)
api_router.include_router(endpoints_groups.router)
api_router.include_router(endpoints_notification.router)
api_router.include_router(endpoints_users.router)

for endpoints_file in glob.glob("./app/modules/*/endpoints_*.py"):
    endpoint_module = importlib.import_module(endpoints_file[2:-3].replace("/", "."))
    if hasattr(endpoint_module, "module"):
        module: Module = endpoint_module.module
        module_list.append(module)
        api_router.include_router(module.router)
    else:
        hyperion_error_logger.error(
            f"Module {endpoints_file.split('/')[3]} does not declare a module. It won't be enabled."
        )
