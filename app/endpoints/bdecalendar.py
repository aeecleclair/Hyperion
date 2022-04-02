from fastapi import APIRouter

router = APIRouter()


@router.get("/events")
async def get_events():

    return ""


@router.get("/events/unconfirmed")
async def get_events_unconfirmed():

    return ""


@router.post("/events")
async def create_events():

    return ""


@router.put("/events/{events_id}")
async def edit_events_id(events_id):

    return ""


@router.put("/events/{events_id}/confirm")
async def edit_events_id_confirm(events_id):

    return ""


@router.delete("/events/{events_id}")
async def delete_events_id(events_id):

    return ""
