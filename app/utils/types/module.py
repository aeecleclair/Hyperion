from app.utils.types.groups_type import GroupType


class Module:
    """Module representation in Hyperion"""

    def __init__(
        self,
        root: str,
        default_allowed_groups_ids: list[GroupType] = [],
    ):
        self.root = root
        self.default_allowed_groups_ids = default_allowed_groups_ids
