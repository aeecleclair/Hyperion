import logging
import uuid

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core, schemas_core
from app.core.groups.groups_type import GroupType
from app.core.module import Module
from app.core.users import cruds_users
from app.dependencies import (
    get_db,
    is_user_a_member_of,
    is_user_an_ecl_member,
)
from app.modules.greencode import cruds_greencode, models_greencode, schemas_greencode

module = Module(
    root="greencode",
    tag="GreenCode",
    default_allowed_groups_ids=[GroupType.student, GroupType.staff],
)

hyperion_error_logger = logging.getLogger("hyperion.error")


@module.router.get(
    "/greencode/items",
    response_model=list[schemas_greencode.ItemAdmin],
    status_code=200,
)
async def get_items(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.greencode)),
):
    """
    Get all Item with all the users that discovered each Item.

    **The user must be from greencode group to use this endpoint**
    """

    items = await cruds_greencode.get_items(db=db)
    result: list[schemas_greencode.ItemAdmin] = []
    for item in items:
        users = [
            schemas_core.CoreUserSimple(**membership.user.__dict__)
            for membership in item.memberships
        ]
        result.append(schemas_greencode.ItemAdmin(users=users, **item.__dict__))
    return result


@module.router.get(
    "/greencode/items/me",
    response_model=list[schemas_greencode.ItemComplete],
    status_code=200,
)
async def get_user_items(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_an_ecl_member),
):
    """
    Get current user's discovered Items.
    """
    return await cruds_greencode.get_user_items(user_id=user.id, db=db)


@module.router.get(
    "/greencode/{qr_code_content}",
    response_model=schemas_greencode.ItemComplete,
    status_code=200,
)
async def get_item_by_qr_code(
    qr_code_content: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_an_ecl_member),
):
    """
    Get Item by Qr code content.
    """

    item = await cruds_greencode.get_item_by_qr_code_content(
        qr_code_content=qr_code_content,
        db=db,
    )
    if item is None:
        raise HTTPException(
            status_code=404,
            detail="No Item match with the qr_code_content",
        )
    return item


@module.router.post(
    "/greencode/item",
    response_model=schemas_greencode.ItemComplete,
    status_code=201,
)
async def create_item(
    item: schemas_greencode.ItemBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.greencode)),
):
    """
    Create a new Item.

    **The user must be from greencode group to use this endpoint**
    """

    db_item = models_greencode.GreenCodeItem(
        id=uuid.uuid4(),
        **item.model_dump(),
    )

    try:
        return await cruds_greencode.create_item(db=db, item=db_item)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@module.router.delete(
    "/greencode/item/{item_id}",
    status_code=204,
)
async def delete_item(
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.greencode)),
):
    """
    Delete an Item by item_id.

    **This endpoint is only usable by greencode group**
    """

    try:
        await cruds_greencode.delete_item(item_id=item_id, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@module.router.patch(
    "/greencode/item/{item_id}",
    status_code=204,
)
async def update_item(
    item_id: uuid.UUID,
    item_update: schemas_greencode.ItemUpdate,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.greencode)),
):
    """
    Update an Item by item_id.

    **This endpoint is only usable by greencode group**
    """
    item = await cruds_greencode.get_item_by_id(
        item_id=item_id,
        db=db,
    )
    if not item:
        raise HTTPException(
            status_code=404,
            detail="Invalid item_id",
        )

    try:
        await cruds_greencode.update_item(
            item_id=item_id,
            item_update=item_update,
            db=db,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@module.router.post(
    "/greencode/item/{item_id}/me",
    status_code=204,
)
async def create_current_user_membership(
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_an_ecl_member),
):
    """
    Create a new membership for item_id and current user.

    """

    try:
        return await cruds_greencode.create_membership(
            db=db,
            item_id=item_id,
            user_id=user.id,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@module.router.delete(
    "/greencode/item/{item_id}/me",
    status_code=204,
)
async def delete_current_user_membership(
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_an_ecl_member),
):
    """
    Delete membership for item_id and current user.

    """

    try:
        await cruds_greencode.delete_membership(item_id=item_id, user_id=user.id, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@module.router.post(
    "/greencode/item/{item_id}/{user_id}",
    status_code=204,
)
async def create_membership(
    item_id: uuid.UUID,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.greencode)),
):
    """
    Create a new membership for item_id and user_id.

    **The user must be from greencode group to use this endpoint**
    """

    try:
        return await cruds_greencode.create_membership(
            db=db,
            item_id=item_id,
            user_id=user_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@module.router.delete(
    "/greencode/item/{item_id}/{user_id}",
    status_code=204,
)
async def delete_membership(
    item_id: uuid.UUID,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.greencode)),
):
    """
    Delete membership for item_id and user_id.

    **The user must be from greencode group to use this endpoint**
    """

    try:
        await cruds_greencode.delete_membership(item_id=item_id, user_id=user_id, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@module.router.get(
    "/greencode/completion/all",
    response_model=list[schemas_greencode.Completion],
    status_code=200,
)
async def get_completions(
    db: AsyncSession = Depends(get_db),
    current_user: models_core.CoreUser = Depends(
        is_user_a_member_of(GroupType.greencode),
    ),
):
    """
    Get all users completions.

    **This endpoint is only usable by greencode group**
    """

    total_count = await cruds_greencode.get_items_count(db=db)
    greencode_users = await cruds_greencode.get_greencode_users(db=db)

    completions = [
        schemas_greencode.Completion(
            user=schemas_greencode.CoreUserSimple(**user.__dict__),
            discovered_count=await cruds_greencode.get_items_count_for_user(
                user_id=user.id,
                db=db,
            ),
            total_count=total_count,
        )
        for user in greencode_users
    ]
    return completions


@module.router.get(
    "/greencode/completion/me",
    response_model=schemas_greencode.Completion,
    status_code=200,
)
async def get_current_user_completion(
    db: AsyncSession = Depends(get_db),
    current_user: models_core.CoreUser = Depends(
        is_user_an_ecl_member,
    ),
):
    """
    Get current user completion

    """

    total_count = await cruds_greencode.get_items_count(db=db)
    count = await cruds_greencode.get_items_count_for_user(
        user_id=current_user.id,
        db=db,
    )

    completion = schemas_greencode.Completion(
        user=schemas_greencode.CoreUserSimple(**current_user.__dict__),
        discovered_count=count,
        total_count=total_count,
    )
    return completion


@module.router.get(
    "/greencode/completion/{user_id}",
    response_model=schemas_greencode.Completion,
    status_code=200,
)
async def get_user_completion(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: models_core.CoreUser = Depends(
        is_user_a_member_of(GroupType.greencode),
    ),
):
    """
    Get user completion by user_id.

    **This endpoint is only usable by greencode group**
    """

    user = await cruds_users.get_user_by_id(user_id=user_id, db=db)
    if user is None:
        raise HTTPException(
            status_code=404,
            detail="Invalid user_id",
        )

    total_count = await cruds_greencode.get_items_count(db=db)
    count = await cruds_greencode.get_items_count_for_user(
        user_id=user_id,
        db=db,
    )

    completion = schemas_greencode.Completion(
        user=schemas_greencode.CoreUserSimple(**user.__dict__),
        discovered_count=count,
        total_count=total_count,
    )
    return completion
