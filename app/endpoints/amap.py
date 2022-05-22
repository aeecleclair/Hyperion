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


@router.get("/amap/delieveries/{deliveries_id}/products")
async def get_products_from_delieveries(deliveries_id):

    return ""


@router.post("/amap/delieveries/{deliveries_id}/products")
async def create_products_from_delieveries(deliveries_id):

    return ""


@router.delete("/amap/delieveries/{deliveries_id}/products/{products_id}")
async def delete_products_from_delieveries_id(deliveries_id, products_id):

    return ""


@router.get("/amap/delieveries/{deliveries_id}/orders")
async def get_orders_from_delieveries(deliveries_id):

    return ""


@router.post("/amap/delieveries/{deliveries_id}/orders")
async def create_orders_from_delieveries(deliveries_id):

    return ""


@router.put("/amap/delieveries/{deliveries_id}/orders")
async def edit_orders_from_delieveries(deliveries_id):

    return ""


@router.get("/amap/orders/{orders_id}")
async def get_orders_id(orders_id):

    return ""


@router.get("/amap/users/cash")
async def get_cash_from_users():

    return ""


@router.get("/amap/users/{users_id}/cash")
async def get_cash_from_users_id(users_id):

    return ""


@router.post("/amap/users/{users_id}/cash")
async def create_cash_from_users_id(users_id):

    return ""


@router.put("/amap/users/{users_id}/cash")
async def edit_cash_from_users_id(users_id):

    return ""
