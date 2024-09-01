"""
Various FastAPI [dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/)

They are used in endpoints function signatures. For example:
```python
async def get_users(db: AsyncSession = Depends(get_db)):
```
"""

import logging
from collections.abc import AsyncGenerator, Callable, Coroutine
from functools import lru_cache
from typing import Any, cast

import redis
from fastapi import BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core import models_core, security
from app.core.auth import schemas_auth
from app.core.config import Settings, construct_prod_settings
from app.core.groups.groups_type import GroupType, get_ecl_groups
from app.core.payment.payment_tool import PaymentTool
from app.modules.raid.utils.drive.drive_file_manager import DriveFileManager
from app.types.scopes_type import ScopeType
from app.types.websocket import WebsocketConnectionManager
from app.utils.auth import auth_utils
from app.utils.communication.notifications import NotificationManager, NotificationTool
from app.utils.redis import connect
from app.utils.tools import (
    is_user_external,
    is_user_member_of_an_allowed_group,
)

# We could maybe use hyperion.security
hyperion_access_logger = logging.getLogger("hyperion.access")
hyperion_error_logger = logging.getLogger("hyperion.error")

redis_client: redis.Redis | bool | None = (
    None  # Create a global variable for the redis client, so that it can be instancied in the startup event
)
# Is None if the redis client is not instantiated, is False if the redis client is instancied but not connected, is a redis.Redis object if the redis client is connected

websocket_connection_manager: WebsocketConnectionManager | None = None

engine: AsyncEngine | None = (
    None  # Create a global variable for the database engine, so that it can be instancied in the startup event
)
SessionLocal: Callable[[], AsyncSession] | None = (
    None  # Create a global variable for the database session, so that it can be instancied in the startup event
)


notification_manager: NotificationManager | None = None

drive_file_manage: DriveFileManager | None = None

payment_tool: PaymentTool | None = None


async def get_request_id(request: Request) -> str:
    """
    The request identifier is a unique UUID which is used to associate logs saved during the same request
    """
    # `request_id` is a string injected in the state by our middleware
    # We force Mypy to consider it as a str instead of Any
    request_id = cast(str, request.state.request_id)

    return request_id


