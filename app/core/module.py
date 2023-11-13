from fastapi import APIRouter

from app.core.groups.groups_type import GroupType


class Module:
    """Module representation in Hyperion"""

    def __init__(
        self,
        root: str,
        default_allowed_groups_ids: list[GroupType] | None = None,
        router: APIRouter | None = None,
    ):
        self.root = root
        self.default_allowed_groups_ids = default_allowed_groups_ids or []
        self.router = router or APIRouter()
