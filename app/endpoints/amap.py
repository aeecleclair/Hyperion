import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_amap, cruds_users
from app.dependencies import get_db, is_user_a_member, is_user_a_member_of
from app.endpoints.users import read_user
from app.models import models_amap, models_core
from app.schemas import schemas_amap
from app.utils.tools import is_user_member_of_an_allowed_group
from app.utils.types.amap_types import DeliveryStatusType
from app.utils.types.groups_type import GroupType
from app.utils.types.tags import Tags

router = APIRouter()


@router.get(
    "/amap/products",
    response_model=list[schemas_amap.ProductComplete],
    status_code=200,
    tags=[Tags.amap],
)
async def get_products(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.amap)),
):
    """
    Return all products

    **The user must be a member of the group AMAP to use this endpoint**
    """
    products = await cruds_amap.get_products(db)
    return products


@router.post(
    "/amap/products",
    response_model=schemas_amap.ProductComplete,
    status_code=201,
    tags=[Tags.amap],
)
async def create_product(
    product: schemas_amap.ProductSimple,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.amap)),
):
    """
    Create a new product

    **The user must be a member of the group AMAP to use this endpoint**
    """
    db_product = models_amap.Product(id=str(uuid.uuid4()), **product.dict())

    try:
        result = await cruds_amap.create_product(product=db_product, db=db)
        return result
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.get(
    "/amap/products/{product_id}",
    response_model=schemas_amap.ProductComplete,
    status_code=200,
    tags=[Tags.amap],
)
async def get_product_by_id(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get a specific product
    """
    product = await cruds_amap.get_product_by_id(product_id=product_id, db=db)

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    return product


@router.patch(
    "/amap/products/{product_id}",
    status_code=204,
    tags=[Tags.amap],
)
async def edit_product(
    product_id: str,
    product_update: schemas_amap.ProductEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.amap)),
):
    """
    Edit a product

    **The user must be a member of the group AMAP to use this endpoint**
    """

    product = await cruds_amap.get_product_by_id(db=db, product_id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    await cruds_amap.edit_product(
        db=db, product_id=product_id, product_update=product_update
    )


@router.delete(
    "/amap/products/{product_id}",
    status_code=204,
    tags=[Tags.amap],
)
async def delete_product(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.amap)),
):
    """
    Delete a product. A product can not be deleted if it is already used in a delivery.

    **The user must be a member of the group AMAP to use this endpoint**
    """

    product = await cruds_amap.get_product_by_id(db=db, product_id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if await cruds_amap.is_product_used(db=db, product_id=product_id):
        raise HTTPException(
            status_code=403, detail="This product is used in a delivery"
        )

    await cruds_amap.delete_product(db=db, product_id=product_id)


@router.get(
    "/amap/deliveries",
    response_model=list[schemas_amap.DeliveryReturn],
    status_code=200,
    tags=[Tags.amap],
)
async def get_deliveries(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get all deliveries.
    """
    return await cruds_amap.get_deliveries(db)


@router.post(
    "/amap/deliveries",
    response_model=schemas_amap.DeliveryReturn,
    status_code=201,
    tags=[Tags.amap],
)
async def create_delivery(
    delivery: schemas_amap.DeliveryBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.amap)),
):
    """
    Create a new delivery.

    **The user must be a member of the group AMAP to use this endpoint**
    """

    db_delivery = schemas_amap.DeliveryComplete(
        id=str(uuid.uuid4()),
        status=DeliveryStatusType.creation,
        **delivery.dict(),
    )
    try:
        result = await cruds_amap.create_delivery(delivery=db_delivery, db=db)
        return result
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.delete(
    "/amap/deliveries/{delivery_id}",
    status_code=204,
    tags=[Tags.amap],
)
async def delete_delivery(
    delivery_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.amap)),
):
    """
    Delete a delivery.

    **The user must be a member of the group AMAP to use this endpoint**
    """

    delivery_db = await cruds_amap.get_delivery_by_id(db=db, delivery_id=delivery_id)
    if delivery_db is not None:
        if delivery_db.status == DeliveryStatusType.creation:
            await cruds_amap.delete_delivery(db=db, delivery_id=delivery_id)
        else:
            raise HTTPException(
                status_code=403,
                detail=f"You can't remove a product if the delivery is not in creation mode. The current mode is {delivery_db.status}.",
            )
    else:
        raise HTTPException(status_code=404, detail="Delivery not found.")


