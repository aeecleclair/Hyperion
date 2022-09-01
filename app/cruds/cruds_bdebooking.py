from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import models_bdebooking
from app.schemas import schemas_bdebooking
from app.utils.types.bdebooking_type import Decision


async def get_bookings(
    db: AsyncSession,
    # decision: Decision
) -> list[models_bdebooking.Booking]:
    result = await db.execute(
        select(models_bdebooking.Booking)
        # .where(
        #     models_bdebooking.Booking.decision == decision
        # )
    )
    return result.scalars().all()


async def get_applicant_bookings(
    db: AsyncSession, applicant_id: str
) -> list[models_bdebooking.Booking]:
    result = await db.execute(
        select(models_bdebooking.Booking).where(
            models_bdebooking.Booking.applicant_id == applicant_id
        )
    )
    return result.scalars().all()


async def get_booking_by_id(
    db: AsyncSession, booking_id: str
) -> models_bdebooking.Booking | None:
    result = await db.execute(
        select(models_bdebooking.Booking).where(
            models_bdebooking.Booking.id == booking_id
        )
    )
    return result.scalars().first()


async def create_booking(db: AsyncSession, booking: schemas_bdebooking.BookingComplete):
    db_booking = models_bdebooking.Booking(**booking.dict())
    db.add(db_booking)
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def edit_booking(db: AsyncSession, booking: schemas_bdebooking.BookingEdit):
    await db.execute(
        update(models_bdebooking.Booking)
        .where(models_bdebooking.Booking.id == booking.id)
        .values(**booking.dict(exclude_none=True))
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError()


async def confirm_booking(db: AsyncSession, decision: Decision, booking_id: str):
    await db.execute(
        update(models_bdebooking.Booking)
        .where(models_bdebooking.Booking.id == booking_id)
        .values(decision=decision)
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError()


async def delete_booking(db: AsyncSession, booking_id: str):
    await db.execute(
        delete(models_bdebooking.Booking).where(
            models_bdebooking.Booking.id == booking_id
        )
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError()


async def get_rooms(db: AsyncSession) -> list[models_bdebooking.Room]:
    result = await db.execute(select(models_bdebooking.Room))
    return result.scalars().all()


async def get_room_by_id(
    db: AsyncSession, room_id: str
) -> models_bdebooking.Room | None:
    result = await db.execute(
        select(models_bdebooking.Room).where(models_bdebooking.Room.id == room_id)
    )
    return result.scalars().first()


async def create_room(db: AsyncSession, room: schemas_bdebooking.RoomComplete):
    db.add(models_bdebooking.Room(**room.dict()))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError()


async def edit_room(db: AsyncSession, room: schemas_bdebooking.RoomComplete):
    await db.execute(
        update(models_bdebooking.Room)
        .where(models_bdebooking.Room.id == room.id)
        .values(name=room.name)
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError()


async def delete_room(db: AsyncSession, room_id: str):
    await db.execute(
        delete(models_bdebooking.Room).where(models_bdebooking.Room.id == room_id)
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError()
