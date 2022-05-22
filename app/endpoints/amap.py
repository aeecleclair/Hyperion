import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_amap
from app.dependencies import get_db
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
        return await cruds_amap.create_delivery(product=db_delivery, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.delete("/amap/delieveries/{delivery_id}", status_code=204, tags=[Tags.amap])
async def delete_delivery(delivery_id: str, db: AsyncSession = Depends(get_db)):
    # TODO check if the client is admin

    await cruds_amap.delete_delivery(db=db, delivery_id=delivery_id)


@router.get(
    "/amap/deliveries/{delivery_id}/products",
    response_model=list[schemas_amap.ProductComplete],
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
    "/amap/deliveries/{delivery_id}/products",
    response_model=list[schemas_amap.ProductComplete],
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
    "/amap/deliveries/{delivery_id}/products/{product_id}",
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
    "/amap/deliveries/{delivery_id}/orders",
    response_model=list[schemas_amap.OrderReturn],
    status_code=200,
    tags=[Tags.amap],
)
async def get_orders_from_delivery(
    delivery_id: str, db: AsyncSession = Depends(get_db)
):
    orders = await cruds_amap.get_orders_from_delivery(delivery_id=delivery_id, db=db)
    return [await get_order_by_id(order.order_id,db) for order in orders]


@router.get(
    "/amap/deliveries/{delivery_id}/orders/{order_id}",
    response_model=schemas_amap.OrderReturn,
    status_code=200,
    tags=[Tags.amap],
)
async def get_order_by_id(order_id: str, db: AsyncSession = Depends(get_db)):
    order = await cruds_amap.get_order_by_id(order_id=order_id, db=db)
    quantities = await cruds_amap.get_quantities_of_order(db=db,order_id=order_id)
    products = []
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    for p in order.products:
        quantity = quantities[p.id]
        products.append(schemas_amap.ProductQuantity(quantity=quantity,id=p.id,category=p.category,name=p.name,price=p.price))
    print(products)
    print(order)
    return schemas_amap.OrderReturn(products=products,user_id=order.user_id,delivery_id=order.delivery_id,collection_slot=order.collection_slot,delivery_date=order.delivery_date,order_id=order.order_id,amount=order.amount,ordering_date=order.ordering_date)


@router.post(
    "/amap/deliveries/{delivery_id}/orders",
    response_model=schemas_amap.OrderReturn,
    status_code=201,
    tags=[Tags.amap],
)
async def add_order_to_delievery(
    order: schemas_amap.OrderBase,
    delivery_id: str,
    db: AsyncSession = Depends(get_db),
):
    locked = await cruds_amap.checkif_delivery_locked(db=db, delivery_id=delivery_id)
    if locked:
        raise HTTPException(status_code=403, detail="Delivery locked")
    else:
        amount = 0.0
        for i in range(len(order.products_ids)):
            prod = await cruds_amap.get_product_by_id(
                product_id=order.products_ids[i], db=db
            )
            if prod is not None:
                amount += prod.price * order.products_quantity[i]
        ordering_date = datetime.now()
        order_id = str(uuid.uuid4())
        db_order = schemas_amap.OrderComplete(
            order_id=order_id,
            amount=amount,
            ordering_date=ordering_date,
            **order.dict(),
        )
        balance = await cruds_amap.get_cash_by_id(db=db, user_id=order.user_id)
        if balance is not None:
            if balance.balance < amount:
                raise HTTPException(status_code=403, detail="Not enough money")
            else:
                try:
                    await cruds_amap.add_order_to_delivery(
                        order=db_order,
                        db=db,
                    )
                    await cruds_amap.edit_cash_by_id(
                        db=db,
                        user_id=order.user_id,
                        balance=schemas_amap.CashBase(balance=balance.balance - amount),
                    )
                    return await get_order_by_id(order_id=db_order.order_id, db=db)
                except ValueError as error:
                    raise HTTPException(status_code=422, detail=str(error))
        else:
            raise HTTPException(status_code=404, detail="No cash found")


@router.patch(
    "/amap/deliveries/{delivery_id}/orders",
    status_code=200,
    tags=[Tags.amap],
)
async def edit_orders_from_delieveries(
    delivery_id: str, order: schemas_amap.OrderEdit, db: AsyncSession = Depends(get_db)
):
    locked = await cruds_amap.checkif_delivery_locked(db=db, delivery_id=delivery_id)
    if locked:
        raise HTTPException(status_code=403, detail="Delivery locked")
    else:
        amount = 0.0
        for i in range(len(order.products_ids)):
            prod = await cruds_amap.get_product_by_id(
                product_id=order.products_ids[i], db=db
            )
            if prod is not None:
                amount += prod.price * order.products_quantity[i]
        ordering_date = datetime.now()
        db_order = schemas_amap.OrderComplete(
            amount=amount, ordering_date=ordering_date, **order.dict()
        )
        previous_order = await cruds_amap.get_order_by_id(
            db=db, order_id=order.order_id
        )
        if previous_order is not None:
            previous_amount = previous_order.amount
            balance = await cruds_amap.get_cash_by_id(db=db, user_id=order.user_id)
            if balance is not None:
                if balance.balance + previous_amount < amount:
                    raise HTTPException(status_code=403, detail="Not enough money")
                else:
                    try:
                        await cruds_amap.edit_order(
                            order=db_order,
                            db=db,
                        )
                        await cruds_amap.edit_cash_by_id(
                            db=db,
                            user_id=order.user_id,
                            balance=schemas_amap.CashBase(
                                balance=balance.balance + previous_amount - amount
                            ),
                        )
                    except ValueError as error:
                        raise HTTPException(status_code=422, detail=str(error))
            else:
                raise HTTPException(status_code=404, detail="No cash found")
        else:
            raise HTTPException(status_code=404, detail="No order found")


@router.delete(
    "/amap/deliveries/{delivery_id}/orders/{order_id}",
    status_code=204,
    tags=[Tags.amap],
)
async def remove_order(
    order_id: str, delivery_id: str, db: AsyncSession = Depends(get_db)
):
    # TODO check if the client is admin or the good user
    locked = await cruds_amap.checkif_delivery_locked(db=db, delivery_id=delivery_id)
    if locked:
        raise HTTPException(status_code=403, detail="Delivery locked")
    else:
        order = await cruds_amap.get_order_by_id(db=db, order_id=order_id)
        if order is not None:
            amount = order.amount
            balance = await cruds_amap.get_cash_by_id(db=db, user_id=order.user_id)
            if balance is not None:
                await cruds_amap.edit_cash_by_id(
                    db=db,
                    user_id=order.user_id,
                    balance=schemas_amap.CashBase(balance=balance.balance + amount),
                )
                await cruds_amap.remove_order(db=db, order_id=order_id)
            else:
                raise HTTPException(status_code=404, detail="No cash found")
        else:
            raise HTTPException(status_code=404, detail="No order found")


@router.get(
    "/amap/users/cash",
    response_model=list[schemas_amap.CashComplete],
    status_code=200,
    tags=[Tags.amap],
)
async def get_users_cash(db: AsyncSession = Depends(get_db)):
    cash = await cruds_amap.get_users_cash(db)
    res = []
    for c in cash:
        user = await read_user(user_id=c.user_id, db=db)
        res.append(schemas_amap.CashComplete(user=user, balance=c.balance))
    return res


@router.get(
    "/amap/users/{user_id}/cash",
    response_model=schemas_amap.CashComplete,
    status_code=200,
    tags=[Tags.amap],
)
async def get_cash_by_id(user_id: str, db: AsyncSession = Depends(get_db)):
    cash = await cruds_amap.get_cash_by_id(user_id=user_id, db=db)
    if cash is not None:
        user = await read_user(user_id=cash.user_id, db=db)
        return schemas_amap.CashComplete(balance=cash.balance, user=user)


@router.post(
    "/amap/users/{user_id}/cash",
    response_model=schemas_amap.CashBase,
    status_code=201,
    tags=[Tags.amap],
)
async def create_cash_of_user(
    user_id: str, balance: schemas_amap.CashBase, db: AsyncSession = Depends(get_db)
):
    # TODO check if the client is admin
    user = await read_user(user_id=user_id, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    result = await cruds_amap.create_cash_of_user(
        cash=schemas_amap.CashDB(user_id=user_id, **balance.dict()),
        db=db,
    )
    return schemas_amap.CashBase(**result.__dict__)


@router.patch(
    "/amap/users/{user_id}/cash",
    status_code=200,
    tags=[Tags.amap],
)
async def edit_cash_by_id(
    user_id: str, balance: schemas_amap.CashBase, db: AsyncSession = Depends(get_db)
):
    # TODO check if the client is admin
    user = await read_user(user_id=user_id, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await cruds_amap.edit_cash_by_id(user_id=user_id, balance=balance, db=db)


@router.get(
    "/amap/users/{user_id}/orders",
    response_model=list[schemas_amap.OrderReturn],
    status_code=200,
    tags=[Tags.amap],
)
async def get_orders_of_user(user_id: str, db: AsyncSession = Depends(get_db)):
    orders = await cruds_amap.get_orders_of_user(user_id=user_id, db=db)
    print(orders)
    res = [await get_order_by_id(order.order_id, db) for order in orders]
    return res
