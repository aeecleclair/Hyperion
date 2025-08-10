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
from typing import Annotated, Any, cast

import calypsso
import redis
import starlette
import starlette.datastructures
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from app.core.auth import schemas_auth
from app.core.groups.groups_type import AccountType, GroupType, get_school_account_types
from app.core.payment.payment_tool import PaymentTool
from app.core.payment.types_payment import HelloAssoConfigName
from app.core.users import models_users
from app.core.utils import security
from app.core.utils.config import Settings, construct_prod_settings
from app.modules.raid.utils.drive.drive_file_manager import DriveFileManager
from app.types.exceptions import (
    InvalidAppStateTypeError,
    PaymentToolCredentialsNotSetException,
)
from app.types.scheduler import Scheduler
from app.types.scopes_type import ScopeType
from app.types.websocket import WebsocketConnectionManager
from app.utils.auth import auth_utils
from app.utils.communication.notifications import NotificationManager, NotificationTool
from app.utils.state import (
    LifespanState,
    RuntimeLifespanState,
    disconnect_redis_client,
    disconnect_scheduler,
    disconnect_websocket_connection_manager,
    init_engine,
    init_mail_templates,
    init_payment_tools,
    init_redis_client,
    init_scheduler,
    init_SessionLocal,
    init_websocket_connection_manager,
)
from app.utils.tools import (
    is_user_external,
    is_user_member_of_any_group,
)

# We could maybe use hyperion.security
hyperion_access_logger = logging.getLogger("hyperion.access")
hyperion_error_logger = logging.getLogger("hyperion.error")


async def init_app_state(
    app: FastAPI,
    settings: Settings,
    hyperion_error_logger: logging.Logger,
) -> LifespanState:
    """
    Initialize the state of the application. This dependency should be used at the start of the application lifespan.

    This methode should be called as a dependency, and test may override it to provide their own state.
    ```python
    state = app.dependency_overrides.get(
        init_app_state,
        init_app_state,
    )(
        app=app,
        settings=settings,
        hyperion_error_logger=hyperion_error_logger,
    )
    state = cast("LifespanState", state)
    ```
    """
    engine = init_engine(settings=settings)

    SessionLocal = init_SessionLocal(engine)

    redis_client = init_redis_client(
        settings=settings,
        hyperion_error_logger=hyperion_error_logger,
    )

    scheduler = await init_scheduler(
        settings=settings,
        app=app,
    )

    ws_manager = await init_websocket_connection_manager(
        settings=settings,
    )

    notification_manager = NotificationManager(settings=settings)

    drive_file_manager = DriveFileManager()

    payment_tools = init_payment_tools(
        settings=settings,
        hyperion_error_logger=hyperion_error_logger,
    )

    mail_templates = init_mail_templates(settings=settings)

    return LifespanState(
        engine=engine,
        SessionLocal=SessionLocal,
        redis_client=redis_client,
        scheduler=scheduler,
        ws_manager=ws_manager,
        notification_manager=notification_manager,
        drive_file_manager=drive_file_manager,
        payment_tools=payment_tools,
        mail_templates=mail_templates,
    )


async def disconnect_state(
    state: LifespanState,
    hyperion_error_logger: logging.Logger,
) -> None:
    """
    Disconnect items requiring it. This dependency should be used at the end of the application lifespan.

    This methode should be called as a dependency as test may need to run additional steps
    """
    disconnect_redis_client(state["redis_client"])
    await disconnect_scheduler(state["scheduler"])
    await disconnect_websocket_connection_manager(state["ws_manager"])

    hyperion_error_logger.info("Application state disconnected successfully.")


def get_app_state(request: Request) -> RuntimeLifespanState:
    """
    Get the application state from the request. The state is injected by our middleware.
    """
    # `request.state` may be a TypedDict or a starlette State object
    # depending if it is accessed in an endpoint or the lifespan

    # `state` should be a RuntimeLifespanState object injected in the state by our middleware
    # We force Mypy to consider it as a RuntimeLifespanState instead of Any

    if isinstance(request.state, dict):
        return cast("RuntimeLifespanState", request.state)
    if isinstance(request.state, starlette.datastructures.State):
        return cast("RuntimeLifespanState", request.state.__dict__["_state"])
    raise InvalidAppStateTypeError


