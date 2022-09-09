"""Basic function creating the database tables and calling the router"""

import logging
import logging.config
import os
import uuid

from fastapi import FastAPI, Request
from icalendar import Calendar
from sqlalchemy.exc import IntegrityError

from app import api
from app.core.log import LogConfig
from app.database import Base, SessionLocal, engine
from app.dependencies import get_settings
from app.models import models_core
from app.utils.types.groups_type import GroupType

app = FastAPI()


hyperion_access_logger = logging.getLogger("hyperion.access")


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

    response = await call_next(request)

    if request.client is not None:
        client_address = f"{request.client.host}:{request.client.port}"
    else:
        client_address = "unknown"

    hyperion_access_logger.info(
        f'{client_address} - "{request.method} {request.url.path}" {response.status_code} ({request_id})'
    )
    return response


# Alembic should be used for any migration, this function can only create new tables and ensure that the necessary groups are available
@app.on_event("startup")
async def startup():
    # Initialize loggers
    # Unfortunately, FastAPI does not support using dependency in startup events.
    # We reproduce FastAPI logic to access settings. See https://github.com/tiangolo/fastapi/issues/425#issuecomment-954963966
    settings = app.dependency_overrides.get(get_settings, get_settings)()
    LogConfig().initialize_loggers(settings=settings)

    # Create the data folders if it does not exist
    if not os.path.exists("data/profile-pictures/"):
        os.makedirs("data/profile-pictures/")

    # Create folder for calendars
    if not os.path.exists("data/ics/"):
        os.makedirs("data/ics/")

    if not os.path.exists("data/ics/ae_calendar.ics"):
        calendar = Calendar()
        calendar.add("version", "2.0")
        calendar.add("proid", "myecl.fr")
        with open("data/ics/ae_calendar.ics", "wb") as file_calendar:
            file_calendar.write(calendar.to_ical())
        hyperion_access_logger.info("ae_calendar.ics has been created.")

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
