import logging
import uuid
from datetime import UTC, datetime

from fastapi import Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.feed.utils_feed import create_feed_news
from app.core.groups.groups_type import AccountType, GroupType
from app.core.notification.schemas_notification import Message
from app.core.notification.utils_notification import get_topic_by_root_and_identifier
from app.core.users import models_users
from app.dependencies import (
    get_db,
    get_notification_manager,
    get_notification_tool,
    is_user,
    is_user_a_school_member,
    is_user_in,
)
from app.modules.advert import (
    cruds_advert,
    models_advert,
    schemas_advert,
)
from app.modules.advert.factory_advert import AdvertFactory
from app.types import standard_responses
from app.types.content_type import ContentType
from app.types.module import Module
from app.utils.communication.notifications import NotificationManager, NotificationTool
from app.utils.tools import (
    get_file_from_data,
    is_group_id_valid,
    is_user_member_of_any_group,
    save_file_as_data,
)

root = "advert"
module = Module(
    root=root,
    tag="Advert",
    default_allowed_account_types=[AccountType.student, AccountType.staff],
    factory=AdvertFactory(),
)

hyperion_error_logger = logging.getLogger("hyperion.error")


@module.router.get(
    "/advert/advertisers",
    response_model=list[schemas_advert.AdvertiserComplete],
    status_code=200,
)
async def read_advertisers(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_a_school_member),
):
    """
    Get existing advertisers.

    **The user must be authenticated to use this endpoint**
    """

    return await cruds_advert.get_advertisers(db=db)


@module.router.post(
    "/advert/advertisers",
    response_model=schemas_advert.AdvertiserComplete,
    status_code=201,
)
async def create_advertiser(
    advertiser: schemas_advert.AdvertiserBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
    notification_manager: NotificationManager = Depends(get_notification_manager),
):
    """
    Create a new advertiser.

    Each advertiser is associated with a `manager_group`. Users belonging to this group are able to manage the adverts related to the advertiser.

    **This endpoint is only usable by administrators**
    """

    # We need to check that advertiser.group_manager_id is a valid group
    if not await is_group_id_valid(advertiser.group_manager_id, db=db):
        raise HTTPException(
            status_code=400,
            detail="Invalid id, group_manager_id must be a valid group id",
        )

    db_advertiser = models_advert.Advertiser(
        id=str(uuid.uuid4()),
        name=advertiser.name,
        group_manager_id=advertiser.group_manager_id,
    )

    result = await cruds_advert.create_advertiser(db_advertiser=db_advertiser, db=db)

    await notification_manager.register_new_topic(
        topic_id=uuid.uuid4(),
        name=f"📣 Annonce - {db_advertiser.name}",
        module_root=root,
        topic_identifier=db_advertiser.id,
        restrict_to_group_id=None,
        restrict_to_members=True,
        db=db,
    )

    return result


@module.router.delete(
    "/advert/advertisers/{advertiser_id}",
    status_code=204,
)
async def delete_advertiser(
    advertiser_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Delete an advertiser. All adverts associated with the advertiser will also be deleted from the database.

    **This endpoint is only usable by administrators**
    """
    advertiser = await cruds_advert.get_advertiser_by_id(
        advertiser_id=advertiser_id,
        db=db,
    )
    if advertiser is None:
        raise HTTPException(
            status_code=404,
            detail="Invalid advertiser_id",
        )

    for advert in advertiser.adverts:
        await cruds_advert.delete_advert(advert_id=advert.id, db=db)

    await cruds_advert.delete_advertiser(advertiser_id=advertiser_id, db=db)


@module.router.patch(
    "/advert/advertisers/{advertiser_id}",
    status_code=204,
)
async def update_advertiser(
    advertiser_id: str,
    advertiser_update: schemas_advert.AdvertiserUpdate,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Update an advertiser

    **This endpoint is only usable by administrators**
    """
    advertiser = await cruds_advert.get_advertiser_by_id(
        advertiser_id=advertiser_id,
        db=db,
    )
    if not advertiser:
        raise HTTPException(
            status_code=404,
            detail="Invalid advertiser_id",
        )

    await cruds_advert.update_advertiser(
        advertiser_id=advertiser_id,
        advertiser_update=advertiser_update,
        db=db,
    )


@module.router.get(
    "/advert/me/advertisers",
    response_model=list[schemas_advert.AdvertiserComplete],
    status_code=200,
)
async def get_current_user_advertisers(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
):
    """
    Return all advertisers the current user can manage.

    **The user must be authenticated to use this endpoint**
    """
    user_groups_ids = [group.id for group in user.groups]

    return await cruds_advert.get_advertisers_by_groups(
        db=db,
        user_groups_ids=user_groups_ids,
    )


@module.router.get(
    "/advert/adverts",
    response_model=list[schemas_advert.AdvertReturnComplete],
    status_code=200,
)
async def read_adverts(
    advertisers: list[str] = Query(default=[]),
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_a_school_member),
):
    """
    Get existing adverts. If advertisers optional parameter is used, search adverts by advertisers

    **The user must be authenticated to use this endpoint**
    """

    if advertisers:
        return await cruds_advert.get_adverts_by_advertisers(
            advertisers=advertisers,
            db=db,
        )
    return await cruds_advert.get_adverts(db=db)


