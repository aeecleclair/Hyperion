from typing import Sequence

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import models_todos


async def get_items_by_user_id(
    db: AsyncSession,
    user_id: str,
) -> Sequence[models_todos.TodosItem]:
    # On récupère tous les éléments TodosItem
    # dont le user_id correspond à celui que l'on recherche
    result = await db.execute(
        select(models_todos.TodosItem).where(
            models_todos.TodosItem.user_id == user_id,
        )
    )
    return result.scalars().all()


async def create_item(
    db: AsyncSession,
    item: models_todos.TodosItem,
) -> models_todos.TodosItem:
    # Avec `db.add(item)` l'élément est placé tout seul dans la bonne table de la bdd.
    # todo_item est en effet une instance du model : models_todos.TodosItem
    db.add(item)
    try:
        await db.commit()
        return item
    except IntegrityError as error:
        # En cas d'erreur d'ajout de l'objet, on revient en arrière (rollback de la db)
        # pour annuler les modifications de la db et on lève une erreur.
        await db.rollback()
        raise ValueError(error)


async def edit_done_status(
    db: AsyncSession,
    id: str,
    done: bool,
) -> None:
    # On met à jour le champ `done` de l'élément TodosItem

    await db.execute(
        update(models_todos.TodosItem)
        .where(models_todos.TodosItem.id == id)
        .values(done=done)
    )
    await db.commit()
