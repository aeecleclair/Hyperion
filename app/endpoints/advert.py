import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pytz import timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.cruds import cruds_advert
from app.dependencies import (
    get_db,
    get_request_id,
    get_settings,
    is_user_a_member,
    is_user_a_member_of,
)
from app.models import models_advert, models_core
from app.schemas import schemas_advert
from app.utils.tools import (
    get_file_from_data,
    is_group_id_valid,
    is_user_member_of_an_allowed_group,
    save_file_as_data,
)
from app.utils.types import standard_responses
from app.utils.types.groups_type import GroupType
from app.utils.types.tags import Tags

router = APIRouter()


@router.get(
    "/advert/advertisers",
    response_model=list[schemas_advert.AdvertiserComplete],
    status_code=200,
    tags=[Tags.advert],
)
async def read_advertisers(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Get existing advertisers.

    **This endpoint is only usable by administrators**
    """

    return await cruds_advert.get_advertisers(db=db)


@router.post(
    "/advert/advertisers",
    response_model=schemas_advert.AdvertiserComplete,
    status_code=201,
    tags=[Tags.advert],
)
async def create_advertiser(
    advertiser: schemas_advert.AdvertiserBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
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

    try:
        advertiser_db = schemas_advert.AdvertiserComplete(
            id=str(uuid.uuid4()),
            name=advertiser.name,
            group_manager_id=advertiser.group_manager_id,
        )

        return await cruds_advert.create_advertiser(advertiser=advertiser_db, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.delete(
    "/advert/advertisers/{advertiser_id}",
    status_code=204,
    tags=[Tags.advert],
)
async def delete_advertiser(
    advertiser_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Delete an advertiser. All adverts associated with the advertiser will also be deleted from the database.

    **This endpoint is only usable by administrators**
    """
    advertiser = await cruds_advert.get_advertiser_by_id(
        advertiser_id=advertiser_id, db=db
    )
    if advertiser is None:
        raise HTTPException(
            status_code=404,
            detail="Invalid advertiser_id",
        )

    for advert in advertiser.adverts:
        await cruds_advert.delete_advert(advert_id=advert.id, db=db)

    await cruds_advert.delete_advertiser(advertiser_id=advertiser_id, db=db)


@router.patch(
    "/advert/advertisers/{advertiser_id}",
    status_code=204,
    tags=[Tags.advert],
)
async def update_advertiser(
    advertiser_id: str,
    advertiser_update: schemas_advert.AdvertiserUpdate,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Update an advertiser

    **This endpoint is only usable by administrators**
    """
    advertiser = await cruds_advert.get_advertiser_by_id(
        advertiser_id=advertiser_id, db=db
    )
    if not advertiser:
        raise HTTPException(
            status_code=404,
            detail="Invalid advertiser_id",
        )

    await cruds_advert.update_advertiser(
        advertiser_id=advertiser_id, advertiser_update=advertiser_update, db=db
    )


@router.get(
    "/advert/me/advertisers",
    response_model=list[schemas_advert.AdvertiserComplete],
    status_code=200,
    tags=[Tags.advert],
)
async def get_current_user_advertisers(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Return all advertisers the current user can manage.

    **The user must be authenticated to use this endpoint**
    """

    user_advertisers: list[models_advert.Advertiser] = []

    existing_advertisers: list[
        models_advert.Advertiser
    ] = await cruds_advert.get_advertisers(db=db)

    for advertiser in existing_advertisers:
        if is_user_member_of_an_allowed_group(
            allowed_groups=[advertiser.group_manager_id],
            user=user,
        ):
            user_advertisers.append(advertiser)

    return user_advertisers


@router.get(
    "/advert/adverts",
    response_model=list[schemas_advert.AdvertComplete],
    status_code=200,
    tags=[Tags.advert],
)
async def read_adverts(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get existing adverts

    **The user must be authenticated to use this endpoint**
    """

    return await cruds_advert.get_adverts(db=db)


@router.get(
    "/advert/adverts/search",
    response_model=list[schemas_advert.AdvertComplete],
    status_code=200,
    tags=[Tags.advert],
)
async def search_adverts(
    advertisers: list[str] = Query(default=[]),
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Search adverts by advertisers

    **The user must be authenticated to use this endpoint**
    """

    return await cruds_advert.get_adverts_by_advertisers(advertisers=advertisers, db=db)


@router.get(
    "/advert/adverts/{advert_id}",
    response_model=schemas_advert.AdvertComplete,
    status_code=200,
    tags=[Tags.advert],
)
async def read_advert(
    advert_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get an advert

    **The user must be authenticated to use this endpoint**
    """

    return await cruds_advert.get_advert_by_id(advert_id=advert_id, db=db)


@router.post(
    "/advert/adverts",
    response_model=schemas_advert.AdvertComplete,
    status_code=201,
    tags=[Tags.advert],
)
async def create_advert(
    advert: schemas_advert.AdvertBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
    settings: Settings = Depends(get_settings),
):
    """
    Create a new advert

    **The user must be a member of the advertiser group_manager to use this endpoint**
    """
    advertiser = await cruds_advert.get_advertiser_by_id(
        advertiser_id=advert.advertiser_id, db=db
    )
    if advertiser is None:
        raise HTTPException(
            status_code=404,
            detail="Invalid advertiser_id",
        )
    if not is_user_member_of_an_allowed_group(user, [advertiser.group_manager_id]):
        raise HTTPException(
            status_code=403,
            detail=f"Unauthorized to manage {advertiser.name} adverts",
        )

    db_advert = schemas_advert.AdvertComplete(
        id=str(uuid.uuid4()),
        date=datetime.now(timezone(settings.TIMEZONE)),
        **advert.dict(),
    )
    try:
        result = await cruds_advert.create_advert(advert=db_advert, db=db)
        return result
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.patch("/advert/adverts/{advert_id}", status_code=204, tags=[Tags.advert])
async def update_advert(
    advert_id: str,
    advert_update: schemas_advert.AdvertUpdate,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
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

    if not is_user_member_of_an_allowed_group(
        user, [advert.advertiser.group_manager_id]
    ):
        raise HTTPException(
            status_code=403,
            detail=f"Unauthorized to manage {advert.advertiser.name} adverts",
        )

    await cruds_advert.update_advert(
        advert_id=advert_id, advert_update=advert_update, db=db
    )


@router.delete("/advert/adverts/{advert_id}", status_code=204, tags=[Tags.advert])
async def delete_advert(
    advert_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
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

    if not is_user_member_of_an_allowed_group(
        user, [GroupType.admin, advert.advertiser.group_manager_id]
    ):
        raise HTTPException(
            status_code=403,
            detail=f"Unauthorized to manage {advert.advertiser.name} adverts",
        )

    await cruds_advert.delete_advert(advert_id=advert_id, db=db)


@router.get(
    "/advert/adverts/{advert_id}/image",
    response_class=FileResponse,
    status_code=200,
    tags=[Tags.advert],
)
async def read_advert_image(
    advert_id: str,
):
    """
    Get the image of an advert

    **The user must be authenticated to use this endpoint**
    """
    return get_file_from_data(
        default_asset="assets/images/default_advert.png",
        directory="adverts",
        filename=str(advert_id),
    )


@router.post(
    "/advert/adverts/{advert_id}/poster",
    response_model=standard_responses.Result,
    status_code=201,
    tags=[Tags.advert],
)
async def create_advert_image(
    advert_id: str,
    image: UploadFile = File(...),
    user: models_core.CoreUser = Depends(is_user_a_member),
    request_id: str = Depends(get_request_id),
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
        image=image,
        directory="adverts",
        filename=str(advert_id),
        request_id=request_id,
        max_file_size=4 * 1024 * 1024,
        accepted_content_types=["image/jpeg", "image/png", "image/webp"],
    )

    return standard_responses.Result(success=True)
