from app.utils.types.module import Module

associations = Module(root="/associations")


@associations.router.get("/associations")
async def get_associations():
    return ""


@associations.router.get("/associations/{association_id}")
async def get_association(association_id):
    return ""


@associations.router.put("/associations")
async def edit_association():
    return ""


@associations.router.post("/associations")
async def create_association():
    return ""


@associations.router.get("/associations/{association_id}/users")
async def get_users_association(association_id):
    return ""


@associations.router.post("/associations/{association_id}/users/{user_id}")
async def create_user_association(association_id, user_id):
    return ""


@associations.router.delete("/associations/{association_id}/users/{user_id}")
async def delete_user_association(association_id, user_id):
    return ""


@associations.router.post("/associations/{association_id}/admins/{user_id}")
async def create_admin_association(association_id, user_id):
    return ""


@associations.router.delete("/associations/{association_id}/admins/{user_id}")
async def delete_admin_association(association_id, user_id):
    return ""
