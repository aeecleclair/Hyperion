import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_calendar
from app.dependencies import get_db, is_user_a_member, is_user_a_member_of
from app.models import models_calendar, models_core
from app.schemas import schemas_calendar
from app.utils.types.groups_type import GroupType
from app.utils.types.tags import Tags

router = APIRouter()


@router.get(
    "/calendar/",
    response_model=list[schemas_calendar.EventComplete],
    status_code=200,
    tags=[Tags.calendar],
)
async def get_events(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """Get all events from the database."""
    events = await cruds_calendar.get_all_events(db=db)
    return events


@router.post(
    "/calendar/event/",
    response_model=schemas_calendar.EventBase,
    status_code=201,
    tags=[Tags.calendar],
)
async def add_event(
    event: schemas_calendar.EventBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """Add an event to the calendar."""

    # We need to generate a new UUID for the todo
    event_id = str(uuid.uuid4())

    db_event = models_calendar.Event(
        id=event_id,
        **event.dict(),  # We add all informations contained in the schema
    )
    try:
        return await cruds_calendar.add_event(event=db_event, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.get(
    "/calendar/event/{event_id}",
    response_model=schemas_calendar.EventBase,
    status_code=200,
    tags=[Tags.calendar],
)
async def get_event_by_id(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """Get an event's information by its id."""

    event = await cruds_calendar.get_event(db=db, event_id=event_id)
    if event is not None:
        return event
    else:
        raise HTTPException(status_code=404)
