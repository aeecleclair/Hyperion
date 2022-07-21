from app.models.models_core import CoreUser
from app.utils.types.groups_type import GroupType


def is_user_member_of_an_allowed_group(user: CoreUser, allowed_groups: list[GroupType]):
    # We can not directly test is group_id is in user.groups
    # As user.groups is a list of CoreGroup and group_id is an UUID
    for allowed_group in allowed_groups:
        for user_group in user.groups:
            if allowed_group == user_group.id:
                # We know the user is a member of at least one allowed group
                return True
    return False
