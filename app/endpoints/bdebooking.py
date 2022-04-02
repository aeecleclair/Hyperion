@app.get("/bookings")
async def get_bookings():

    return ""


@app.get("/bookings/unconfirmed")
async def get_bookings_unconfirmed():

    return ""


@app.post("/bookings")
async def create_bookings():

    return ""


@app.put("/bookings/{bookings_id}")
async def edit_bookings_id(bookings_id):

    return ""


@app.put("/bookings/{bookings_id}/confirm")
async def edit_bookings_id_confirm(bookings_id):

    return ""


@app.delete("/bookings/{bookings_id}")
async def delete_bookings_id(bookings_id):

    return ""
