from enum import Enum

from app.utils.types.groups_type import GroupType
from app.utils.types.module import Module


class ModuleList(Module, Enum):
    advert = Module(
        root="advert",
        default_allowed_groups_ids=[GroupType.student, GroupType.staff],
    )
    amap = Module(
        root="amap",
        default_allowed_groups_ids=[GroupType.student, GroupType.staff],
    )
    bdebooking = Module(
        root="booking",
        default_allowed_groups_ids=[GroupType.student, GroupType.staff],
    )
    centralisation = Module(
        root="centralisation",
        default_allowed_groups_ids=[GroupType.student, GroupType.staff],
    )
    cinema = Module(
        root="cinema",
        default_allowed_groups_ids=[GroupType.student, GroupType.staff],
    )
    calendar = Module(
        root="home",
        default_allowed_groups_ids=[GroupType.student, GroupType.staff],
    )
    event = Module(
        root="event",
        default_allowed_groups_ids=[GroupType.student, GroupType.staff],
    )
    loan = Module(
        root="loan",
        default_allowed_groups_ids=[GroupType.student, GroupType.staff],
    )
    raffle = Module(
        root="tombola",
        default_allowed_groups_ids=[GroupType.student, GroupType.staff],
    )
    campaign = Module(
        root="vote",
        default_allowed_groups_ids=[GroupType.AE],
    )
