from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import models_thread
from app.schemas import schemas_threads


async def get_threads(db: AsyncSession) -> list[models_thread.Thread]:
    result = await db.execute(select(models_thread.Thread))
    return result.scalars().all()


async def get_user_threads(
    db: AsyncSession, core_user_id: str
) -> list[models_thread.Thread]:
    result = await db.execute(
        select(models_thread.Thread)
        .join(models_thread.ThreadMember)
        .where(
            models_thread.Thread.is_public
            or models_thread.ThreadMember.core_user_id == core_user_id
        )
    )
    return result.scalars().all()


async def get_thread_by_id(db: AsyncSession, thread_id: str) -> models_thread.Thread:
    result = (
        (
            await db.execute(
                select(models_thread.Thread).where(models_thread.Thread.id == thread_id)
            )
        )
        .scalars()
        .first()
    )
    if result is None:
        raise ValueError("Thread not found")
    return result


async def add_user_to_thread(
    db: AsyncSession, thread_id: str, core_user_id: str
) -> models_thread.ThreadMember:
    member = models_thread.ThreadMember(thread_id=thread_id, core_user_id=core_user_id)
    db.add(member)
    try:
        await db.commit()
        return member
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def add_users_to_thread(
    db: AsyncSession, thread_id: str, core_user_ids: list[str]
) -> list[models_thread.ThreadMember]:
    members = [
        models_thread.ThreadMember(thread_id=thread_id, core_user_id=i)
        for i in core_user_ids
    ]
    db.add_all(members)
    try:
        await db.commit()
        return members
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def remove_user_from_thread(
    db: AsyncSession, thread_id: str, core_user_id: str
) -> None:
    await db.execute(
        delete(models_thread.ThreadMember).where(
            models_thread.ThreadMember.thread_id == thread_id
            and models_thread.ThreadMember.core_user_id == core_user_id
        )
    )
    await db.commit()


async def remove_users_from_thread(
    db: AsyncSession, thread_id: str, core_user_ids: list[str]
) -> None:
    await db.execute(
        delete(models_thread.ThreadMember).where(
            models_thread.ThreadMember.thread_id == thread_id
            and models_thread.ThreadMember.core_user_id in core_user_ids
        )
    )
    await db.commit()


async def get_thread_member_from_base(
    db: AsyncSession, member_base: schemas_threads.ThreadMemberBase
) -> models_thread.ThreadMember:
    result = (
        (
            await db.execute(
                select(models_thread.ThreadMember).where(
                    models_thread.ThreadMember.thread_id == member_base.thread_id
                    and models_thread.ThreadMember.core_user_id
                    == member_base.core_user_id
                )
            )
        )
        .scalars()
        .first()
    )
    if result is None:
        raise ValueError("This member is not from that thread")
    return result


async def create_message(
    db: AsyncSession,
    message: schemas_threads.ThreadMessageBase,
    author: schemas_threads.ThreadMemberBase,
) -> models_thread.ThreadMessage:
    member = await get_thread_member_from_base(db, author)
    created_message = models_thread.ThreadMessage(
        thread_member_id=member.id, content=message.content, image=message.image
    )
    db.add(message)
    try:
        await db.commit()
        return created_message
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def edit_message(
    db: AsyncSession,
    message_id: str,
    message_content: schemas_threads.ThreadMessageBase,
) -> None:
    await db.execute(
        update(models_thread.ThreadMessage)
        .where(models_thread.ThreadMessage.id == message_id)
        .values(**message_content.dict())
    )
    await db.commit()
