import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_bdebooking
from app.dependencies import get_db
from app.schemas import schemas_bdebooking
from app.utils.types.tags import Tags

router = APIRouter()


# Prefix "/bdebooking" added in api.py
@router.get(
    "/bdebooking/bookings",
    response_model=list[schemas_bdebooking.BookingComplete],
    status_code=200,
    tags=[Tags.bdebooking],
)
async def get_confirmed_bookings(db: AsyncSession = Depends(get_db)):
    bookings = cruds_bdebooking.get_bookings(db=db, confirmed=True)
    return bookings


@router.get(
    "/bdebooking/bookings/unconfirmed",
    response_model=list[schemas_bdebooking.BookingComplete],
    status_code=200,
    tags=[Tags.bdebooking],
)
async def get_unconfirmed_bookings(db: AsyncSession = Depends(get_db)):
    bookings = cruds_bdebooking.get_bookings(db=db, confirmed=False)
    return bookings


@router.post("/bdebooking/bookings", status_code=201, tags=[Tags.bdebooking])
async def create_bookings(
    booking: schemas_bdebooking.BookingBase, db: AsyncSession = Depends(get_db)
):
    db_booking = schemas_bdebooking.BookingComplete(
        id=str(uuid.uuid4()), confirmed=False, **booking.dict()
    )
    try:
        await cruds_bdebooking.create_booking(booking=db_booking, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.patch(
    "/bdebooking/bookings/{booking_id}", status_code=200, tags=[Tags.bdebooking]
)
async def edit_bookings_id(
    booking_id: str,
    booking: schemas_bdebooking.BookingBase,
    db: AsyncSession = Depends(get_db),
):
    db_booking = schemas_bdebooking.BookingComplete(
        id=booking_id, confirmed=False, **booking.dict()
    )
    try:
        await cruds_bdebooking.edit_booking(
            booking_id=booking_id, booking=db_booking, db=db
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.patch(
    "/bdebooking/bookings/{booking_id}/confirm",
    status_code=200,
    tags=[Tags.bdebooking],
)
async def confirm_booking(booking_id: str, db: AsyncSession = Depends(get_db)):
    await cruds_bdebooking.confirm_booking(booking_id=booking_id, db=db)


@router.delete(
    "/bdebooking/bookings/{booking_id}", status_code=204, tags=[Tags.bdebooking]
)
async def delete_bookings_id(booking_id, db: AsyncSession = Depends(get_db)):
    await cruds_bdebooking.delete_booking(booking_id=booking_id, db=db)
