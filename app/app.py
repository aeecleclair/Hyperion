"""File defining the Metadata. And the basic functions creating the database tables and calling the router"""

import logging
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import alembic.command as alembic_command
import alembic.config as alembic_config
import alembic.migration as alembic_migration
from calypsso import get_calypsso_app
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from redis import Redis
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app import api
from app.core.core_endpoints import coredata_core, models_core
from app.core.google_api.google_api import GoogleAPI
from app.core.groups import models_groups
from app.core.groups.groups_type import GroupType
from app.core.schools import models_schools
from app.core.schools.schools_type import SchoolType
from app.core.utils.config import Settings
from app.core.utils.log import LogConfig
from app.dependencies import (
    get_db,
    get_redis_client,
    get_scheduler,
    get_websocket_connection_manager,
    init_and_get_db_engine,
)
from app.module import module_list
from app.types.exceptions import (
    ContentHTTPException,
    GoogleAPIInvalidCredentialsError,
    MultipleWorkersWithoutRedisInitializationError,
)
from app.types.sqlalchemy import Base
from app.utils import initialization
from app.utils.redis import limiter

if TYPE_CHECKING:
    import redis

from app.types.scheduler import Scheduler
from app.types.websocket import WebsocketConnectionManager

# NOTE: We can not get loggers at the top of this file like we do in other files
# as the loggers are not yet initialized


def get_alembic_config(connection: Connection) -> alembic_config.Config:
    """
    Return the alembic configuration object in a synchronous way
    """
    alembic_cfg = alembic_config.Config("alembic.ini")
    alembic_cfg.attributes["connection"] = connection

    return alembic_cfg


def get_alembic_current_revision(connection: Connection) -> str | None:
    """
    Return the current revision of the database in a synchronous way

    NOTE: SQLAlchemy does not support `Inspection on an AsyncConnection`. If you have an AsyncConnection, the call to this method must be wrapped in a `run_sync` call to obtain a Connection.
    See https://alembic.sqlalchemy.org/en/latest/cookbook.html#programmatic-api-use-connection-sharing-with-asyncio for more information.
        Exemple usage:
        ```python
        async with engine.connect() as conn:
            await conn.run_sync(run_alembic_upgrade)
        ```
    """

    context = alembic_migration.MigrationContext.configure(connection)
    return context.get_current_revision()


def stamp_alembic_head(connection: Connection) -> None:
    """
    Stamp the database with the latest revision in a synchronous way

    NOTE: SQLAlchemy does not support `Inspection on an AsyncConnection`. If you have an AsyncConnection, the call to this method must be wrapped in a `run_sync` call to obtain a Connection.
    See https://alembic.sqlalchemy.org/en/latest/cookbook.html#programmatic-api-use-connection-sharing-with-asyncio for more information.
        Exemple usage:
        ```python
        async with engine.connect() as conn:
            await conn.run_sync(run_alembic_upgrade)
        ```
    """
    alembic_cfg = get_alembic_config(connection)
    alembic_command.stamp(alembic_cfg, "head")


def run_alembic_upgrade(connection: Connection) -> None:
    """
    Run the alembic upgrade command to upgrade the database to the latest version (`head`) in a synchronous way

    WARNING: SQLAlchemy does not support `Inspection on an AsyncConnection`. The call to Alembic must be wrapped in a `run_sync` call.
    See https://alembic.sqlalchemy.org/en/latest/cookbook.html#programmatic-api-use-connection-sharing-with-asyncio for more information.

    NOTE: SQLAlchemy does not support `Inspection on an AsyncConnection`. If you have an AsyncConnection, the call to this method must be wrapped in a `run_sync` call to obtain a Connection.
    See https://alembic.sqlalchemy.org/en/latest/cookbook.html#programmatic-api-use-connection-sharing-with-asyncio for more information.
        Exemple usage:
        ```python
        async with engine.connect() as conn:
            await conn.run_sync(run_alembic_upgrade)
        ```
    """

    alembic_cfg = get_alembic_config(connection)

    alembic_command.upgrade(alembic_cfg, "head")


