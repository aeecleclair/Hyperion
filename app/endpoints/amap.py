from ..main import app


@app.get("/products")
async def get_products():

    return ""


@app.post("/products")
async def create_products():

    return ""


@app.get("/products/{products_id}")
async def get_products_id(products_id):

    return ""


@app.put("/products/{products_id}")
async def edit_products(products_id):

    return ""


@app.delete("/products/{products_id}")
async def delete_products(products_id):

    return ""


@app.get("/deliveries")
async def get_delieveries():

    return ""


@app.post("/deliveries")
async def create_delieveries():

    return ""


@app.delete("/delieveries/{deliveries_id}")
async def delete_deliveries(deliveries_id):

    return ""


@app.get("/delieveries/{deliveries_id}/products")
async def get_products_from_delieveries(deliveries_id):

    return ""


@app.post("/delieveries/{deliveries_id}/products")
async def create_products_from_delieveries(deliveries_id):

    return ""


@app.delete("/delieveries/{deliveries_id}/products/{products_id}")
async def delete_products_from_delieveries_id(deliveries_id, products_id):

    return ""


@app.get("/delieveries/{deliveries_id}/orders")
async def get_orders_from_delieveries(deliveries_id):

    return ""


@app.post("/delieveries/{deliveries_id}/orders")
async def create_orders_from_delieveries(deliveries_id):

    return ""


@app.put("/delieveries/{deliveries_id}/orders")
async def edit_orders_from_delieveries(deliveries_id):

    return ""


@app.get("/orders/{orders_id}")
async def get_orders_id(orders_id):

    return ""


@app.get("/users/cash")
async def get_cash_from_users():

    return ""


@app.get("/users/{users_id}/cash")
async def get_cash_from_users_id(users_id):

    return ""


@app.post("/users/{users_id}/cash")
async def create_cash_from_users_id(users_id):

    return ""


@app.put("/users/{users_id}/cash")
async def edit_cash_from_users_id(users_id):

    return ""
