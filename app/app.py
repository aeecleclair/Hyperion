"""File defining the Metadata. And the basic functions creating the database tables and calling the router"""
import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import Literal

import alembic.command as alembic_command
import alembic.config as alembic_config
import alembic.migration as alembic_migration
import redis
from fastapi import FastAPI, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

from app import api
from app.core.config import Settings
from app.core.log import LogConfig
from app.cruds import cruds_core, cruds_groups
from app.database import Base
from app.dependencies import (
    get_db_engine,
    get_redis_client,
    get_session_maker,
    get_settings,
)
from app.models import models_core
from app.utils.redis import limiter
from app.utils.types.groups_type import GroupType
from app.utils.types.module_list import ModuleList

# NOTE: We can not get loggers at the top of this file like we do in other files
# as the loggers are not yet initialized


def get_alembic_config(connection: Connection) -> alembic_config.Config:
    """
    Return the alembic configuration object
    """
    alembic_cfg = alembic_config.Config("alembic.ini")
    alembic_cfg.attributes["connection"] = connection

    return alembic_cfg


def get_alembic_current_revision(connection: Connection) -> str | None:
    """
    Return the current revision of the database
    """

    context = alembic_migration.MigrationContext.configure(connection)
    return context.get_current_revision()


def stamp_alembic_head(connection: Connection) -> None:
    """
    Stamp the database with the latest revision
    """
    alembic_cfg = get_alembic_config(connection)
    alembic_command.stamp(alembic_cfg, "head")


def run_alembic_upgrade(connection: Connection) -> None:
    """
    Run the alembic upgrade command to upgrade the database to the latest version (`head`)

    WARNING: SQLAlchemy does not support `Inspection on an AsyncConnection`. The call to Alembic must be wrapped in a `run_sync` call.
    See https://alembic.sqlalchemy.org/en/latest/cookbook.html#programmatic-api-use-connection-sharing-with-asyncio for more information.

    Exemple usage:
    ```python
    async with engine.connect() as conn:
        await conn.run_sync(run_alembic_upgrade)
    ```
    """

    alembic_cfg = get_alembic_config(connection)

    alembic_command.upgrade(alembic_cfg, "head")


async def update_db_tables(engine: AsyncEngine, drop_db: bool = False):
    """Create db tables
    Alembic should be used for any migration, this function can only create new tables and ensure that the necessary groups are available
    """

    hyperion_error_logger = logging.getLogger("hyperion.error")

    try:
        async with engine.begin() as conn:
            if drop_db:
                # All tables should be dropped, including the alembic_version table
                # or Hyperion will think that the database is up to date and will not initialize it
                # when running tests a second time.
                # To let SQLAlchemy drop the alembic_version table, we created a AlembicVersion model.
                await conn.run_sync(Base.metadata.drop_all)

            # run_sync is used to run a synchronous function in an asynchronous context
            # the function `get_alembic_current_revision` will be called with "a synchronous-style Connection as the first argument"
            # See https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#sqlalchemy.ext.asyncio.AsyncConnection.run_sync
            alembic_current_revision = await conn.run_sync(get_alembic_current_revision)

            if alembic_current_revision is None:
                # We generate the database using SQLAlchemy
                # in order not to have to run all migrations one by one
                # See https://alembic.sqlalchemy.org/en/latest/cookbook.html#building-an-up-to-date-database-from-scratch
                hyperion_error_logger.info(
                    "Startup: Database tables not created yet, creating them"
                )

                # Create all tables
                await conn.run_sync(Base.metadata.create_all)
                # We stamp the database with the latest revision so that
                # alembic knows that the database is up to date
                await conn.run_sync(stamp_alembic_head)
            else:
                hyperion_error_logger.info(
                    f"Startup: Database tables already created (current revision: {alembic_current_revision}), running migrations"
                )
                await conn.run_sync(run_alembic_upgrade)

            hyperion_error_logger.info("Startup: Database tables updated")
    except Exception as error:
        hyperion_error_logger.fatal(
            f"Startup: Could not create tables in the database: {error}"
        )
        raise


async def initialize_groups(SessionLocal, hyperion_error_logger):
    """Add the necessary groups for account types"""
    async with SessionLocal() as db:
        for id in GroupType:
            exists = await cruds_groups.get_group_by_id(group_id=id, db=db)
            # We don't want to recreate the groups if they already exist
            if not exists:
                group = models_core.CoreGroup(
                    id=id, name=id.name, description="Group type"
                )

                try:
                    db.add(group)
                    await db.commit()
                except IntegrityError as error:
                    hyperion_error_logger.fatal(
                        f"Startup: Could not add group {group.name}<{group.id}> in the database: {error}"
                    )
                    await db.rollback()


