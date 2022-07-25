"""Basic function creating the database tables and calling the router"""

import logging
import logging.config
import uuid

from fastapi import FastAPI, Request
from sqlalchemy.exc import IntegrityError

from app import api
from app.core.log import LogConfig
from app.database import Base, SessionLocal, engine
from app.models import models_core
from app.utils.types.groups_type import AccountType

app = FastAPI()

# create file handler which logs even debug messages
fh = logging.FileHandler("access.log")
fh.setLevel(logging.DEBUG)

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
fh.setFormatter(formatter)


hyperion_access_logger = logging.getLogger("hyperion.access")
hyperion_access_logger.setLevel(logging.DEBUG)
hyperion_access_logger.addHandler(fh)



LogConfig.initialize_loggers()

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

    # If the client host and port is provided, we want to log it
    if request.client is not None:
        client_address = f"{request.client.host}:{request.client.port}"
    else:
        client_address = "unknown"

    hyperion_access_logger.info(
        f'{client_address} - "{request.method} {request.url.path}" {response.status_code} ({request_id})'
    )
    return response


# Alembic should be used for any migration, this function can only create new tables and ensure that the necessary groups are avaible
@app.on_event("startup")
async def startup():
    # create db tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Add the necessary groups for account types
    description = "Account type"
    account_types = [
        models_core.CoreGroup(id=id, name=id.name, description=description)
        for id in AccountType
    ]
    async with SessionLocal() as db:
        try:
            db.add_all(account_types)
            await db.commit()
        except IntegrityError:
            await db.rollback()


app.include_router(api.api_router)
