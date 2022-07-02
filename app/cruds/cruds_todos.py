from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import models_todos


async def get_todo_items_by_user_id(
    db: AsyncSession, user_id: str
) -> list[models_todos.TodosItem]:

    result = await db.execute(
        select(models_todos.TodosItem).where(models_todos.TodosItem.user_id == user_id)
    )
    return result.scalars().all()


async def create_todo_item(
    db: AsyncSession, todo_item: models_todos.TodosItem
) -> models_todos.TodosItem:

    db.add(todo_item)
    try:
        await db.commit()
        return todo_item
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)
