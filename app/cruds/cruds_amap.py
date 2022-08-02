"""File defining the functions called by the endpoints, making queries to the table using the models"""


from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.cruds import cruds_users
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


async def get_delivery_by_id(
    db: AsyncSession, delivery_id: str
) -> models_amap.Delivery | None:
    result = await db.execute(
        select(models_amap.Delivery)
        .where(models_amap.Delivery.id == delivery_id)
        .options(selectinload(models_amap.Delivery.products))
    )
    return result.scalars().first()


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
        id=delivery.id,
        delivery_date=delivery.delivery_date,
        products=products,
        locked=delivery.locked,
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


async def get_quantities_of_order(db: AsyncSession, order_id: str) -> dict:
    result_db = await db.execute(
        select(models_amap.AmapOrderContent).where(
            models_amap.AmapOrderContent.order_id == order_id
        )
    )
    result = result_db.scalars().all()
    result_treated = {}
    for i in range(len(result)):
        result_treated[result[i].product_id] = result[i].quantity
    return result_treated


async def checkif_delivery_locked(db: AsyncSession, delivery_id: str) -> bool:
    delivery = await get_delivery_by_id(db=db, delivery_id=delivery_id)
    if delivery is not None:
        return delivery.locked
    else:
        return True


async def add_order_to_delivery(
    db: AsyncSession,
    order: schemas_amap.OrderComplete,
):
    delivery = await get_delivery_by_id(db=db, delivery_id=order.delivery_id)
    user = await cruds_users.get_user_by_id(db=db, user_id=order.user_id)
    products = []
    for p in order.products_ids:
        product = await get_product_by_id(db=db, product_id=p)
        if product is not None:
            products.append(product)
    if delivery is not None and user is not None:
        db_add = models_amap.Order(
            delivery=delivery,
            user=user,
            products=products,
            user_id=order.user_id,
            delivery_id=order.delivery_id,
            order_id=order.order_id,
            amount=order.amount,
            collection_slot=order.collection_slot,
            ordering_date=order.ordering_date,
            delivery_date=order.delivery_date,
        )

        db.add(db_add)
        try:
            await db.commit()
            for i in range(len(order.products_ids)):
                await db.execute(
                    update(models_amap.AmapOrderContent)
                    .where(
                        models_amap.AmapOrderContent.order_id == order.order_id,
                        models_amap.AmapOrderContent.product_id
                        == order.products_ids[i],
                    )
                    .values(quantity=order.products_quantity[i])
                )
                await db.commit()
        except IntegrityError:
            await db.rollback()
            raise ValueError("This product is already in this delivery")
    else:
        raise ValueError("Delivery or user not found.")


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
            delivery_date=order.delivery_date,
        )
    )
    await db.commit()


async def remove_order(db: AsyncSession, order_id: str):
    await db.execute(
        delete(models_amap.Order).where(models_amap.Order.order_id == order_id)
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
    db: AsyncSession, cash: schemas_amap.CashDB
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


async def get_orders_of_user(db: AsyncSession, user_id: str) -> list[models_amap.Order]:
    result = await db.execute(
        select(models_amap.Order)
        .where(models_amap.Order.user_id == user_id)
        .options(selectinload(models_amap.Order.products))
    )
    return result.scalars().all()
