from fastapi import APIRouter

from app.utils.types.groups_type import GroupType


class Module:
    """Module representation in Hyperion"""

    def __init__(
        self,
        router=APIRouter(),
        default_allowed_groups_ids: list[GroupType] = [],
    ):
        self.router = router
        self.default_allowed_groups_ids = default_allowed_groups_ids
