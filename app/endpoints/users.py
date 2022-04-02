from fastapi import APIRouter

router = APIRouter()


@router.get("/users")
async def get_users():

    return {"users": ["K2", "Tyshaud"]}


@router.post("/users")
async def create_user():

    return ""


@router.get("/users/{user_id}")
async def get_user(user_id):

    return ""


@router.put("/users/{user_id}")
async def edit_user(user_id):

    return ""


@router.delete("/users/{user_id}")
async def delete_user(user_id):

    return ""
