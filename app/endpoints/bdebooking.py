from fastapi import APIRouter

router = APIRouter()


# Prefix "/bdebooking" added in api.py
@router.get("/bdebooking/bookings")
async def get_bookings():

    return ""


@router.get("/bdebooking/bookings/unconfirmed")
async def get_bookings_unconfirmed():

    return ""


@router.post("/bdebooking/bookings")
async def create_bookings():

    return ""


@router.put("/bdebooking/bookings/{bookings_id}")
async def edit_bookings_id(bookings_id):

    return ""


@router.put("/bdebooking/bookings/{bookings_id}/confirm")
async def edit_bookings_id_confirm(bookings_id):

    return ""


@router.delete("/bdebooking/bookings/{bookings_id}")
async def delete_bookings_id(bookings_id):

    return ""