def update_db_tables(
    sync_engine: Engine,
    hyperion_error_logger: logging.Logger,
    drop_db: bool = False,
) -> None:
    """
    If the database is not initialized, create the tables and stamp the database with the latest revision.
    Otherwise, run the alembic upgrade command to upgrade the database to the latest version (`head`).

    if drop_db is True, we will drop all tables before creating them again

    This method requires a synchronous engine
    """

    try:
        # We have an Engine, we want to acquire a Connection
        with sync_engine.begin() as conn:
            if drop_db:
                initialization.drop_db_sync(conn)

            alembic_current_revision = get_alembic_current_revision(conn)

            if alembic_current_revision is None:
                # We generate the database using SQLAlchemy
                # in order not to have to run all migrations one by one
                # See https://alembic.sqlalchemy.org/en/latest/cookbook.html#building-an-up-to-date-database-from-scratch
                hyperion_error_logger.info(
                    "Startup: Database tables not created yet, creating them",
                )

                # Create all tables
                Base.metadata.create_all(conn)
                # We stamp the database with the latest revision so that
                # alembic knows that the database is up to date
                stamp_alembic_head(conn)
            else:
                hyperion_error_logger.info(
                    f"Startup: Database tables already created (current revision: {alembic_current_revision}), running migrations",
                )
                run_alembic_upgrade(conn)

            hyperion_error_logger.info("Startup: Database tables updated")
    except Exception as error:
        hyperion_error_logger.fatal(
            f"Startup: Could not create tables in the database: {error}",
        )
        raise


def initialize_groups(
    sync_engine: Engine,
    hyperion_error_logger: logging.Logger,
) -> None:
    """Add the necessary groups for account types"""

    hyperion_error_logger.info("Startup: Adding new groups to the database")
    with Session(sync_engine) as db:
        for group_type in GroupType:
            exists = initialization.get_group_by_id_sync(group_id=group_type, db=db)
            # We don't want to recreate the groups if they already exist
            if not exists:
                group = models_groups.CoreGroup(
                    id=group_type,
                    name=group_type.name,
                    description="Group type",
                )

                try:
                    initialization.create_group_sync(group=group, db=db)
                except IntegrityError as error:
                    hyperion_error_logger.fatal(
                        f"Startup: Could not add group {group.name}<{group.id}> in the database: {error}",
                    )


def initialize_schools(
    sync_engine: Engine,
    hyperion_error_logger: logging.Logger,
) -> None:
    """Add the necessary shools"""

    hyperion_error_logger.info("Startup: Adding new groups to the database")
    with Session(sync_engine) as db:
        for school in SchoolType:
            exists = initialization.get_school_by_id_sync(school_id=school.value, db=db)
            # We don't want to recreate the groups if they already exist
            if not exists:
                db_school = models_schools.CoreSchool(
                    id=school.value,
                    name=school.name,
                    email_regex="null",
                )

                try:
                    initialization.create_school_sync(school=db_school, db=db)
                except IntegrityError as error:
                    hyperion_error_logger.fatal(
                        f"Startup: Could not add school {db_school.name}<{db_school.id}> in the database: {error}",
                    )


def initialize_module_visibility(
    sync_engine: Engine,
    hyperion_error_logger: logging.Logger,
) -> None:
    """Add the default module visibilities for Titan"""

    with Session(sync_engine) as db:
        module_awareness = initialization.get_core_data_sync(
            coredata_core.ModuleVisibilityAwareness,
            db,
        )

        new_modules = [
            module
            for module in module_list
            if module.root not in module_awareness.roots
        ]
        # Is run to create default module visibilities or when the table is empty
        if new_modules:
            hyperion_error_logger.info(
                f"Startup: Some modules visibility settings are empty, initializing them ({[module.root for module in new_modules]})",
            )
            for module in new_modules:
                if module.default_allowed_groups_ids is not None:
                    for group_id in module.default_allowed_groups_ids:
                        module_group_visibility = models_core.ModuleGroupVisibility(
                            root=module.root,
                            allowed_group_id=group_id,
                        )
                        try:
                            initialization.create_module_group_visibility_sync(
                                module_visibility=module_group_visibility,
                                db=db,
                            )
                        except ValueError as error:
                            hyperion_error_logger.fatal(
                                f"Startup: Could not add module visibility {module.root} in the database: {error}",
                            )
                if module.default_allowed_account_types is not None:
                    for account_type in module.default_allowed_account_types:
                        module_account_type_visibility = (
                            models_core.ModuleAccountTypeVisibility(
                                root=module.root,
                                allowed_account_type=account_type,
                            )
                        )
                        try:
                            initialization.create_module_account_type_visibility_sync(
                                module_visibility=module_account_type_visibility,
                                db=db,
                            )
                        except ValueError as error:
                            hyperion_error_logger.fatal(
                                f"Startup: Could not add module visibility {module.root} in the database: {error}",
                            )
            initialization.set_core_data_sync(
                coredata_core.ModuleVisibilityAwareness(
                    roots=[module.root for module in module_list],
                ),
                db,
            )
            hyperion_error_logger.info(
                f"Startup: Modules visibility settings initialized for {[module.root for module in new_modules]}",
            )
        else:
            hyperion_error_logger.info(
                "Startup: Modules visibility settings already initialized",
            )


