from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db
from app.cruds import cruds_bdebooking
from app.schemas import schemas_bdebooking


# Is it possible to avoid alle these import in each files

router = APIRouter()

# Prefix "/bdebooking" added in api.py


@router.get("/bookings/")
async def get_users(db: AsyncSession = Depends(get_db)):
    bookings = await cruds_bdebooking.get_booking(db)
    return bookings


@router.get("/bookings/unconfirmed", response_model=list[schemas_bdebooking.Booking])
async def get_booking_unconfirmed(db: AsyncSession = Depends(get_db)):
    bookings = await cruds_bdebooking.get_booking_unconfirmed(db)
    return bookings


@router.get("/bookings/confirmed", response_model=list[schemas_bdebooking.Booking])
async def get_booking_confirmed(db: AsyncSession = Depends(get_db)):
    bookings = await cruds_bdebooking.get_booking_unconfirmed(db)
    return bookings


@router.post("/bookings/", response_model=schemas_bdebooking.Booking)
async def create_bookings(
    booking: schemas_bdebooking.Booking, db: AsyncSession = Depends(get_db)
):
    try:
        return await cruds_bdebooking.create_booking(booking=booking, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.put("/bookings/{bookings_id}")
async def edit_bookings_id(bookings_id):

    return ""


@router.put("/bookings/{bookings_id}/confirm")
async def edit_bookings_id_confirm(bookings_id):

    return ""


@router.delete("/bookings/{bookings_id}")
async def delete_bookings_id(bookings_id):

    return ""
