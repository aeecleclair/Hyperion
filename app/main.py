"""Basic functions creating the database tables and calling the router"""

import logging
import os
import uuid
from typing import Literal

import redis
from fastapi import FastAPI, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app import api
from app.core.config import Settings
from app.core.log import LogConfig
from app.cruds import cruds_groups
from app.database import Base, SessionLocal, engine
from app.dependencies import get_redis_client, get_settings
from app.models import models_core
from app.utils.redis import limiter
from app.utils.types.groups_type import GroupType

app = FastAPI()


hyperion_access_logger = logging.getLogger("hyperion.access")
hyperion_security_logger = logging.getLogger("hyperion.security")
hyperion_error_logger = logging.getLogger("hyperion.error")

# Unfortunately, FastAPI does not support using dependency in startup events.
# We reproduce FastAPI logic to access settings. See https://github.com/tiangolo/fastapi/issues/425#issuecomment-954963966
settings = app.dependency_overrides.get(get_settings, get_settings)()


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
    redis_client: redis.Redis | Literal[False] | None = app.dependency_overrides.get(
        get_redis_client, get_redis_client
    )(settings=settings)

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
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # We use a Debug logger to log the error as personal data may be present in the request
    hyperion_error_logger.debug(
        f"Validation error: {exc.errors()} ({request.state.request_id})"
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"detail": exc.errors(), "body": exc.body}),
    )


# Alembic should be used for any migration, this function can only create new tables and ensure that the necessary groups are available
@app.on_event("startup")
async def startup():
    # Initialize loggers

    LogConfig().initialize_loggers(settings=settings)

    if not app.dependency_overrides.get(get_redis_client, get_redis_client)(
        settings=settings
    ):
        hyperion_error_logger.info("Redis client not configured")

    # Create the data folders if it does not exist
    if not os.path.exists("data/profile-pictures/"):
        os.makedirs("data/profile-pictures/")
    if not os.path.exists("data/campaigns/"):
        os.makedirs("data/campaigns/")

    # Create folder for calendars
    if not os.path.exists("data/ics/"):
        os.makedirs("data/ics/")

    # create db tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Add the necessary groups for account types
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


app.include_router(api.api_router)
