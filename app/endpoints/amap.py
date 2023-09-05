import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from pytz import timezone
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.cruds import cruds_amap, cruds_users
from app.dependencies import (
    get_db,
    get_notification_tool,
    get_redis_client,
    get_request_id,
    get_settings,
    is_user_a_member,
    is_user_a_member_of,
)
from app.endpoints.users import read_user
from app.models import models_amap, models_core
from app.schemas import schemas_amap
from app.schemas.schemas_notification import Message
from app.utils.communication.notifications import NotificationTool
from app.utils.redis import locker_get, locker_set
from app.utils.tools import is_user_member_of_an_allowed_group
from app.utils.types.amap_types import DeliveryStatusType
from app.utils.types.groups_type import GroupType
from app.utils.types.tags import Tags

router = APIRouter()

hyperion_amap_logger = logging.getLogger("hyperion.amap")
hyperion_error_logger = logging.getLogger("hyperion.error")


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
        raise HTTPException(status_code=400, detail=str(error))


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
            status_code=400, detail="This product is used in a delivery"
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
    if await cruds_amap.is_there_a_delivery_on(
        db=db, delivery_date=db_delivery.delivery_date
    ):
        raise HTTPException(
            status_code=400, detail="There is already a delivery planned that day."
        )

    result = await cruds_amap.create_delivery(delivery=db_delivery, db=db)
    return result


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
    if delivery_db is None:
        raise HTTPException(status_code=404, detail="Delivery not found.")

    if delivery_db.status != DeliveryStatusType.creation:
        raise HTTPException(
            status_code=400,
            detail=f"You can't remove a product if the delivery is not in creation mode. The current mode is {delivery_db.status}.",
        )

    await cruds_amap.delete_delivery(db=db, delivery_id=delivery_id)


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
    if delivery_db is None:
        raise HTTPException(status_code=404, detail="Delivery not found.")

    if delivery_db.status != DeliveryStatusType.creation:
        raise HTTPException(
            status_code=400,
            detail=f"You can't edit a delivery if the delivery is not in creation mode. The current mode is {delivery_db.status}.",
        )

    await cruds_amap.edit_delivery(db=db, delivery_id=delivery_id, delivery=delivery)


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
    if delivery is None:
        raise HTTPException(status_code=404, detail="Delivery not found.")

    if delivery.status != DeliveryStatusType.creation:
        raise HTTPException(
            status_code=403,
            detail=f"You can't add a product if the delivery is not in creation mode. The current mode is {delivery.status}.",
        )

    try:
        await cruds_amap.add_product_to_delivery(
            delivery_id=delivery_id,
            products_ids=products_ids,
            db=db,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


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
    if delivery is None:
        raise HTTPException(status_code=404, detail="Delivery not found.")

    if delivery.status != DeliveryStatusType.creation:
        raise HTTPException(
            status_code=403,
            detail=f"You can't remove a product if the delivery is not in creation mode. The current mode is {delivery.status}.",
        )

    await cruds_amap.remove_product_from_delivery(
        db=db, delivery_id=delivery_id, products_ids=products_ids
    )


@router.get(
    "/amap/deliveries/{delivery_id}/orders",
    response_model=list[schemas_amap.OrderReturn],
    status_code=200,
    tags=[Tags.amap],
)
async def get_orders_from_delivery(
    delivery_id: str,
    db: AsyncSession = Depends(get_db),
    user_req: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.amap)),
):
    """
    Get orders from a delivery.

    **The user must be a member of the group AMAP to use this endpoint**
    """
    delivery = await cruds_amap.get_delivery_by_id(db=db, delivery_id=delivery_id)
    if delivery is None:
        raise HTTPException(status_code=404, detail="Delivery not found")

    orders = await cruds_amap.get_orders_from_delivery(db=db, delivery_id=delivery_id)
    res = []
    for order in orders:
        order_content = await cruds_amap.get_products_of_order(
            db=db, order_id=order.order_id
        )
        products = [
            schemas_amap.ProductQuantity(**product.__dict__)
            for product in order_content
        ]
        res.append(schemas_amap.OrderReturn(productsdetail=products, **order.__dict__))
    return res


