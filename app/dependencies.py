"""
Various FastAPI [dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/)

They are used in endpoints function signatures. For example:
```python
async def get_users(db: AsyncSession = Depends(get_db)):
```
"""

import logging
from collections.abc import AsyncGenerator, Callable
from functools import lru_cache
from typing import Annotated, cast

import calypsso
import redis
import starlette
import starlette.datastructures
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from app.core.payment.payment_tool import PaymentTool
from app.core.payment.types_payment import HelloAssoConfigName
from app.core.utils.config import Settings, construct_prod_settings
from app.types.exceptions import (
    InvalidAppStateTypeError,
    PaymentToolCredentialsNotSetException,
)
from app.types.scheduler import Scheduler
from app.types.websocket import WebsocketConnectionManager
from app.utils.communication.notifications import NotificationManager, NotificationTool
from app.utils.state import (
    GlobalState,
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

# We could maybe use hyperion.security
hyperion_access_logger = logging.getLogger("hyperion.access")
hyperion_error_logger = logging.getLogger("hyperion.error")

GLOBAL_STATE: GlobalState


async def init_state(
    app: FastAPI,
    settings: Settings,
    hyperion_error_logger: logging.Logger,
) -> None:
    """
    Initialize the global state for the project. This dependency should be called at the start of the application lifespan.

    This methode should be called as a dependency, and test may override it to provide their own state.
    ```python
    app.dependency_overrides.get(
        init_state,
        init_state,
    )(
        app=app,
        settings=settings,
        hyperion_error_logger=hyperion_error_logger,
    )
    ```
    """
    global GLOBAL_STATE

    engine = init_engine(settings=settings)

    SessionLocal = init_SessionLocal(engine)

    redis_client = init_redis_client(
        settings=settings,
        hyperion_error_logger=hyperion_error_logger,
    )

    scheduler = await init_scheduler(
        settings=settings,
        _dependency_overrides=app.dependency_overrides,
    )

    ws_manager = await init_websocket_connection_manager(
        settings=settings,
    )

    notification_manager = NotificationManager(settings=settings)

    payment_tools = init_payment_tools(
        settings=settings,
        hyperion_error_logger=hyperion_error_logger,
    )

    mail_templates = init_mail_templates(settings=settings)

    GLOBAL_STATE = GlobalState(
        engine=engine,
        SessionLocal=SessionLocal,
        redis_client=redis_client,
        scheduler=scheduler,
        ws_manager=ws_manager,
        notification_manager=notification_manager,
        payment_tools=payment_tools,
        mail_templates=mail_templates,
    )


async def disconnect_state(
    hyperion_error_logger: logging.Logger,
) -> None:
    """
    Disconnect items requiring it. This dependency should be used at the end of the application lifespan.

    This methode should be called as a dependency as tests may need to run additional steps
    """

    disconnect_redis_client(GLOBAL_STATE["redis_client"])
    await disconnect_scheduler(GLOBAL_STATE["scheduler"])
    await disconnect_websocket_connection_manager(GLOBAL_STATE["ws_manager"])

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


async def get_db() -> AsyncGenerator[AsyncSession]:
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
    async with GLOBAL_STATE["SessionLocal"]() as db:
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


async def get_unsafe_db() -> AsyncGenerator[AsyncSession]:
    """
    Return a database session but don't close it automatically

    It should only be used for really specific cases where `get_db` will not work
    """

    async with GLOBAL_STATE["SessionLocal"]() as db:
        yield db


def get_redis_client() -> redis.Redis | None:
    """
    Dependency that returns the redis client

    If the redis client is not available, it will return None.
    """
    return GLOBAL_STATE["redis_client"]


def get_scheduler() -> Scheduler:
    return GLOBAL_STATE["scheduler"]


def get_websocket_connection_manager() -> WebsocketConnectionManager:
    return GLOBAL_STATE["ws_manager"]


def get_notification_manager() -> NotificationManager:
    """
    Dependency that returns the notification manager.
    This dependency provide a low level tool allowing to use notification manager internal methods.

    If you want to send a notification, prefer `get_notification_tool` dependency.
    """
    return GLOBAL_STATE["notification_manager"]


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


@lru_cache
def get_payment_tool(
    name: HelloAssoConfigName,
) -> Callable[[], PaymentTool]:
    def get_payment_tool() -> PaymentTool:
        payment_tools = GLOBAL_STATE["payment_tools"]
        if name not in payment_tools:
            hyperion_error_logger.warning(
                f"HelloAsso API credentials are not set for {name.value}, payment won't be available",
            )
            raise PaymentToolCredentialsNotSetException

        return payment_tools[name]

    return get_payment_tool


def get_mail_templates() -> calypsso.MailTemplates:
    """
    Dependency that returns the mail templates manager.
    """

    return GLOBAL_STATE["mail_templates"]
