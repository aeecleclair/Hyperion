from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from app.core.auth import schemas_auth
from app.core.auth.dependencies_auth import get_token_with_scopes
from app.core.users import cruds_users, schemas_users
from app.dependencies import get_db
from app.types.scopes_type import ScopeType


def get_request_user(
    scopes: list[list[ScopeType]] | None = None,
) -> Callable[
    [AsyncSession, schemas_auth.FunctionalTokenData],
    Coroutine[Any, Any, schemas_users.CoreUser],
]:
    """
    Generate a dependency which will:
     * check the request header contain a valid JWT token
     * make sure the token contain the given scopes
     * return the corresponding user `models_users.CoreUser` object

    This endpoint allows to require scopes other than the API scope. This should only be used by the auth endpoints.
    To restrict an endpoint from the API, use `is_user_in`.
    """
    scopes = scopes or [[ScopeType.API]]

    async def get_user_from_user_id(
        db: AsyncSession = Depends(get_db),
        token: schemas_auth.FunctionalTokenData = Depends(
            get_token_with_scopes(scopes),
        ),
    ) -> schemas_users.CoreUser:
        """
        Dependency that makes sure the token is valid, contains the expected scopes and returns the corresponding user.
        The expected scopes are passed as list of list of scopes, each list of scopes is an "AND" condition, and the list of list of scopes is an "OR" condition.
        """
        user = await cruds_users.get_user_by_id_schema(db=db, user_id=token.id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    return get_user_from_user_id
