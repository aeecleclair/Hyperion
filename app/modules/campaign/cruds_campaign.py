import logging
import uuid
from collections.abc import Sequence

from fastapi import HTTPException
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.campaign import models_campaign, schemas_campaign
from app.modules.campaign.types_campaign import ListType, StatusType

hyperion_error_logger = logging.getLogger("hyperion.error")


async def get_status(
    db: AsyncSession,
) -> StatusType:
    # TODO: we may want to use a CoreData instead of a complete table
    result = await db.execute(select(models_campaign.Status))
    status = result.scalars().all()
    if len(status) > 1:
        hyperion_error_logger.error(
            "There is more than one status in the database, this should never happen",
        )
        raise ValueError(  # noqa: TRY003
            "There is more than one status in the database, this should never happen",
        )
    if len(status) == 0:
        # The status was never set in the database, we can create a default status in the database and return it
        # Since this is the only place a row can be added to the status table, there should never be more than one row in the table
        status_model = models_campaign.Status(status=StatusType.waiting, id="id")
        db.add(status_model)
        return StatusType.waiting

    # The status is contained in the only result returned by the database
    return status[0].status


async def set_status(
    db: AsyncSession,
    new_status: StatusType,
):
    await db.execute(update(models_campaign.Status).values(status=new_status))


async def get_vote_count(db: AsyncSession, section_id: str):
    count = await db.execute(
        select(models_campaign.HasVoted).where(
            models_campaign.HasVoted.section_id == section_id,
        ),
    )
    return len(count.scalars().all())


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
                program=None,
                members=[],
            ),
        )


async def get_sections(db: AsyncSession) -> Sequence[models_campaign.Sections]:
    """Return all users from database."""

    result = await db.execute(
        select(models_campaign.Sections).options(
            selectinload(models_campaign.Sections.lists),
        ),
    )
    return result.scalars().all()


async def get_section_by_id(db: AsyncSession, section_id: str):
    """Return section with the given name."""
    result = await db.execute(
        select(models_campaign.Sections)
        .where(models_campaign.Sections.id == section_id)
        .options(selectinload(models_campaign.Sections.lists)),
    )
    return result.scalars().first()


async def add_section(db: AsyncSession, section: models_campaign.Sections) -> None:
    """Add a section of AEECL."""
    db.add(section)


async def delete_section(db: AsyncSession, section_id: str) -> None:
    """Delete a section."""
    result = await db.execute(
        select(models_campaign.Sections)
        .where(models_campaign.Sections.id == section_id)
        .options(selectinload(models_campaign.Sections.lists)),
    )
    section = result.scalars().all()
    if section != []:
        if section[0].lists == [] or (
            len(section[0].lists) == 1 and "blank" in (section[0].lists)[0].id
        ):
            await db.execute(
                delete(models_campaign.Lists).where(
                    models_campaign.Lists.section_id == section_id,
                ),
            )
            await db.execute(
                delete(models_campaign.Sections).where(
                    models_campaign.Sections.id == section_id,
                ),
            )
        else:
            raise HTTPException(status_code=400, detail="This section still has lists")
    else:
        raise HTTPException(status_code=400, detail="Section not found")


async def delete_lists_from_section(db: AsyncSession, section_id: str) -> None:
    await db.execute(
        delete(models_campaign.Lists).where(
            models_campaign.Lists.section_id == section_id,
        ),
    )
    await db.commit()


async def get_lists(db: AsyncSession) -> Sequence[models_campaign.Lists]:
    """Return all the campaign lists."""
    result = await db.execute(
        select(models_campaign.Lists)
        .options(
            selectinload(models_campaign.Lists.members).selectinload(
                models_campaign.ListMemberships.user,
            ),
            selectinload(models_campaign.Lists.section),
        )
        .order_by(models_campaign.Lists.type),
    )
    return result.scalars().all()


