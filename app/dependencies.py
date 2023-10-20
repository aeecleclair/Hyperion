"""
Various FastAPI [dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/)

They are used in endpoints function signatures. For example:
```python
async def get_users(db: AsyncSession = Depends(get_db)):
```
"""

import logging
from functools import lru_cache
from typing import Any, AsyncGenerator, Callable, Coroutine

import redis
from fastapi import BackgroundTasks, Depends, HTTPException, Request, status
from jose import jwt
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core import security
from app.core.config import Settings
from app.cruds import cruds_users
from app.models import models_core
from app.schemas import schemas_auth
from app.utils.communication.notifications import NotificationManager, NotificationTool
from app.utils.redis import connect
from app.utils.tools import is_user_member_of_an_allowed_group
from app.utils.types.groups_type import GroupType
from app.utils.types.scopes_type import ScopeType

# We could maybe use hyperion.security
hyperion_access_logger = logging.getLogger("hyperion.access")
hyperion_error_logger = logging.getLogger("hyperion.error")

redis_client: redis.Redis | bool | None = None  # Create a global variable for the redis client, so that it can be instancied in the startup event
# Is None if the redis client is not instantiated, is False if the redis client is instancied but not connected, is a redis.Redis object if the redis client is connected

engine: AsyncEngine | None = None  # Create a global variable for the database engine, so that it can be instancied in the startup event
SessionLocal: Callable[
    [], AsyncSession
] | None = None  # Create a global variable for the database session, so that it can be instancied in the startup event


notification_manager: NotificationManager | None = None


async def get_request_id(request: Request) -> str:
    """
    The request identifier is a unique UUID which is used to associate logs saved during the same request
    """
    return request.state.request_id


def get_db_engine(settings: Settings) -> AsyncEngine:
    """Return the database engine, if the engine doesn't exit yet it will create one based on the settings"""
    global engine
    global SessionLocal
    if settings.SQLITE_DB:
        SQLALCHEMY_DATABASE_URL = f"sqlite+aiosqlite:///./{settings.SQLITE_DB}"  # Connect to the test's database
    else:
        SQLALCHEMY_DATABASE_URL = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}/{settings.POSTGRES_DB}"

    if engine is None:
        engine = create_async_engine(
            SQLALCHEMY_DATABASE_URL, echo=settings.DATABASE_DEBUG
        )
        SessionLocal = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
    return engine


