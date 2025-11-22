import uuid
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.groups_type import AccountType, GroupType
from app.core.users.models_users import CoreUser
from app.dependencies import get_db, is_user, is_user_in
from app.modules.pmf import cruds_pmf, schemas_pmf, types_pmf
from app.types.module import Module
from app.utils.tools import is_user_member_of_any_group

router = APIRouter(tags=["pmf"])

module = Module(
    root="pmf",
    tag="Pmf",
    router=router,
    default_allowed_account_types=[
        AccountType.student,
        AccountType.staff,
        AccountType.former_student,
    ],
    factory=None,
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
    # user: CoreUser = Depends(is_user(included_account_types=[AccountType.former_student])),
):
    return await cruds_pmf.get_offers(
        db=db,
        included_offer_types=includedOfferTypes,
        included_tags=includedTags,
        included_location_types=includedLocationTypes,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/pmf/offer/",
    response_model=list[schemas_pmf.OfferComplete],
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
        author_id=user.id,
    )
    return await cruds_pmf.create_offer(db=db, offer=offer_db)


@router.put(
    "/pmf/offer/{offer_id}",
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
    "/pmf/offer/{offer_id}",
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
async def get_all_tags(
    db: AsyncSession = Depends(get_db),
) -> list[schemas_pmf.TagComplete]:
    return await cruds_pmf.get_all_tags(db=db)


@router.get(
    "/pmf/tag/{tag_id}",
    response_model=schemas_pmf.TagComplete | None,
    status_code=200,
)
async def get_tag(
    tag_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> schemas_pmf.TagComplete | None:
    tags = await cruds_pmf.get_all_tags(db=db)
    for tag in tags:
        if tag.id == tag_id:
            return tag
    return None


@router.post(
    "/pmf/tag/",
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
        created_at=date.today(),
    )
    await cruds_pmf.create_tag(tag=tag_db, db=db)
    return tag_db


@router.put(
    "/pmf/tag/{tag_id}",
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
    "/pmf/tag/{tag_id}",
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
