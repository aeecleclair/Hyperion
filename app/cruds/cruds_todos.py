from typing import Sequence

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import models_todos


async def get_items_by_user_id(
    db: AsyncSession,
    user_id: str,
) -> Sequence[models_todos.TodosItem]:
    """
    Return all items from a given user
    """

    result = await db.execute(
        select(models_todos.TodosItem).where(
            models_todos.TodosItem.user_id == user_id,
        )
    )
    return result.scalars().all()


async def get_item_by_id(
    db: AsyncSession,
    id: str,
) -> models_todos.TodosItem | None:
    """
    Return an item by its id
    """

    result = await db.execute(
        select(models_todos.TodosItem).where(
            models_todos.TodosItem.id == id,
        )
    )
    return result.scalars().first()


async def create_item(
    db: AsyncSession,
    item: models_todos.TodosItem,
) -> models_todos.TodosItem:
    """
    Create a new item
    """

    db.add(item)
    try:
        await db.commit()
        return item
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def edit_done_status(
    db: AsyncSession,
    id: str,
    done: bool,
) -> None:
    """
    Mark an item as done or not done
    """

    await db.execute(
        update(models_todos.TodosItem)
        .where(models_todos.TodosItem.id == id)
        .values(done=done)
    )
    await db.commit()
