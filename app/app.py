"""File defining the Metadata. And the basic functions creating the database tables and calling the router"""

import logging
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

import alembic.command as alembic_command
import alembic.config as alembic_config
import alembic.migration as alembic_migration
import redis
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
from app.core.core_endpoints import coredata_core
from app.core.google_api.google_api import GoogleAPI
from app.core.groups import models_groups
from app.core.groups.groups_type import AccountType, GroupType
from app.core.notification.cruds_notification import get_notification_topic
from app.core.schools import models_schools
from app.core.schools.schools_type import SchoolType
from app.core.utils.config import Settings
from app.core.utils.log import LogConfig
from app.dependencies import (
    disconnect_state,
    get_db,
    get_notification_manager,
    get_redis_client,
    init_state,
)
from app.module import all_modules, module_list, permissions_list
from app.types.exceptions import (
    ContentHTTPException,
    GoogleAPIInvalidCredentialsError,
    MultipleWorkersWithoutRedisInitializationError,
)
from app.types.sqlalchemy import Base
from app.utils import initialization
from app.utils.auth.providers import AuthPermissions
from app.utils.communication.notifications import NotificationManager
from app.utils.redis import limiter
from app.utils.state import LifespanState

if TYPE_CHECKING:
    import redis

    from app.types.factory import Factory


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


async def run_factories(
    db: AsyncSession,
    settings: Settings,
    hyperion_error_logger: logging.Logger,
) -> None:
    """Run the factories to create default data in the database"""
    if not settings.USE_FACTORIES:
        return

    hyperion_error_logger.info("Startup: Factories enabled")
    # Importing the core_factory at the beginning of the factories.
    factories_list: list[Factory] = []
    for module in all_modules:
        if module.factory:
            factories_list.append(module.factory)
            hyperion_error_logger.info(
                f"Module {module.root} declares a factory {module.factory.__class__.__name__} with dependencies {module.factory.depends_on}",
            )
        else:
            hyperion_error_logger.warning(
                f"Module {module.root} does not declare a factory. It won't provide any base data.",
            )

    # We have to run the factories in a specific order to make sure the dependencies are met
    # For that reason, we will run the first factory that has no dependencies, after that we remove it from the list of the dependencies from the other factories
    # And we loop until there are no more factories to run and we use a boolean to avoid infinite loops with circular dependencies
    no_factory_run_during_last_loop = False
    ran_factories: list[type[Factory]] = []
    while len(factories_list) > 0 and not no_factory_run_during_last_loop:
        no_factory_run_during_last_loop = True
        for factory in factories_list:
            if all(depend in ran_factories for depend in factory.depends_on):
                no_factory_run_during_last_loop = False
                # Check if the factory should be run
                if await factory.should_run(db):
                    hyperion_error_logger.info(
                        f"Startup: Running factory {factory.__class__.__name__}",
                    )
                    try:
                        await factory.run(db, settings)
                    except Exception as error:
                        hyperion_error_logger.fatal(
                            f"Startup: Could not run factories: {error}",
                        )
                        raise
                else:
                    hyperion_error_logger.info(
                        f"Startup: Factory {factory.__class__.__name__} is not necessary, skipping it",
                    )
                ran_factories.append(factory.__class__)
                factories_list.remove(factory)
                break
        if no_factory_run_during_last_loop:
            hyperion_error_logger.error(
                "Factories are not correctly configured, some factories are not running.",
            )
            break
    hyperion_error_logger.info("Startup: Factories have been run")


def initialize_module_visibility(
    sync_engine: Engine,
    hyperion_error_logger: logging.Logger,
) -> None:
    """Add the default module visibilities for Titan"""
    AUTH_PERMISSIONS_CONSTANT = [AuthPermissions.app, AuthPermissions.api]
    AUTH_PERMISSIONS_LIST =[ list(AccountType), list(AccountType)]

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
        new_auth = [
            auth for auth in AUTH_PERMISSIONS_CONSTANT if auth.value not in module_awareness.roots
        ]
        # Is run to create default module visibilities or when the table is empty
        if new_modules or new_auth:
            hyperion_error_logger.info(
                f"Startup: Some modules visibility or auth settings are empty, initializing them : ({[module.root for module in new_modules] + new_auth})",
            )
            for module in new_modules:
                module_permissions = (
                    list(module.permissions) if module.permissions else []
                )
                access_permission = next(
                    (p for p in module_permissions if p.startswith("access_")),
                    None,
                )
                if access_permission:
                    if module.default_allowed_groups_ids is not None:
                        for group_id in module.default_allowed_groups_ids:
                            try:
                                initialization.create_group_permission_sync(
                                    group_id=group_id,
                                    permission_name=access_permission,
                                    db=db,
                                )
                            except ValueError as error:
                                hyperion_error_logger.fatal(
                                    f"Startup: Could not add module visibility {module.root} in the database: {error}",
                                )
                    if module.default_allowed_account_types is not None:
                        for account_type in module.default_allowed_account_types:
                            try:
                                initialization.create_account_type_permission_sync(
                                    account_type=account_type,
                                    permission_name=access_permission,
                                    db=db,
                                )
                            except ValueError as error:
                                hyperion_error_logger.fatal(
                                    f"Startup: Could not add module visibility {module.root} in the database: {error}",
                                )
            for i,auth in enumerate(new_auth):
                for account_type in AUTH_PERMISSIONS_LIST[i]:
                    try:
                        initialization.create_account_type_permission_sync(
                            account_type=account_type,
                            permission_name=auth,
                            db=db,
                        )
                    except ValueError as error:
                        hyperion_error_logger.fatal(
                            f"Startup: Could not add auth visibility {auth} in the database: {error}",
                        )
            initialization.set_core_data_sync(
                coredata_core.ModuleVisibilityAwareness(
                    roots=[module.root for module in module_list] + AUTH_PERMISSIONS_CONSTANT,
                ),
                db,
            )
            hyperion_error_logger.info(
                f"Startup: Modules visibility settings initialized for {[module.root for module in new_modules ] + new_auth}",
            )
        else:
            hyperion_error_logger.info(
                "Startup: Modules visibility settings already initialized",
            )


