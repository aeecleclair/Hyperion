from sqlalchemy import delete, select, update, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import models_thread
from app.schemas import schemas_threads
from app.utils.types.thread_permissions_types import ThreadPermission


async def get_threads(db: AsyncSession) -> list[models_thread.Thread]:
    result = await db.execute(select(models_thread.Thread))
    return result.scalars().all()


async def create_thread(
    db: AsyncSession, thread_params: schemas_threads.ThreadBase
) -> models_thread.Thread:
    thread = models_thread.Thread(
        name=thread_params.name,
        is_public=thread_params.is_public,
        image=thread_params.image,
    )
    if (
        await db.execute(
            select(models_thread.Thread).where(
                func.lower(models_thread.Thread.name) == thread_params.name.lower()
            )
        )
    ).first() is not None:
        raise ValueError("A thread with a similar name already exists !")
    db.add(thread)
    try:
        await db.commit()
        return thread
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def get_public_threads(db: AsyncSession) -> set[models_thread.Thread]:
    result = await db.execute(select(models_thread.Thread).where(models_thread.Thread.is_public))
    return set(result.scalars().all())


async def get_user_threads(
    db: AsyncSession, user_id: str
) -> set[models_thread.Thread]:
    result = await db.execute(
        select(models_thread.ThreadMember)
        .where(models_thread.ThreadMember.user_id == user_id)
        .options(selectinload(models_thread.ThreadMember.thread))
    )
    return set(i.thread for i in result.scalars().all())


async def get_thread_by_id(
    db: AsyncSession, thread_id: str
) -> models_thread.Thread | None:
    result = (
        (
            await db.execute(
                select(models_thread.Thread).where(models_thread.Thread.id == thread_id)
            )
        )
        .scalars()
        .first()
    )
    return result


async def add_user_to_thread(
    db: AsyncSession, thread_id: str, member_params: schemas_threads.UserWithPermissions
) -> models_thread.ThreadMember:
    member = models_thread.ThreadMember(
        thread_id=thread_id,
        user_id=member_params.user_id,
        permissions=member_params.permissions,
    )
    db.add(member)
    try:
        await db.commit()
        return member
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def add_users_to_thread(
    db: AsyncSession,
    thread_id: str,
    members_params: list[schemas_threads.UserWithPermissions],
) -> list[models_thread.ThreadMember]:
    members = [
        models_thread.ThreadMember(
            thread_id=thread_id, user_id=i.user_id, permissions=i.permissions
        )
        for i in members_params
    ]
    db.add_all(members)
    try:
        await db.commit()
        return members
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def remove_user_from_thread(
    db: AsyncSession, thread_id: str, user_id: str
) -> None:
    await db.execute(
        delete(models_thread.ThreadMember).where(
            (models_thread.ThreadMember.thread_id == thread_id)
            & (models_thread.ThreadMember.user_id == user_id)
        )
    )
    await db.commit()


async def remove_users_from_thread(
    db: AsyncSession, thread_id: str, user_ids: list[str]
) -> None:
    await db.execute(
        delete(models_thread.ThreadMember).where(
            (models_thread.ThreadMember.thread_id == thread_id)
            & (models_thread.ThreadMember.user_id in user_ids)
        )
    )
    await db.commit()


async def get_thread_member_from_base(
    db: AsyncSession, member_base: schemas_threads.ThreadMemberBase
) -> models_thread.ThreadMember | None:
    result = (
        (
            await db.execute(
                select(models_thread.ThreadMember).where(
                    (models_thread.ThreadMember.thread_id == member_base.thread_id)
                    & (models_thread.ThreadMember.user_id == member_base.user_id)
                )
            )
        )
        .scalars()
        .first()
    )
    return result


async def create_message(
    db: AsyncSession,
    message: schemas_threads.ThreadMessageBase,
    author: schemas_threads.ThreadMemberBase,
) -> models_thread.ThreadMessage:
    member = await get_thread_member_from_base(db, author)
    if member is None:
        raise ValueError("Member does not exist")
    if not member.has_permission(ThreadPermission.SEND_MESSAGES):
        raise ValueError("Missing permissions")
    created_message = models_thread.ThreadMessage(
        thread_id=author.thread_id,
        author_id=author.user_id,
        content=message.content,
        image=message.image,
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
