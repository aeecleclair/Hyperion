from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import models_campaign
from app.schemas import schemas_campaign
from app.utils.types.campaign_type import ListType, StatusType


async def get_status(db: AsyncSession) -> models_campaign.Status:
    result = await db.execute(select(models_campaign.Status))
    status = result.scalars().all()
    if status == []:
        db_status = models_campaign.Status(id="status", status=StatusType.waiting)
        db.add(db_status)
        try:
            await db.commit()
            return db_status
        except IntegrityError:
            await db.rollback()
            raise ValueError("Error in status creation")
    else:
        return status[0]


async def set_status(db: AsyncSession, new_status: schemas_campaign.VoteStatus):
    current_status = await db.execute(select(models_campaign.Status))
    await db.execute(
        update(models_campaign.Status)
        .where(
            models_campaign.Status.status == current_status.scalars().all()[0].status
        )
        .values(status=new_status.status)
    )


async def add_blank_option(db: AsyncSession):
    result = await db.execute(select(models_campaign.Sections.id))
    sections_ids = result.scalars().all()

    result = await db.execute(
        select(models_campaign.Lists.section_id).where(
            models_campaign.Lists.type == ListType.blank
        )
    )
    blank_lists = result.scalars().all()
    for sid in sections_ids:
        if sid not in blank_lists:
            db.add(
                models_campaign.Lists(
                    id="blank" + sid,
                    name="Vote Blanc",
                    description="",
                    section_id=sid,
                    type=ListType.blank,
                    members=[],
                )
            )
    try:
        await db.commit()
    except IntegrityError as err:
        await db.rollback()
        raise ValueError(err)


async def get_sections(db: AsyncSession) -> list[models_campaign.Sections]:
    """Return all users from database."""

    result = await db.execute(select(models_campaign.Sections))
    return result.scalars().all()


async def get_section_by_id(db: AsyncSession, section_id: str):
    """Return section with the given name."""
    result = await db.execute(
        select(models_campaign.Sections).where(
            models_campaign.Sections.id == section_id
        )
    )
    return result.scalars().first()


async def add_section(db: AsyncSession, section: models_campaign.Sections) -> None:
    """Add a section of AEECL."""
    db.add(section)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError("This name is already used")


async def delete_section(db: AsyncSession, section_id: str) -> None:
    """Delete a section."""
    result = await db.execute(
        select(models_campaign.Sections).where(
            models_campaign.Sections.id == section_id
        )
    )
    section = result.scalars().all()
    if section[0].lists == []:
        await db.execute(
            delete(models_campaign.Sections).where(
                models_campaign.Sections.id == section_id
            )
        )
        await db.commit()
    else:
        raise ValueError("This section still has lists")


async def get_lists(db: AsyncSession) -> list[models_campaign.Lists]:
    """Return all the campaign lists."""
    result = await db.execute(
        select(models_campaign.Lists).options(
            selectinload(models_campaign.Lists.members).selectinload(
                models_campaign.ListMemberships.user
            ),
            selectinload(models_campaign.Lists.section),
        )
    )
    lists = result.scalars().all()
    return lists


async def get_list_by_id(
    db: AsyncSession, list_id: str
) -> models_campaign.Lists | None:
    """Return list with the given id."""
    result = await db.execute(
        select(models_campaign.Lists)
        .where(models_campaign.Lists.id == list_id)
        .options(
            selectinload(models_campaign.Lists.members).selectinload(
                models_campaign.ListMemberships.user
            ),
            selectinload(models_campaign.Lists.section),
        )
    )
    return result.scalars().first()


async def add_list(
    db: AsyncSession,
    campaign_list: schemas_campaign.ListComplete,
) -> None:
    """Add a list of AEECL."""
    db.add(
        models_campaign.Lists(
            members=[
                models_campaign.ListMemberships(**member.dict())
                for member in campaign_list.members
            ],
            **campaign_list.dict(exclude={"members"}),
        )
    )
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
    db: AsyncSession, list_id: str, campaign_list: schemas_campaign.ListEdit
) -> None:
    """Update a campaign list."""
    if campaign_list.members is not None:
        await db.execute(
            update(models_campaign.Lists)
            .where(models_campaign.Lists.id == list_id)
            .values(
                members=[
                    models_campaign.ListMemberships(**member.dict())
                    for member in campaign_list.members
                ],
                **campaign_list.dict(exclude={"members"}, exclude_none=True),
            )
        )
    else:
        await db.execute(
            update(models_campaign.Lists)
            .where(models_campaign.Lists.id == list_id)
            .values(**campaign_list.dict(exclude_none=True))
        )

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError()


async def add_vote(db: AsyncSession, vote: models_campaign.Votes) -> None:
    """Add a vote."""
    db.add(vote)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError("Error occured when adding a vote.")


async def get_has_voted(
    db: AsyncSession, user_id: str, section_id: str
) -> models_campaign.HasVoted | None:
    """Return HasVoted object from the db."""
    result = await db.execute(
        select(models_campaign.HasVoted)
        .where(models_campaign.HasVoted.user_id == user_id)
        .where(models_campaign.HasVoted.section_id == section_id)
    )
    return result.scalars().first()


async def mark_has_voted(db: AsyncSession, user_id: str, section_id: str) -> None:
    """Mark user has having vote for the given section."""
    has_voted = models_campaign.HasVoted(user_id=user_id, section_id=section_id)
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
    db: AsyncSession, section_id: str
) -> list[models_campaign.Votes]:
    result = await db.execute(
        select(models_campaign.Votes)
        .join(
            models_campaign.Lists,
            onclause=models_campaign.Lists.id == models_campaign.Votes.list_id,
        )
        .where(models_campaign.Lists.section == section_id)
    )
    return result.scalars().all()


async def delete_votes(db: AsyncSession) -> None:
    """Delete all votes in the db."""
    await db.execute(delete(models_campaign.Votes))
    await db.execute(delete(models_campaign.HasVoted))
