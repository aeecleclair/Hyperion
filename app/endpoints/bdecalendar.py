from fastapi import APIRouter

router = APIRouter()


# Prefix "/bdecalendar" added in api.py
@router.get("/bdecalendar/events")
async def get_events():

    return ""


@router.get("/bdecalendar/events/unconfirmed")
async def get_events_unconfirmed():

    return ""


@router.post("/bdecalendar/events")
async def create_events():

    return ""


@router.put("/events/{events_id}")
async def edit_events_id(events_id):

    return ""


@router.put("/bdecalendar/events/{events_id}/confirm")
async def edit_events_id_confirm(events_id):

    return ""


@router.delete("/bdecalendar/events/{events_id}")
async def delete_events_id(events_id):

    return ""
