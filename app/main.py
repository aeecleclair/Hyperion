from fastapi import FastAPI
from app import api

# from . import models
from .database import engine, Base

Base.metadata.create_all(bind=engine)


app = FastAPI()

# Décommenter cette partie en dev pour créer la base de donnée la première fois


@app.on_event("startup")
async def startup():
    # create db tables
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


app.include_router(api.api_router)