def use_route_path_as_operation_ids(app: FastAPI) -> None:
    """
    Simplify operation IDs so that generated API clients have simpler function names.

    Theses names may be used by API clients to generate function names.
    The operation_id will have the format "method_path", like "get_users_me".

    See https://fastapi.tiangolo.com/advanced/path-operation-advanced-configuration/
    """
    for route in app.routes:
        if isinstance(route, APIRoute):
            # The operation_id should be unique.
            # It is possible to set multiple methods for the same endpoint method but it's not considered a good practice.
            method = "_".join(route.methods)
            route.operation_id = method.lower() + route.path.replace("/", "_")


def init_db(
    settings: Settings,
    hyperion_error_logger: logging.Logger,
    drop_db: bool = False,
) -> None:
    """
    Init the database by creating the tables and adding the necessary groups

    The method will use a synchronous engine to create the tables and add the groups
    """
    # Initialize the sync engine
    sync_engine = initialization.get_sync_db_engine(settings=settings)

    # Update database tables
    update_db_tables(
        sync_engine=sync_engine,
        hyperion_error_logger=hyperion_error_logger,
        drop_db=drop_db,
    )

    # Initialize database tables
    initialize_groups(
        sync_engine=sync_engine,
        hyperion_error_logger=hyperion_error_logger,
    )

    # TODO: we may allow the following steps to be run by other workers
    # and may not need to wait for them
    # These two steps could use an async database connection
    initialize_schools(
        sync_engine=sync_engine,
        hyperion_error_logger=hyperion_error_logger,
    )
    initialize_module_visibility(
        sync_engine=sync_engine,
        hyperion_error_logger=hyperion_error_logger,
    )


async def init_google_API(
    db: AsyncSession,
    settings: Settings,
) -> None:
    # Init Google API credentials

    google_api = GoogleAPI()

    if google_api.is_google_api_configured(settings):
        try:
            await google_api.get_credentials(db, settings)

        except GoogleAPIInvalidCredentialsError:
            # We expect this error to be raised if the credentials were never set before
            pass


async def init_lifespan(
    app: FastAPI,
    settings: Settings,
    hyperion_error_logger: logging.Logger,
    drop_db: bool,
) -> tuple[Scheduler, WebsocketConnectionManager]:
    hyperion_error_logger.info("Startup: Initializing application")
    hyperion_error_logger.info(settings)

    # Init the Redis client
    redis_client: redis.Redis | bool | None = app.dependency_overrides.get(
        get_redis_client,
        get_redis_client,
    )(settings=settings)

    # Initialization steps should only be run once across all workers
    # We use Redis locks to ensure that the initialization steps are only run once
    if initialization.get_number_of_workers() > 1 and not isinstance(
        redis_client,
        Redis,
    ):
        raise MultipleWorkersWithoutRedisInitializationError

    # We need to run the database initialization only once across all the workers
    # Other workers have to wait for the db to be initialized
    await initialization.use_lock_for_workers(
        init_db,
        "init_db",
        redis_client,
        hyperion_error_logger,
        unlock_key="db_initialized",
        settings=settings,
        hyperion_error_logger=hyperion_error_logger,
        drop_db=drop_db,
    )

    async for db in app.dependency_overrides.get(
        get_db,
        get_db,
    )():
        await initialization.use_lock_for_workers(
            init_google_API,
            "init_google_API",
            redis_client,
            hyperion_error_logger,
            db=db,
            settings=settings,
        )

    ws_manager: WebsocketConnectionManager = app.dependency_overrides.get(
        get_websocket_connection_manager,
        get_websocket_connection_manager,
    )(settings=settings)

    arq_scheduler: Scheduler = app.dependency_overrides.get(
        get_scheduler,
        get_scheduler,
    )(settings=settings)

    await ws_manager.connect_broadcaster()
    await arq_scheduler.start(
        redis_host=settings.REDIS_HOST,
        redis_port=settings.REDIS_PORT,
        redis_password=settings.REDIS_PASSWORD,
        _dependency_overrides=app.dependency_overrides,
    )
    return arq_scheduler, ws_manager


