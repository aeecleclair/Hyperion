from fastapi import FastAPI
from app.endpoints import amap, associations, bdebooking, bdecalendar, users


app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}
