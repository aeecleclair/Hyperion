import logging
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import schemas_auth
from app.core.auth.dependencies_auth import get_token_with_scopes
from app.core.groups import groups_type
from app.dependencies import get_db
from app.modules.sport_competition import (
    cruds_sport_competition,
    schemas_sport_competition,
)
from app.modules.sport_competition.permissions_sport_competition import (
    SportCompetitionPermissions,
)
from app.modules.sport_competition.types_sport_competition import CompetitionGroupType
from app.types.scopes_type import ScopeType

hyperion_access_logger = logging.getLogger("hyperion.access")


def is_competition_user() -> Callable[
    [
        AsyncSession,
        schemas_auth.FunctionalTokenData,
        schemas_sport_competition.CompetitionEdition,
    ],
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
        token: schemas_auth.FunctionalTokenData = Depends(
            get_token_with_scopes([[ScopeType.API]]),
        ),
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
            user_id=token.id,
            edition_id=edition.id,
        )
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    return get_user_from_user_id


def has_user_competition_access(
    group_id: str | None = None,
    competition_group: CompetitionGroupType | None = None,
    exclude_external: bool = False,
) -> Callable[
    [
        schemas_auth.FunctionalTokenData,
        schemas_sport_competition.CompetitionEdition,
        AsyncSession,
    ],
    Coroutine[Any, Any, schemas_auth.FunctionalTokenData],
]:
    """
    Generate a dependency which will:
        * check if the request header contains a valid API JWT token (a token that can be used to call endpoints from the API)
        * make sure the user making the request exists and is a member of the group with the given id (if provided)
        * make sure the user is a member of the competition group with the given id for the current edition (if provided)
    """

    async def is_user_a_member_of(
        token: schemas_auth.FunctionalTokenData = Depends(
            get_token_with_scopes([[ScopeType.API]]),
        ),
        edition: schemas_sport_competition.CompetitionEdition = Depends(
            get_current_edition,
        ),
        db: AsyncSession = Depends(get_db),
    ) -> schemas_auth.FunctionalTokenData:
        """
        A dependency that checks that user is a member of the group with the given id then returns the corresponding user.
        """
        if exclude_external and token.account_type == groups_type.AccountType.external:
            raise HTTPException(
                status_code=403,
                detail="User is external",
            )
        if group_id is not None and not any(
            group == group_id for group in token.group_ids
        ):
            raise HTTPException(
                status_code=403,
                detail="User is not a member of the group",
            )
        if competition_group is not None and not (
            await token.check_permission(
                SportCompetitionPermissions.manage_sport_competition,
                db,
            )
        ):
            user_groups = (
                await cruds_sport_competition.load_user_competition_groups_memberships(
                    db=db,
                    user_id=token.id,
                    edition_id=edition.id,
                )
            )
            if not any(group.group == competition_group for group in user_groups):
                raise HTTPException(
                    status_code=403,
                    detail="User is not a member of the competition group",
                )
        return token

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
