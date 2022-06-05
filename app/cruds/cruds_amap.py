"""File defining the functions called by the endpoints, making queries to the table using the models"""


from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import models_amap
from app.schemas import schemas_amap


async def get_products(db: AsyncSession) -> list[models_amap.Product]:
    """Return all product from database"""

    result = await db.execute(select(models_amap.Product))
    return result.scalars().all()


async def create_product(
    product: schemas_amap.ProductBase, db: AsyncSession
) -> models_amap.Product:
    """Create a new product in database and return it"""

    db_product = models_amap.Product(**product.dict())
    db.add(db_product)
    try:
        await db.commit()
        return db_product
    except IntegrityError:
        await db.rollback()
        raise ValueError("This name is already used")


async def get_product_by_id(
    product_id: str, db: AsyncSession
) -> models_amap.Product | None:
    result = await db.execute(
        select(models_amap.Product).where(models_amap.Product.id == product_id)
    )
    return result.scalars().first()


async def edit_product(
    product_id: str, product_update: schemas_amap.ProductBase, db: AsyncSession
):
    await db.execute(
        update(models_amap.Product)
        .where(models_amap.Product.id == product_id)
        .values(**product_update.dict(exclude_none=True))
    )
    await db.commit()


async def delete_product(db: AsyncSession, product_id: str):
    """Delete a product from database by id"""

    await db.execute(
        delete(models_amap.Product).where(models_amap.Product.id == product_id)
    )
    await db.commit()


async def get_deliveries(db: AsyncSession) -> list[models_amap.Delivery]:
    """Return all deliveries from database"""
    result = await db.execute(
        select(models_amap.Delivery).options(
            selectinload(models_amap.Delivery.products)
        )
    )
    return result.scalars().all()


async def create_delivery(
    delivery: schemas_amap.DeliveryComplete, db: AsyncSession
) -> models_amap.Delivery:
    """Create a new delivery in database and return it"""
    products_ids = delivery.products_ids
    products = []
    for id in products_ids:
        res = await db.execute(
            select(models_amap.Product).where(models_amap.Product.id == id)
        )
        p = res.scalars().first()
        if p is not None:
            products.append(p)
    db_delivery = models_amap.Delivery(
        id=delivery.id, delivery_date=delivery.delivery_date, products=products
    )
    db.add(db_delivery)
    try:
        await db.commit()
        return db_delivery
    except IntegrityError:
        await db.rollback()
        raise ValueError(
            "A Delivery is already planned on that day. Consider editing this one."
        )


async def delete_delivery(db: AsyncSession, delivery_id: str):
    """Delete a delivery from database by id"""

    await db.execute(
        delete(models_amap.Delivery).where(models_amap.Delivery.id == delivery_id)
    )
    await db.commit()


async def get_products_from_delivery(
    db: AsyncSession, delivery_id: str
) -> list[models_amap.Product] | None:
    result = await db.execute(
        select(models_amap.Delivery)
        .where(models_amap.Delivery.id == delivery_id)
        .options(selectinload(models_amap.Delivery.products))
    )
    delivery = result.scalars().first()
    if delivery is not None:
        return delivery.products
    return None


async def add_product_to_delivery(
    db: AsyncSession, link: schemas_amap.AddProductDelivery
):
    """Add a product to a delivery products list"""
    db_add = models_amap.AmapDeliveryContent(**link.dict())
    db.add(db_add)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError("This product is already in this delivery")


async def remove_product_from_delivery(
    db: AsyncSession, product_id: str, delivery_id: str
):
    """Remove a product from a delivery products list"""

    await db.execute(
        delete(models_amap.AmapDeliveryContent).where(
            models_amap.AmapDeliveryContent.product_id == product_id
            and models_amap.AmapDeliveryContent.delivery_id == delivery_id
        )
    )
    await db.commit()


async def get_orders_from_delivery(
    db: AsyncSession, delivery_id: str
) -> list[models_amap.Order]:
    result = await db.execute(
        select(models_amap.Order)
        .where(models_amap.Order.delivery_id == delivery_id)
        .options(selectinload(models_amap.Order.products))
    )
    return result.scalars().all()


async def get_order_by_id(db: AsyncSession, order_id: str) -> models_amap.Order | None:
    result = await db.execute(
        select(models_amap.Order)
        .where(models_amap.Order.order_id == order_id)
        .options(selectinload(models_amap.Order.products))
    )
    return result.scalars().first()


async def add_order_to_delivery(
    db: AsyncSession,
    order: schemas_amap.OrderBase,
) -> models_amap.Order:
    db_add = models_amap.Order(**order.dict())

    db.add(db_add)
    try:
        await db.commit()
        return db_add
    except IntegrityError:
        await db.rollback()
        raise ValueError("This product is already in this delivery")


async def edit_order(db: AsyncSession, order: schemas_amap.OrderComplete):
    await db.execute(
        update(models_amap.Order)
        .where(models_amap.Order.order_id == order.order_id)
        .values(**order.dict(exclude_none=True))
    )
    await db.commit()


async def get_users_cash(db: AsyncSession) -> list[models_amap.Cash]:
    result = await db.execute(select(models_amap.Cash))
    return result.scalars().all()


async def get_cash_by_id(db: AsyncSession, user_id: str) -> models_amap.Cash | None:
    result = await db.execute(
        select(models_amap.Cash).where(models_amap.Cash.user_id == user_id)
    )
    return result.scalars().first()


async def create_cash_of_user(
    db: AsyncSession, cash: schemas_amap.CashBase
) -> models_amap.Cash:
    db_add = models_amap.Cash(**cash.dict(exclude_none=True))
    db.add(db_add)
    try:
        await db.commit()
        return db_add
    except IntegrityError:
        await db.rollback()
        raise ValueError("This user already has a balance")


async def edit_cash_by_id(
    db: AsyncSession, user_id: str, balance: schemas_amap.CashBase
):
    await db.execute(
        update(models_amap.Cash)
        .where(models_amap.Cash.user_id == user_id)
        .values(**balance.dict())
    )
    await db.commit()