async def initialize_notification_topics(
    db: AsyncSession,
    hyperion_error_logger: logging.Logger,
    notification_manager: NotificationManager,
) -> None:
    existing_topics = await get_notification_topic(db=db)
    existing_topics_id = [topic.id for topic in existing_topics]
    for module in all_modules:
        if module.registred_topics:
            for registred_topic in module.registred_topics:
                if registred_topic.id not in existing_topics_id:
                    # We want to register this new topic
                    hyperion_error_logger.info(
                        f"Registering topic {registred_topic.name} ({registred_topic.id})",
                    )
                    await notification_manager.register_new_topic(
                        topic_id=registred_topic.id,
                        name=registred_topic.name,
                        module_root=registred_topic.module_root,
                        topic_identifier=registred_topic.topic_identifier,
                        restrict_to_group_id=registred_topic.restrict_to_group_id,
                        restrict_to_members=registred_topic.restrict_to_members,
                        db=db,
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
    with Session(sync_engine) as db:
        initialization.clean_permissions_sync(db, permissions_list)


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


def test_configuration(
    settings: Settings,
    hyperion_error_logger: logging.Logger,
) -> None:
    """
    Test configuration and log warnings if some settings are not configured correctly.
    """

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


async def init_lifespan(
    app: FastAPI,
    settings: Settings,
    hyperion_error_logger: logging.Logger,
    drop_db: bool,
) -> LifespanState:
    hyperion_error_logger.info("Startup: Initializing application")

    # We get `init_state` as a dependency, as tests
    # should override it to provide their own state
    await app.dependency_overrides.get(
        init_state,
        init_state,
    )(
        app=app,
        settings=settings,
        hyperion_error_logger=hyperion_error_logger,
    )

    redis_client: Redis | None = app.dependency_overrides.get(
        get_redis_client,
        get_redis_client,
    )()

    # Initialization steps should only be run once across all workers
    # We use Redis locks to ensure that the initialization steps are only run once
    number_of_workers = initialization.get_number_of_workers()
    if number_of_workers > 1 and not isinstance(
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
        number_of_workers,
        hyperion_error_logger,
        unlock_key="db_initialized",
        settings=settings,
        hyperion_error_logger=hyperion_error_logger,
        drop_db=drop_db,
    )

    await initialization.use_lock_for_workers(
        test_configuration,
        "test_configuration",
        redis_client,
        number_of_workers,
        hyperion_error_logger,
        settings=settings,
        hyperion_error_logger=hyperion_error_logger,
    )

    get_db_dependency: Callable[
        [],
        AsyncGenerator[AsyncSession],
    ] = app.dependency_overrides.get(
        get_db,
        get_db,
    )
    # We need to run the factories only once across all the workers
    async for db in get_db_dependency():
        await initialization.use_lock_for_workers(
            run_factories,
            "run_factories",
            redis_client,
            number_of_workers,
            hyperion_error_logger,
            db=db,
            settings=settings,
            hyperion_error_logger=hyperion_error_logger,
        )
    async for db in get_db_dependency():
        await initialization.use_lock_for_workers(
            init_google_API,
            "init_google_API",
            redis_client,
            number_of_workers,
            hyperion_error_logger,
            db=db,
            settings=settings,
        )

    async for db in get_db_dependency():
        notification_manager = app.dependency_overrides.get(
            get_notification_manager,
            get_notification_manager,
        )()
        await initialization.use_lock_for_workers(
            initialize_notification_topics,
            "initialize_notification_topics",
            redis_client,
            number_of_workers,
            hyperion_error_logger,
            db=db,
            hyperion_error_logger=hyperion_error_logger,
            notification_manager=notification_manager,
        )

    return LifespanState()


# We wrap the application in a function to be able to pass the settings and drop_db parameters
# The drop_db parameter is used to drop the database tables before creating them again
def get_application(settings: Settings, drop_db: bool = False) -> FastAPI:
    # Initialize loggers
    LogConfig().initialize_loggers(settings=settings)

    hyperion_access_logger = logging.getLogger("hyperion.access")
    hyperion_security_logger = logging.getLogger("hyperion.security")
    hyperion_error_logger = logging.getLogger("hyperion.error")

    # Creating a lifespan which will be called when the application starts then shuts down
    # https://fastapi.tiangolo.com/advanced/events/
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[LifespanState]:
        state = await init_lifespan(
            app=app,
            settings=settings,
            hyperion_error_logger=hyperion_error_logger,
            drop_db=drop_db,
        )

        yield state

        hyperion_error_logger.info("Shutting down")
        await app.dependency_overrides.get(
            disconnect_state,
            disconnect_state,
        )(
            hyperion_error_logger=hyperion_error_logger,
        )

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

    get_redis_client_dependency = app.dependency_overrides.get(
        get_redis_client,
        get_redis_client,
    )

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

        ip_address = str(
            request.client.host,
        )  # host can be an Object of type IPv4Address or IPv6Address and would be refused by redis
        port = request.client.port
        client_address = f"{ip_address}:{port}"

        redis_client: redis.Redis | None = get_redis_client_dependency()

        # We test the ip address with the redis limiter
        process = True
        if redis_client and settings.ENABLE_RATE_LIMITER:  # If redis is configured
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