async def initialize_module_visibility(SessionLocal, hyperion_error_logger):
    """Add the default module visibilities for Titan"""
    async with SessionLocal() as db:
        # Is run to create default module visibilies or when the table is empty
        haveBeenInitialized = (
            len(await cruds_core.get_all_module_visibility_membership(db)) > 0
        )
        if haveBeenInitialized:
            return
        for module in ModuleList:
            for default_group_id in module.value.default_allowed_groups_ids:
                module_visibility_exists = await cruds_core.get_module_visibility(
                    root=module.value.root, group_id=default_group_id, db=db
                )

                # We don't want to recreate the module visibility if they already exist
                if not module_visibility_exists:
                    module_visibility = models_core.ModuleVisibility(
                        root=module.value.root, allowed_group_id=default_group_id.value
                    )
                    try:
                        db.add(module_visibility)
                        await db.commit()
                    except IntegrityError as error:
                        hyperion_error_logger.fatal(
                            f"Startup: Could not add module visibility {module.root}<{default_group_id}> in the database: {error}"
                        )
                        await db.rollback()


# We wrap the application in a function to be able to pass the settings and drop_db parameters
# The drop_db parameter is used to drop the database tables before creating them again
def get_application(settings: Settings, drop_db: bool = False) -> FastAPI:
    LogConfig().initialize_loggers(settings=settings)

    hyperion_access_logger = logging.getLogger("hyperion.access")
    hyperion_security_logger = logging.getLogger("hyperion.security")
    hyperion_error_logger = logging.getLogger("hyperion.error")

    # Create folder for calendars
    if not os.path.exists("data/ics/"):
        os.makedirs("data/ics/")

    if not os.path.exists("data/core/"):
        os.makedirs("data/core/")

    # Creating a lifespan which will be called when the application starts then shuts down
    # https://fastapi.tiangolo.com/advanced/events/
    @asynccontextmanager
    async def startup(app: FastAPI):
        # Initialize loggers

        if (
            app.dependency_overrides.get(get_redis_client, get_redis_client)(
                settings=settings
            )
            is False
        ):
            hyperion_error_logger.info("Redis client not configured")

        # Update database tables
        engine = app.dependency_overrides.get(get_db_engine, get_db_engine)(
            settings=settings
        )
        await update_db_tables(engine, drop_db)

        # Initialize database tables
        SessionLocal = app.dependency_overrides.get(
            get_session_maker, get_session_maker
        )()
        await initialize_groups(SessionLocal, hyperion_error_logger)
        await initialize_module_visibility(SessionLocal, hyperion_error_logger)

        yield
        hyperion_error_logger.info("Shutting down")

    app = FastAPI(lifespan=startup)
    app.include_router(api.api_router)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def logging_middleware(
        request: Request,
        call_next,
    ):
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

        if request.client is not None:
            ip_address = request.client.host
            port = request.client.port
            client_address = f"{ip_address}:{port}"
        else:
            client_address = "unknown"

        settings: Settings = app.dependency_overrides.get(get_settings, get_settings)()
        redis_client: redis.Redis | Literal[
            False
        ] | None = app.dependency_overrides.get(get_redis_client, get_redis_client)(
            settings=settings
        )

        # We test the ip address with the redis limiter
        process = True
        if redis_client:  # If redis is configured
            process, log = limiter(
                redis_client, ip_address, settings.REDIS_LIMIT, settings.REDIS_WINDOW
            )
            if log:
                hyperion_security_logger.warning(
                    f"Rate limit reached for {ip_address} (limit: {settings.REDIS_LIMIT}, window: {settings.REDIS_WINDOW})"
                )
        if process:
            response = await call_next(request)

            hyperion_access_logger.info(
                f'{client_address} - "{request.method} {request.url.path}" {response.status_code} ({request_id})'
            )
        else:
            response = Response(status_code=429, content="Too Many Requests")
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        # We use a Debug logger to log the error as personal data may be present in the request
        hyperion_error_logger.debug(
            f"Validation error: {exc.errors()} ({request.state.request_id})"
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=jsonable_encoder({"detail": exc.errors(), "body": exc.body}),
        )

    return app
