import uuid
from pathlib import Path

from fastapi import Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.groups_type import AccountType, GroupType
from app.core.users import models_users
from app.dependencies import get_db, is_user_an_ecl_member, is_user_in
from app.modules.calendar import cruds_calendar, models_calendar, schemas_calendar
from app.modules.calendar.types_calendar import Decision
from app.types.module import Module
from app.utils.tools import is_user_member_of_any_group

module = Module(
    root="event",
    tag="Calendar",
    default_allowed_account_types=[AccountType.student, AccountType.staff],
)

ical_file_path = "data/ics/ae_calendar.ics"


@module.router.get(
    "/calendar/events/",
    response_model=list[schemas_calendar.EventReturn],
    status_code=200,
)
async def get_events(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.BDE)),
):
    """Get all events from the database."""
    return await cruds_calendar.get_all_events(db=db)


@module.router.get(
    "/calendar/events/confirmed",
    response_model=list[schemas_calendar.EventComplete],
    status_code=200,
)
async def get_confirmed_events(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_an_ecl_member),
):
    """
    Get all confirmed events.

    **Usable by every member**
    """
    return await cruds_calendar.get_confirmed_events(db=db)


@module.router.get(
    "/calendar/events/user/{applicant_id}",
    response_model=list[schemas_calendar.EventReturn],
    status_code=200,
)
async def get_applicant_bookings(
    applicant_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_an_ecl_member),
):
    """
    Get one user bookings.

    **Usable by the user or admins**
    """
    if user.id == applicant_id or is_user_member_of_any_group(
        user,
        [GroupType.BDE],
    ):
        return await cruds_calendar.get_applicant_events(
            db=db,
            applicant_id=applicant_id,
        )
    raise HTTPException(status_code=403)


@module.router.get(
    "/calendar/events/{event_id}",
    response_model=schemas_calendar.EventComplete,
    status_code=200,
)
async def get_event_by_id(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_an_ecl_member),
):
    """Get an event's information by its id."""

    event = await cruds_calendar.get_event(db=db, event_id=event_id)
    if event is not None:
        return event
    raise HTTPException(status_code=404)


@module.router.get(
    "/calendar/events/{event_id}/applicant",
    response_model=schemas_calendar.EventApplicant,
    status_code=200,
)
async def get_event_applicant(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.BDE)),
):
    event = await cruds_calendar.get_event(db=db, event_id=event_id)
    if event is not None:
        return event.applicant
    raise HTTPException(status_code=404)


@module.router.post(
    "/calendar/events/",
    response_model=schemas_calendar.EventReturn,
    status_code=201,
)
async def add_event(
    event: schemas_calendar.EventBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_an_ecl_member),
):
    """Add an event to the calendar."""

    event_id = str(uuid.uuid4())

    db_event = models_calendar.Event(
        id=event_id,
        decision=Decision.pending,
        applicant_id=user.id,
        **event.model_dump(),
    )

    return await cruds_calendar.add_event(event=db_event, db=db)


@module.router.patch(
    "/calendar/events/{event_id}",
    status_code=204,
)
async def edit_bookings_id(
    event_id: str,
    event_edit: schemas_calendar.EventEdit,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_an_ecl_member),
):
    """
    Edit an event.

    **Only usable by admins or applicant before decision**
    """
    event = await cruds_calendar.get_event(db=db, event_id=event_id)

    if event is not None and not (
        (user.id == event.applicant_id and event.decision == Decision.pending)
        or is_user_member_of_any_group(user, [GroupType.BDE])
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to edit this event",
        )

    await cruds_calendar.edit_event(event_id=event_id, event=event_edit, db=db)


@module.router.patch(
    "/calendar/events/{event_id}/reply/{decision}",
    status_code=204,
)
async def confirm_booking(
    event_id: str,
    decision: Decision,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.BDE)),
):
    """
    Give a decision to an event.

    **Only usable by admins**
    """
    await cruds_calendar.confirm_event(event_id=event_id, decision=decision, db=db)


@module.router.delete(
    "/calendar/events/{event_id}",
    status_code=204,
)
async def delete_bookings_id(
    event_id,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_an_ecl_member),
):
    """
    Remove an event.

    **Only usable by admins or applicant before decision**
    """
    event = await cruds_calendar.get_event(db=db, event_id=event_id)

    if event is not None and (
        (user.id == event.applicant_id and event.decision == Decision.pending)
        or is_user_member_of_any_group(user, [GroupType.BDE])
    ):
        await cruds_calendar.delete_event(event_id=event_id, db=db)

    else:
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to delete this event",
        )


@module.router.post(
    "/calendar/ical/create",
    status_code=204,
)
async def recreate_ical_file(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Create manually the icalendar file

    **Only usable by global admins**
    """

    await cruds_calendar.create_icalendar_file(db=db)


@module.router.get(
    "/calendar/ical",
    response_class=FileResponse,
    status_code=200,
)
async def get_icalendar_file(db: AsyncSession = Depends(get_db)):
    """Get the icalendar file corresponding to the event in the database."""

    if Path(ical_file_path).exists():
        return FileResponse(ical_file_path)

    raise HTTPException(status_code=404)