AppState = Annotated[RuntimeLifespanState, Depends(get_app_state)]


async def get_request_id(state: AppState) -> str:
    """
    The request identifier is a unique UUID which is used to associate logs saved during the same request
    """

    return state["request_id"]


@lru_cache
def get_settings() -> Settings:
    """
    Return a settings object, based on `.env` dotenv
    """
    # `lru_cache()` decorator is here to prevent the class to be instantiated multiple times.
    # See https://fastapi.tiangolo.com/advanced/settings/#lru_cache-technical-details
    return construct_prod_settings()


async def get_db(state: AppState) -> AsyncGenerator[AsyncSession, None]:
    """
    Return a database session that will be automatically committed and closed after usage.

    If an HTTPException is raised during the request, we consider that the error was expected and managed by the endpoint. We commit the session.
    If an other exception is raised, we rollback the session to avoid.

    Cruds and endpoints should never call `db.commit()` or `db.rollback()` directly.
    After adding an object to the session, calling `await db.flush()` will integrate the changes in the transaction without committing them.

    If an endpoint needs to add objects to the sessions that should be committed even in case of an unexpected error,
    it should start a SAVEPOINT after adding the object.

    ```python
    # Add here the object that should always be committed, even in case of an unexpected error
    await db.add(object)
    await db.flush()

    # Start a SAVEPOINT. If the code in the following context manager raises an exception, the changes will be rolled back to this point.
    async with db.begin_nested():
        # Add objects that may be rolled back in case of an error here
    ```
    """
    async with state["SessionLocal"]() as db:
        try:
            yield db
        except HTTPException:
            await db.commit()
            raise
        except Exception:
            await db.rollback()
            raise
        else:
            await db.commit()
        finally:
            await db.close()


async def get_unsafe_db(state: AppState) -> AsyncGenerator[AsyncSession, None]:
    """
    Return a database session but don't close it automatically

    It should only be used for really specific cases where `get_db` will not work
    """

    async with state["SessionLocal"]() as db:
        yield db


def get_redis_client(state: AppState) -> redis.Redis | None:
    """
    Dependency that returns the redis client

    If the redis client is not available, it will return None.
    """
    return state["redis_client"]


def get_scheduler(state: AppState) -> Scheduler:
    return state["scheduler"]


def get_websocket_connection_manager(state: AppState) -> WebsocketConnectionManager:
    return state["ws_manager"]


def get_notification_manager(state: AppState) -> NotificationManager:
    """
    Dependency that returns the notification manager.
    This dependency provide a low level tool allowing to use notification manager internal methods.

    If you want to send a notification, prefer `get_notification_tool` dependency.
    """
    return state["notification_manager"]


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


def get_drive_file_manager(state: AppState) -> DriveFileManager:
    """
    Dependency that returns the drive file manager.
    """

    return state["drive_file_manager"]


@lru_cache
def get_payment_tool(
    name: HelloAssoConfigName,
) -> Callable[[AppState], PaymentTool]:
    def get_payment_tool(
        state: AppState,
    ) -> PaymentTool:
        payment_tools = state["payment_tools"]
        if name not in payment_tools:
            hyperion_error_logger.warning(
                f"HelloAsso API credentials are not set for {name.value}, payment won't be available",
            )
            raise PaymentToolCredentialsNotSetException

        return payment_tools[name]

    return get_payment_tool


