from fastapi import APIRouter

router = APIRouter()


@router.get("/products")
async def get_products():

    return ""


@router.post("/products")
async def create_products():

    return ""


@router.get("/products/{products_id}")
async def get_products_id(products_id):

    return ""


@router.put("/products/{products_id}")
async def edit_products(products_id):

    return ""


@router.delete("/products/{products_id}")
async def delete_products(products_id):

    return ""


@router.get("/deliveries")
async def get_delieveries():

    return ""


@router.post("/deliveries")
async def create_delieveries():

    return ""


@router.delete("/delieveries/{deliveries_id}")
async def delete_deliveries(deliveries_id):

    return ""


@router.get("/delieveries/{deliveries_id}/products")
async def get_products_from_delieveries(deliveries_id):

    return ""


@router.post("/delieveries/{deliveries_id}/products")
async def create_products_from_delieveries(deliveries_id):

    return ""


@router.delete("/delieveries/{deliveries_id}/products/{products_id}")
async def delete_products_from_delieveries_id(deliveries_id, products_id):

    return ""


@router.get("/delieveries/{deliveries_id}/orders")
async def get_orders_from_delieveries(deliveries_id):

    return ""


@router.post("/delieveries/{deliveries_id}/orders")
async def create_orders_from_delieveries(deliveries_id):

    return ""


@router.put("/delieveries/{deliveries_id}/orders")
async def edit_orders_from_delieveries(deliveries_id):

    return ""


@router.get("/orders/{orders_id}")
async def get_orders_id(orders_id):

    return ""


@router.get("/users/cash")
async def get_cash_from_users():

    return ""


@router.get("/users/{users_id}/cash")
async def get_cash_from_users_id(users_id):

    return ""


@router.post("/users/{users_id}/cash")
async def create_cash_from_users_id(users_id):

    return ""


@router.put("/users/{users_id}/cash")
async def edit_cash_from_users_id(users_id):

    return ""
