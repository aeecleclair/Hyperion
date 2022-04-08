from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db
from app.cruds import cruds_bdebooking
from app.schemas import schemas_bdebooking


# Is it possible to avoid alle these import in each files

router = APIRouter()

# Prefix "/bdebooking" added in api.py


@router.get("/bookings/")  # list[schemas_bdebooking.Booking] provoque un bug
async def get_users(db: AsyncSession = Depends(get_db)):
    bookings = await cruds_bdebooking.get_booking(db)
    return bookings


@router.get("/bookings/unconfirmed")  # response_model=list[schemas_bdebooking.Booking]
async def get_booking_unconfirmed(db: AsyncSession = Depends(get_db)):
    bookings = await cruds_bdebooking.get_booking_unconfirmed(db)
    return bookings


@router.get("/bookings/confirmed")  # response_model=list[schemas_bdebooking.Booking]
async def get_booking_confirmed(db: AsyncSession = Depends(get_db)):
    bookings = await cruds_bdebooking.get_booking_confirmed(db)
    return bookings


@router.post("/bookings/")  # response_model=schemas_bdebooking.Booking
async def create_bookings(
    booking: schemas_bdebooking.Booking, db: AsyncSession = Depends(get_db)
):
    try:
        return await cruds_bdebooking.create_booking(booking=booking, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.put("/bookings/{booking_id}")
async def edit_booking(
    booking_modifiy: schemas_bdebooking.Booking,
    booking_id: int,
    db: AsyncSession = Depends(get_db),
):
    try:
        await cruds_bdebooking.modify_booking(
            booking_modify=booking_modifiy, db=db, booking_id=booking_id
        )
        return f"The booking {booking_id} is modified !"
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.put("/bookings/{booking_id}/confirm")
async def booking_confirm(booking_id: int, db: AsyncSession = Depends(get_db)):
    try:
        await cruds_bdebooking.confirm_booking(db=db, booking_id=booking_id)
        return f"The booking {booking_id} is confirmed !"
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.put("/bookings/{booking_id}/unconfirm")
async def booking_unconfirm(booking_id: int, db: AsyncSession = Depends(get_db)):
    try:
        await cruds_bdebooking.unconfirm_booking(db=db, booking_id=booking_id)
        return f"The booking {booking_id} is waiting for confirmation"
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.delete("/bookings/{booking_id}")
async def delete_booking(booking_id: int, db: AsyncSession = Depends(get_db)):
    booking = cruds_bdebooking.get_booking_by_id(db=db, booking_id=booking_id)
    if booking.pending:
        return f"The booking {booking_id} is confirmed you can't modify it !"
    else:
        await cruds_bdebooking.delete_booking(db=db, booking_id=booking_id)
        return f"The booking {booking_id} is deleted !"
