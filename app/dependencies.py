"""
Various FastAPI [dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/)

They are used in endpoints function signatures. For example:
```python
async def get_users(db: AsyncSession = Depends(get_db)):
```
"""
from functools import lru_cache
from typing import AsyncGenerator

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
def get_settings():
    """
    Return a settings object, based on `.env` dotenv
    """
    # `lru_cache()` decorator is here to prevent the class to be instanciated multiple times.
    # See https://fastapi.tiangolo.com/advanced/settings/#lru_cache-technical-details
    return Settings(_env_file=".env")


async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(security.oauth2_scheme)
) -> models_core.CoreUser:
    """
    Make sure the token is valid and return the corresponding user.
    """
    try:
        payload = jwt.decode(
            token,
            Settings.ACCESS_TOKEN_SECRET_KEY,
            algorithms=[security.jwt_algorithme],
        )
        token_data = schemas_core.TokenData(**payload)
    except (jwt.JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )

    user_id = token_data.sub

    user = await cruds_users.get_user_by_id(db=db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def generate_is_user_a_member_of_dependency(group_id: GroupType):
    async def is_user_a_member_of(
        db: AsyncSession = Depends(get_db),
        user: models_core.CoreUser = Depends(get_current_user),
    ):
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
