"""File defining all the routes for the module, to configure the router"""

from enum import Enum

from fastapi import APIRouter

from app.endpoints import (
    admin,
    amap,
    associations,
    auth,
    bdebooking,
    calendar,
    campaign,
    cinema,
    core,
    groups,
    loan,
    module_visibility,
    raffle,
    users,
)
from app.utils.types.module import Module


class ModuleList(Module, Enum):
    admin = admin.admin
    amap = amap.amap
    bdebooking = bdebooking.bdebooking
    calendar = calendar.calendar
    campaign = campaign.campaign
    cinema = cinema.cinema
    loan = loan.loan
    raffle = raffle.raffle


class CoreRouter(Module, Enum):
    """Router for core elements of Hyperion"""

    associations = associations.associations
    auth = auth.auth
    core = core.core
    groups = groups.groups
    module_visibility = module_visibility.module_visibility
    users = users.users


api_router = APIRouter()
for module in ModuleList:
    api_router.include_router(module.value.router)

for core_module in CoreRouter:
    api_router.include_router(module.value.router)
