"""File defining the functions called by the endpoints, making queries to the table using the models"""


from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload, selectinload

from app.models import models_amap
from app.schemas import schemas_amap
from app.utils.types.amap_types import DeliveryStatusType


async def get_products(db: AsyncSession) -> list[models_amap.Product]:
    """Return all products from database"""

    result = await db.execute(select(models_amap.Product))
    return result.scalars().all()


async def create_product(
    product: models_amap.Product,
    db: AsyncSession,
) -> models_amap.Product:
    """Create a new product in database and return it"""

    db.add(product)
    try:
        await db.commit()
        return product
    except IntegrityError:
        await db.rollback()
        raise ValueError("This name is already used")


async def get_product_by_id(
    product_id: str,
    db: AsyncSession,
) -> models_amap.Product | None:
    result = await db.execute(
        select(models_amap.Product).where(models_amap.Product.id == product_id)
    )
    return result.scalars().first()


async def edit_product(
    product_id: str,
    product_update: schemas_amap.ProductEdit,
    db: AsyncSession,
):
    await db.execute(
        update(models_amap.Product)
        .where(models_amap.Product.id == product_id)
        .values(**product_update.dict(exclude_none=True))
    )
    await db.commit()


async def is_product_used(
    db: AsyncSession,
    product_id: str,
) -> bool:
    result = await db.execute(
        select(models_amap.AmapDeliveryContent).where(
            models_amap.AmapDeliveryContent.product_id == product_id
        )
    )
    return result.scalars().all() != []


async def is_product_used_in_order(db: AsyncSession, product_id: str) -> bool:
    result = await db.execute(
        select(models_amap.AmapOrderContent).where(
            models_amap.AmapDeliveryContent.product_id == product_id
        )
    )
    return result.scalars().all() != []


async def delete_product(
    db: AsyncSession,
    product_id: str,
):
    """Delete a product from database by id"""

    await db.execute(
        delete(models_amap.Product).where(models_amap.Product.id == product_id)
    )
    await db.commit()


async def get_deliveries(
    db: AsyncSession,
) -> list[models_amap.Delivery]:
    """Return all deliveries from database"""
    result = await db.execute(
        select(models_amap.Delivery).options(
            selectinload(models_amap.Delivery.products),
            selectinload(models_amap.Delivery.orders),
        )
    )
    return result.scalars().all()


async def get_delivery_by_id(
    db: AsyncSession,
    delivery_id: str,
) -> models_amap.Delivery | None:
    result = await db.execute(
        select(models_amap.Delivery)
        .where(models_amap.Delivery.id == delivery_id)
        .options(
            selectinload(models_amap.Delivery.products),
            noload(models_amap.Delivery.orders),
        )
    )
    return result.scalars().first()


async def create_delivery(
    delivery: schemas_amap.DeliveryComplete,
    db: AsyncSession,
) -> models_amap.Delivery | None:
    """Create a new delivery in database and return it"""
    db.add(models_amap.Delivery(**delivery.dict(exclude={"products_ids"})))
    for id in delivery.products_ids:
        db.add(models_amap.AmapDeliveryContent(product_id=id, delivery_id=delivery.id))
    try:
        await db.commit()
        return await get_delivery_by_id(db=db, delivery_id=delivery.id)
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


async def add_product_to_delivery(
    db: AsyncSession,
    products_ids: schemas_amap.DeliveryProductsUpdate,
    delivery_id: str,
):
    """Add a product to a delivery products list"""
    for id in products_ids.products_ids:
        db.add(models_amap.AmapDeliveryContent(product_id=id, delivery_id=delivery_id))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError("This product is already in this delivery")


async def remove_product_from_delivery(
    db: AsyncSession,
    products_ids: schemas_amap.DeliveryProductsUpdate,
    delivery_id: str,
):
    """Remove a product from a delivery products list"""
    for id in products_ids.products_ids:
        await db.execute(
            delete(models_amap.AmapDeliveryContent).where(
                models_amap.AmapDeliveryContent.product_id == id
                and models_amap.AmapDeliveryContent.delivery_id == delivery_id
            )
        )

    await db.commit()


async def edit_delivery(
    db: AsyncSession, delivery_id: str, delivery: schemas_amap.DeliveryUpdate
):
    await db.execute(
        update(models_amap.Delivery)
        .where(models_amap.Delivery.id == delivery_id)
        .values(**delivery.dict(exclude_none=True))
    )
    await db.commit()


async def get_order_by_id(db: AsyncSession, order_id: str) -> models_amap.Order | None:
    result = await db.execute(
        select(models_amap.Order)
        .where(models_amap.Order.order_id == order_id)
        .options(
            selectinload(models_amap.Order.user),
            noload(models_amap.Order.products),
        )
    )
    return result.scalars().first()


