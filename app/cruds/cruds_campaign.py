from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import models_campaign
from app.schemas import schemas_campaign


async def get_sections(db: AsyncSession) -> list[models_campaign.Sections]:
    """Return all users from database."""

    result = await db.execute(select(models_campaign.Sections))
    return result.scalars().all()


async def get_section_by_name(db: AsyncSession, section_name: str):
    """Return section with the given name."""
    result = await db.execute(
        select(models_campaign.Sections).where(
            models_campaign.Sections.name == section_name
        )
    )
    return result.scalars().first()


async def add_section(db: AsyncSession, section: schemas_campaign.SectionBase) -> None:
    """Add a section of AEECL."""
    db_section = models_campaign.Sections(**section.dict())
    db.add(db_section)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError("This name is already used")


async def delete_section(db: AsyncSession, section_name: str) -> None:
    """Delete a section."""
    await db.execute(
        delete(models_campaign.Sections).where(
            models_campaign.Sections.name == section_name
        )
    )
    await db.commit()


async def get_lists_from_section(
    db: AsyncSession, section_name: str
) -> list[models_campaign.Lists]:
    """Return all campaign lists of the given section."""
    result = await db.execute(
        select(models_campaign.Lists).where(
            models_campaign.Lists.section == section_name
        )
    )
    lists = result.scalars().all()
    return lists


async def get_lists(db: AsyncSession) -> list[models_campaign.Lists]:
    """Return all the campaign lists."""
    result = await db.execute(select(models_campaign.Lists))
    lists = result.scalars().all()
    return lists


async def get_list_by_id(db: AsyncSession, list_id: str) -> models_campaign.Lists:
    """Return list with the given id."""
    result = await db.execute(
        select(models_campaign.Lists).where(models_campaign.Lists.id == list_id)
    )
    return result.scalars().first()


async def add_list(db: AsyncSession, campaign_list: models_campaign.Lists) -> None:
    """Add a section of AEECL."""
    db.add(campaign_list)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError("This list alreay exist.")


async def delete_list(db: AsyncSession, list_id: str) -> None:
    """Delete a campaign list."""
    await db.execute(
        delete(models_campaign.Lists).where(models_campaign.Lists.id == list_id)
    )
    await db.commit()


async def update_list(
    db: AsyncSession, list_id, campaign_list: schemas_campaign.ListBase
) -> None:
    """Update a campaign list."""
    await db.execute(
        update(models_campaign.Lists)
        .where(models_campaign.Lists.id == list_id)
        .values(**campaign_list.dict(exclude_none=True))
    )
    await db.commit()


async def add_vote(db: AsyncSession, vote: models_campaign.Votes) -> None:
    """Add a vote."""
    db.add(vote)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError("Error occured when adding a vote.")


async def get_has_voted(
    db: AsyncSession, user_id: str, section_name: str
) -> models_campaign.HasVoted:
    """Return HasVoted object from the db."""
    result = await db.execute(
        select(models_campaign.HasVoted)
        .where(models_campaign.HasVoted.user_id == user_id)
        .where(models_campaign.HasVoted.section_name == section_name)
    )
    return result.scalars().first()


async def mark_has_voted(db: AsyncSession, user_id: str, section_name: str) -> None:
    """Mark user has having vote for the given section."""
    has_voted = models_campaign.HasVoted(user_id=user_id, section_name=section_name)
    db.add(has_voted)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError("The user has already voted.")


async def get_votes(db: AsyncSession) -> list[models_campaign.Votes]:
    result = await db.execute(select(models_campaign.Votes))
    return result.scalars().all()


async def get_votes_for_section(
    db: AsyncSession, section_name: str
) -> list[models_campaign.Votes]:
    result = await db.execute(
        select(models_campaign.Votes)
        .join(
            models_campaign.Lists,
            onclause=models_campaign.Lists.id == models_campaign.Votes.list_id,
        )
        .where(models_campaign.Lists.section == section_name)
    )
    return result.scalars().all()


async def delete_votes(db: AsyncSession) -> None:
    """Delete all votes in the db."""
    await db.execute(delete(models_campaign.Votes))
    await db.execute(delete(models_campaign.HasVoted))
