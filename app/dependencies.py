"""
Various FastAPI [dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/)

They are used in endpoints function signatures. For example:
```python
async def get_users(db: AsyncSession = Depends(get_db)):
```
"""

from functools import lru_cache
from typing import Any, AsyncGenerator, Callable, Coroutine

from fastapi import Depends, HTTPException, Request, status
from jose import jwt
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import Settings
from app.cruds import cruds_users
from app.database import SessionLocal
from app.models import models_core
from app.schemas import schemas_core
from app.utils.types.groups_type import GroupType
from app.utils.types.scopes_type import ScopeType


async def get_request_id(request: Request) -> str:
    """
    The request identifier is an unique UUID which is used to associate logs saved during the same request
    """
    return request.state.request_id


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Return a database session
    """

    async with SessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()


@lru_cache()
def get_settings() -> Settings:
    """
    Return a settings object, based on `.env` dotenv
    """
    # `lru_cache()` decorator is here to prevent the class to be instantiated multiple times.
    # See https://fastapi.tiangolo.com/advanced/settings/#lru_cache-technical-details
    return Settings(_env_file=".env")


def get_user_from_token_with_scopes(
    scopes: list[ScopeType] = [],
) -> Callable[[AsyncSession, Settings, str], Coroutine[Any, Any, models_core.CoreUser]]:
    """
    Generate a dependency which will:
     * check the request header contain a valid JWT token
     * make sure the token contain the given scopes
     * return the corresponding user `models_core.CoreUser` object

    This endpoints allow to requires other scopes than the API scope. This should only be used by the auth endpoints.
    To restrict and endpoint from the API, use `is_user_a_member_of`.
    """

    async def get_current_user(
        db: AsyncSession = Depends(get_db),
        settings: Settings = Depends(get_settings),
        token: str = Depends(security.oauth2_scheme),
    ) -> models_core.CoreUser:
        """
        Dependency that make sure the token is valid, contain the expected scopes and return the corresponding user.
        """
        print("Get user")
        try:
            payload = jwt.decode(
                token,
                settings.ACCESS_TOKEN_SECRET_KEY,
                algorithms=[security.jwt_algorithme],
            )
            print(payload)
            token_data = schemas_core.TokenData(**payload)
            print(token_data)
        except (jwt.JWTError, ValidationError) as error:
            # TODO logging
            print(error)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Could not validate credentials",
            )

        for scope in scopes:
            # `scopes` contain a " " separated list of scopes
            if scope not in token_data.scopes:
                raise HTTPException(
                    status_code=403,
                    detail=f"Unauthorized, token does not contain the scope {scope}",
                )

        user_id = token_data.sub

        user = await cruds_users.get_user_by_id(db=db, user_id=user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    return get_current_user


def is_user_a_member(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(
        get_user_from_token_with_scopes([ScopeType.API])
    ),
) -> models_core.CoreUser:
    """
    A dependency that check that:
        * check the request header contain a valid API JWT token (a token that can be used to call endpoints from the API)
        * make sure the user making the request exist

    To check the user is the member of a group, use is_user_a_member_of generator
    """
    return user


def is_user_a_member_of(
    group_id: GroupType,
) -> Callable[
    [AsyncSession, models_core.CoreUser], Coroutine[Any, Any, models_core.CoreUser]
]:
    """
    Generate a dependency which which will:
        * check the request header contain a valid API JWT token (a token that can be used to call endpoints from the API)
        * make sure the user making the request exist and is a member of the group with the given id
        * return the corresponding user `models_core.CoreUser` object
    """

    async def is_user_a_member_of(
        db: AsyncSession = Depends(get_db),
        user: models_core.CoreUser = Depends(
            get_user_from_token_with_scopes([ScopeType.API])
        ),
    ) -> models_core.CoreUser:
        """
        A dependency that check that user is a member of the group with the given id then return the corresponding user.
        """
        # We can not directly test is group_id is in user.groups
        # As user.groups is a list of CoreGroup as group_id is an UUID
        for user_group in user.groups:
            if group_id == user_group.id:
                # We know the user is a member of the group, we don't need to return an error and can return the CoreUser object
                return user

        raise HTTPException(
            status_code=403,
            detail=f"Unauthorized, user is not a member of the group {group_id}",
        )

    return is_user_a_member_of


async def get_token_data(
    settings: Settings = Depends(get_settings),
    token: str = Depends(security.oauth2_scheme),
) -> schemas_core.TokenData:
    """
    Dependency that return the token payload data
    """
    try:
        payload = jwt.decode(
            token,
            settings.ACCESS_TOKEN_SECRET_KEY,
            algorithms=[security.jwt_algorithme],
        )
        token_data = schemas_core.TokenData(**payload)
    except (jwt.JWTError, ValidationError) as error:
        # TODO logging
        print(error)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )

    return token_data
