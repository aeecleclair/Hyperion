from fastapi import APIRouter

from app.core.groups.groups_type import GroupType


class Module:
    def __init__(
        self,
        root: str,
        default_allowed_groups_ids: list[GroupType],
        router: APIRouter | None = None,
    ):
        """
        Initialize a new Module object.
        :param root: the root of the module, used by Titan
        :param default_allowed_groups_ids: list of groups that should be able to see the module by default
        :param router: an optional custom APIRouter
        """
        self.root = root
        self.default_allowed_groups_ids = default_allowed_groups_ids
        self.router = router or APIRouter()
