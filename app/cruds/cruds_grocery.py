"""File defining the functions called by the endpoints, making queries to the table using the models"""

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import models_grocery
from app.schemas import schemas_core, schemas_grocery


async def get_products(
    db: AsyncSession,
) -> list[models_grocery.Product]:

    result = await db.execute(select(models_grocery.Product))
    return result.scalars().all()


async def create_product(
    product: models_grocery.Product,
    db: AsyncSession,
) -> None:

    db.add(product)

    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def update_product(
    product_id: str,
    product_update: schemas_grocery.ProductEdit,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_grocery.Product)
        .where(models_grocery.Product.id == product_id)
        .values(**product_update.dict(exclude_none=True))
    )
    await db.commit()


async def delete_product(
    product_id: str,
    db: AsyncSession,
) -> None:

    await db.execute(
        delete(models_grocery.Product).where(models_grocery.Product.id == product_id)
    )
    await db.commit()


async def get_category_by_id(
    category_id: str,
    db: AsyncSession,
) -> models_grocery.Category | None:
    result = await db.execute(
        select(models_grocery.Category).where(models_grocery.Category.id == category_id)
    )
    return result.scalars().first()


async def create_category(
    category: models_grocery.Category,
    db: AsyncSession,
) -> None:

    db.add(category)

    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def update_category(
    category_id: str,
    category_update: schemas_grocery.CategoryUpdate,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_grocery.Category)
        .where(models_grocery.Category.id == category_id)
        .values(**category_update.dict(exclude_none=True))
    )
    await db.commit()


async def delete_category(
    category_id: str,
    db: AsyncSession,
) -> None:

    await db.execute(
        delete(models_grocery.Category).where(models_grocery.Category.id == category_id)
    )
    await db.commit()
