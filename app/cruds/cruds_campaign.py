import uuid

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import models_campaign
from app.schemas import schemas_campaign
from app.utils.types.campaign_type import ListType, StatusType


async def get_status(
    db: AsyncSession,
) -> StatusType:
    result = await db.execute(select(models_campaign.Status))
    status = result.scalars().all()
    if len(status) > 1:
        raise ValueError(
            "There is more than one status in the database, this should never happen"
        )
    if len(status) == 0:
        # The status was never set in the database, we can create a default status in the database and return it
        # Since this is the only place a row can be added to the status table, there should never be more than one row in the table
        status_model = models_campaign.Status(status=StatusType.waiting, id="id")
        db.add(status_model)
        try:
            await db.commit()
        except IntegrityError as err:
            await db.rollback()
            raise ValueError(err)
        return StatusType.waiting

    # The status is contained in the only result returned by the database
    return status[0].status


async def set_status(
    db: AsyncSession,
    new_status: StatusType,
):
    await db.execute(update(models_campaign.Status).values(status=new_status))
    await db.commit()


async def add_blank_option(db: AsyncSession):
    result = await db.execute(select(models_campaign.Sections.id))
    sections_ids = result.scalars().all()

    for section_id in sections_ids:
        db.add(
            models_campaign.Lists(
                id=str(uuid.uuid4()),
                name="Vote Blanc",
                description="",
                section_id=section_id,
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

    result = await db.execute(
        select(models_campaign.Sections).options(
            selectinload(models_campaign.Sections.lists)
        )
    )
    return result.scalars().all()


async def get_section_by_id(db: AsyncSession, section_id: str):
    """Return section with the given name."""
    result = await db.execute(
        select(models_campaign.Sections)
        .where(models_campaign.Sections.id == section_id)
        .options(selectinload(models_campaign.Sections.lists))
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
        select(models_campaign.Sections)
        .where(models_campaign.Sections.id == section_id)
        .options(selectinload(models_campaign.Sections.lists))
    )
    section = result.scalars().all()
    if section != []:
        if section[0].lists == [] or (
            len(section[0].lists) == 1 and "blank" in (section[0].lists)[0].id
        ):
            await db.execute(
                delete(models_campaign.Lists).where(
                    models_campaign.Lists.section_id == section_id
                )
            )
            await db.execute(
                delete(models_campaign.Sections).where(
                    models_campaign.Sections.id == section_id
                )
            )
            await db.commit()
        else:
            raise ValueError("This section still has lists")


async def delete_lists_from_section(db: AsyncSession, section_id: str) -> None:
    await db.execute(
        delete(models_campaign.Lists).where(
            models_campaign.Lists.section_id == section_id
        )
    )
    await db.commit()


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
    campaign_list: models_campaign.Lists,
) -> None:
    """Add a list to a section then add the members to the list."""
    db.add(campaign_list)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError("This list already exist.")


async def remove_members_from_list(
    db: AsyncSession,
    list_id: str,
) -> None:
    """
    Remove all members from a given list. The list nor users won't be deleted.
    """
    await db.execute(
        delete(models_campaign.ListMemberships).where(
            models_campaign.ListMemberships.list_id == list_id
        )
    )
    await db.commit()


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
    await db.execute(
        update(models_campaign.Lists)
        .where(models_campaign.Lists.id == list_id)
        .values(**campaign_list.dict(exclude={"members"}, exclude_none=True))
    )

    # We may need to recreate the list of members
    if campaign_list.members is not None:
        # First we remove all the members
        await remove_members_from_list(list_id=list_id, db=db)
        # Then we add the new members
        for member in campaign_list.members:
            members_db = models_campaign.ListMemberships(
                user_id=member.user_id,
                role=member.role,
                list_id=list_id,
            )

            db.add(members_db)

        await db.execute(
            update(models_campaign.Lists)
            .where(models_campaign.Lists.id == list_id)
            .values(
                **campaign_list.dict(exclude={"members"}, exclude_none=True),
            )
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
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def has_user_voted_for_section(
    db: AsyncSession, user_id: str, section_id: str
) -> bool:
    """Return HasVoted object from the db."""
    result = await db.execute(
        select(models_campaign.HasVoted)
        .where(models_campaign.HasVoted.user_id == user_id)
        .where(models_campaign.HasVoted.section_id == section_id)
    )
    has_voted: models_campaign.HasVoted | None = result.scalars().first()
    return has_voted is not None


async def mark_has_voted(db: AsyncSession, user_id: str, section_id: str) -> None:
    """Mark user has having vote for the given section."""
    has_voted = models_campaign.HasVoted(user_id=user_id, section_id=section_id)
    db.add(has_voted)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError("The user has already voted.")


async def get_has_voted(
    db: AsyncSession,
    user_id: str,
) -> list[models_campaign.HasVoted]:
    """Return all the sections the user has voted for."""
    result = await db.execute(
        select(models_campaign.HasVoted).where(
            models_campaign.HasVoted.user_id == user_id
        )
    )
    return result.scalars().all()


async def get_votes(db: AsyncSession) -> list[models_campaign.Votes]:
    result = await db.execute(select(models_campaign.Votes))
    return result.scalars().all()


async def delete_votes(db: AsyncSession) -> None:
    """Delete all votes in the db."""
    await db.execute(delete(models_campaign.Votes))
    await db.execute(delete(models_campaign.HasVoted))
    await db.commit()


async def reset_campaign(db: AsyncSession) -> None:
    """Reset the campaign."""
    await db.execute(delete(models_campaign.ListMemberships))
    await db.execute(delete(models_campaign.Sections))
    await db.execute(delete(models_campaign.Lists))
    await db.execute(delete(models_campaign.Votes))
    await db.execute(delete(models_campaign.HasVoted))
    await db.commit()
