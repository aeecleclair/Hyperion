from enum import Enum

from app.utils.types.groups_type import GroupType
from app.utils.types.module import Module


class ModuleList(Module, Enum):
    admin = Module(
        root="/admin",
        default_allowed_groups_ids=[GroupType.admin],
    )
    amap = Module(
        root="/amap",
        default_allowed_groups_ids=[GroupType.student, GroupType.admin],
    )
    bdebooking = Module(
        root="/booking",
        default_allowed_groups_ids=[GroupType.admin, GroupType.student],
    )
    calendar = Module(
        root="/calendar",
        default_allowed_groups_ids=[GroupType.student],
    )
    campaign = Module(
        root="/campaign",
        default_allowed_groups_ids=[],
    )
    cinema = Module(
        root="/cinema",
        default_allowed_groups_ids=[GroupType.admin],
    )
    loan = Module(
        root="/loan",
        default_allowed_groups_ids=[GroupType.admin],
    )
    raffle = Module(
        root="/tombola",
        default_allowed_groups_ids=[],
    )
