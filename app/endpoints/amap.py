import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_amap
from app.dependencies import get_db
from app.endpoints.users import read_user
from app.schemas import schemas_amap
from app.utils.types.tags import Tags

router = APIRouter()


# Prefix "/amap" added in api.py
@router.get(
    "/amap/products",
    response_model=list[schemas_amap.ProductBase],
    status_code=200,
    tags=[Tags.amap],
)
async def get_products(db: AsyncSession = Depends(get_db)):
    """Return all AMAP products from database as a list of dictionaries"""
    products = await cruds_amap.get_products(db)
    return products


@router.post(
    "/amap/products",
    response_model=schemas_amap.ProductBase,
    status_code=201,
    tags=[Tags.amap],
)
async def create_product(
    product: schemas_amap.ProductCreate,
    db: AsyncSession = Depends(get_db),
):
    # TODO check if the client is admin
    db_product = schemas_amap.ProductBase(id=str(uuid.uuid4()), **product.dict())
    try:
        return await cruds_amap.create_product(product=db_product, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.get(
    "/amap/products/{product_id}",
    response_model=schemas_amap.ProductBase,
    status_code=200,
    tags=[Tags.amap],
)
async def get_product_by_id(product_id: str, db: AsyncSession = Depends(get_db)):
    product = await cruds_amap.get_product_by_id(product_id=product_id, db=db)
    return product


@router.put(
    "/amap/products/{product_id}",
    response_model=schemas_amap.ProductBase,
    tags=[Tags.amap],
)
async def edit_product(
    product_id: str,
    product_update: schemas_amap.ProductEdit,
    db: AsyncSession = Depends(get_db),
):
    # TODO check if the client is admin
    product = await cruds_amap.get_product_by_id(db=db, product_id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    await cruds_amap.edit_product(
        db=db, product_id=product_id, product_update=product_update
    )

    return product


@router.delete("/amap/products/{product_id}", status_code=204, tags=[Tags.amap])
async def delete_product(product_id: str, db: AsyncSession = Depends(get_db)):
    # TODO check if the client is admin

    await cruds_amap.delete_product(db=db, product_id=product_id)


@router.get(
    "/amap/deliveries",
    response_model=list[schemas_amap.DeliveryBase],
    status_code=200,
    tags=[Tags.amap],
)
async def get_delieveries(db: AsyncSession = Depends(get_db)):
    """Return all AMAP planned deliveries from database as a list of dictionaries"""
    deliveries = await cruds_amap.get_deliveries(db)
    return deliveries


@router.post(
    "/amap/deliveries",
    response_model=schemas_amap.DeliveryBase,
    status_code=201,
    tags=[Tags.amap],
)
async def create_delivery(
    delivery: schemas_amap.DeliveryCreate,
    db: AsyncSession = Depends(get_db),
):
    # TODO check if the client is admin
    db_delivery = schemas_amap.DeliveryBase(id=str(uuid.uuid4()), **delivery.dict())
    try:
        return await cruds_amap.create_delivery(delivery=db_delivery, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.delete("/amap/delieveries/{delivery_id}", status_code=204, tags=[Tags.amap])
async def delete_delivery(delivery_id: str, db: AsyncSession = Depends(get_db)):
    # TODO check if the client is admin

    await cruds_amap.delete_delivery(db=db, delivery_id=delivery_id)


@router.get(
    "/amap/delieveries/{delivery_id}/products",
    response_model=list[schemas_amap.ProductBase],
    status_code=200,
    tags=[Tags.amap],
)
async def get_products_from_delivery(
    delivery_id: str, db: AsyncSession = Depends(get_db)
):
    products = await cruds_amap.get_products_from_delivery(
        delivery_id=delivery_id, db=db
    )
    return products


@router.post(
    "/amap/delieveries/{delivery_id}/products",
    response_model=list[schemas_amap.ProductBase],
    status_code=201,
    tags=[Tags.amap],
)
async def add_product_to_delievery(
    product_id: str, delivery_id: str, db: AsyncSession = Depends(get_db)
):
    # TODO check if the client is admin
    product = await cruds_amap.get_product_by_id(db=db, product_id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    else:
        try:
            await cruds_amap.add_product_to_delivery(
                link=schemas_amap.AddProductDelivery(
                    product_id=product_id, delivery_id=delivery_id
                ),
                db=db,
            )
            return get_products_from_delivery(db=db, delivery_id=delivery_id)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error))


@router.delete(
    "/amap/delieveries/{delivery_id}/products/{product_id}",
    status_code=204,
    tags=[Tags.amap],
)
async def remove_product_from_delievery(
    delivery_id: str, product_id: str, db: AsyncSession = Depends(get_db)
):
    # TODO check if the client is admin
    await cruds_amap.remove_product_from_delivery(
        db=db, delivery_id=delivery_id, product_id=product_id
    )


@router.get(
    "/amap/delieveries/{delivery_id}/orders",
    response_model=list[schemas_amap.OrderBase],
    status_code=200,
    tags=[Tags.amap],
)
async def get_orders_from_delivery(
    delivery_id: str, db: AsyncSession = Depends(get_db)
):
    orders = await cruds_amap.get_orders_from_delivery(delivery_id=delivery_id, db=db)
    return orders


@router.get(
    "/amap/delieveries/{delivery_id}/orders/{order_id}",
    response_model=schemas_amap.OrderBase,
    status_code=200,
    tags=[Tags.amap],
)
async def get_order_by_id(order_id: str, db: AsyncSession = Depends(get_db)):
    order = await cruds_amap.get_order_by_id(order_id=order_id, db=db)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post(
    "/amap/delieveries/{delivery_id}/orders",
    response_model=schemas_amap.OrderBase,
    status_code=201,
    tags=[Tags.amap],
)
async def add_order_to_delievery(
    order: schemas_amap.OrderCreate,
    db: AsyncSession = Depends(get_db),
):

    amount = sum([p.price for p in order.products])
    ordering_date = datetime.now()
    order_id = str(uuid.uuid4())
    db_order = schemas_amap.OrderBase(
        id=order_id, amount=amount, ordering_date=ordering_date, **order.dict()
    )
    try:
        await cruds_amap.add_order_to_delivery(
            order=db_order,
            db=db,
        )

        return get_order_by_id(db=db, order_id=order_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.put(
    "/amap/delieveries/{delivery_id}/orders",
    response_model=schemas_amap.OrderBase,
    status_code=200,
    tags=[Tags.amap],
)
async def edit_orders_from_delieveries(
    delivery_id: str, order: schemas_amap.OrderEdit, db: AsyncSession = Depends(get_db)
):
    amount = sum([p.price for p in order.products])
    ordering_date = datetime.now()
    db_order = schemas_amap.OrderBase(
        amount=amount, ordering_date=ordering_date, **order.dict()
    )
    try:
        await cruds_amap.edit_order(
            order=db_order,
            db=db,
        )

        return order
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.get(
    "/amap/users/cash",
    response_model=list[schemas_amap.CashBase],
    status_code=200,
    tags=[Tags.amap],
)
async def get_users_cash(db: AsyncSession = Depends(get_db)):
    cash = await cruds_amap.get_users_cash(db)
    return cash


@router.get(
    "/amap/users/{user_id}/cash",
    response_model=schemas_amap.CashBase,
    status_code=201,
    tags=[Tags.amap],
)
async def get_cash_by_id(user_id: str, db: AsyncSession = Depends(get_db)):
    cash = await cruds_amap.get_cash_by_id(user_id=user_id, db=db)
    return cash


@router.post(
    "/amap/users/{user_id}/cash",
    response_model=schemas_amap.CashBase,
    status_code=201,
    tags=[Tags.amap],
)
async def create_cash_of_user(
    user_id: str, balance: float, db: AsyncSession = Depends(get_db)
):
    # TODO check if the client is admin
    user = await read_user(user_id=user_id, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return await cruds_amap.create_cash_of_user(
        cash=schemas_amap.CashBase(user=user, user_id=user_id, balance=balance), db=db
    )


@router.put(
    "/amap/users/{user_id}/cash",
    status_code=200,
    tags=[Tags.amap],
)
async def edit_cash_by_id(
    user_id: str, balance: float, db: AsyncSession = Depends(get_db)
):
    # TODO check if the client is admin
    user = await read_user(user_id=user_id, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await cruds_amap.edit_cash_by_id(
        user_id=user_id, balance=schemas_amap.CashUpdate(balance=balance), db=db
    )
