import uuid
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.groups_type import AccountType, GroupType
from app.core.permissions.type_permissions import ModulePermissions
from app.core.users import models_users
from app.core.users.models_users import CoreUser
from app.dependencies import get_db, is_user, is_user_in
from app.modules.pmf import cruds_pmf, factory_pmf, schemas_pmf, types_pmf
from app.types.content_type import ContentType
from app.types.module import Module
from app.utils.tools import is_user_member_of_any_group
from app.utils.tools import (
    delete_file_from_data,
    get_file_from_data,
    save_file_as_data,
)
router = APIRouter(tags=["pmf"])


class PmfPermissions(ModulePermissions):
    access_pmf = "access_pmf"


module = Module(
    root="pmf",
    tag="Pmf",
    router=router,
    default_allowed_account_types=[
        AccountType.student,
        AccountType.staff,
        AccountType.former_student,
    ],
    factory=factory_pmf.PmfFactory,
    permissions=PmfPermissions,
)


@router.get(
    "/pmf/offers/{offer_id}",
    response_model=schemas_pmf.OfferComplete,
    status_code=200,
)
async def get_offer(
    offer_id: UUID,
    db: AsyncSession = Depends(get_db),
    # Allow only former students to access this endpoint
    # user: CoreUser = Depends(is_user(included_account_types=[AccountType.former_student])),
):
    offer = await cruds_pmf.get_offer_by_id(
        offer_id=offer_id,
        db=db,
    )

    if offer is None:
        raise HTTPException(status_code=404, detail="Offer not found")

    return offer


@router.get(
    "/pmf/users/{author_id}/offers",
    response_model=list[schemas_pmf.OfferSimple],
    status_code=200,
)
async def get_offers_by_author_id(
    author_id: str,
    db: AsyncSession = Depends(get_db),
    includedOfferTypes: list[types_pmf.OfferType] = Query(default=[]),
    includedTags: list[str] = Query(default=[]),
    includedLocationTypes: list[types_pmf.LocationType] = Query(default=[]),
    limit: int | None = Query(default=50, gt=0, le=50),
    offset: int | None = Query(default=0, ge=0),
    user: models_users.CoreUser = Depends(is_user()),
):
    show_hidden = True
    if author_id != user.id and not is_user_member_of_any_group(
        user,
        [
            GroupType.admin,
        ],
    ):
        show_hidden = False
    return await cruds_pmf.get_offers_by_author_id(
        author_id=author_id,
        db=db,
        included_offer_types=includedOfferTypes,
        included_tags=includedTags,
        included_location_types=includedLocationTypes,
        limit=limit,
        offset=offset,
        show_hidden=show_hidden,
    )


@router.get(
    "/pmf/me/offers",
    response_model=list[schemas_pmf.OfferSimple],
    status_code=200,
)
async def get_me_offers(
    db: AsyncSession = Depends(get_db),
    includedOfferTypes: list[types_pmf.OfferType] = Query(default=[]),
    includedTags: list[str] = Query(default=[]),
    includedLocationTypes: list[types_pmf.LocationType] = Query(default=[]),
    limit: int | None = Query(default=50, gt=0, le=50),
    offset: int | None = Query(default=0, ge=0),
    user: models_users.CoreUser = Depends(is_user()),
):
    return await cruds_pmf.get_offers_by_author_id(
        author_id=user.id,
        db=db,
        included_offer_types=includedOfferTypes,
        included_tags=includedTags,
        included_location_types=includedLocationTypes,
        limit=limit,
        offset=offset,
        show_hidden=True,
    )

@router.get(
    "/pmf/me/profile",
    response_model=schemas_pmf.ProfileComplete,
    status_code=200,
)
async def get_me_profile(
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
):
    return await cruds_pmf.get_profile(
        user_id=user.id,
        db=db,
    )

@router.post(
    "/pmf/me/profile",
    response_model=schemas_pmf.ProfileBase,
    status_code=201,
)
async def create_me_profile(
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(
    is_user(included_account_types=[AccountType.student]),
    ),
):
    await cruds_pmf.create_profile(
        schemas_pmf.ProfileBase(
        user_id=user.id
        ),
        db=db,
    )
    db.flush()
    return await cruds_pmf.get_profile(user_id=user.id, db=db)

