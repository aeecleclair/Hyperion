import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.groups_type import AccountType
from app.core.permissions.type_permissions import ModulePermissions
from app.core.users import models_users
from app.dependencies import (
    get_db,
    is_user_allowed_to,
)
from app.modules.todo import (
    cruds_todo,
    schemas_todo,
)
from app.types.module import Module

router = APIRouter()


class TodoPermissions(ModulePermissions):
    access_todo = "access_todo"


module = Module(
    root="todo",
    tag="Todo",
    default_allowed_account_types=[AccountType.student, AccountType.staff],
    factory=None,
    permissions=TodoPermissions,
)


@module.router.get(
    "/todo/todos",
    response_model=list[schemas_todo.Todo],
    status_code=200,
)
async def get_todos(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([TodoPermissions.access_todo]),
    ),
):
    """
    Get todos.

    **The user must be authenticated to use this endpoint**
    """

    return await cruds_todo.get_todos_by_user_id(db=db, user_id=user.id)


@module.router.post(
    "/todo/todos",
    status_code=201,
)
async def create_todo(
    todo_create: schemas_todo.TodoBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([TodoPermissions.access_todo]),
    ),
):
    """
    Create a todo.

    **The user must be authenticated to use this endpoint**
    """

    todo = schemas_todo.Todo(
        id=uuid.uuid4(),
        description=todo_create.description,
        done=False,
        user_id=user.id,
    )
    await cruds_todo.create_todo(db=db, todo=todo)
    return todo


@module.router.patch(
    "/todo/todos/{todo_id}",
    status_code=204,
)
async def update_todo(
    todo_id: uuid.UUID,
    todo_update: schemas_todo.TodoEdit,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([TodoPermissions.access_todo]),
    ),
):
    """
    Update a todo.

    **The user must be authenticated to use this endpoint**
    """

    existing_todo = await cruds_todo.get_todo_by_id(db=db, todo_id=todo_id)
    if not existing_todo or existing_todo.user_id != user.id:
        raise HTTPException(status_code=404, detail="Todo not found")

    await cruds_todo.update_todo(db=db, todo_id=todo_id, todo=todo_update)


@module.router.delete(
    "/todo/todos/{todo_id}",
    status_code=204,
)
async def delete_todo(
    todo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([TodoPermissions.access_todo]),
    ),
):
    """
    Delete a todo.

    **The user must be authenticated to use this endpoint**
    """

    existing_todo = await cruds_todo.get_todo_by_id(db=db, todo_id=todo_id)
    if not existing_todo or existing_todo.user_id != user.id:
        raise HTTPException(status_code=404, detail="Todo not found")

    await cruds_todo.delete_todo(db=db, todo_id=todo_id)
