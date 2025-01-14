"""File defining all the routes for the module, to configure the router"""

import logging

from fastapi import APIRouter

from app.core import endpoints_core
from app.core.auth import endpoints_auth
from app.core.google_api import endpoints_google_api
from app.core.groups import endpoints_groups
from app.core.notification import endpoints_notification
from app.core.payment import endpoints_payment
from app.core.schools import endpoints_schools
from app.core.users import endpoints_users
from app.modules.module_list import module_list

hyperion_error_logger = logging.getLogger("hyperion.error")

api_router = APIRouter()

api_router.include_router(endpoints_auth.router)
api_router.include_router(endpoints_core.router)
api_router.include_router(endpoints_google_api.router)
api_router.include_router(endpoints_groups.router)
api_router.include_router(endpoints_notification.router)
api_router.include_router(endpoints_payment.router)
api_router.include_router(endpoints_users.router)
api_router.include_router(endpoints_schools.router)

for module in module_list:
    api_router.include_router(module.router)