@router.get(
    "/amap/orders/{order_id}",
    response_model=schemas_amap.OrderReturn,
    status_code=200,
    tags=[Tags.amap],
)
async def get_order_by_id(
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

    products = await cruds_amap.get_products_of_order(db=db, order_id=order_id)
    return schemas_amap.OrderReturn(productsdetail=products, **order.__dict__)


@router.post(
    "/amap/orders",
    response_model=schemas_amap.OrderReturn,
    status_code=201,
    tags=[Tags.amap],
)
async def add_order_to_delievery(
    order: schemas_amap.OrderBase,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis | None = Depends(get_redis_client),
    user: models_core.CoreUser = Depends(is_user_a_member),
    settings: Settings = Depends(get_settings),
    request_id: str = Depends(get_request_id),
):
    """
    Add an order to a delivery.

    **A member of the group AMAP can create an order for every user**
    """
    delivery = await cruds_amap.get_delivery_by_id(db=db, delivery_id=order.delivery_id)

    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")

    if delivery.status != DeliveryStatusType.orderable:
        raise HTTPException(
            status_code=400,
            detail=f"You can't order if the delivery is not in orderable mode. The current mode is {delivery.status}",
        )

    if len(order.products_ids) != len(order.products_quantity):
        raise HTTPException(status_code=400, detail="Invalid request")

    if not (
        user.id == order.user_id
        or is_user_member_of_an_allowed_group(user, [GroupType.amap])
    ):
        raise HTTPException(
            status_code=403, detail="You are not allowed to add this order"
        )

    amount = 0.0
    for product_id, product_quantity in zip(
        order.products_ids, order.products_quantity
    ):
        prod = await cruds_amap.get_product_by_id(product_id=product_id, db=db)
        if prod is None or prod not in delivery.products:
            raise HTTPException(status_code=403, detail="Invalid product")
        amount += prod.price * product_quantity

    ordering_date = datetime.now(timezone(settings.TIMEZONE))
    order_id = str(uuid.uuid4())
    db_order = schemas_amap.OrderComplete(
        order_id=order_id,
        amount=amount,
        ordering_date=ordering_date,
        delivery_date=delivery.delivery_date,
        **order.dict(),
    )
    balance: models_amap.Cash | None = await cruds_amap.get_cash_by_id(
        db=db,
        user_id=order.user_id,
    )

    # If the balance does not exist, we create a new one with a balance of 0
    if not balance:
        new_cash_db = schemas_amap.CashDB(
            balance=0,
            user_id=order.user_id,
        )
        balance = models_amap.Cash(
            **new_cash_db.dict(),
        )
        await cruds_amap.create_cash_of_user(
            cash=balance,
            db=db,
        )

    if not amount:
        raise HTTPException(status_code=400, detail="You can't order nothing")

    redis_key = "amap_" + order.user_id

    if not isinstance(redis_client, Redis) or locker_get(
        redis_client=redis_client, key=redis_key
    ):
        raise HTTPException(status_code=429, detail="Too fast !")
    locker_set(redis_client=redis_client, key=redis_key, lock=True)

    try:
        await cruds_amap.add_order_to_delivery(
            order=db_order,
            db=db,
        )
        await cruds_amap.remove_cash(
            db=db,
            user_id=order.user_id,
            amount=amount,
        )

        orderret = await cruds_amap.get_order_by_id(order_id=db_order.order_id, db=db)
        productsret = await cruds_amap.get_products_of_order(db=db, order_id=order_id)

        hyperion_amap_logger.info(
            f"Add_order_to_delivery: An order has been created for user {order.user_id} for an amount of {amount}€. ({request_id})"
        )
        productsret
        return schemas_amap.OrderReturn(productsdetail=productsret, **orderret.__dict__)

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    finally:
        locker_set(redis_client=redis_client, key=redis_key, lock=False)


@router.patch(
    "/amap/orders/{order_id}",
    status_code=204,
    tags=[Tags.amap],
)
async def edit_order_from_delievery(
    order_id: str,
    order: schemas_amap.OrderEdit,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis | None = Depends(get_redis_client),
    user: models_core.CoreUser = Depends(is_user_a_member),
    settings: Settings = Depends(get_settings),
    request_id: str = Depends(get_request_id),
):
    """
    Edit an order.

    **A member of the group AMAP can edit orders of other users**
    """

    previous_order = await cruds_amap.get_order_by_id(db=db, order_id=order_id)
    if not previous_order:
        raise HTTPException(status_code=404, detail="Order not found")

    delivery = await cruds_amap.get_delivery_by_id(
        db=db, delivery_id=previous_order.delivery_id
    )
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")

    if delivery.status != DeliveryStatusType.orderable:
        raise HTTPException(
            status_code=400,
            detail=f"You can't edit an order if the delivery is not in orderable mode. The current mode is {delivery.status}s",
        )

    if not (
        user.id == previous_order.user_id
        or is_user_member_of_an_allowed_group(user, [GroupType.amap])
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to edit this order",
        )

    if order.products_ids is None:
        try:
            await cruds_amap.edit_order_without_products(
                order=order, db=db, order_id=order_id
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error))

    else:
        if order.products_quantity is None or len(order.products_quantity) != len(
            order.products_ids
        ):
            raise HTTPException(status_code=400, detail="Invalid request")

        amount = 0.0
        for product_id, product_quantity in zip(
            order.products_ids, order.products_quantity
        ):
            prod = await cruds_amap.get_product_by_id(product_id=product_id, db=db)
            if prod is None or prod not in delivery.products:
                raise HTTPException(status_code=400, detail="Invalid product")
            amount += prod.price * product_quantity

        db_order = schemas_amap.OrderComplete(
            order_id=order_id,
            ordering_date=previous_order.ordering_date,
            delivery_date=delivery.delivery_date,
            delivery_id=previous_order.delivery_id,
            user_id=previous_order.user_id,
            amount=amount,
            **order.dict(),
        )

        previous_amount = previous_order.amount
        balance = await cruds_amap.get_cash_by_id(db=db, user_id=previous_order.user_id)
        if not balance:
            raise HTTPException(status_code=404, detail="No cash found")

        redis_key = "amap_" + previous_order.user_id

        if not isinstance(redis_client, Redis) or locker_get(
            redis_client=redis_client, key=redis_key
        ):
            raise HTTPException(status_code=429, detail="Too fast !")
        locker_set(redis_client=redis_client, key=redis_key, lock=True)

        try:
            await cruds_amap.edit_order_with_products(
                order=db_order,
                db=db,
            )
            await cruds_amap.remove_cash(
                db=db,
                user_id=previous_order.user_id,
                amount=amount,
            )
            await cruds_amap.add_cash(
                db=db,
                user_id=previous_order.user_id,
                amount=previous_amount,
            )
            hyperion_amap_logger.info(
                f"Edit_order: Order {order_id} has been edited for user {db_order.user_id}. Amount was {previous_amount}€, is now {amount}€. ({request_id})"
            )

        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error))

        finally:
            locker_set(redis_client=redis_client, key=redis_key, lock=False)


