import json
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Depends, HTTPException
from redis import Redis
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from app.core.auth import schemas_auth
from app.core.groups.groups_type import AccountType, GroupType
from app.core.permissions.cruds_permissions import get_permissions_by_permission_name
from app.core.permissions.type_permissions import ModulePermissions
from app.core.utils import security
from app.core.utils.config import Settings
from app.dependencies import get_db, get_redis_client, get_request_id, get_settings
from app.types.exceptions import TokenClassMismatchError
from app.types.scopes_type import ScopeType
from app.utils.auth import auth_utils

# Keep permissions in Redis for 1 hour
PERMISSION_CACHE_TTL = 3600

CACHE_KEY_PREFIX = "core:permissions:"


async def get_cached_permission_requirements(
    permission_name: ModulePermissions,
    db: AsyncSession,
    settings: Settings,
    redis_client: Redis | None = None,
) -> tuple[list[str], list[AccountType]]:
    cache_key = CACHE_KEY_PREFIX + permission_name
    if settings.ENABLE_REDIS_CACHE and redis_client is not None:
        cached_data = redis_client.get(cache_key)

        if cached_data is not None:
            # Decode the JSON payload from Redis
            data = json.loads(cached_data)
            account_types = [AccountType(acc) for acc in data["account_types"]]
            return (data["groups"], account_types)

    # Cache miss: fetch from PostgreSQL
    perm_config = await get_permissions_by_permission_name(
        db,
        permission_name,
    )

    if settings.ENABLE_REDIS_CACHE and redis_client is not None:
        # Save to Redis and set expiration
        redis_client.set(
            cache_key,
            json.dumps(
                {
                    "groups": perm_config.groups,
                    "account_types": [acc.value for acc in perm_config.account_types],
                },
            ),
            ex=PERMISSION_CACHE_TTL,
        )

    return perm_config.groups, perm_config.account_types


def get_token_data(
    settings: Settings = Depends(get_settings),
    token: str = Depends(security.oauth2_scheme),
    request_id: str = Depends(get_request_id),
    redis_client: Redis | None = Depends(get_redis_client),
) -> schemas_auth.FunctionalTokenData:
    """
    Dependency that returns the token payload data
    """
    token_data = auth_utils.get_token_data(
        settings=settings,
        token=token,
        request_id=request_id,
    )
    return schemas_auth.FunctionalTokenData(
        sub=token_data.sub,
        iss=token_data.iss,
        aud=token_data.aud,
        cid=token_data.cid,
        iat=token_data.iat,
        nonce=token_data.nonce,
        scopes=token_data.scopes,
        account_type=token_data.account_type,
        group_ids=token_data.group_ids,
        school_id=token_data.school_id,
        settings=settings,
        redis_client=redis_client,
    )


def get_token_with_scopes(
    scopes: list[list[ScopeType]],
) -> Callable[
    [schemas_auth.FunctionalTokenData],
    schemas_auth.FunctionalTokenData,
]:
    """
    Generate a dependency which will:
     * check the request header contain a valid JWT token
     * make sure the token contain the given scopes
     * return the token data

    This endpoint allows to require scopes other than the API scope. This should only be used by the auth endpoints.
    To restrict an endpoint from the API, use `is_user_in`.
    """

    def get_current_token_data(
        token_data: schemas_auth.FunctionalTokenData = Depends(get_token_data),
    ) -> schemas_auth.FunctionalTokenData:
        """
        Dependency that makes sure the token is valid, contains the expected scopes and returns the corresponding user_id.
        The expected scopes are passed as list of list of scopes, each list of scopes is an "AND" condition, and the list of list of scopes is an "OR" condition.
        """

        token = auth_utils.get_token_with_scopes(
            scopes=scopes,
            token_data=token_data,
        )
        if not isinstance(token, schemas_auth.FunctionalTokenData):
            raise TokenClassMismatchError(
                type(token).__name__,
                schemas_auth.FunctionalTokenData.__name__,
            )
        return token

    return get_current_token_data


