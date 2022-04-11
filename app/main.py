"""Basic function creating the database tables and calling the router"""

from fastapi import FastAPI

from app import api
from app.database import Base, engine

app = FastAPI()


# Alembic should be used for any migration, this function can only create new tables
@app.on_event("startup")
async def startup():
    # create db tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


app.include_router(api.api_router)
