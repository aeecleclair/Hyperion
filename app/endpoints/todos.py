import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_todos
from app.dependencies import get_db
from app.models import models_todos
from app.schemas import schemas_todos
from app.utils.types.tags import Tags

router = APIRouter()


@router.get(
    "/todos/{user_id}",
    response_model=list[schemas_todos.TodosItemInDB],
    status_code=200,
    tags=[Tags.todos],
)
async def get_todos(user_id: str, db: AsyncSession = Depends(get_db)):
    groups = await cruds_todos.get_todo_items_by_user_id(db=db, user_id=user_id)
    return groups


@router.post(
    "/todos/",
    response_model=schemas_todos.TodosItemBase,
    status_code=201,
    tags=[Tags.todos],
)
async def create_todo(
    todo_item: schemas_todos.TodosItemBase, db: AsyncSession = Depends(get_db)
):
    # Currently, todo_item is a schema instance
    # To add it to the database, we need to create a model

    # We need to generate a new UUID for the todo
    todo_id = str(uuid.uuid4())
    # And get the current date and time
    creation_time = datetime.now()

    db_todo_item = models_todos.TodosItem(
        todo_id=todo_id,
        creation_time=creation_time,
        **todo_item.dict(),  # We add all informations contained in the schema
    )
    try:
        res = await cruds_todos.create_todo_item(todo_item=db_todo_item, db=db)
        return res
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
