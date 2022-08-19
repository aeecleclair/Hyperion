from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import models_bdebooking
from app.schemas import schemas_bdebooking


async def get_bookings(
    db: AsyncSession, confirmed: bool
) -> list[models_bdebooking.Booking]:
    result = await db.execute(
        select(models_bdebooking.Booking).where(
            models_bdebooking.Booking.confirmed is confirmed
        )
    )
    return result.scalars().all()


async def create_booking(db: AsyncSession, booking: schemas_bdebooking.BookingComplete):
    db_booking = models_bdebooking.Booking(**booking.dict())
    db.add(db_booking)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError()


async def edit_booking(
    db: AsyncSession, booking_id: str, booking: schemas_bdebooking.BookingComplete
):
    await db.execute(
        update(models_bdebooking.Booking)
        .where(models_bdebooking.Booking.id == booking_id)
        .values(**booking.dict(exclude_none=True))
    )
    await db.commit()


async def confirm_booking(db: AsyncSession, booking_id: str):
    await db.execute(
        update(models_bdebooking.Booking)
        .where(models_bdebooking.Booking.id == booking_id)
        .values(confirmed=True)
    )
    await db.commit()


async def delete_booking(db: AsyncSession, booking_id: str):
    await db.execute(
        delete(models_bdebooking.Booking).where(
            models_bdebooking.Booking.id == booking_id
        )
    )
    await db.commit()
