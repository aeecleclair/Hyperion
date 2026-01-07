import logging
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups import groups_type
from app.core.users import models_users
from app.dependencies import (
    get_db,
    get_user_from_token_with_scopes,
    get_user_id_from_token_with_scopes,
)
from app.modules.sport_competition import (
    cruds_sport_competition,
    schemas_sport_competition,
)
from app.modules.sport_competition.permissions_sport_competition import (
    SportCompetitionPermissions,
)
from app.modules.sport_competition.types_sport_competition import CompetitionGroupType
from app.types.scopes_type import ScopeType
from app.utils.tools import has_user_permission

hyperion_access_logger = logging.getLogger("hyperion.access")


def get_competition_user_from_token_with_scopes(
    scopes: list[list[ScopeType]],
) -> Callable[
    [AsyncSession, str],
    Coroutine[Any, Any, schemas_sport_competition.CompetitionUser],
]:
    """
    Generate a dependency which will:
     * check the request header contain a valid JWT token
     * make sure the token contain the given scopes
     * return the corresponding user `models_users.CoreUser` object

    This endpoint allows to require scopes other than the API scope. This should only be used by the auth endpoints.
    To restrict an endpoint from the API, use `is_user_in`.
    """

    async def get_user_from_user_id(
        db: AsyncSession = Depends(get_db),
        user_id: str = Depends(get_user_id_from_token_with_scopes(scopes)),
        edition: schemas_sport_competition.CompetitionEdition = Depends(
            get_current_edition,
        ),
    ) -> schemas_sport_competition.CompetitionUser:
        """
        Dependency that makes sure the token is valid, contains the expected scopes and returns the corresponding user.
        The expected scopes are passed as list of list of scopes, each list of scopes is an "AND" condition, and the list of list of scopes is an "OR" condition.
        """
        user = await cruds_sport_competition.load_competition_user_by_id(
            db=db,
            user_id=user_id,
            edition_id=edition.id,
        )
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    return get_user_from_user_id


def is_competition_user(
    group_id: str | None = None,
    competition_group: CompetitionGroupType | None = None,
    exclude_external: bool = False,
) -> Callable[
    [schemas_sport_competition.CompetitionUser],
    Coroutine[Any, Any, schemas_sport_competition.CompetitionUser],
]:
    """
    Generate a dependency which will:
        * check if the request header contains a valid API JWT token (a token that can be used to call endpoints from the API)
        * make sure the user making the request exists and is a member of the group with the given id (if provided)
        * make sure the user is a member of the competition group with the given id for the current edition (if provided)
    """

    async def is_user_a_member_of(
        user: schemas_sport_competition.CompetitionUser = Depends(
            get_competition_user_from_token_with_scopes([[ScopeType.API]]),
        ),
        edition: schemas_sport_competition.CompetitionEdition = Depends(
            get_current_edition,
        ),
        db: AsyncSession = Depends(get_db),
    ) -> schemas_sport_competition.CompetitionUser:
        """
        A dependency that checks that user is a member of the group with the given id then returns the corresponding user.
        """
        if (
            exclude_external
            and user.user.account_type == groups_type.AccountType.external
        ):
            raise HTTPException(
                status_code=403,
                detail="User is external",
            )
        if group_id is not None and not any(
            group.id == group_id for group in user.user.groups
        ):
            raise HTTPException(
                status_code=403,
                detail="User is not a member of the group",
            )
        if competition_group is not None and not (
            await has_user_permission(
                user.user,
                SportCompetitionPermissions.manage_sport_competition,
                db,
            )
        ):
            user_groups = (
                await cruds_sport_competition.load_user_competition_groups_memberships(
                    db=db,
                    user_id=user.user_id,
                    edition_id=edition.id,
                )
            )
            if not any(group.group == competition_group for group in user_groups):
                raise HTTPException(
                    status_code=403,
                    detail="User is not a member of the competition group",
                )
        return user

    return is_user_a_member_of


def has_user_competition_access(
    group_id: str | None = None,
    competition_group: CompetitionGroupType | None = None,
    exclude_external: bool = False,
) -> Callable[
    [models_users.CoreUser],
    Coroutine[Any, Any, models_users.CoreUser],
]:
    """
    Generate a dependency which will:
        * check if the request header contains a valid API JWT token (a token that can be used to call endpoints from the API)
        * make sure the user making the request exists and is a member of the group with the given id (if provided)
        * make sure the user is a member of the competition group with the given id for the current edition (if provided)
    """

    async def is_user_a_member_of(
        user: models_users.CoreUser = Depends(
            get_user_from_token_with_scopes([[ScopeType.API]]),
        ),
        edition: schemas_sport_competition.CompetitionEdition = Depends(
            get_current_edition,
        ),
        db: AsyncSession = Depends(get_db),
    ) -> models_users.CoreUser:
        """
        A dependency that checks that user is a member of the group with the given id then returns the corresponding user.
        """
        if exclude_external and user.account_type == groups_type.AccountType.external:
            raise HTTPException(
                status_code=403,
                detail="User is external",
            )
        if group_id is not None and not any(
            group.id == group_id for group in user.groups
        ):
            raise HTTPException(
                status_code=403,
                detail="User is not a member of the group",
            )
        if competition_group is not None and not (
            await has_user_permission(
                user,
                SportCompetitionPermissions.manage_sport_competition,
                db,
            )
        ):
            user_groups = (
                await cruds_sport_competition.load_user_competition_groups_memberships(
                    db=db,
                    user_id=user.id,
                    edition_id=edition.id,
                )
            )
            if not any(group.group == competition_group for group in user_groups):
                raise HTTPException(
                    status_code=403,
                    detail="User is not a member of the competition group",
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
