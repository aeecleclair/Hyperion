from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


j = [1, 2, 3]

maVariable = 4

if 1:
    print(1)
