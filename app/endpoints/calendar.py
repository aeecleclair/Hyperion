import os
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.cruds import cruds_calendar
from app.dependencies import get_db, get_settings, is_user_a_member, is_user_a_member_of
from app.models import models_calendar, models_core
from app.schemas import schemas_calendar
from app.utils.tools import is_user_member_of_an_allowed_group
from app.utils.types.calendar_types import Decision
from app.utils.types.groups_type import GroupType
from app.utils.types.tags import Tags

router = APIRouter()
ical_file_path = "data/ics/ae_calendar.ics"


@router.get(
    "/calendar/events/",
    response_model=list[schemas_calendar.EventReturn],
    status_code=200,
    tags=[Tags.calendar],
)
async def get_events(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.BDE)),
):
    """Get all events from the database."""
    events = await cruds_calendar.get_all_events(db=db)
    return events


@router.get(
    "/calendar/events/confirmed",
    response_model=list[schemas_calendar.EventComplete],
    status_code=200,
    tags=[Tags.calendar],
)
async def get_confirmed_events(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get all confirmed events.

    **Usable by every member**
    """
    events = await cruds_calendar.get_confirmed_events(db=db)
    return events


@router.get(
    "/calendar/events/user/{applicant_id}",
    response_model=list[schemas_calendar.EventReturn],
    status_code=200,
    tags=[Tags.calendar],
)
async def get_applicant_bookings(
    applicant_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get one user bookings.

    **Usable by the user or admins**
    """
    if user.id == applicant_id or is_user_member_of_an_allowed_group(
        user, [GroupType.BDE]
    ):
        bookings = await cruds_calendar.get_applicant_events(
            db=db, applicant_id=applicant_id
        )
        return bookings
    else:
        raise HTTPException(status_code=403)


@router.get(
    "/calendar/events/{event_id}",
    response_model=schemas_calendar.EventComplete,
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


@router.get(
    "calendar/events/{event_id}/applicant",
    response_model=schemas_calendar.EventApplicant,
    status_code=200,
    tags=[Tags.calendar],
)
async def get_event_applicant(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.BDE)),
):
    event = await cruds_calendar.get_event(db=db, event_id=event_id)
    if event is not None:
        return event.applicant
    else:
        raise HTTPException(status_code=404)


@router.post(
    "/calendar/events/",
    response_model=schemas_calendar.EventComplete,
    status_code=201,
    tags=[Tags.calendar],
)
async def add_event(
    event: schemas_calendar.EventBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
    settings: Settings = Depends(get_settings),
):
    """Add an event to the calendar."""

    event_id = str(uuid.uuid4())

    db_event = models_calendar.Event(
        id=event_id,
        decision=Decision.pending,
        applicant_id=user.id,
        **event.dict(),
    )
    try:
        return await cruds_calendar.add_event(event=db_event, db=db, settings=settings)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.patch(
    "/calendar/events/{event_id}",
    status_code=204,
    tags=[Tags.calendar],
)
async def edit_bookings_id(
    event_id: str,
    event_edit: schemas_calendar.EventEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Edit an event.

    **Only usable by admins or applicant before decision**
    """
    event = await cruds_calendar.get_event(db=db, event_id=event_id)

    if event is not None and not (
        (user.id == event.applicant_id and event.decision == Decision.pending)
        or is_user_member_of_an_allowed_group(user, [GroupType.BDE])
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to edit this event",
        )

    try:
        await cruds_calendar.edit_event(event_id=event_id, event=event_edit, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.patch(
    "/calendar/events/{event_id}/reply/{decision}",
    status_code=204,
    tags=[Tags.booking],
)
async def confirm_booking(
    event_id: str,
    decision: Decision,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.BDE)),
    settings: Settings = Depends(get_settings),
):
    """
    Give a decision to an event.

    **Only usable by admins**
    """
    await cruds_calendar.confirm_event(
        event_id=event_id, decision=decision, db=db, settings=settings
    )


@router.delete("/calendar/events/{event_id}", status_code=204, tags=[Tags.calendar])
async def delete_bookings_id(
    event_id,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
    settings: Settings = Depends(get_settings),
):
    """
    Remove an event.

    **Only usable by admins or applicant before decision**
    """
    event = await cruds_calendar.get_event(db=db, event_id=event_id)

    if event is not None and (
        (user.id == event.applicant_id and event.decision == Decision.pending)
        or is_user_member_of_an_allowed_group(user, [GroupType.BDE])
    ):
        await cruds_calendar.delete_event(event_id=event_id, db=db, settings=settings)

    else:
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to delete this event",
        )


@router.post(
    "/calendar/ical/create",
    status_code=204,
    tags=[Tags.calendar],
)
async def recreate_ical_file(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
    settings: Settings = Depends(get_settings),
):
    """
    Create manually the icalendar file

    **Only usable by global admins**
    """

    await cruds_calendar.create_icalendar_file(db=db, settings=settings)


@router.get(
    "/calendar/ical",
    response_class=FileResponse,
    status_code=200,
    tags=[Tags.calendar],
)
async def get_icalendar_file(db: AsyncSession = Depends(get_db)):
    """Get the icalendar file corresponding to the event in the database."""

    if os.path.exists(ical_file_path):
        return FileResponse(ical_file_path)

    else:
        raise HTTPException(status_code=404)
