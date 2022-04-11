from fastapi import APIRouter

router = APIRouter()


# Prefix "/amap" added in api.py
@router.get("/amap/products")
async def get_products():

    return ""


@router.post("/amap/products")
async def create_products():

    return ""


@router.get("/amap/products/{products_id}")
async def get_products_id(products_id):

    return ""


@router.put("/amap/products/{products_id}")
async def edit_products(products_id):

    return ""


@router.delete("/amap/products/{products_id}")
async def delete_products(products_id):

    return ""


@router.get("/amap/deliveries")
async def get_delieveries():

    return ""


@router.post("/amap/deliveries")
async def create_delieveries():

    return ""


@router.delete("/amap/delieveries/{deliveries_id}")
async def delete_deliveries(deliveries_id):

    return ""


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