@router.patch(
    "/amap/deliveries/{delivery_id}",
    status_code=204,
    tags=[Tags.amap],
)
async def edit_delivery(
    delivery_id: str,
    delivery: schemas_amap.DeliveryUpdate,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.amap)),
):
    """
    Edit a delivery.

    **The user must be a member of the group AMAP to use this endpoint**
    """

    delivery_db = await cruds_amap.get_delivery_by_id(db=db, delivery_id=delivery_id)
    if delivery_db is not None:
        if delivery_db.status == DeliveryStatusType.creation:
            await cruds_amap.edit_delivery(
                db=db, delivery_id=delivery_id, delivery=delivery
            )
        else:
            raise HTTPException(
                status_code=403,
                detail=f"You can't edit a delivery if the delivery is not in creation mode. The current mode is {delivery_db.status}.",
            )
    else:
        raise HTTPException(status_code=404, detail="Delivery not found.")


@router.post(
    "/amap/deliveries/{delivery_id}/products",
    status_code=201,
    tags=[Tags.amap],
)
async def add_product_to_delivery(
    products_ids: schemas_amap.DeliveryProductsUpdate,
    delivery_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.amap)),
):
    """
    Add `product_id` product to `delivery_id` delivery. This endpoint will only add a membership between the two objects.

    **The user must be a member of the group AMAP to use this endpoint**
    """
    delivery = await cruds_amap.get_delivery_by_id(db=db, delivery_id=delivery_id)
    if delivery is not None:
        if delivery.status == DeliveryStatusType.creation:
            try:
                await cruds_amap.add_product_to_delivery(
                    delivery_id=delivery_id,
                    products_ids=products_ids,
                    db=db,
                )

            except ValueError as error:
                raise HTTPException(status_code=400, detail=str(error))
        else:
            raise HTTPException(
                status_code=403,
                detail=f"You can't add a product if the delivery is not in creation mode. The current mode is {delivery.status}.",
            )
    else:
        raise HTTPException(status_code=404, detail="Delivery not found.")


@router.delete(
    "/amap/deliveries/{delivery_id}/products",
    status_code=204,
    tags=[Tags.amap],
)
async def remove_product_from_delivery(
    delivery_id: str,
    products_ids: schemas_amap.DeliveryProductsUpdate,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.amap)),
):
    """
    Remove a given product from a delivery. This won't delete the product nor the delivery.

    **The user must be a member of the group AMAP to use this endpoint**
    """
    delivery = await cruds_amap.get_delivery_by_id(db=db, delivery_id=delivery_id)
    if delivery is not None:
        if delivery.status == DeliveryStatusType.creation:
            await cruds_amap.remove_product_from_delivery(
                db=db, delivery_id=delivery_id, products_ids=products_ids
            )
        else:
            raise HTTPException(
                status_code=403,
                detail=f"You can't remove a product if the delivery is not in creation mode. The current mode is {delivery.status}.",
            )
    else:
        raise HTTPException(status_code=404, detail="Delivery not found.")


@router.get(
    "/amap/deliveries/{delivery_id}/orders",
    response_model=list[schemas_amap.OrderReturn],
    status_code=200,
    tags=[Tags.amap],
)
async def get_orders_from_delivery(
    delivery_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.amap)),
):
    """
    Get orders from a delivery.

    **The user must be a member of the group AMAP to use this endpoint**
    """
    orders = await cruds_amap.get_orders_from_delivery(db=db, delivery_id=delivery_id)
    res = []
    for order in orders:
        products = await cruds_amap.get_products_of_order(
            db=db, order_id=order.order_id
        )
        res.append(schemas_amap.OrderReturn(productsdetail=products, **order.__dict__))
    return res


