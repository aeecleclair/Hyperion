"""FastAPI dependencies for the raid module.

Provides `get_current_raid_edition` (the active edition) plus helpers used
across endpoints to enforce the disjoint participant / volunteer track and
fetch scoped entities with a 404 fallback.
"""

from uuid import UUID

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.modules.raid import cruds_raid, schemas_raid


async def get_current_raid_edition(
    db: AsyncSession = Depends(get_db),
) -> schemas_raid.RaidEdition:
    edition = await cruds_raid.get_active_edition(db)
    if not edition:
        raise HTTPException(status_code=404, detail="No active raid edition")
    return edition


async def get_participant_or_404(
    user_id: str,
    edition_id: UUID,
    db: AsyncSession,
) -> schemas_raid.RaidParticipant:
    participant = await cruds_raid.get_participant_by_user_id(user_id, edition_id, db)
    if participant is None:
        raise HTTPException(status_code=404, detail="Participant not found")
    return participant


async def get_volunteer_or_404(
    user_id: str,
    edition_id: UUID,
    db: AsyncSession,
) -> schemas_raid.RaidVolunteer:
    volunteer = await cruds_raid.get_volunteer_by_user_id(user_id, edition_id, db)
    if volunteer is None:
        raise HTTPException(status_code=404, detail="Volunteer not found")
    return volunteer


async def ensure_user_is_not_participant_in_edition(
    user_id: str,
    edition_id: UUID,
    db: AsyncSession,
) -> None:
    participant = await cruds_raid.get_participant_by_user_id(user_id, edition_id, db)
    if participant is not None:
        raise HTTPException(
            status_code=400,
            detail="User is already a participant in this edition",
        )


async def ensure_user_is_not_volunteer_in_edition(
    user_id: str,
    edition_id: UUID,
    db: AsyncSession,
) -> None:
    volunteer = await cruds_raid.get_volunteer_by_user_id(user_id, edition_id, db)
    if volunteer is not None:
        raise HTTPException(
            status_code=400,
            detail="User is already a volunteer in this edition",
        )
