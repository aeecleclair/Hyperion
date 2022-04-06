from turtle import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import models_bdebooking
from ..schemas import schemas_bdebooking
from sqlalchemy import select, delete


async def get_booking(db: AsyncSession):
    """Get all the bookings in the database from the schema schema_bdebooking.Booking"""

    result = await db.execute(select(models_bdebooking.RoomBooking))
    return result.scalars().all()


async def get_booking_confirmed(db: AsyncSession):
    """Get all the confirmed bookings in the database from the schema schema_bdebooking.Booking"""

    result = await db.execute(
        select(models_bdebooking.RoomBooking).where(
            not models_bdebooking.RoomBooking.pending
        )
    )
    return result.scalars().all()


async def get_booking_unconfirmed(db: AsyncSession):
    """Get all the unconfirmed bookings in the database from the schema schema_bdebooking.Booking"""

    result = await db.execute(
        select(models_bdebooking.RoomBooking).where(
            models_bdebooking.RoomBooking.pending
        )
    )
    return result.scalars().all()


async def get_booking_by_id(db: AsyncSession, booking_id: int):
    """Get a booking in the database from the schema schema_bdebooking.Booking"""

    result = (
        (
            await db.execute(
                select(models_bdebooking.RoomBooking).where(
                    models_bdebooking.RoomBooking.id == booking_id
                )
            )
        )
        .scalars()
        .first()
    )
    if result is None:
        raise ValueError("This booking does not exist")
    return result


async def create_booking(booking: schemas_bdebooking.Booking, db: AsyncSession):
    """Create a booking in the database from the schema schema_bdebooking.Booking"""

    db_booking = models_bdebooking.RoomBooking(
        booker=booking.booker,
        room=booking.room,
        start=booking.start,
        end=booking.end,
        reason=booking.reason,
        notes=booking.notes,
        key=booking.key,
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
    """Delete a booking in the database from the schema schema_bdebooking.Booking"""

    await db.execute(
        delete(models_bdebooking.RoomBooking).where(
            models_bdebooking.RoomBooking.id == booking_id
        )
    )
    await db.commit()


async def confirm_booking(db: AsyncSession, booking_id: int):
    """Modify the field pending of a booking in the database from the schema schema_bdebooking.Booking"""
    # Modify the field pending of a booking in the database from the schema schema_bdebooking.Booking
    await db.execute(
        update(models_bdebooking.Booking)
        .values(pending=False)
        .where(models_bdebooking.Booking.id == booking_id)
    )
    await db.commit()


async def modify_booking(
    booking_modify: schemas_bdebooking.Booking, db: AsyncSession, booking_id: int
):
    """Modify the booking in the database from the schema schema_bdebooking.Booking"""

    await db.execute(
        update(models_bdebooking.Booking)
        .where(models_bdebooking.Booking.id == booking_id)
        .values(
            booker=booking_modify.booker,
            room=booking_modify.room,
            start=booking_modify.start,
            end=booking_modify.end,
            reason=booking_modify.reason,
            notes=booking_modify.notes,
            key=booking_modify.key,
            multiple_days=booking_modify.multiple_days,
            recurring=booking_modify.recurring,
        )
    )
    await db.commit()