@router.get(
    "/amap/deliveries/{delivery_id}/orders/{order_id}",
    response_model=schemas_amap.OrderReturn,
    status_code=200,
    tags=[Tags.amap],
)
async def get_order_by_id(
    delivery_id: str,
    order_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.amap)),
):
    """
    Get content of an order.

    **The user must be a member of the group AMAP to use this endpoint**
    """

    order = await cruds_amap.get_order_by_id(order_id=order_id, db=db)
    if order is None:
        raise HTTPException(status_code=404, detail="Delivery not found")
    if delivery_id != order.delivery_id:
        raise HTTPException(
            status_code=404, detail="The order does not belong to this delivery"
        )

    products = await cruds_amap.get_products_of_order(db=db, order_id=order_id)
    return schemas_amap.OrderReturn(productsdetail=products, **order.__dict__)


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
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get orders from a delivery.

    **The user must be a member of the group AMAP to use this endpoint**
    """
    delivery = await cruds_amap.get_delivery_by_id(db=db, delivery_id=delivery_id)
    if delivery is not None:
        if delivery.status == DeliveryStatusType.orderable:
            if user.id == order.user_id or is_user_member_of_an_allowed_group(
                user, [GroupType.amap]
            ):
                # Price calculation
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
                balance: models_amap.Cash | None = await cruds_amap.get_cash_by_id(
                    db=db,
                    user_id=order.user_id,
                )
                # If the balance does not exist, we create a new one with a balance of 0
                if balance is None:
                    new_cash_db = schemas_amap.CashDB(
                        balance=0,
                        user_id=order.user_id,
                    )
                    # And we use it for the rest of the function
                    balance = models_amap.Cash(
                        **new_cash_db.dict(),
                    )
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
                            balance=schemas_amap.CashEdit(
                                balance=balance.balance - amount
                            ),
                        )
                        orderret = await cruds_amap.get_order_by_id(
                            order_id=db_order.order_id, db=db
                        )
                        productsret = await cruds_amap.get_products_of_order(
                            db=db, order_id=order_id
                        )
                        return schemas_amap.OrderReturn(
                            productsdetail=productsret, **orderret.__dict__
                        )
                    except ValueError as error:
                        raise HTTPException(status_code=422, detail=str(error))
        else:
            raise HTTPException(
                status_code=403,
                detail=f"You can't order if the delivery is not in orderable mode. The current mode is {delivery.status}.",
            )
    else:
        raise HTTPException(status_code=404, detail="Delivery not found.")


@router.patch(
    "/amap/deliveries/{delivery_id}/orders/{order_id}",
    status_code=204,
    tags=[Tags.amap],
)
async def edit_order_from_delievery(
    order_id: str,
    delivery_id: str,
    order: schemas_amap.OrderEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Edit an order.

    **The user must be a member of the group AMAP to use this endpoint**
    """

    delivery = await cruds_amap.get_delivery_by_id(db=db, delivery_id=delivery_id)
    if delivery is not None:
        if delivery.status == DeliveryStatusType.orderable:
            previous_order = await cruds_amap.get_order_by_id(db=db, order_id=order_id)
            if previous_order is not None:
                if (
                    user.id == previous_order.user_id
                    or is_user_member_of_an_allowed_group(user, [GroupType.amap])
                ):
                    if order.products_ids is not None:  # Products edition
                        if order.products_quantity is not None:
                            if len(order.products_quantity) == len(order.products_ids):
                                amount = 0.0
                                for i in range(len(order.products_ids)):
                                    prod = await cruds_amap.get_product_by_id(
                                        product_id=order.products_ids[i], db=db
                                    )
                                    if prod is not None:
                                        amount += (
                                            prod.price * order.products_quantity[i]
                                        )
                                ordering_date = datetime.now()
                                db_order = schemas_amap.OrderComplete(
                                    amount=amount,
                                    ordering_date=ordering_date,
                                    **order.dict(),
                                )
                                previous_amount = previous_order.amount
                                balance = await cruds_amap.get_cash_by_id(
                                    db=db, user_id=previous_order.user_id
                                )
                                if balance is not None:
                                    if balance.balance + previous_amount < amount:
                                        raise HTTPException(
                                            status_code=403, detail="Not enough money"
                                        )
                                    else:
                                        try:
                                            await cruds_amap.edit_order(
                                                order=db_order,
                                                db=db,
                                            )
                                            await cruds_amap.edit_cash_by_id(
                                                db=db,
                                                user_id=previous_order.user_id,
                                                balance=schemas_amap.CashEdit(
                                                    balance=balance.balance
                                                    + previous_amount
                                                    - amount
                                                ),
                                            )
                                        except ValueError as error:
                                            raise HTTPException(
                                                status_code=422, detail=str(error)
                                            )
                                else:
                                    raise HTTPException(
                                        status_code=404, detail="No cash found"
                                    )
                            else:
                                raise HTTPException(
                                    status_code=400,
                                    detail="Error in products and quantities list",
                                )
                    else:
                        await cruds_amap.edit_order(
                            order=db_order,
                            db=db,
                        )

                else:
                    raise HTTPException(status_code=403)
            else:
                raise HTTPException(status_code=404, detail="Order not found")
        else:
            raise HTTPException(
                status_code=403,
                detail=f"You can't edit an order if the delivery is not in orderable mode. The current mode is {delivery.status}.",
            )
    else:
        raise HTTPException(status_code=404, detail="Delivery not found.")


