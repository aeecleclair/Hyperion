import uuid
from collections.abc import Sequence
from typing import TYPE_CHECKING, cast

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.todo import models_todo, schemas_todo

if TYPE_CHECKING:
    from sqlalchemy.engine import CursorResult


async def get_todos_by_user_id(
    user_id: str,
    db: AsyncSession,
) -> list[schemas_todo.Todo]:
    result = await db.execute(
        select(models_todo.Todo).where(
            models_todo.Todo.user_id == user_id,
        ),
    )
    return [
        schemas_todo.Todo(
            id=todo.id,
            description=todo.description,
            done=todo.done,
            user_id=todo.user_id,
        )
        for todo in result.scalars().all()
    ]


async def create_todo(
    todo: schemas_todo.Todo,
    db: AsyncSession,
):
    db.add(
        models_todo.Todo(
            id=todo.id,
            description=todo.description,
            done=todo.done,
            user_id=todo.user_id,
        ),
    )


async def update_todo(
    todo_id: uuid.UUID,
    todo: schemas_todo.TodoEdit,
    db: AsyncSession,
):
    await db.execute(
        update(models_todo.Todo)
        .where(models_todo.Todo.id == todo_id)
        .values(**todo.model_dump(exclude_none=True)),
    )


async def delete_todo(
    todo_id: uuid.UUID,
    db: AsyncSession,
):
    await db.execute(
        delete(models_todo.Todo).where(
            models_todo.Todo.id == todo_id,
        ),
    )


async def get_todo_by_id(
    todo_id: uuid.UUID,
    db: AsyncSession,
) -> schemas_todo.Todo | None:
    result = (
        await db.execute(
            select(models_todo.Todo).where(
                models_todo.Todo.id == todo_id,
            ),
        )
    ).scalar_one_or_none()

    return (
        schemas_todo.Todo(
            id=result.id,
            description=result.description,
            done=result.done,
            user_id=result.user_id,
        )
        if result
        else None
    )
