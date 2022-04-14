"""Basic function creating the database tables and calling the router"""

from fastapi import FastAPI
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal

from app import api
from app.database import Base, engine
from app.utils.types.account_type import AccountType
from app.models import models_core


app = FastAPI()


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
