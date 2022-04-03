from fastapi import FastAPI

from app import api

app = FastAPI()

app.include_router(api.api_router)