@router.post(
    "/pmf/me/profile/cv",
    response_model=None,
    status_code=201,
)
async def create_me_cv(
    pdf: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(
    is_user(included_account_types=[AccountType.student])),
):
    id=uuid.uuid4()
    cv_simple = schemas_pmf.CvSimple(
    id=id,
    created_on=datetime.now(UTC).date(),
    user_id=user.id,
    name=pdf.filename
    )

    await cruds_pmf.create_cv(
        cv=cv_simple,
        db=db,
    )

    await save_file_as_data(
        upload_file=pdf,
        directory="pmf/pdf",
        filename=str(id),
        max_file_size=10 * 1024 * 1024,  # 10 MB
        accepted_content_types=[ContentType.pdf],
    )

@module.router.patch(
        "/pmf/profile/cv/{cv_id}",
        response_model=None,
        status_code=204,
)
async def patch_cv(
    cv_id:str,
    cv_update: schemas_pmf.CvUpdate,
    user: CoreUser = Depends(is_user),
    db: AsyncSession = Depends(get_db),
):
    cv = cruds_pmf.get_cv_by_id(cv_id=cv_id,db=db)
    if user.id != cv.user_id:
        raise HTTPException(
            status_code=403,
            detail="Forbidden, you are not the author of this cv"
        )
    await cruds_pmf.update_cv(cv_id=cv_id,cv_update=cv_update,db=db)

@module.router.get(
    "/pmf/profile/cv/{cv_id}/pdf",
    response_class=FileResponse,
    status_code=200,
)
async def get_cv_pdf(
    cv_id:str,
    user: CoreUser = Depends(is_user()),
    db: AsyncSession = Depends(get_db)
):
    cv = await cruds_pmf.get_cv_by_id(cv_id=cv_id,db=db)
    if cv is None:
        raise HTTPException(
            status_code=404,
            detail="The cv does not exist.",
        )
    if cv.user_id != user.id and not is_user_member_of_any_group(
        user,
        [
            GroupType.admin,
        ],
    ) and not user in cv.allowed_users:
        raise HTTPException(status_code=403, detail="Forbidden")

    return get_file_from_data(
        default_asset="assets/pdf/default_PDF.pdf",
        directory="pmf/pdf",
        filename=str(cv_id),
    )

@router.get(
    "/pmf/offers/",
    response_model=list[schemas_pmf.OfferSimple],
    status_code=200,
)
async def get_offers(
    db: AsyncSession = Depends(get_db),
    includedOfferTypes: list[types_pmf.OfferType] = Query(default=[]),
    includedTags: list[str] = Query(default=[]),
    includedLocationTypes: list[types_pmf.LocationType] = Query(default=[]),
    limit: int | None = Query(default=50, gt=0, le=50),
    offset: int | None = Query(default=0, ge=0),
    # Allow only former students to access this endpoint
    user: CoreUser = Depends(is_user()),
):
    show_hidden = True
    if not is_user_member_of_any_group(
        user,
        [
            GroupType.admin,
        ],
    ):
        show_hidden = False

    return await cruds_pmf.get_offers(
        db=db,
        included_offer_types=includedOfferTypes,
        included_tags=includedTags,
        included_location_types=includedLocationTypes,
        limit=limit,
        offset=offset,
        show_hidden=show_hidden,
    )


@router.post(
    "/pmf/offers/",
    response_model=schemas_pmf.OfferComplete,
    status_code=200,
)
async def create_offer(
    offer: schemas_pmf.OfferBase,
    db: AsyncSession = Depends(get_db),
    # Allow only former students to create offer
    user: CoreUser = Depends(
        is_user(included_account_types=[AccountType.former_student]),
    ),
):
    # Only admin can post offers on behalf of others
    if offer.author_id != user.id and not is_user_member_of_any_group(
        user,
        [
            GroupType.admin,
        ],
    ):
        raise HTTPException(
            status_code=403,
            detail="Forbidden, you are not the author of this offer",
        )

    offer_db = schemas_pmf.OfferSimple(
        **offer.model_dump(),
        id=uuid.uuid4(),
        hidden=True,
    )
    await cruds_pmf.create_offer(db=db, offer=offer_db)
    await db.flush()
    return await cruds_pmf.get_offer_by_id(offer_id=offer_db.id, db=db)


