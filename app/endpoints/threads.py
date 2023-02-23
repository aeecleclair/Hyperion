from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_threads
from app.dependencies import get_db, is_user_a_member
from app.models import models_core
from app.schemas import schemas_threads
from app.utils.types.tags import Tags
from app.utils.types.thread_permissions_types import ThreadPermission

router = APIRouter()


@router.get(
    "/threads",
    response_model=list[schemas_threads.ThreadBase],
    status_code=200,
    tags=[Tags.threads],
)
async def get_user_threads(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    return list((await cruds_threads.get_user_threads(db, user.id)).union(await cruds_threads.get_public_threads(db)))


@router.post(
    "/threads",
    status_code=204,
    tags=[Tags.threads],
)
async def create_thread(
    thread_params: schemas_threads.ThreadBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    try:
        thread = await cruds_threads.create_thread(db, thread_params)
        await cruds_threads.add_user_to_thread(
            db,
            thread.id,
            schemas_threads.UserWithPermissions(
                user_id=user.id, permissions=ThreadPermission.ADMINISTRATOR
            ),
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get(
    "/threads/{thread_id}/users",
    response_model=list[schemas_threads.ThreadMember],
    status_code=200,
    tags=[Tags.threads],
)
async def get_users_in_thread(
    thread_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    thread = await cruds_threads.get_thread_by_id(db, thread_id)
    if thread is None:
        raise HTTPException(404, "Thread not found")
    return thread.members


@router.post(
    "/threads/{thread_id}/users",
    status_code=204,
    tags=[Tags.threads],
)
async def add_user_to_thread(
    thread_id: str,
    member_params: schemas_threads.UserWithPermissions,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    adder = await cruds_threads.get_thread_member_from_base(
        db, schemas_threads.ThreadMemberBase(thread_id=thread_id, user_id=user.id)
    )
    if adder is None:
        raise HTTPException(403, "The thread does not exist or you are not part of it")
    if not adder.has_permission(ThreadPermission.ADD_MEMBERS):
        raise HTTPException(403, "Insufficient permissions")
    await cruds_threads.add_user_to_thread(
        db,
        thread_id,
        schemas_threads.UserWithPermissions(
            user_id=member_params.user_id,
            permissions=member_params.permissions,
        ),
    )


@router.get(
    "/threads/{thread_id}/messages",
    response_model=list[schemas_threads.ThreadMessage],
    status_code=200,
    tags=[Tags.threads],
)
async def get_thread_messages(
    thread_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    thread_member = await cruds_threads.get_thread_member_from_base(
        db, schemas_threads.ThreadMemberBase(thread_id=thread_id, user_id=user.id)
    )
    if thread_member is None:
        raise HTTPException(404, "This member is not from that thread")
    # TODO : uncomment the line
    # return thread_member.thread.messages


@router.post(
    "/threads/{thread_id}/messages",
    status_code=204,
    tags=[Tags.threads],
)
async def send_message(
    thread_id: str,
    message: schemas_threads.ThreadMessageBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    await cruds_threads.create_message(
        db,
        message,
        schemas_threads.ThreadMemberBase(thread_id=thread_id, user_id=user.id),
    )
