from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/users")
async def users():

    return {"users": ["K2", "Tyshaud"]}