def get_mail_templates(
    state: AppState,
) -> calypsso.MailTemplates:
    """
    Dependency that returns the mail templates manager.
    """

    return state["mail_templates"]


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
    Coroutine[Any, Any, models_users.CoreUser],
]:
    """
    Generate a dependency which will:
     * check the request header contain a valid JWT token
     * make sure the token contain the given scopes
     * return the corresponding user `models_users.CoreUser` object

    This endpoint allows to require scopes other than the API scope. This should only be used by the auth endpoints.
    To restrict an endpoint from the API, use `is_user_in`.
    """

    async def get_current_user(
        db: AsyncSession = Depends(get_db),
        token_data: schemas_auth.TokenData = Depends(get_token_data),
    ) -> models_users.CoreUser:
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
    excluded_groups: list[GroupType] | None = None,
    included_groups: list[GroupType] | None = None,
    excluded_account_types: list[AccountType] | None = None,
    included_account_types: list[AccountType] | None = None,
    exclude_external: bool = False,
) -> Callable[[models_users.CoreUser], models_users.CoreUser]:
    """
    A dependency that will:
        * check if the request header contains a valid API JWT token (a token that can be used to call endpoints from the API)
        * make sure the user making the request exists

    To check if the user is not external, use is_user_a_member dependency
    To check if the user is not external and is the member of a group, use is_user_in generator
    To check if the user has an ecl account type, use is_user_a_school_member dependency
    """

    excluded_groups = excluded_groups or []
    excluded_account_types = excluded_account_types or []
    included_account_types = included_account_types or list(AccountType)

    def is_user(
        user: models_users.CoreUser = Depends(
            get_user_from_token_with_scopes([[ScopeType.API]]),
        ),
    ) -> models_users.CoreUser:
        groups_id: list[str] = [group.id for group in user.groups]
        if GroupType.admin in groups_id:
            return user
        if user.account_type in excluded_account_types:
            raise HTTPException(
                status_code=403,
                detail="Unauthorized, user account type is not allowed",
            )
        if exclude_external and is_user_external(user):
            raise HTTPException(
                status_code=403,
                detail="Unauthorized, user is an external user",
            )
        if is_user_member_of_any_group(user, excluded_groups):
            raise HTTPException(
                status_code=403,
                detail=f"Unauthorized, user is a member of any of the groups {excluded_groups}",
            )
        if included_groups is not None and not is_user_member_of_any_group(
            user,
            included_groups,
        ):
            raise HTTPException(
                status_code=403,
                detail="Unauthorized, user is not a member of an allowed group",
            )
        if user.account_type not in included_account_types:
            raise HTTPException(
                status_code=403,
                detail="Unauthorized, user account type is not allowed",
            )
        return user

    return is_user


def is_user_a_member(
    user: models_users.CoreUser = Depends(
        is_user(exclude_external=True),
    ),
    request_id: str = Depends(get_request_id),
) -> models_users.CoreUser:
    """
    A dependency that will:
        * check if the request header contains a valid API JWT token (a token that can be used to call endpoints from the API)
        * make sure the user making the request exists
        * make sure the user is not an external user

    To check if the user is the member of a group, use is_user_in generator
    """
    return user


def is_user_a_school_member(
    user: models_users.CoreUser = Depends(
        is_user(included_account_types=get_school_account_types()),
    ),
    request_id: str = Depends(get_request_id),
) -> models_users.CoreUser:
    """
    A dependency that will:
        * check if the request header contains a valid API JWT token (a token that can be used to call endpoints from the API)
        * make sure the user making the request exists and is a member of Student, Staff, Association or AE
        * make sure the user is not an external user
        * make sure the user making the request exists

    To check if the user is the member of a group, use is_user_in generator
    """

    return user


def is_user_in(
    group_id: GroupType,
    exclude_external: bool = False,
) -> Callable[[models_users.CoreUser], Coroutine[Any, Any, models_users.CoreUser]]:
    """
    Generate a dependency which will:
        * check if the request header contains a valid API JWT token (a token that can be used to call endpoints from the API)
        * make sure the user making the request exists and is a member of the group with the given id
        * make sure the user is not an external user if `exclude_external` is True
        * return the corresponding user `models_users.CoreUser` object
    """

    async def is_user_in(
        user: models_users.CoreUser = Depends(
            is_user(included_groups=[group_id], exclude_external=exclude_external),
        ),
        request_id: str = Depends(get_request_id),
    ) -> models_users.CoreUser:
        """
        A dependency that checks that user is a member of the group with the given id then returns the corresponding user.
        """

        return user

    return is_user_in
