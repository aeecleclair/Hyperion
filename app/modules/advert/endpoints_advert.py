import logging
import uuid
from datetime import UTC, datetime

from fastapi import Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.associations import cruds_associations
from app.core.feed.utils_feed import create_feed_news
from app.core.groups.groups_type import AccountType
from app.core.notification.schemas_notification import Message
from app.core.notification.utils_notification import get_topic_by_root_and_identifier
from app.core.permissions.type_permissions import ModulePermissions
from app.core.users import models_users
from app.dependencies import (
    get_db,
    get_notification_manager,
    get_notification_tool,
    is_user_allowed_to,
)
from app.modules.advert import (
    cruds_advert,
    models_advert,
    schemas_advert,
)
from app.modules.advert.factory_advert import AdvertFactory
from app.types.content_type import ContentType
from app.types.module import Module
from app.utils.communication.notifications import NotificationManager, NotificationTool
from app.utils.tools import (
    compress_and_save_image_file,
    get_file_from_data,
    is_user_member_of_an_association,
    is_user_member_of_an_association_id,
)

root = "advert"


class AdvertPermissions(ModulePermissions):
    access_adverts = "access_adverts"
    manage_advertisers = "manage_advertisers"


module = Module(
    root=root,
    tag="Advert",
    default_allowed_account_types=[AccountType.student, AccountType.staff],
    factory=AdvertFactory(),
    permissions=AdvertPermissions,
)

hyperion_error_logger = logging.getLogger("hyperion.error")


@module.router.get(
    "/advert/adverts",
    response_model=list[schemas_advert.AdvertComplete],
    status_code=200,
)
async def read_adverts(
    advertisers: list[uuid.UUID] = Query(default=[]),
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([AdvertPermissions.access_adverts]),
    ),
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
    response_model=schemas_advert.AdvertComplete,
    status_code=200,
)
async def read_advert(
    advert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([AdvertPermissions.access_adverts]),
    ),
):
    """
    Get an advert

    **The user must be authenticated to use this endpoint**
    """

    return await cruds_advert.get_advert_by_id(advert_id=advert_id, db=db)


@module.router.post(
    "/advert/adverts",
    response_model=schemas_advert.AdvertComplete,
    status_code=201,
)
async def create_advert(
    advert: schemas_advert.AdvertBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([AdvertPermissions.access_adverts]),
    ),
    notification_tool: NotificationTool = Depends(get_notification_tool),
    notification_manager: NotificationManager = Depends(get_notification_manager),
):
    """
    Create a new advert

    **The user must be a member of the advertiser group to use this endpoint**
    """
    association = await cruds_associations.get_association_by_id(
        db=db,
        association_id=advert.advertiser_id,
    )
    if not association:
        raise HTTPException(
            status_code=404,
            detail="Association not found",
        )
    if not is_user_member_of_an_association(
        user=user,
        association=association,
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to create adverts for this association",
        )

    advert_id = uuid.uuid4()
    db_advert = models_advert.Advert(
        id=advert_id,
        date=datetime.now(UTC),
        advertiser_id=advert.advertiser_id,
        title=advert.title,
        content=advert.content,
        post_to_feed=advert.post_to_feed,
        notification=advert.notification,
    )

    await cruds_advert.create_advert(db_advert=db_advert, db=db)

    if advert.notification:
        message = Message(
            title=f"📣 Annonce - {db_advert.title}",
            content=db_advert.content,
            action_module=module.root,
        )

        topic = await get_topic_by_root_and_identifier(
            module_root=root,
            topic_identifier=str(association.id),
            db=db,
        )
        if topic is None:
            # This means that the association never sent a news before, we have thus
            # never registred its topic
            topic_id = uuid.uuid4()
            await notification_manager.register_new_topic(
                topic_id=topic_id,
                name=f"📣 Annonce - {association.name}",
                module_root=root,
                topic_identifier=str(association.id),
                restrict_to_group_id=None,
                restrict_to_members=True,
                db=db,
            )
        else:
            topic_id = topic.id

        await notification_tool.send_notification_to_topic(
            topic_id=topic_id,
            message=message,
        )

    if advert.post_to_feed:
        await create_feed_news(
            title=advert.title,
            start=datetime.now(UTC),
            end=None,
            entity=association.name,
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

    return db_advert


@module.router.patch(
    "/advert/adverts/{advert_id}",
    status_code=204,
)
async def update_advert(
    advert_id: uuid.UUID,
    advert_update: schemas_advert.AdvertUpdate,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([AdvertPermissions.access_adverts]),
    ),
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

    if not await is_user_member_of_an_association_id(
        user=user,
        association_id=advert.advertiser_id,
        db=db,
    ):
        raise HTTPException(
            status_code=403,
            detail=f"Unauthorized to manage {advert.advertiser_id} adverts",
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
    advert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([AdvertPermissions.access_adverts]),
    ),
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

    if not await is_user_member_of_an_association_id(
        user=user,
        association_id=advert.advertiser_id,
        db=db,
    ):
        raise HTTPException(
            status_code=403,
            detail=f"Unauthorized to manage {advert.advertiser_id} adverts",
        )

    await cruds_advert.delete_advert(advert_id=advert_id, db=db)


@module.router.get(
    "/advert/adverts/{advert_id}/picture",
    response_class=FileResponse,
    status_code=200,
)
async def read_advert_image(
    advert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([AdvertPermissions.access_adverts]),
    ),
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
        directory="adverts",
        filename=advert_id,
        raise_http_exception=True,
    )


@module.router.post(
    "/advert/adverts/{advert_id}/picture",
    status_code=204,
)
async def create_advert_image(
    advert_id: uuid.UUID,
    image: UploadFile = File(...),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([AdvertPermissions.access_adverts]),
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Add an image to an advert

    **The user must be authenticated to use this endpoint**
    """
    advert = await cruds_advert.get_advert_by_id(advert_id=advert_id, db=db)
    if not advert:
        raise HTTPException(
            status_code=404,
            detail="Invalid advert_id",
        )

    if not await is_user_member_of_an_association_id(
        user=user,
        association_id=advert.advertiser_id,
        db=db,
    ):
        raise HTTPException(
            status_code=403,
            detail=f"Unauthorized to manage {advert.advertiser_id} adverts",
        )

    await compress_and_save_image_file(
        upload_file=image,
        directory="adverts",
        filename=advert_id,
        accepted_content_types=[
            ContentType.jpg,
            ContentType.png,
            ContentType.webp,
        ],
        max_file_size=1024 * 1024 * 5,  # 5 MB
        height=315,
        width=851,
        quality=85,
        fit=True,
    )
