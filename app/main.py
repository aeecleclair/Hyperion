from fastapi import FastAPI
from app import api


app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


app.include_router(api.api_router)