async def get_list_by_id(
    db: AsyncSession,
    list_id: str,
) -> models_campaign.Lists | None:
    """Return list with the given id."""
    result = await db.execute(
        select(models_campaign.Lists)
        .where(models_campaign.Lists.id == list_id)
        .options(
            selectinload(models_campaign.Lists.members).selectinload(
                models_campaign.ListMemberships.user,
            ),
            selectinload(models_campaign.Lists.section),
        ),
    )
    return result.scalars().first()


async def add_list(
    db: AsyncSession,
    campaign_list: models_campaign.Lists,
) -> None:
    """Add a list to a section then add the members to the list."""
    db.add(campaign_list)


async def remove_members_from_list(
    db: AsyncSession,
    list_id: str,
) -> None:
    """
    Remove all members from a given list. The list nor users won't be deleted.
    """
    await db.execute(
        delete(models_campaign.ListMemberships).where(
            models_campaign.ListMemberships.list_id == list_id,
        ),
    )


async def delete_list(db: AsyncSession, list_id: str) -> None:
    """Delete a campaign list."""
    await remove_members_from_list(list_id=list_id, db=db)
    await db.execute(
        delete(models_campaign.Lists).where(models_campaign.Lists.id == list_id),
    )


async def delete_list_by_type(list_type: ListType, db: AsyncSession) -> None:
    """Delete all campaign list by type."""

    lists = await get_lists(db)
    for list_obj in lists:
        if list_obj.type == list_type:
            await remove_members_from_list(list_id=list_obj.id, db=db)

    await db.execute(
        delete(models_campaign.Lists).where(models_campaign.Lists.type == list_type),
    )


async def update_list(
    db: AsyncSession,
    list_id: str,
    campaign_list: schemas_campaign.ListEdit,
) -> None:
    """Update a campaign list."""
    await db.execute(
        update(models_campaign.Lists)
        .where(models_campaign.Lists.id == list_id)
        .values(**campaign_list.model_dump(exclude={"members"}, exclude_none=True)),
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
                **campaign_list.model_dump(exclude={"members"}, exclude_none=True),
            ),
        )


async def add_vote(db: AsyncSession, vote: models_campaign.Votes) -> None:
    """Add a vote."""
    db.add(vote)


async def has_user_voted_for_section(
    db: AsyncSession,
    user_id: str,
    section_id: str,
) -> bool:
    """Return HasVoted object from the db."""
    result = await db.execute(
        select(models_campaign.HasVoted).where(
            models_campaign.HasVoted.user_id == user_id,
            models_campaign.HasVoted.section_id == section_id,
        ),
    )
    has_voted: models_campaign.HasVoted | None = result.scalars().first()
    return has_voted is not None


async def mark_has_voted(db: AsyncSession, user_id: str, section_id: str) -> None:
    """Mark user has having vote for the given section."""
    has_voted = models_campaign.HasVoted(user_id=user_id, section_id=section_id)
    db.add(has_voted)


async def get_has_voted(
    db: AsyncSession,
    user_id: str,
) -> Sequence[models_campaign.HasVoted]:
    """Return all the sections the user has voted for."""
    result = await db.execute(
        select(models_campaign.HasVoted).where(
            models_campaign.HasVoted.user_id == user_id,
        ),
    )
    return result.scalars().all()


async def get_votes(db: AsyncSession) -> Sequence[models_campaign.Votes]:
    result = await db.execute(select(models_campaign.Votes))
    return result.scalars().all()


async def delete_votes(db: AsyncSession) -> None:
    """Delete all votes in the db."""
    await db.execute(delete(models_campaign.Votes))
    await db.execute(delete(models_campaign.HasVoted))


async def reset_campaign(db: AsyncSession) -> None:
    """Reset the campaign.
    This will delete all the votes and blank list lists."""
    await db.execute(delete(models_campaign.Votes))
    await db.execute(delete(models_campaign.HasVoted))
    await delete_list_by_type(ListType.blank, db)