async def get_orders_from_delivery(
    db: AsyncSession, delivery_id: str
) -> list[models_amap.Order]:
    result = await db.execute(
        select(models_amap.Order)
        .where(models_amap.Order.delivery_id == delivery_id)
        .options(
            noload(models_amap.Order.products), selectinload(models_amap.Order.user)
        )
    )
    return result.scalars().all()


async def get_products_of_order(
    db: AsyncSession, order_id: str
) -> list[models_amap.AmapOrderContent]:
    result_db = await db.execute(
        select(models_amap.AmapOrderContent)
        .where(models_amap.AmapOrderContent.order_id == order_id)
        .options(selectinload(models_amap.AmapOrderContent.product))
    )
    return result_db.scalars().all()


async def add_order_to_delivery(
    db: AsyncSession,
    order: schemas_amap.OrderComplete,
):
    db.add(
        models_amap.Order(**order.dict(exclude={"products_ids", "products_quantity"}))
    )
    try:
        await db.commit()
        for i in range(len(order.products_ids)):
            db.add(
                models_amap.AmapOrderContent(
                    order_id=order.order_id,
                    product_id=order.products_ids[i],
                    quantity=order.products_quantity[i],
                )
            )
            await db.commit()
    except IntegrityError as err:
        await db.rollback()
        raise ValueError(err)


async def edit_order(db: AsyncSession, order: schemas_amap.OrderComplete):
    await db.execute(
        delete(models_amap.AmapOrderContent).where(
            models_amap.AmapOrderContent.order_id == order.order_id
        )
    )
    await db.commit()
    for i in range(len(order.products_ids)):
        db.add(
            models_amap.AmapOrderContent(
                order_id=order.order_id,
                product_id=order.products_ids[i],
                quantity=order.products_quantity[i],
            )
        )
        await db.commit()
    await db.execute(
        update(models_amap.Order)
        .where(models_amap.Order.order_id == order.order_id)
        .values(
            user_id=order.user_id,
            delivery_id=order.delivery_id,
            order_id=order.order_id,
            amount=order.amount,
            collection_slot=order.collection_slot,
            ordering_date=order.ordering_date,
        )
    )
    await db.commit()


async def remove_order(db: AsyncSession, order_id: str):
    await db.execute(
        delete(models_amap.Order).where(models_amap.Order.order_id == order_id)
    )
    await db.commit()


async def get_users_cash(db: AsyncSession) -> list[models_amap.Cash]:
    result = await db.execute(
        select(models_amap.Cash).options(selectinload(models_amap.Cash.user))
    )
    return result.scalars().all()


async def get_cash_by_id(db: AsyncSession, user_id: str) -> models_amap.Cash | None:
    result = await db.execute(
        select(models_amap.Cash)
        .where(models_amap.Cash.user_id == user_id)
        .options(selectinload(models_amap.Cash.user))
    )
    return result.scalars().first()


async def create_cash_of_user(
    db: AsyncSession, cash: models_amap.Cash
) -> models_amap.Cash:
    db.add(cash)
    try:
        await db.commit()
        return cash
    except IntegrityError as err:
        await db.rollback()
        raise ValueError(err)


async def edit_cash_by_id(
    db: AsyncSession, user_id: str, balance: schemas_amap.CashEdit
):
    await db.execute(
        update(models_amap.Cash)
        .where(models_amap.Cash.user_id == user_id)
        .values(**balance.dict())
    )
    await db.commit()


async def get_orders_of_user(db: AsyncSession, user_id: str) -> list[models_amap.Order]:
    result = await db.execute(
        select(models_amap.Order)
        .where(models_amap.Order.user_id == user_id)
        .options(selectinload(models_amap.Order.products))
    )
    return result.scalars().all()


async def open_ordering_of_delivery(db: AsyncSession, delivery_id: str):
    await db.execute(
        update(models_amap.Delivery)
        .where(models_amap.Delivery.id == delivery_id)
        .values(status=DeliveryStatusType.orderable)
    )
    await db.commit()


async def lock_delivery(db: AsyncSession, delivery_id: str):
    await db.execute(
        update(models_amap.Delivery)
        .where(models_amap.Delivery.id == delivery_id)
        .values(status=DeliveryStatusType.locked)
    )
    await db.commit()


async def mark_delivery_as_delivered(db: AsyncSession, delivery_id: str):
    await db.execute(
        update(models_amap.Delivery)
        .where(models_amap.Delivery.id == delivery_id)
        .values(status=DeliveryStatusType.delivered)
    )
    await db.commit()
