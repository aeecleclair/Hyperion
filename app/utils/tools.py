from rapidfuzz import process
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_groups, cruds_users
from app.models import models_core
from app.models.models_core import CoreUser
from app.utils.types.groups_type import GroupType


def is_user_member_of_an_allowed_group(
    user: CoreUser,
    allowed_groups: list[GroupType] | list[str],
) -> bool:
    """
    Test if the provided user is a member of at least one group from `allowed_groups`.

    When required groups can only be determined on runtime a list of strings (group UUIDs) can be provided.
    This may be useful for modules that can be used multiple times like loans module.
    NOTE: if the provided string does not match a valid group, the function will return False
    """
    # We can not directly test is group_id is in user.groups
    # As user.groups is a list of CoreGroup and group_id is an UUID
    for allowed_group in allowed_groups:
        for user_group in user.groups:
            if allowed_group == user_group.id:
                # We know the user is a member of at least one allowed group
                return True
    return False


def fuzzy_search_user(
    query: str,
    users: list[models_core.CoreUser],
    limit: int = 10,
) -> list[models_core.CoreUser]:
    """
    Search for users using Fuzzy String Matching

    `query` will be compared against `users` name, firstname and nickname.
    The size of the answer can be limited using `limit` parameter.

    Use RapidFuzz library
    """

    # We can give a dictionary of {object: string used for the comparison} to the extract function
    # https://maxbachmann.github.io/RapidFuzz/Usage/process.html#extract

    # TODO: we may want to cache this object. Its generation may take some time if there is a big user base
    choices = {}

    for user in users:
        choices[user] = f"{user.firstname} {user.name} {user.nickname}"

    results: list[tuple[str, int | float, models_core.CoreUser]] = process.extract(
        query, choices, limit=limit
    )

    # results has the format : (string used for the comparison, similarity score, object)
    return [res[2] for res in results]


async def is_group_id_valid(group_id: str, db: AsyncSession) -> bool:
    """
    Test if the provided group_id is a valid group.

    The group may be
     - an account type
     - a group type
     - a group created on runtime and stored in the database
    """
    return await cruds_groups.get_group_by_id(db=db, group_id=group_id) is not None


async def is_user_id_valid(user_id: str, db: AsyncSession) -> bool:
    """
    Test if the provided user_id is a valid user.
    """
    return await cruds_users.get_user_by_id(db=db, user_id=user_id) is not None
