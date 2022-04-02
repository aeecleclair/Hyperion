from fastapi import APIRouter

router = APIRouter()


# Prefix "/bdebooking" added in api.py
@router.get("/bookings")
async def get_bookings():

    return ""


@router.get("/bookings/unconfirmed")
async def get_bookings_unconfirmed():

    return ""


@router.post("/bookings")
async def create_bookings():

    return ""


@router.put("/bookings/{bookings_id}")
async def edit_bookings_id(bookings_id):

    return ""


@router.put("/bookings/{bookings_id}/confirm")
async def edit_bookings_id_confirm(bookings_id):

    return ""


@router.delete("/bookings/{bookings_id}")
async def delete_bookings_id(bookings_id):

    return ""
