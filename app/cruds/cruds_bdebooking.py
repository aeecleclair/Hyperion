from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import models_bdebooking
from ..schemas import schemas_bdebooking
from sqlalchemy import select, delete


async def get_booking(db: AsyncSession):
    result = await db.execute(select(models_bdebooking.RoomBooking))
    return result.scalars().all()


async def get_booking_confirmed(db: AsyncSession):
    result = await db.execute(
        select(models_bdebooking.RoomBooking).where(
            not models_bdebooking.RoomBooking.pending
        )
    )
    return result.scalars().all()


async def get_booking_unconfirmed(db: AsyncSession):
    result = await db.execute(
        select(models_bdebooking.RoomBooking).where(
            models_bdebooking.RoomBooking.pending
        )
    )
    return result.scalars().all()


async def get_booking_by_id(db: AsyncSession, booking_id: int):
    result = await db.execute(
        select(models_bdebooking.RoomBooking).where(
            models_bdebooking.RoomBooking.id == booking_id
        )
    )
    return result.scalars().first()


async def create_booking(booking: schemas_bdebooking.Booking, db: AsyncSession):
    # create a booking in the database from the schema schema_bdebooking.Booking
    db_booking = models_bdebooking.RoomBooking(
        booker=booking.booker,
        room=booking.room,
        start=booking.start,
        end=booking.end,
        reason=booking.reason,
        notes=booking.notes,
        key=booking.key,
        pending=booking.pending,
        multiple_days=booking.multiple_days,
        recurring=booking.recurring,
    )
    db.add(db_booking)
    try:
        await db.commit()
        return db_booking
    except IntegrityError:
        await db.rollback()
        raise ValueError("This booking request is already done")


async def delete_booking(db: AsyncSession, booking_id: int):
    await db.execute(
        delete(models_bdebooking.RoomBooking).where(
            models_bdebooking.RoomBooking.id == booking_id
        )
    )
    await db.commit()


async def confirm_booking(db: AsyncSession, booking_id: int):
    await db.execute(
        delete(models_bdebooking.RoomBooking).where(
            models_bdebooking.RoomBooking.id == booking_id
        )
    )
    await db.commit()


async def modify_booking(db: AsyncSession, booking_id: int):
    await db.execute(
        delete(models_bdebooking.RoomBooking).where(
            models_bdebooking.RoomBooking.id == booking_id
        )
    )
    await db.commit()