# We wrap the application in a function to be able to pass the settings and drop_db parameters
# The drop_db parameter is used to drop the database tables before creating them again
def get_application(settings: Settings, drop_db: bool = False) -> FastAPI:
    # Initialize loggers
    LogConfig().initialize_loggers(settings=settings)

    hyperion_access_logger = logging.getLogger("hyperion.access")
    hyperion_security_logger = logging.getLogger("hyperion.security")
    hyperion_error_logger = logging.getLogger("hyperion.error")

    # We use warning level so that the message is not sent to matrix again
    if not settings.MATRIX_TOKEN:
        hyperion_error_logger.warning(
            "Matrix handlers are not configured in the .env file",
        )
    else:
        if not settings.MATRIX_LOG_ERROR_ROOM_ID:
            hyperion_error_logger.warning(
                "Matrix handler is disabled for the error room",
            )
        if not settings.MATRIX_LOG_AMAP_ROOM_ID:
            hyperion_error_logger.warning(
                "Matrix handler is disabled for the AMAP room",
            )

    # Create folder for calendars if they don't already exists
    Path("data/ics/").mkdir(parents=True, exist_ok=True)
    Path("data/core/").mkdir(parents=True, exist_ok=True)

    # Creating a lifespan which will be called when the application starts then shuts down
    # https://fastapi.tiangolo.com/advanced/events/
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator:
        arq_scheduler, ws_manager = await init_lifespan(
            app=app,
            settings=settings,
            hyperion_error_logger=hyperion_error_logger,
            drop_db=drop_db,
        )

        yield
        hyperion_error_logger.info("Shutting down")
        await arq_scheduler.close()
        await ws_manager.disconnect_broadcaster()

    # Initialize app
    app = FastAPI(
        title="Hyperion",
        version=settings.HYPERION_VERSION,
        lifespan=lifespan,
    )
    app.include_router(api.api_router)
    use_route_path_as_operation_ids(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    calypsso = get_calypsso_app()
    app.mount("/calypsso", calypsso, "Calypsso")

    # We need to init the database engine to be able to use it in dependencies
    init_and_get_db_engine(settings)

    @app.middleware("http")
    async def logging_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """
        This middleware is called around each request.
        It logs the request and inject a unique identifier in the request that should be used to associate logs saved during the request.
        """
        # We use a middleware to log every request
        # See https://fastapi.tiangolo.com/tutorial/middleware/

        # We generate a unique identifier for the request and save it as a state.
        # This identifier will allow combining logs associated with the same request
        # https://www.starlette.io/requests/#other-state
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # This should never happen, but we log it just in case
        if request.client is None:
            hyperion_security_logger.warning(
                f"Client information not available for {request.url.path}",
            )
            raise HTTPException(status_code=400, detail="No client information")

        ip_address = request.client.host
        port = request.client.port
        client_address = f"{ip_address}:{port}"

        redis_client: redis.Redis | Literal[False] | None = (
            app.dependency_overrides.get(
                get_redis_client,
                get_redis_client,
            )(settings=settings)
        )

        # We test the ip address with the redis limiter
        process = True
        if redis_client:  # If redis is configured
            process, log = limiter(
                redis_client,
                ip_address,
                settings.REDIS_LIMIT,
                settings.REDIS_WINDOW,
            )
            if log:
                hyperion_security_logger.warning(
                    f"Rate limit reached for {ip_address} (limit: {settings.REDIS_LIMIT}, window: {settings.REDIS_WINDOW})",
                )
        if process:
            response = await call_next(request)

            hyperion_access_logger.info(
                f'{client_address} - "{request.method} {request.url.path}" {response.status_code} ({request_id})',
            )
        else:
            response = Response(status_code=429, content="Too Many Requests")
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ):
        # We use a Debug logger to log the error as personal data may be present in the request
        hyperion_error_logger.debug(
            f"Validation error: {exc.errors()} ({request.state.request_id})",
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=jsonable_encoder({"detail": exc.errors(), "body": exc.body}),
        )

    @app.exception_handler(ContentHTTPException)
    async def auth_exception_handler(
        request: Request,
        exc: ContentHTTPException,
    ):
        return JSONResponse(
            status_code=exc.status_code,
            content=jsonable_encoder(exc.content),
            headers=exc.headers,
        )

    return app