@router.patch(
    "/pmf/offers/{offer_id}",
    response_model=None,
    status_code=204,
)
async def update_offer(
    offer_id: UUID,
    offer_update: schemas_pmf.OfferUpdate,
    db: AsyncSession = Depends(get_db),
    # Allow only former students to update offer
    user: CoreUser = Depends(
        is_user(included_account_types=[AccountType.former_student]),
    ),
):
    offer_db = await cruds_pmf.get_offer_by_id(offer_id=offer_id, db=db)
    if not offer_db:
        raise HTTPException(status_code=404, detail="Offer not found")

    # Only the author or admin can update the offer
    if offer_db.author_id != user.id and not is_user_member_of_any_group(
        user,
        [
            GroupType.admin,
        ],
    ):
        raise HTTPException(
            status_code=403,
            detail="Forbidden, you are not the author of this offer",
        )

    await cruds_pmf.update_offer(
        offer_id=offer_id,
        structure_update=offer_update,
        db=db,
    )


@router.delete(
    "/pmf/offers/{offer_id}",
    response_model=None,
    status_code=204,
)
async def delete_offer(
    offer_id: UUID,
    db: AsyncSession = Depends(get_db),
    # Allow only former students to delete offer
    user: CoreUser = Depends(
        is_user(included_account_types=[AccountType.former_student]),
    ),
):
    offer_db = await cruds_pmf.get_offer_by_id(offer_id=offer_id, db=db)
    if not offer_db:
        raise HTTPException(status_code=404, detail="Offer not found")

    # Only the author or admin can delete the offer
    if offer_db.author_id != user.id and not is_user_member_of_any_group(
        user,
        [
            GroupType.admin,
        ],
    ):
        raise HTTPException(
            status_code=403,
            detail="Forbidden, you are not the author of this offer",
        )

    await cruds_pmf.delete_offer(offer_id=offer_id, db=db)


@router.get(
    "/pmf/tags/",
    response_model=list[schemas_pmf.TagComplete],
    status_code=200,
)
async def get_tags(
    db: AsyncSession = Depends(get_db),
) -> list[schemas_pmf.TagComplete]:
    return await cruds_pmf.get_tags(db=db)


@router.get(
    "/pmf/tags/{tag_id}",
    response_model=schemas_pmf.TagComplete | None,
    status_code=200,
)
async def get_tag(
    tag_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> schemas_pmf.TagComplete:
    tag = await cruds_pmf.get_tag_by_id(tag_id=tag_id, db=db)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return schemas_pmf.TagComplete(
        tag=tag.tag,
        id=tag.id,
        created_on=tag.created_on,
    )


@router.post(
    "/pmf/tags/",
    response_model=schemas_pmf.TagComplete,
    status_code=201,
)
async def create_tag(
    tag: schemas_pmf.TagBase,
    db: AsyncSession = Depends(get_db),
    # Allow only admin to create tags
    user: CoreUser = Depends(
        is_user_in(group_id=GroupType.admin),
    ),
):
    existing_tag = await cruds_pmf.get_tag_by_name(tag_name=tag.tag, db=db)
    if existing_tag:
        raise HTTPException(status_code=400, detail="Tag already exists")

    tag_db = schemas_pmf.TagComplete(
        **tag.model_dump(),
        id=uuid.uuid4(),
        created_on=datetime.now(UTC).date(),
    )
    await cruds_pmf.create_tag(tag=tag_db, db=db)
    return tag_db


@router.put(
    "/pmf/tags/{tag_id}",
    response_model=None,
    status_code=204,
)
async def update_tag(
    tag_id: UUID,
    tag_update: schemas_pmf.TagBase,
    db: AsyncSession = Depends(get_db),
    # Allow only admin to update tags
    user: CoreUser = Depends(
        is_user_in(group_id=GroupType.admin),
    ),
):
    existing_tag = await cruds_pmf.get_tag_by_id(tag_id=tag_id, db=db)
    if not existing_tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    await cruds_pmf.update_tag(tag_id=tag_id, tag_update=tag_update, db=db)


@router.delete(
    "/pmf/tags/{tag_id}",
    response_model=None,
    status_code=204,
)
async def delete_tag(
    tag_id: UUID,
    db: AsyncSession = Depends(get_db),
    # Allow only admin to delete tags
    user: CoreUser = Depends(
        is_user_in(group_id=GroupType.admin),
    ),
):
    existing_tag = await cruds_pmf.get_tag_by_id(tag_id=tag_id, db=db)
    if not existing_tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    await cruds_pmf.delete_tag(tag_id=tag_id, db=db)
