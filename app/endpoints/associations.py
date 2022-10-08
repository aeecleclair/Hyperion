from fastapi import APIRouter

router = APIRouter()


@router.get("/associations")
async def get_associations():

    return ""


@router.get("/associations/{association_id}")
async def get_association(association_id):

    return ""


@router.put("/associations")
async def edit_association():

    return ""


@router.post("/associations")
async def create_association():

    return ""


@router.get("/associations/{association_id}/users")
async def get_users_association(association_id):

    return ""


@router.post("/associations/{association_id}/users/{user_id}")
async def create_user_association(association_id, user_id):

    return ""


@router.delete("/associations/{association_id}/users/{user_id}")
async def delete_user_association(association_id, user_id):

    return ""


@router.post("/associations/{association_id}/admins/{user_id}")
async def create_admin_association(association_id, user_id):

    return ""


@router.delete("/associations/{association_id}/admins/{user_id}")
async def delete_admin_association(association_id, user_id):

    return ""
