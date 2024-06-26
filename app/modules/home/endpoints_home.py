from app.core.groups.groups_type import GroupType
from app.types.module import Module

module = Module(
    root="home",
    tag="Home",
    default_allowed_groups_ids=[GroupType.student, GroupType.staff],
)
