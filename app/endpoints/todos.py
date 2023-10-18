import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_todos
from app.dependencies import get_db, is_user_a_member
from app.models import models_core, models_todos
from app.schemas import schemas_todos
from app.utils.types.tags import Tags

router = APIRouter()


@router.get(
    "/todos/",
    response_model=list[schemas_todos.TodosItemComplete],
    status_code=200,
    tags=[Tags.todos],
)
async def get_todos(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Return all the todos of the current user
    """

    return await cruds_todos.get_items_by_user_id(db=db, user_id=user.id)


# We define a new endpoint, accepting a POST, that intend to create a new todo
@router.post(
    "/todos/",
    response_model=schemas_todos.TodosItemBase,
    status_code=201,
    tags=[Tags.todos],
)
async def create_todo(
    item: schemas_todos.TodosItemBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    # Currently, `item` is a schema instance
    # To add it to the database, we need to create a model

    # We need to generate a new UUID for the todo
    todo_id = str(uuid.uuid4())
    # And get the current date and time
    creation_time = date.today()

    db_item = models_todos.TodosItem(
        id=todo_id,
        creation=creation_time,
        user_id=user.id,
        **item.dict(),  # We add all informations contained in the schema, the operation is called unpacking
    )
    try:
        res = await cruds_todos.create_item(
            item=db_item,
            db=db,
        )
        return res
    except ValueError as error:
        # If we failed to create the object in the database, we send back a 400 error code with the detail of the error
        raise HTTPException(status_code=400, detail=str(error))


# We define a POST endpoint to make a todo as done or undone
@router.post(
    "/todos/{id}/check",
    status_code=204,
    tags=[Tags.todos],
)
async def check_todo(
    id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Mark an item as done or not done depending its current status
    """

    # We first need to make sur an item with the identifier `id` exist
    item = await cruds_todos.get_item_by_id(db=db, id=id)
    if item is None:
        raise HTTPException(status_code=404, detail="Todo item not found")
    # We need to make sure the item belongs to the current user
    if item.user_id != user.id:
        raise HTTPException(
            status_code=403, detail="The user can only edit its own items"
        )

    current_status = item.done
    new_status = not current_status

    await cruds_todos.edit_done_status(
        db=db,
        id=id,
        done=new_status,
    )