@router.delete(
    "/amap/deliveries/{delivery_id}/orders/{order_id}",
    status_code=204,
    tags=[Tags.amap],
)
async def remove_order(
    order_id: str,
    delivery_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Delete an order.

    **The user must be a member of the group AMAP to use this endpoint**
    """
    delivery = await cruds_amap.get_delivery_by_id(db=db, delivery_id=delivery_id)
    if delivery is not None:
        if delivery.status == DeliveryStatusType.orderable:
            order = await cruds_amap.get_order_by_id(db=db, order_id=order_id)
            if order is None:
                raise HTTPException(status_code=404, detail="No order found")
            if order.delivery_id != delivery_id:
                raise HTTPException(
                    status_code=404, detail="The order is not in this delivery"
                )

            if user.id == order.user_id or is_user_member_of_an_allowed_group(
                user, [GroupType.amap]
            ):
                amount = order.amount
                balance = await cruds_amap.get_cash_by_id(db=db, user_id=order.user_id)
                if balance is not None:
                    await cruds_amap.edit_cash_by_id(
                        db=db,
                        user_id=order.user_id,
                        balance=schemas_amap.CashEdit(balance=balance.balance + amount),
                    )
                    await cruds_amap.remove_order(db=db, order_id=order_id)
                else:
                    raise HTTPException(status_code=404, detail="No cash found")
                return Response(status_code=204)
            else:
                raise HTTPException(status_code=403)
        else:
            raise HTTPException(
                status_code=403,
                detail=f"You can't remove an order if the delivery is not in orderable mode. The current mode is {delivery.status}.",
            )
    else:
        raise HTTPException(status_code=404, detail="Delivery not found.")


@router.post(
    "/amap/deliveries/{delivery_id}/openordering", status_code=204, tags=[Tags.amap]
)
async def open_ordering_of_delivery(
    delivery_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.amap)),
):
    delivery = await cruds_amap.get_delivery_by_id(db=db, delivery_id=delivery_id)
    if delivery is not None:
        if delivery.status == DeliveryStatusType.creation:
            await cruds_amap.open_ordering_of_delivery(delivery_id=delivery_id, db=db)
        else:
            raise HTTPException(
                status_code=403,
                detail=f"You can't open ordering for a delivery if it is not in creation mode. The current mode is {delivery.status}.",
            )
    else:
        raise HTTPException(status_code=404, detail="Delivery not found.")


@router.post("/amap/deliveries/{delivery_id}/lock", status_code=204, tags=[Tags.amap])
async def lock_delivery(
    delivery_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.amap)),
):
    delivery = await cruds_amap.get_delivery_by_id(db=db, delivery_id=delivery_id)
    if delivery is not None:
        if delivery.status == DeliveryStatusType.orderable:
            await cruds_amap.lock_delivery(delivery_id=delivery_id, db=db)
        else:
            raise HTTPException(
                status_code=403,
                detail=f"You can't mark a delivery as locked if it is not in orderable mode. The current mode is {delivery.status}.",
            )
    else:
        raise HTTPException(status_code=404, detail="Delivery not found.")


@router.post(
    "/amap/deliveries/{delivery_id}/delivered", status_code=204, tags=[Tags.amap]
)
async def mark_delivery_as_delivered(
    delivery_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.amap)),
):
    delivery = await cruds_amap.get_delivery_by_id(db=db, delivery_id=delivery_id)
    if delivery is not None:
        if delivery.status == DeliveryStatusType.locked:
            await cruds_amap.mark_delivery_as_delivered(delivery_id=delivery_id, db=db)
        else:
            raise HTTPException(
                status_code=403,
                detail=f"You can't mark a delivery as delivered if it is not in locked mode. The current mode is {delivery.status}.",
            )
    else:
        raise HTTPException(status_code=404, detail="Delivery not found.")


@router.post(
    "/amap/deliveries/{delivery_id}/archive", status_code=204, tags=[Tags.amap]
)
async def archive_of_delivery(
    delivery_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.amap)),
):
    delivery = await cruds_amap.get_delivery_by_id(db=db, delivery_id=delivery_id)
    if delivery is not None:
        if delivery.status == DeliveryStatusType.delivered:
            orders = await get_orders_from_delivery(
                delivery_id=delivery_id, db=db, user=user
            )
            with open(
                f"data/amap/delivery-{delivery_id}.json",
                "w",
            ) as file:
                json.dump(
                    {
                        "delivery": schemas_amap.DeliveryReturn(**delivery.__dict__),
                        "orders": [
                            schemas_amap.OrderReturn(**order.__dict__)
                            for order in orders
                        ],
                    },
                    file,
                )
            await cruds_amap.delete_delivery(db=db, delivery_id=delivery_id)
        else:
            raise HTTPException(
                status_code=403,
                detail=f"You can't archive a delivery if it is not in delivered mode. The current mode is {delivery.status}.",
            )
    else:
        raise HTTPException(status_code=404, detail="Delivery not found.")


@router.get(
    "/amap/users/cash",
    response_model=list[schemas_amap.CashComplete],
    status_code=200,
    tags=[Tags.amap],
)
async def get_users_cash(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.amap)),
):
    """
    Get cash from all users.

    **The user must be a member of the group AMAP to use this endpoint**
    """
    cash = await cruds_amap.get_users_cash(db)
    return cash


@router.get(
    "/amap/users/{user_id}/cash",
    response_model=schemas_amap.CashComplete,
    status_code=200,
    tags=[Tags.amap],
)
async def get_cash_by_id(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get cash from a specific user.

    **The user must be a member of the group AMAP to use this endpoint or can only access the endpoint for its own user_id**
    """
    user_db = await cruds_users.get_user_by_id(db=db, user_id=user_id)
    if user_db is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user_id == user.id or is_user_member_of_an_allowed_group(user, [GroupType.amap]):
        cash = await cruds_amap.get_cash_by_id(user_id=user_id, db=db)
        if cash is not None:
            return cash
        else:
            # We want to return a balance of 0 but we don't want to add it to the database
            # An admin AMAP has indeed to add a cash to the user the first time
            # TODO: this is a strange behaviour
            return schemas_amap.CashComplete(balance=0, user_id=user_id, user=user_db)
    else:
        raise HTTPException(
            status_code=403,
            detail="Users that are not member of the group AMAP can only access the endpoint for their own user_id.",
        )


@router.post(
    "/amap/users/{user_id}/cash",
    response_model=schemas_amap.CashComplete,
    status_code=201,
    tags=[Tags.amap],
)
async def create_cash_of_user(
    user_id: str,
    cash: schemas_amap.CashEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.amap)),
):
    """
    Create cash for an user.

    **The user must be a member of the group AMAP to use this endpoint**
    """

    user = await read_user(user_id=user_id, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    existing_cash = await cruds_amap.get_cash_by_id(db=db, user_id=user_id)
    if existing_cash is not None:
        raise HTTPException(
            status_code=400,
            detail="This user already has a cash.",
        )

    cash_db = models_amap.Cash(user_id=user_id, balance=cash.balance)

    await cruds_amap.create_cash_of_user(
        cash=cash_db,
        db=db,
    )

    # We can not directly return the cash_db because it does not contain the user.
    # Calling get_cash_by_id will return the cash with the user loaded as it's a relationship.
    return await cruds_amap.get_cash_by_id(
        user_id=user_id,
        db=db,
    )


@router.patch(
    "/amap/users/{user_id}/cash",
    status_code=204,
    tags=[Tags.amap],
)
async def edit_cash_by_id(
    user_id: str,
    balance: schemas_amap.CashEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.amap)),
):
    """
    Edit cash for an user. This will add the balance to the current balance.
    A negative value can be provided to remove money from the user.

    **The user must be a member of the group AMAP to use this endpoint**
    """
    user = await read_user(user_id=user_id, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    cash = await cruds_amap.get_cash_by_id(db=db, user_id=user_id)
    if cash is None:
        raise HTTPException(
            status_code=404,
            detail="The user don't have a cash.",
        )

    await cruds_amap.edit_cash_by_id(user_id=user_id, balance=balance, db=db)


@router.get(
    "/amap/users/{user_id}/orders",
    response_model=list[schemas_amap.OrderReturn],
    status_code=200,
    tags=[Tags.amap],
)
async def get_orders_of_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get orders from an user.

    **The user must be a member of the group AMAP to use this endpoint or can only access the endpoint for its own user_id**
    """
    user = await read_user(user_id=user_id, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_id == user.id or is_user_member_of_an_allowed_group(user, [GroupType.amap]):
        orders = await cruds_amap.get_orders_of_user(user_id=user_id, db=db)
        res = []
        for order in orders:
            products = await cruds_amap.get_products_of_order(
                db=db, order_id=order.order_id
            )
            res.append(
                schemas_amap.OrderReturn(productsdetail=products, **order.__dict__)
            )
        return res
    else:
        raise HTTPException(status_code=403)
