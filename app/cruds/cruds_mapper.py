from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import models_mapper
from app.schemas import schemas_mapper


async def get_members(
    db: AsyncSession,
) -> list[models_mapper.Member]:
    """Return all members"""
    result = await db.execute(
        select(models_mapper.Member))
    return result.scalars().all()

async def create_member(
    member: models_mapper.Member,
    db: AsyncSession,
) -> models_mapper.Member:
    db.add(member)
    try:
        await db.commit()
        return member
    except IntegrityError:
        await db.rollback()
        raise ValueError("Member already exists")
    
async def update_member(
    member_id: str,
    member_update: schemas_mapper.MemberUpdate,
    db: AsyncSession,
):
    await db.execute(
        update(models_mapper.Member)
        .where(models_mapper.Member.id == member_id)
        .values(**member_update.dict(exclude_unset=True))
    )
    await db.commit()

async def get_member_by_id(
    member_id: str,
    db: AsyncSession,
) -> models_mapper.Member | None:
    """Return the member with id"""

    result = await db.execute(
        select(models_mapper.Member)
        .where(models_mapper.Member.id == member_id)
    )
    return result.scalars().first()

async def delete_member_by_id(
    member_id: str,
    db: AsyncSession,
):
    await db.execute(
        delete(models_mapper.Member).where(models_mapper.Member.id == member_id)
    )
    await db.commit()

async def create_room(
    room: models_mapper.Room,
    db: AsyncSession,
) -> models_mapper.Room:
    db.add(room)
    try:
        await db.commit()
        return room
    except IntegrityError:
        await db.rollback()
        raise ValueError("Room already exists")
    
async def update_room(
    room_id: str,
    room_update: schemas_mapper.RoomUpdate,
    db: AsyncSession,
):
    await db.execute(
        update(models_mapper.Room)
        .where(models_mapper.Room.id == room_id)
        .values(**room_update.dict(exclude_unset=True))
    )
    await db.commit()

async def get_room_by_id(
    room_id: str,
    db: AsyncSession,
) -> models_mapper.Room | None:
    """Return the room with id"""

    result = await db.execute(
        select(models_mapper.Room)
        .where(models_mapper.Room.id == room_id)
    )
    return result.scalars().first()

async def delete_room_by_id(
    room_id: str,
    db: AsyncSession,
):
    await db.execute(
        delete(models_mapper.Room).where(models_mapper.Room.id == room_id)
    )
    await db.commit()

