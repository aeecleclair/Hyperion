from fastapi import APIRouter

from app.utils.types.groups_type import GroupType


class Module:
    """Module representation in Hyperion"""

    def __init__(
        self,
        root,
        router=APIRouter(),
        default_allowed_groups_ids: list[GroupType] = [],
    ):
        self.root = root
        self.router = router
        self.default_allowed_groups_ids = default_allowed_groups_ids
