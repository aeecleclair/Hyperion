@app.get("/events")
async def get_events():

    return ""


@app.get("/events/unconfirmed")
async def get_events_unconfirmed():

    return ""


@app.post("/events")
async def create_events():

    return ""


@app.put("/events/{events_id}")
async def edit_events_id(events_id):

    return ""


@app.put("/events/{events_id}/confirm")
async def edit_events_id_confirm(events_id):

    return ""


@app.delete("/events/{events_id}")
async def delete_events_id(events_id):

    return ""