@router.delete(
    "/amap/orders/{order_id}",
    status_code=204,
    tags=[Tags.amap],
)
async def remove_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis | None = Depends(get_redis_client),
    user: models_core.CoreUser = Depends(is_user_a_member),
    request_id: str = Depends(get_request_id),
):
    """
    Delete an order.

    **A member of the group AMAP can delete orders of other users**
    """
    is_user_admin = is_user_member_of_an_allowed_group(user, [GroupType.amap])
    order = await cruds_amap.get_order_by_id(db=db, order_id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="No order found")

    delivery = await cruds_amap.get_delivery_by_id(db=db, delivery_id=order.delivery_id)
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")

    if delivery.status != DeliveryStatusType.orderable and not (
        is_user_admin and delivery.status == DeliveryStatusType.locked
    ):
        raise HTTPException(
            status_code=400,
            detail=f"You can't remove an order if the delivery is not in orderable mode. The current mode is {delivery.status}",
        )

    if not (user.id == order.user_id or is_user_admin):
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to delete this order",
        )

    amount = order.amount
    balance = await cruds_amap.get_cash_by_id(db=db, user_id=order.user_id)
    if not balance:
        raise HTTPException(status_code=404, detail="No cash found")

    redis_key = "amap_" + order.user_id

    if not isinstance(redis_client, Redis) or locker_get(
        redis_client=redis_client, key=redis_key
    ):
        raise HTTPException(status_code=429, detail="Too fast !")
    locker_set(redis_client=redis_client, key=redis_key, lock=True)

    try:
        await cruds_amap.remove_order(
            db=db,
            order_id=order_id,
        )
        await cruds_amap.add_cash(
            db=db,
            user_id=order.user_id,
            amount=amount,
        )
        hyperion_amap_logger.info(
            f"Delete_order: Order {order_id} by {order.user_id} was deleted. {amount}€ were refunded. ({request_id})"
        )
        return Response(status_code=204)

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    finally:
        locker_set(redis_client=redis_client, key=redis_key, lock=False)


