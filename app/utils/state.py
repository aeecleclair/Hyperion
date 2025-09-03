import logging
from collections.abc import Callable
from typing import Any, TypedDict

import calypsso
import redis
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.payment.payment_tool import PaymentTool
from app.core.payment.types_payment import HelloAssoConfigName
from app.core.utils.config import Settings
from app.modules.raid.utils.drive.drive_file_manager import DriveFileManager
from app.types.scheduler import OfflineScheduler, Scheduler
from app.types.sqlalchemy import SessionLocalType
from app.types.websocket import WebsocketConnectionManager
from app.utils.communication.notifications import NotificationManager


class GlobalState(TypedDict):
    """
    This global state is contained as a global Python object. Use dependencies to access it
    """

    # Database engine
    engine: AsyncEngine
    # Database session creator
    SessionLocal: SessionLocalType
    # We may not have a Redis Client if it was not configured
    redis_client: redis.Redis | None
    scheduler: Scheduler
    ws_manager: WebsocketConnectionManager
    notification_manager: NotificationManager
    drive_file_manager: DriveFileManager
    payment_tools: dict[HelloAssoConfigName, PaymentTool]
    mail_templates: calypsso.MailTemplates


class LifespanState(TypedDict):
    """
    The LifespanState is contained instead of the FastAPI app
    """


class RuntimeLifespanState(LifespanState):
    """
    Requests contains an extended version of the LifespanState for each request.
    """

    request_id: str


def init_engine(settings: Settings) -> AsyncEngine:
    """
    Return the (asynchronous) database engine, if the engine doesn't exit yet it will create one based on the settings
    """

    if settings.SQLITE_DB:
        SQLALCHEMY_DATABASE_URL = f"sqlite+aiosqlite:///./{settings.SQLITE_DB}"
    else:
        SQLALCHEMY_DATABASE_URL = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}/{settings.POSTGRES_DB}"

    return create_async_engine(
        SQLALCHEMY_DATABASE_URL,
        echo=settings.DATABASE_DEBUG,
    )


def init_SessionLocal(engine: AsyncEngine) -> SessionLocalType:
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


def init_redis_client(
    settings: Settings,
    hyperion_error_logger: logging.Logger,
) -> redis.Redis | None:
    """
    Initialize the Redis client if the settings specify a Redis connection.
    Returns None if Redis is not configured.
    """
    redis_client: redis.Redis | None = None
    if settings.REDIS_HOST:
        try:
            redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                socket_keepalive=True,
            )
            redis_client.ping()  # Test the connection
        except redis.exceptions.ConnectionError:
            hyperion_error_logger.exception(
                "Redis connection error: Check the Redis configuration or the Redis server",
            )
    return redis_client


def disconnect_redis_client(redis_client: redis.Redis | None) -> None:
    if redis_client is not None:
        redis_client.close()


async def init_scheduler(
    settings: Settings,
    _dependency_overrides: dict[Callable[..., Any], Callable[..., Any]],
) -> Scheduler:
    if settings.REDIS_HOST:
        scheduler = Scheduler()

        await scheduler.start(
            redis_host=settings.REDIS_HOST,
            redis_port=settings.REDIS_PORT,
            redis_password=settings.REDIS_PASSWORD,
            _dependency_overrides=_dependency_overrides,
        )
    else:
        scheduler = OfflineScheduler()

    return scheduler


async def disconnect_scheduler(
    scheduler: Scheduler,
):
    await scheduler.close()


async def init_websocket_connection_manager(
    settings: Settings,
) -> WebsocketConnectionManager:
    ws_manager = WebsocketConnectionManager(settings=settings)

    await ws_manager.connect_broadcaster()

    return ws_manager


async def disconnect_websocket_connection_manager(
    ws_manager: WebsocketConnectionManager,
) -> None:
    await ws_manager.disconnect_broadcaster()


def init_payment_tools(
    settings: Settings,
    hyperion_error_logger: logging.Logger,
) -> dict[HelloAssoConfigName, PaymentTool]:
    if settings.HELLOASSO_API_BASE is None:
        hyperion_error_logger.error(
            "HelloAsso API base URL is not set in settings, payment won't be available",
        )
        return {}

    payment_tools: dict[HelloAssoConfigName, PaymentTool] = {}
    for helloasso_config_name in settings.HELLOASSO_CONFIGURATIONS:
        payment_tools[helloasso_config_name] = PaymentTool(
            config=settings.HELLOASSO_CONFIGURATIONS[helloasso_config_name],
            helloasso_api_base=settings.HELLOASSO_API_BASE,
        )

    return payment_tools


def init_mail_templates(
    settings: Settings,
) -> calypsso.MailTemplates:
    return calypsso.MailTemplates(
        product_name="MyECL",
        payment_product_name="MyECLPay",
        entity_name="ÉCLAIR",
        entity_site_url="https://myecl.fr/",
        api_base_url=settings.CLIENT_URL,
    )