def get_session_maker() -> Callable[[], AsyncSession]:
    """
    Return the session maker
    """
    global SessionLocal
    if SessionLocal is None:
        hyperion_error_logger.error("Database engine is not initialized")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database engine is not initialized",
        )
    return SessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Return a database session
    """
    global SessionLocal
    if SessionLocal is None:
        hyperion_error_logger.error("Database engine is not initialized")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database engine is not initialized",
        )
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
    return Settings(_env_file=".env")  # type:ignore


# (issue ouverte sur github: https://github.com/pydantic/pydantic/issues/3072)


def get_redis_client(
    settings: Settings = Depends(get_settings),
) -> redis.Redis | None | bool:
    """
    Dependency that returns the redis client

    Settings can be None if the redis client is already instanced, so that we don't need to pass the settings to the function.
    Is None if the redis client is not instantiated, is False if the redis client is instantiated but not connected, is a redis.Redis object if the redis client is connected
    """
    global redis_client
    if redis_client is None:
        if settings.REDIS_HOST != "":
            try:
                redis_client = connect(settings)
            except redis.exceptions.ConnectionError:
                hyperion_error_logger.error(
                    "Redis connection error: Check the Redis configuration or the Redis server"
                )
        else:
            redis_client = False
    return redis_client


def get_notification_manager(
    settings: Settings = Depends(get_settings),
) -> NotificationManager:
    """
    Dependency that returns the notification manager.
    This dependency provide a low level tool allowing to use notification manager internal methods.

    If you want to send a notification, prefer `get_notification_tool` dependency.
    """
    global notification_manager

    if notification_manager is None:
        notification_manager = NotificationManager(settings=settings)

    return notification_manager


def get_notification_tool(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    notification_manager: NotificationManager = Depends(get_notification_manager),
) -> NotificationTool:
    """
    Dependency that returns a notification tool, allowing to send push notification as a background tasks.
    """

    return NotificationTool(
        background_tasks=background_tasks,
        notification_manager=notification_manager,
        db=db,
    )


def get_user_from_token_with_scopes(
    scopes: list[list[ScopeType]] = [],
) -> Callable[[AsyncSession, Settings, str], Coroutine[Any, Any, models_core.CoreUser]]:
    """
    Generate a dependency which will:
     * check the request header contain a valid JWT token
     * make sure the token contain the given scopes
     * return the corresponding user `models_core.CoreUser` object

    This endpoint allows to require scopes other than the API scope. This should only be used by the auth endpoints.
    To restrict an endpoint from the API, use `is_user_a_member_of`.
    """

    async def get_current_user(
        db: AsyncSession = Depends(get_db),
        settings: Settings = Depends(get_settings),
        token: str = Depends(security.oauth2_scheme),
        request_id: str = Depends(get_request_id),
    ) -> models_core.CoreUser:
        """
        Dependency that makes sure the token is valid, contains the expected scopes and returns the corresponding user.
        The expected scopes are passed as list of list of scopes, each list of scopes is an "AND" condition, and the list of list of scopes is an "OR" condition.
        """
        try:
            payload = jwt.decode(
                token,
                settings.ACCESS_TOKEN_SECRET_KEY,
                algorithms=[security.jwt_algorithme],
            )
            token_data = schemas_auth.TokenData(**payload)
            hyperion_access_logger.info(
                f"Get_current_user: Decoded a token for user {token_data.sub} ({request_id})"
            )
        except (jwt.JWTError, ValidationError) as error:
            hyperion_access_logger.warning(
                f"Get_current_user: Failed to decode a token: {error} ({request_id})"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Could not validate credentials",
            )

        access_granted = False
        if scopes == []:
            access_granted = True
        else:
            for scope_set in scopes:
                # `token_data.scopes` contain a " " separated list of scopes
                # `scope_set` is a list of scopes that must be present in the token
                # If one of the scope set is present in the token, the access is granted

                scope_set_present = True
                for scope in scope_set:
                    scope_set_present = scope_set_present and (
                        scope in token_data.scopes.split(" ")
                    )
                access_granted = access_granted or scope_set_present

        if not access_granted:
            raise HTTPException(
                status_code=403,
                detail=f"Unauthorized, token does not contain at least one of the following scope_set {[[scope.value for scope in scope_set] for scope_set in scopes]}",
            )
        user_id = token_data.sub

        user = await cruds_users.get_user_by_id(db=db, user_id=user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    return get_current_user


def is_user_a_member(
    user: models_core.CoreUser = Depends(
        get_user_from_token_with_scopes([[ScopeType.API]])
    ),
) -> models_core.CoreUser:
    """
    A dependency that will:
        * check if the request header contains a valid API JWT token (a token that can be used to call endpoints from the API)
        * make sure the user making the request exists

    To check if the user is the member of a group, use is_user_a_member_of generator
    """
    return user


def is_user_a_member_of(
    group_id: GroupType,
) -> Callable[[models_core.CoreUser], Coroutine[Any, Any, models_core.CoreUser]]:
    """
    Generate a dependency which will:
        * check if the request header contains a valid API JWT token (a token that can be used to call endpoints from the API)
        * make sure the user making the request exists and is a member of the group with the given id
        * return the corresponding user `models_core.CoreUser` object
    """

    async def is_user_a_member_of(
        user: models_core.CoreUser = Depends(
            get_user_from_token_with_scopes([[ScopeType.API]])
        ),
        request_id: str = Depends(get_request_id),
    ) -> models_core.CoreUser:
        """
        A dependency that checks that user is a member of the group with the given id then returns the corresponding user.
        """
        if is_user_member_of_an_allowed_group(user=user, allowed_groups=[group_id]):
            # We know the user is a member of the group, we don't need to return an error and can return the CoreUser object
            return user

        hyperion_access_logger.warning(
            f"Is_user_a_member_of: user is not a member of the group {group_id} ({request_id})"
        )

        raise HTTPException(
            status_code=403,
            detail=f"Unauthorized, user is not a member of the group {group_id}",
        )

    return is_user_a_member_of


async def get_token_data(
    settings: Settings = Depends(get_settings),
    token: str = Depends(security.oauth2_scheme),
    request_id: str = Depends(get_request_id),
) -> schemas_auth.TokenData:
    """
    Dependency that returns the token payload data
    """
    try:
        payload = jwt.decode(
            token,
            settings.ACCESS_TOKEN_SECRET_KEY,
            algorithms=[security.jwt_algorithme],
        )
        token_data = schemas_auth.TokenData(**payload)
        hyperion_access_logger.info(
            f"Get_token_data: Decoded a token for user {token_data.sub} ({request_id})"
        )
    except (jwt.JWTError, ValidationError) as error:
        hyperion_access_logger.warning(
            f"Get_token_data: Failed to decode a token: {error} ({request_id})"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )

    return token_data
