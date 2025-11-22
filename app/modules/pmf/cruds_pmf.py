from uuid import UUID

from sqlalchemy import delete, select, true, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.users import schemas_users
from app.modules.pmf import models_pmf, schemas_pmf, types_pmf


async def create_offer(offer: schemas_pmf.OfferSimple, db: AsyncSession) -> None:
    """Create a new PMF offer with associated tags."""
    db.add(
        models_pmf.PmfOffer(
            id=offer.id,
            author_id=offer.author_id,
            company_name=offer.company_name,
            title=offer.title,
            description=offer.description,
            offer_type=offer.offer_type,
            location=offer.location,
            location_type=offer.location_type,
            start_date=offer.start_date,
            end_date=offer.end_date,
            duration=offer.duration,
            tags=[],
        ),
    )


async def update_offer(
    offer_id: UUID,
    structure_update: schemas_pmf.OfferUpdate,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_pmf.PmfOffer)
        .where(models_pmf.PmfOffer.id == offer_id)
        .values(**structure_update.model_dump(exclude_unset=True)),
    )


async def delete_offer(offer_id: UUID, db: AsyncSession) -> None:
    await db.execute(
        delete(models_pmf.PmfOffer).where(models_pmf.PmfOffer.id == offer_id),
    )


async def get_offer_by_id(
    offer_id: UUID,
    db: AsyncSession,
) -> models_pmf.PmfOffer | None:
    result = await db.execute(
        select(models_pmf.PmfOffer).where(models_pmf.PmfOffer.id == offer_id),
    )
    return result.scalars().first()


async def get_offers(
    db: AsyncSession,
    included_offer_types: list[types_pmf.OfferType] | None = None,
    included_tags: list[str] | None = None,
    included_location_types: list[types_pmf.LocationType] | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> list[schemas_pmf.OfferComplete]:
    where_clause = (
        (
            models_pmf.PmfOffer.offer_type.in_(included_offer_types)
            if included_offer_types
            else true()
        )
        & (
            models_pmf.PmfOffer.tags.any(models_pmf.Tags.tag.in_(included_tags))
            if included_tags
            else true()
        )
        & (
            models_pmf.PmfOffer.location_type.in_(included_location_types)
            if included_location_types
            else true()
        )
    )

    offers = await db.execute(
        select(models_pmf.PmfOffer).where(where_clause).limit(limit).offset(offset),
    )
    return [
        schemas_pmf.OfferComplete(
            id=offer.id,
            author_id=offer.author_id,
            company_name=offer.company_name,
            title=offer.title,
            description=offer.description,
            offer_type=offer.offer_type,
            location=offer.location,
            location_type=offer.location_type,
            start_date=offer.start_date,
            end_date=offer.end_date,
            duration=offer.duration,
            author=schemas_users.CoreUserSimple.model_validate(offer.author),
            tags=[schemas_pmf.TagComplete.model_validate(tag) for tag in offer.tags],
        )
        for offer in offers.scalars().all()
    ]


async def get_all_tags(db: AsyncSession) -> list[schemas_pmf.TagComplete]:
    tags = await db.execute(
        select(models_pmf.Tags).distinct(models_pmf.Tags.tag),
    )
    return [schemas_pmf.TagComplete.model_validate(tag) for tag in tags.scalars().all()]


async def get_tag_by_name(
    tag_name: str,
    db: AsyncSession,
) -> schemas_pmf.TagComplete | None:
    result = await db.execute(
        select(models_pmf.Tags).where(models_pmf.Tags.tag == tag_name),
    )
    return schemas_pmf.TagComplete.model_validate(result.scalars().first())


async def get_tag_by_id(
    tag_id: UUID,
    db: AsyncSession,
) -> schemas_pmf.TagComplete | None:
    result = await db.execute(
        select(models_pmf.Tags).where(models_pmf.Tags.id == tag_id),
    )
    return schemas_pmf.TagComplete.model_validate(result.scalars().first())


async def create_tag(
    tag: schemas_pmf.TagComplete,
    db: AsyncSession,
) -> None:
    tag_db = models_pmf.Tags(
        id=tag.id,
        tag=tag.tag,
    )
    db.add(tag_db)


async def update_tag(
    tag_id: UUID,
    tag_update: schemas_pmf.TagBase,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_pmf.Tags)
        .where(models_pmf.Tags.id == tag_id)
        .values(**tag_update.model_dump(exclude_unset=True)),
    )


async def delete_tag(
    tag_id: UUID,
    db: AsyncSession,
) -> None:
    await db.execute(
        delete(models_pmf.Tags).where(models_pmf.Tags.id == tag_id),
    )