@module.router.get(
    "/advert/adverts/{advert_id}",
    response_model=schemas_advert.AdvertReturnComplete,
    status_code=200,
)
async def read_advert(
    advert_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_a_school_member),
):
    """
    Get an advert

    **The user must be authenticated to use this endpoint**
    """

    return await cruds_advert.get_advert_by_id(advert_id=advert_id, db=db)


@module.router.post(
    "/advert/adverts",
    response_model=schemas_advert.AdvertReturnComplete,
    status_code=201,
)
async def create_advert(
    advert: schemas_advert.AdvertBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_a_school_member),
    notification_tool: NotificationTool = Depends(get_notification_tool),
):
    """
    Create a new advert

    **The user must be a member of the advertiser group_manager to use this endpoint**
    """
    advertiser = await cruds_advert.get_advertiser_by_id(
        advertiser_id=advert.advertiser_id,
        db=db,
    )
    if advertiser is None:
        raise HTTPException(
            status_code=404,
            detail="Invalid advertiser_id",
        )

    if not is_user_member_of_any_group(user, [advertiser.group_manager_id]):
        raise HTTPException(
            status_code=403,
            detail=f"Unauthorized to manage {advertiser.name} adverts",
        )

    advert_id = uuid.uuid4()
    db_advert = models_advert.Advert(
        id=str(advert_id),
        date=datetime.now(UTC),
        advertiser=advertiser,
        advertiser_id=advert.advertiser_id,
        title=advert.title,
        content=advert.content,
        post_to_feed=advert.post_to_feed,
    )

    result = await cruds_advert.create_advert(db_advert=db_advert, db=db)

    message = Message(
        title=f"📣 Annonce - {result.title}",
        content=result.content,
        action_module=module.root,
    )

    topic = await get_topic_by_root_and_identifier(
        module_root=root,
        topic_identifier=advertiser.id,
        db=db,
    )
    if topic is not None:
        await notification_tool.send_notification_to_topic(
            topic_id=topic.id,
            message=message,
        )

    if advert.post_to_feed:
        await create_feed_news(
            title=advert.title,
            start=datetime.now(UTC),
            end=None,
            entity=advertiser.name,
            location=None,
            action_start=None,
            module=module.root,
            module_object_id=advert_id,
            image_directory="adverts",
            image_id=advert_id,
            require_feed_admin_approval=True,
            db=db,
            notification_tool=notification_tool,
        )

    return result


@module.router.patch(
    "/advert/adverts/{advert_id}",
    status_code=204,
)
async def update_advert(
    advert_id: str,
    advert_update: schemas_advert.AdvertUpdate,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_a_school_member),
):
    """
    Edit an advert

    **The user must be a member of the advertiser group_manager to use this endpoint**
    """
    advert = await cruds_advert.get_advert_by_id(advert_id=advert_id, db=db)
    if not advert:
        raise HTTPException(
            status_code=404,
            detail="Invalid advert_id",
        )

    if not is_user_member_of_any_group(
        user,
        [advert.advertiser.group_manager_id],
    ):
        raise HTTPException(
            status_code=403,
            detail=f"Unauthorized to manage {advert.advertiser.name} adverts",
        )

    await cruds_advert.update_advert(
        advert_id=advert_id,
        advert_update=advert_update,
        db=db,
    )


@module.router.delete(
    "/advert/adverts/{advert_id}",
    status_code=204,
)
async def delete_advert(
    advert_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_a_school_member),
):
    """
    Delete an advert

    **The user must be admin or a member of the advertiser group_manager to use this endpoint**
    """
    advert = await cruds_advert.get_advert_by_id(advert_id=advert_id, db=db)
    if not advert:
        raise HTTPException(
            status_code=404,
            detail="Invalid advert_id",
        )

    if not is_user_member_of_any_group(
        user,
        [GroupType.admin, advert.advertiser.group_manager_id],
    ):
        raise HTTPException(
            status_code=403,
            detail=f"Unauthorized to manage {advert.advertiser.name} adverts",
        )

    await cruds_advert.delete_advert(advert_id=advert_id, db=db)


@module.router.get(
    "/advert/adverts/{advert_id}/picture",
    response_class=FileResponse,
    status_code=200,
)
async def read_advert_image(
    advert_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_a_school_member),
):
    """
    Get the image of an advert

    **The user must be authenticated to use this endpoint**
    """
    advert = await cruds_advert.get_advert_by_id(db=db, advert_id=advert_id)
    if advert is None:
        raise HTTPException(
            status_code=404,
            detail="The advert does not exist",
        )

    return get_file_from_data(
        default_asset="assets/images/default_advert.png",
        directory="adverts",
        filename=str(advert_id),
    )


@module.router.post(
    "/advert/adverts/{advert_id}/picture",
    response_model=standard_responses.Result,
    status_code=201,
)
async def create_advert_image(
    advert_id: str,
    image: UploadFile = File(...),
    user: models_users.CoreUser = Depends(is_user_a_school_member),
    db: AsyncSession = Depends(get_db),
):
    """
    Add an image to an advert

    **The user must be authenticated to use this endpoint**
    """
    advert = await cruds_advert.get_advert_by_id(db=db, advert_id=advert_id)
    if advert is None:
        raise HTTPException(
            status_code=404,
            detail="The advert does not exist",
        )

    await save_file_as_data(
        upload_file=image,
        directory="adverts",
        filename=str(advert_id),
        max_file_size=4 * 1024 * 1024,
        accepted_content_types=[
            ContentType.jpg,
            ContentType.png,
            ContentType.webp,
        ],
    )

    return standard_responses.Result(success=True)