@router.post(
    "/amap/deliveries/{delivery_id}/openordering",
    status_code=204,
    tags=[Tags.amap],
)
async def open_ordering_of_delivery(
    delivery_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.amap)),
):
    delivery = await cruds_amap.get_delivery_by_id(db=db, delivery_id=delivery_id)
    if delivery is None:
        raise HTTPException(status_code=404, detail="Delivery not found.")

    if delivery.status != DeliveryStatusType.creation:
        raise HTTPException(
            status_code=400,
            detail=f"You can't open ordering for a delivery if it is not in creation mode. The current mode is {delivery.status}.",
        )

    await cruds_amap.open_ordering_of_delivery(delivery_id=delivery_id, db=db)


@router.post(
    "/amap/deliveries/{delivery_id}/lock",
    status_code=204,
    tags=[Tags.amap],
)
async def lock_delivery(
    delivery_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.amap)),
):
    delivery = await cruds_amap.get_delivery_by_id(db=db, delivery_id=delivery_id)
    if delivery is None:
        raise HTTPException(status_code=404, detail="Delivery not found.")

    if delivery.status != DeliveryStatusType.orderable:
        raise HTTPException(
            status_code=400,
            detail=f"You can't mark a delivery as locked if it is not in orderable mode. The current mode is {delivery.status}.",
        )
    await cruds_amap.lock_delivery(delivery_id=delivery_id, db=db)


@router.post(
    "/amap/deliveries/{delivery_id}/delivered",
    status_code=204,
    tags=[Tags.amap],
)
async def mark_delivery_as_delivered(
    delivery_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.amap)),
):
    delivery = await cruds_amap.get_delivery_by_id(db=db, delivery_id=delivery_id)
    if delivery is None:
        raise HTTPException(status_code=404, detail="Delivery not found.")

    if delivery.status != DeliveryStatusType.locked:
        raise HTTPException(
            status_code=400,
            detail=f"You can't mark a delivery as delivered if it is not in locked mode. The current mode is {delivery.status}.",
        )
    await cruds_amap.mark_delivery_as_delivered(delivery_id=delivery_id, db=db)


