from app.core.groups.groups_type import GroupType
from app.core.module import Module

module = Module(
    root="home",
    default_allowed_groups_ids=[GroupType.student, GroupType.staff],
)
