import logging
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.groups_type import GroupType
from app.core.users import models_users
from app.dependencies import get_db, is_user
from app.modules.sport_competition import (
    cruds_sport_competition,
    schemas_sport_competition,
)
from app.modules.sport_competition.types_sport_competition import CompetitionGroupType

hyperion_access_logger = logging.getLogger("hyperion.access")


def is_user_a_member_of_extended(
    group_id: GroupType | None = None,
    comptition_group_id: CompetitionGroupType | None = None,
    exclude_external: bool = False,
) -> Callable[[models_users.CoreUser], Coroutine[Any, Any, models_users.CoreUser]]:
    """
    Generate a dependency which will:
        * check if the request header contains a valid API JWT token (a token that can be used to call endpoints from the API)
        * make sure the user making the request exists and is a member of the group with the given id
        * make sure the user is not an external user if `exclude_external` is True
        * return the corresponding user `models_users.CoreUser` object
    """

    async def is_user_a_member_of(
        user: models_users.CoreUser = Depends(
            is_user(
                included_groups=[group_id] if group_id else None,
                exclude_external=exclude_external,
            ),
        ),
        edition: schemas_sport_competition.CompetitionEdition = Depends(
            get_current_edition,
        ),
        db: AsyncSession = Depends(get_db),
    ) -> models_users.CoreUser:
        """
        A dependency that checks that user is a member of the group with the given id then returns the corresponding user.
        """
        if comptition_group_id is None:
            return user
        membership = cruds_sport_competition.load_user_membership_with_group_id(
            user_id=user.id,
            group_id=comptition_group_id,
            edition_id=edition.id,
            db=db,
        )
        if not membership:
            raise HTTPException(
                status_code=403,
                detail="User is not a member of the group",
            )
        return user

    return is_user_a_member_of


async def get_current_edition(
    db: AsyncSession = Depends(get_db),
) -> schemas_sport_competition.CompetitionEdition:
    """
    Dependency that returns the current edition
    """
    current_edition = await cruds_sport_competition.load_active_edition(db)
    if not current_edition:
        raise HTTPException(
            status_code=404,
            detail="No current edition",
        )
    return current_edition
