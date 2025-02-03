from collections.abc import Sequence

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core import models_core
from app.modules.booking import models_booking, schemas_booking
from app.modules.booking.types_booking import Decision


async def get_managers(
    db: AsyncSession,
) -> Sequence[models_booking.Manager]:
    result = await db.execute(select(models_booking.Manager))
    return result.scalars().all()


async def create_manager(
    db: AsyncSession,
    manager: models_booking.Manager,
) -> models_booking.Manager:
    db.add(manager)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise
    else:
        return manager


async def update_manager(
    manager_id: str,
    manager_update: schemas_booking.ManagerUpdate,
    db: AsyncSession,
):
    await db.execute(
        update(models_booking.Manager)
        .where(models_booking.Manager.id == manager_id)
        .values(**manager_update.model_dump(exclude_none=True)),
    )
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def delete_manager(
    manager_id: str,
    db: AsyncSession,
):
    await db.execute(
        delete(models_booking.Manager).where(models_booking.Manager.id == manager_id),
    )
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def get_manager_by_id(
    manager_id: str,
    db: AsyncSession,
) -> models_booking.Manager:
    result = await db.execute(
        select(models_booking.Manager)
        .where(models_booking.Manager.id == manager_id)
        .options(selectinload(models_booking.Manager.rooms)),
    )
    return result.scalars().one()


async def get_user_managers(
    user: models_core.CoreUser,
    db: AsyncSession,
) -> Sequence[models_booking.Manager]:
    groups_id = [group.id for group in user.groups]
    result = await db.execute(
        select(models_booking.Manager).where(
            models_booking.Manager.group_id.in_(groups_id),
        ),
    )
    return result.scalars().all()


async def get_bookings(
    db: AsyncSession,
) -> Sequence[models_booking.Booking]:
    result = await db.execute(
        select(models_booking.Booking).options(
            selectinload(models_booking.Booking.applicant),
        ),
    )
    return result.scalars().all()


async def get_confirmed_bookings(
    db: AsyncSession,
) -> Sequence[schemas_booking.BookingReturnApplicant]:
    result = (
        (
            await db.execute(
                select(models_booking.Booking)
                .where(models_booking.Booking.decision == Decision.approved)
                .options(selectinload(models_booking.Booking.applicant)),
            )
        )
        .scalars()
        .all()
    )
    return [
        schemas_booking.BookingReturnApplicant(
            reason=booking.reason,
            start=booking.start,
            end=booking.end,
            creation=booking.creation,
            note=booking.note,
            room_id=booking.room_id,
            key=booking.key,
            recurrence_rule=booking.recurrence_rule,
            entity=booking.entity,
            decision=Decision.approved,
            applicant=schemas_booking.Applicant(
                id=booking.applicant.id,
                firstname=booking.applicant.firstname,
                name=booking.applicant.name,
                nickname=booking.applicant.nickname,
                email=booking.applicant.email,
                promo=booking.applicant.promo,
                account_type=booking.applicant.account_type,
                school_id=booking.applicant.school_id,
                phone=booking.applicant.phone,
            ),
            applicant_id=booking.applicant_id,
            id=booking.id,
            room=schemas_booking.RoomComplete(
                id=booking.room.id,
                name=booking.room.name,
                manager_id=booking.room.manager_id,
            ),
        )
        for booking in result
    ]


async def get_applicant_bookings(
    db: AsyncSession,
    applicant_id: str,
) -> Sequence[models_booking.Booking]:
    result = await db.execute(
        select(models_booking.Booking)
        .where(models_booking.Booking.applicant_id == applicant_id)
        .options(selectinload(models_booking.Booking.applicant)),
    )
    return result.scalars().all()


async def get_booking_by_id(
    db: AsyncSession,
    booking_id: str,
) -> models_booking.Booking:
    result = await db.execute(
        select(models_booking.Booking)
        .where(models_booking.Booking.id == booking_id)
        .options(selectinload(models_booking.Booking.applicant)),
    )
    return result.scalars().one()


async def create_booking(db: AsyncSession, booking: schemas_booking.BookingComplete):
    db_booking = models_booking.Booking(**booking.model_dump())
    db.add(db_booking)
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def edit_booking(
    db: AsyncSession,
    booking_id: str,
    booking: schemas_booking.BookingEdit,
):
    await db.execute(
        update(models_booking.Booking)
        .where(models_booking.Booking.id == booking_id)
        .values(**booking.model_dump(exclude_none=True)),
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError()


async def confirm_booking(db: AsyncSession, decision: Decision, booking_id: str):
    await db.execute(
        update(models_booking.Booking)
        .where(models_booking.Booking.id == booking_id)
        .values(decision=decision),
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError()


async def delete_booking(db: AsyncSession, booking_id: str):
    await db.execute(
        delete(models_booking.Booking).where(models_booking.Booking.id == booking_id),
    )
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def get_room_by_id(db: AsyncSession, room_id: str) -> models_booking.Room:
    result = await db.execute(
        select(models_booking.Room)
        .where(models_booking.Room.id == room_id)
        .options(selectinload(models_booking.Room.bookings)),
    )
    return result.scalars().one()


async def get_rooms(db: AsyncSession) -> Sequence[models_booking.Room]:
    result = await db.execute(select(models_booking.Room))
    return result.scalars().all()


async def create_room(db: AsyncSession, room: models_booking.Room):
    db.add(room)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise
    else:
        return room


async def edit_room(db: AsyncSession, room_id: str, room: schemas_booking.RoomBase):
    await db.execute(
        update(models_booking.Room)
        .where(models_booking.Room.id == room_id)
        .values(name=room.name, manager_id=room.manager_id),
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError()


async def delete_room(db: AsyncSession, room_id: str):
    room = await get_room_by_id(db=db, room_id=room_id)
    for booking in room.bookings:
        await delete_booking(db=db, booking_id=booking.id)
    await db.execute(
        delete(models_booking.Room).where(models_booking.Room.id == room_id),
    )
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)
