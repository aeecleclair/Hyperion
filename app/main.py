"""Basic function creating the database tables and calling the router"""

import logging
import logging.config
import os
import uuid

from fastapi import FastAPI, Request, Response
from sqlalchemy.exc import IntegrityError

from app import api
from app.core.log import LogConfig
from app.database import Base, SessionLocal, engine
from app.dependencies import get_settings
from app.models import models_core
from app.utils import redis
from app.utils.types.groups_type import GroupType

app = FastAPI()

# We reproduce FastAPI logic to access settings. See https://github.com/tiangolo/fastapi/issues/425#issuecomment-954963966
settings = app.dependency_overrides.get(get_settings, get_settings)()
if settings.REDIS_HOST != "":
    redis_client = redis.connect(settings)
    process_all = False
else:
    process_all = True  # If redis is not configured, we don't use the rate limiter, so we will process every request


hyperion_access_logger = logging.getLogger("hyperion.access")
hyperion_security_logger = logging.getLogger("hyperion.security")


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """
    This middleware is called around each requests.
    It logs the request and inject an unique identifier in the request that should be used to associate logs saved during the request.
    """
    # We use a middleware to log every requests
    # See https://fastapi.tiangolo.com/tutorial/middleware/

    # We generate an unique identifier for the request and save it as a state.
    # This identifier will allow to combine logs associated with the same request
    # https://www.starlette.io/requests/#other-state
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    if request.client is not None:
        ip_address = request.client.host
        port = request.client.port
        client_address = f"{ip_address}:{port}"
    else:
        client_address = "unknown"

    # We test the ip adress with the redis limiter
    if not process_all:  # If redis is configured
        process, log = redis.limiter(
            redis_client, ip_address, settings.REDIS_LIMIT, settings.REDIS_WINDOW
        )
        if log:
            hyperion_security_logger.warning(
                f"Rate limit reached for {ip_address} (limit: {settings.REDIS_LIMIT}, window: {settings.REDIS_WINDOW})"
            )
    if process_all or process:
        response = await call_next(request)

        hyperion_access_logger.info(
            f'{client_address} - "{request.method} {request.url.path}" {response.status_code} ({request_id})'
        )
    else:
        response = Response(status_code=429, content="Too Many Requests")
    return response


# Alembic should be used for any migration, this function can only create new tables and ensure that the necessary groups are available
@app.on_event("startup")
async def startup():
    # Initialize loggers
    LogConfig().initialize_loggers(settings=settings)

    # Create the asset folder if it does not exist
    if not os.path.exists("data/profile-pictures/"):
        os.makedirs("data/profile-pictures/")

    # create db tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Add the necessary groups for account types
    # TODO:fix also in tests
    description = "Group type"
    account_types = [
        models_core.CoreGroup(id=id, name=id.name, description=description)
        for id in GroupType
    ]
    async with SessionLocal() as db:
        try:
            db.add_all(account_types)
            await db.commit()
        except IntegrityError:
            await db.rollback()


app.include_router(api.api_router)