def init_and_get_db_engine(settings: Settings) -> AsyncEngine:
    """
    Return the (asynchronous) database engine, if the engine doesn't exit yet it will create one based on the settings
    """
    global engine
    global SessionLocal
    if settings.SQLITE_DB:
        SQLALCHEMY_DATABASE_URL = f"sqlite+aiosqlite:///./{settings.SQLITE_DB}"
    else:
        SQLALCHEMY_DATABASE_URL = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}/{settings.POSTGRES_DB}"

    if engine is None:
        engine = create_async_engine(
            SQLALCHEMY_DATABASE_URL,
            echo=settings.DATABASE_DEBUG,
        )
        SessionLocal = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return engine


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Return a database session
    """
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


@lru_cache
def get_settings() -> Settings:
    """
    Return a settings object, based on `.env` dotenv
    """
    # `lru_cache()` decorator is here to prevent the class to be instantiated multiple times.
    # See https://fastapi.tiangolo.com/advanced/settings/#lru_cache-technical-details
    return construct_prod_settings()


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
                hyperion_error_logger.exception(
                    "Redis connection error: Check the Redis configuration or the Redis server",
                )
        else:
            redis_client = False
    return redis_client


def get_websocket_connection_manager(
    settings: Settings = Depends(get_settings),
):
    global websocket_connection_manager

    if websocket_connection_manager is None:
        websocket_connection_manager = WebsocketConnectionManager(settings=settings)

    return websocket_connection_manager


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


def get_drive_file_manager() -> DriveFileManager:
    """
    Dependency that returns the drive file manager.
    """
    global drive_file_manage

    if drive_file_manage is None:
        drive_file_manage = DriveFileManager()

    return drive_file_manage


def get_payment_tool(
    settings: Settings = Depends(get_settings),
) -> PaymentTool:
    """
    Dependency that returns the payment manager.

    You should call `payment_tool.is_payment_available()` to know if payment credentials are set in settings.
    """
    global payment_tool

    if payment_tool is None:
        payment_tool = PaymentTool(settings=settings)

    return payment_tool


def get_token_data(
    settings: Settings = Depends(get_settings),
    token: str = Depends(security.oauth2_scheme),
    request_id: str = Depends(get_request_id),
) -> schemas_auth.TokenData:
    """
    Dependency that returns the token payload data
    """
    return auth_utils.get_token_data(
        settings=settings,
        token=token,
        request_id=request_id,
    )


def get_user_from_token_with_scopes(
    scopes: list[list[ScopeType]],
) -> Callable[
    [AsyncSession, schemas_auth.TokenData],
    Coroutine[Any, Any, models_core.CoreUser],
]:
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
        token_data: schemas_auth.TokenData = Depends(get_token_data),
    ) -> models_core.CoreUser:
        """
        Dependency that makes sure the token is valid, contains the expected scopes and returns the corresponding user.
        The expected scopes are passed as list of list of scopes, each list of scopes is an "AND" condition, and the list of list of scopes is an "OR" condition.
        """

        return await auth_utils.get_user_from_token_with_scopes(
            scopes=scopes,
            db=db,
            token_data=token_data,
        )

    return get_current_user


def is_user(
    user: models_core.CoreUser = Depends(
        get_user_from_token_with_scopes([[ScopeType.API]]),
    ),
) -> models_core.CoreUser:
    """
    A dependency that will:
        * check if the request header contains a valid API JWT token (a token that can be used to call endpoints from the API)
        * make sure the user making the request exists

    To check if the user is not external, use is_user_a_member dependency
    To check if the user is not external and is the member of a group, use is_user_a_member_of generator
    """
    return user


def is_user_a_member(
    user: models_core.CoreUser = Depends(
        is_user,
    ),
    request_id: str = Depends(get_request_id),
) -> models_core.CoreUser:
    """
    A dependency that will:
        * check if the request header contains a valid API JWT token (a token that can be used to call endpoints from the API)
        * make sure the user making the request exists
        * make sure the user is not an external user

    To check if the user is the member of a group, use is_user_a_member_of generator
    """
    if is_user_external(user):
        hyperion_access_logger.warning(
            f"Is_user_a_member: user is an external user ({request_id})",
        )

        raise HTTPException(
            status_code=403,
            detail="Unauthorized, user is an external user",
        )

    return user


def is_user_an_ecl_member(
    user: models_core.CoreUser = Depends(
        is_user_a_member,
    ),
    request_id: str = Depends(get_request_id),
) -> models_core.CoreUser:
    """
    A dependency that will:
        * check if the request header contains a valid API JWT token (a token that can be used to call endpoints from the API)
        * make sure the user making the request exists and is a member of Student, Staff, Association or AE
        * make sure the user is not an external user
        * make sure the user making the request exists

    To check if the user is the member of a group, use is_user_a_member_of generator
    """

    if is_user_member_of_an_allowed_group(
        user=user,
        allowed_groups=get_ecl_groups(),
    ):
        # We know the user is a member of the group, we don't need to return an error and can return the CoreUser object
        return user

    hyperion_access_logger.warning(
        f"Is_user_a_member_of: Unauthorized, user is not a member of student, staff, association or AE group ({request_id})",
    )

    raise HTTPException(
        status_code=403,
        detail="Unauthorized, user is not a member of student, staff or AE group",
    )


def is_user_a_member_of(
    group_id: GroupType,
) -> Callable[[models_core.CoreUser], Coroutine[Any, Any, models_core.CoreUser]]:
    """
    Generate a dependency which will:
        * check if the request header contains a valid API JWT token (a token that can be used to call endpoints from the API)
        * make sure the user making the request exists and is a member of the group with the given id
        * make sure the user is not an external user
        * return the corresponding user `models_core.CoreUser` object
    """

    async def is_user_a_member_of(
        user: models_core.CoreUser = Depends(
            is_user_a_member,
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
            f"Is_user_a_member_of: user is not a member of the group {group_id} ({request_id})",
        )

        raise HTTPException(
            status_code=403,
            detail=f"Unauthorized, user is not a member of the group {group_id}",
        )

    return is_user_a_member_of