@router.post(
    "/amap/deliveries/{delivery_id}/archive",
    status_code=204,
    tags=[Tags.amap],
)
async def archive_of_delivery(
    delivery_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.amap)),
):
    delivery = await cruds_amap.get_delivery_by_id(db=db, delivery_id=delivery_id)
    if delivery is None:
        raise HTTPException(status_code=404, detail="Delivery not found.")

    if delivery.status != DeliveryStatusType.delivered:
        raise HTTPException(
            status_code=400,
            detail=f"You can't archive a delivery if it is not in delivered mode. The current mode is {delivery.status}.",
        )

    await cruds_amap.mark_delivery_as_archived(db=db, delivery_id=delivery_id)


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

    if not (
        user_id == user.id or is_user_member_of_an_allowed_group(user, [GroupType.amap])
    ):
        raise HTTPException(
            status_code=403,
            detail="Users that are not member of the group AMAP can only access the endpoint for their own user_id.",
        )

    cash = await cruds_amap.get_cash_by_id(user_id=user_id, db=db)
    if cash is None:
        # We want to return a balance of 0 but we don't want to add it to the database
        # An admin AMAP has indeed to add a cash to the user the first time
        # TODO: this is a strange behaviour
        return schemas_amap.CashComplete(
            balance=0,
            user_id=user_id,
            user=schemas_amap.CoreUserSimple(**user_db.__dict__),
        )

    return cash


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
    request_id: str = Depends(get_request_id),
    settings: Settings = Depends(get_settings),
    notification_tool: NotificationTool = Depends(get_notification_tool),
):
    """
    Create cash for an user.

    **The user must be a member of the group AMAP to use this endpoint**
    """

    user_db = await read_user(user_id=user_id, db=db)
    if not user_db:
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

    hyperion_amap_logger.info(
        f"Create_cash_of_user: A cash has been created for user {cash_db.user_id} for an amount of {cash_db.balance}€. ({request_id})"
    )

    # We can not directly return the cash_db because it does not contain the user.
    # Calling get_cash_by_id will return the cash with the user loaded as it's a relationship.
    result = await cruds_amap.get_cash_by_id(
        user_id=user_id,
        db=db,
    )

    try:
        if result:
            now = datetime.now(timezone(settings.TIMEZONE))
            message = Message(
                context=f"amap-cash-{user_id}",
                is_visible=True,
                title="AMAP - Solde mis à jour",
                content=f"Votre nouveau solde est de {result.balance} €.",
                # The notification will expire in 3 days
                expire_on=now.replace(day=now.day + 3),
            )
            await notification_tool.send_notification_to_user(
                user_id=user_id,
                message=message,
            )
    except Exception as error:
        hyperion_error_logger.error(f"Error while sending AMAP notification, {error}")

    return result


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
    request_id: str = Depends(get_request_id),
):
    """
    Edit cash for an user. This will add the balance to the current balance.
    A negative value can be provided to remove money from the user.

    **The user must be a member of the group AMAP to use this endpoint**
    """
    user_db = await read_user(user_id=user_id, db=db)
    if not user_db:
        raise HTTPException(status_code=404, detail="User not found")

    cash = await cruds_amap.get_cash_by_id(db=db, user_id=user_id)
    if cash is None:
        raise HTTPException(
            status_code=404,
            detail="The user don't have a cash.",
        )

    await cruds_amap.add_cash(user_id=user_id, amount=balance.balance, db=db)

    hyperion_amap_logger.info(
        f"Edit_cash_by_id: Cash has been updated for user {cash.user_id} from an amount of {cash.balance}€ to an amount of {balance.balance}€. ({request_id})"
    )


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
    user_requested = await read_user(user_id=user_id, db=db)
    if not user_requested:
        raise HTTPException(status_code=404, detail="User not found")

    if not (
        user_id == user.id or is_user_member_of_an_allowed_group(user, [GroupType.amap])
    ):
        raise HTTPException(
            status_code=403,
            detail="Users that are not member of the group AMAP can only access the endpoint for their own user_id.",
        )
    orders = await cruds_amap.get_orders_of_user(user_id=user_id, db=db)
    res = []
    for order in orders:
        products = await cruds_amap.get_products_of_order(
            db=db, order_id=order.order_id
        )
        res.append(schemas_amap.OrderReturn(productsdetail=products, **order.__dict__))
    return res


@router.get(
    "/amap/information",
    response_model=schemas_amap.Information,
    status_code=200,
    tags=[Tags.amap],
)
async def get_information(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Return all information
    """
    information = await cruds_amap.get_information(db)

    if information is None:
        return schemas_amap.Information(
            manager="",
            link="",
            description="",
        )

    return information


@router.patch(
    "/amap/information",
    status_code=204,
    tags=[Tags.amap],
)
async def edit_information(
    edit_information: schemas_amap.InformationEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.amap)),
):
    """
    Update information

    **The user must be a member of the group AMAP to use this endpoint**
    """

    # We need to check if informations are already in the database
    information = await cruds_amap.get_information(db)

    if information is None:
        empty_information = models_amap.AmapInformation(
            unique_id="information",
            manager="",
            link="",
            description="",
        )
        try:
            await cruds_amap.add_information(empty_information, db)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error))

    else:
        try:
            await cruds_amap.edit_information(
                information_update=edit_information, db=db
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error))
