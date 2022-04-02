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