def filter_user_token(
    *,
    excluded_groups: list[GroupType | str] | None = None,
    included_groups: list[GroupType | str] | None = None,
    excluded_account_types: list[AccountType] | None = None,
    included_account_types: list[AccountType] | None = None,
    exclude_external: bool = False,
) -> Callable[[schemas_auth.FunctionalTokenData], schemas_auth.FunctionalTokenData]:
    """
    A dependency that will:
        * check if the request header contains a valid API JWT token (a token that can be used to call endpoints from the API)
        * filter the user based on the provided groups and account types
    """

    excluded_groups = excluded_groups or []
    excluded_account_types = excluded_account_types or []
    included_account_types = included_account_types or list(AccountType)

    def filter_token(
        token: schemas_auth.FunctionalTokenData = Depends(
            get_token_with_scopes([[ScopeType.API]]),
        ),
    ) -> schemas_auth.FunctionalTokenData:
        if GroupType.admin in token.group_ids:
            return token
        if token.account_type in excluded_account_types:
            raise HTTPException(
                status_code=403,
                detail="Unauthorized, user account type is not allowed",
            )
        if exclude_external and token.account_type == AccountType.external:
            raise HTTPException(
                status_code=403,
                detail="Unauthorized, user is an external user",
            )
        if any(group_id in token.group_ids for group_id in excluded_groups):
            raise HTTPException(
                status_code=403,
                detail=f"Unauthorized, user is a member of any of the groups {excluded_groups}",
            )
        if included_groups is not None and not any(
            group_id in token.group_ids for group_id in included_groups
        ):
            raise HTTPException(
                status_code=403,
                detail="Unauthorized, user is not a member of an allowed group",
            )
        if token.account_type not in included_account_types:
            raise HTTPException(
                status_code=403,
                detail="Unauthorized, user account type is not allowed",
            )
        return token

    return filter_token


def is_user_admin() -> Callable[
    [schemas_auth.FunctionalTokenData],
    schemas_auth.FunctionalTokenData,
]:
    """
    Generate a dependency which will:
        * check if the request header contains a valid API JWT token (a token that can be used to call endpoints from the API)
        * make sure the user making the request exists and is a member of the group with the given id
        * make sure the user is not an external user if `exclude_external` is True
        * return the corresponding user `models_users.CoreUser` object
    """

    def is_user_in(
        token: schemas_auth.FunctionalTokenData = Depends(
            filter_user_token(included_groups=[GroupType.admin]),
        ),
    ) -> schemas_auth.FunctionalTokenData:
        """
        A dependency that checks that user is a member of the group with the given id then returns the corresponding user.
        """

        return token

    return is_user_in


def is_user_allowed_to(
    permissions_name: list[ModulePermissions],
) -> Callable[
    [schemas_auth.FunctionalTokenData, AsyncSession],
    Coroutine[Any, Any, schemas_auth.FunctionalTokenData],
]:

    async def _is_user_allowed_to(
        token: schemas_auth.FunctionalTokenData = Depends(
            get_token_with_scopes([[ScopeType.API]]),
        ),
        db: AsyncSession = Depends(get_db),
        redis_client: Redis = Depends(get_redis_client),
        settings: Settings = Depends(get_settings),
    ) -> schemas_auth.FunctionalTokenData:

        if GroupType.admin in token.group_ids:
            return token

        allowed_group_ids: set[str] = set()
        allowed_account_types: set[AccountType] = set()
        for permission_name in permissions_name:
            groups, account_types = await get_cached_permission_requirements(
                permission_name,
                db,
                settings,
                redis_client,
            )
            allowed_group_ids.update(groups)
            allowed_account_types.update(account_types)

        user_has_group = any(g_id in allowed_group_ids for g_id in token.group_ids)
        user_has_account = token.account_type in allowed_account_types

        if not (user_has_group or user_has_account):
            raise HTTPException(
                status_code=403,
                detail="Unauthorized, user does not have the required permission",
            )

        return token

    return _is_user_allowed_to
