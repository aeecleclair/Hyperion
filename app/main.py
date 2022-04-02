from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


# Requêtes users
@app.get("/users")
async def get_users():

    return {"users": ["K2", "Tyshaud"]}


@app.post("/users")
async def create_user():

    return ""


@app.get("/users/{user_id}")
async def get_user(user_id):

    return ""


@app.put("/users/{user_id}")
async def edit_user(user_id):

    return ""


@app.delete("/users/{user_id}")
async def delete_user(user_id):

    return ""


# Requêtes associations
@app.get("/associations")
async def get_associations():

    return ""


@app.get("/associations/{association_id}")
async def get_association(association_id):

    return ""


@app.post("/associations")
async def create_association():

    return ""


@app.get("/associations/{association_id}/users")
async def get_users_association(association_id):

    return ""


@app.post("/assocations/{association_id}/users/{user_id}")
async def create_user_association(association_id, user_id):

    return ""


@app.delete("/associations/{association_id}/users/{user_id}")
async def delete_user_association(association_id, user_id):

    return ""


@app.post("/associations/{association_id}/admins/{user_id}")
async def create_admin_association(association_id, user_id):

    return ""


@app.delete("/associations/{association_id}/admins/{user_id}")
async def delete_admin_association(association_id, user_id):

    return ""
