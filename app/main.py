from fastapi import FastAPI
from routers import amap, associations, bdebooking, bdecalendar, users


app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}
