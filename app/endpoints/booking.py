import logging
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.cruds import cruds_booking
from app.dependencies import (
    get_db,
    get_notification_tool,
    get_settings,
    is_user_a_member,
    is_user_a_member_of,
)
from app.models import models_booking, models_core
from app.schemas import schemas_booking
from app.schemas.schemas_notification import Message
from app.utils.tools import is_group_id_valid, is_user_member_of_an_allowed_group
from app.utils.types.booking_type import Decision
from app.utils.types.groups_type import GroupType
from app.utils.types.notification_types import CustomTopic, Topic
from app.utils.types.tags import Tags

router = APIRouter()

hyperion_error_logger = logging.getLogger("hyperion.error")


@router.get(
    "/booking/managers",
    response_model=list[schemas_booking.Manager],
    status_code=200,
    tags=[Tags.booking],
)
async def get_managers(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Get existing managers.

    **This endpoint is only usable by administrators**
    """

    return await cruds_booking.get_managers(db=db)


@router.post(
    "/booking/managers",
    response_model=schemas_booking.Manager,
    status_code=201,
    tags=[Tags.booking],
)
async def create_manager(
    manager: schemas_booking.ManagerBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Create a manager.

    **This endpoint is only usable by administrators**
    """

    # We need to check that manager.group_id is a valid group
    if not await is_group_id_valid(manager.group_id, db=db):
        raise HTTPException(
            status_code=400,
            detail="Invalid id, group_id must be a valid group id",
        )

    try:
        manager_db = models_booking.Manager(
            id=str(uuid.uuid4()),
            name=manager.name,
            group_id=manager.group_id,
        )

        return await cruds_booking.create_manager(manager=manager_db, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.patch(
    "/booking/managers/{manager_id}",
    status_code=204,
    tags=[Tags.booking],
)
async def update_manager(
    manager_id: str,
    manager_update: schemas_booking.ManagerUpdate,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Update a manager, the request should contain a JSON with the fields to change (not necessarily all fields) and their new value.

    **This endpoint is only usable by administrators**
    """

    # We need to check that manager.group_id is a valid group
    if manager_update.group_id is not None and not await is_group_id_valid(
        manager_update.group_id, db=db
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid id, group_id must be a valid group id",
        )

    await cruds_booking.update_manager(
        manager_id=manager_id, manager_update=manager_update, db=db
    )


@router.delete(
    "/booking/managers/{manager_id}",
    status_code=204,
    tags=[Tags.booking],
)
async def delete_manager(
    manager_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Delete a manager only if the manager is not linked to any room

    **This endpoint is only usable by administrators**
    """

    manager = await cruds_booking.get_manager_by_id(db=db, manager_id=manager_id)
    if manager.rooms:
        raise HTTPException(
            status_code=403, detail=str("There are still rooms linked to this manager")
        )
    else:
        await cruds_booking.delete_manager(manager_id=manager_id, db=db)


@router.get(
    "/booking/managers/users/me",
    response_model=list[schemas_booking.Manager],
    status_code=200,
    tags=[Tags.booking],
)
async def get_current_user_managers(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Return all managers the current user is a member.

    **The user must be authenticated to use this endpoint**
    """

    return await cruds_booking.get_user_managers(user=user, db=db)


@router.get(
    "/booking/bookings/users/me/manage",
    response_model=list[schemas_booking.BookingReturnApplicant],
    status_code=200,
    tags=[Tags.booking],
)
async def get_bookings_for_manager(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Return all bookings a user can manage.

    **The user must be authenticated to use this endpoint**
    """

    user_managers = await cruds_booking.get_user_managers(user=user, db=db)

    bookings = await cruds_booking.get_bookings(db=db)

    return [booking for booking in bookings if booking.room.manager in user_managers]


@router.get(
    "/booking/bookings/confirmed/users/me/manage",
    response_model=list[schemas_booking.BookingReturnApplicant],
    status_code=200,
    tags=[Tags.booking],
)
async def get_confirmed_bookings_for_manager(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Return all confirmed bookings a user can manage.
    **The user must be authenticated to use this endpoint**
    """

    user_managers = await cruds_booking.get_user_managers(user=user, db=db)

    bookings = await cruds_booking.get_confirmed_bookings(db=db)

    return [booking for booking in bookings if booking.room.manager in user_managers]


@router.get(
    "/booking/bookings/confirmed",
    response_model=list[schemas_booking.BookingReturn],
    status_code=200,
    tags=[Tags.booking],
)
async def get_confirmed_bookings(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Return all confirmed bookings.

    **The user must be authenticated to use this endpoint**
    """

    bookings = await cruds_booking.get_confirmed_bookings(db=db)

    return bookings


@router.get(
    "/booking/bookings/users/me",
    response_model=list[schemas_booking.BookingReturn],
    status_code=200,
    tags=[Tags.booking],
)
async def get_applicant_bookings(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get the user bookings.

    **Only usable by the user**
    """
    bookings = await cruds_booking.get_applicant_bookings(db=db, applicant_id=user.id)
    return bookings


@router.post(
    "/booking/bookings",
    response_model=schemas_booking.BookingReturn,
    status_code=201,
    tags=[Tags.booking],
)
async def create_booking(
    booking: schemas_booking.BookingBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
    settings: Settings = Depends(get_settings),
    notification_tool=Depends(get_notification_tool),
):
    """
    Create a booking.

    **The user must be authenticated to use this endpoint**
    """
    db_booking = schemas_booking.BookingComplete(
        id=str(uuid.uuid4()),
        decision=Decision.pending,
        applicant_id=user.id,
        **booking.dict(),
    )
    await cruds_booking.create_booking(booking=db_booking, db=db)
    result = await cruds_booking.get_booking_by_id(db=db, booking_id=db_booking.id)

    try:
        if result:
            now = datetime.now(ZoneInfo(settings.TIMEZONE))
            message = Message(
                # We use sunday date as context to avoid sending the recap twice
                context=f"booking-create-{result.id}",
                is_visible=True,
                title="Réservations - Nouvelle réservation 📅",
                content=f"{result.applicant.nickname} - {result.room.name} {result.start.strftime('%m/%d/%Y, %H:%M')} - {result.reason}",
                # The notification will expire the next sunday
                expire_on=now.replace(day=now.day + 3),
            )
            await notification_tool.send_notification_to_topic(
                topic=CustomTopic(topic=Topic.bookingadmin),
                message=message,
            )
    except Exception as error:
        hyperion_error_logger.error(
            f"Error while sending cinema recap notification, {error}"
        )

    return result


@router.patch(
    "/booking/bookings/{booking_id}",
    status_code=204,
    tags=[Tags.booking],
)
async def edit_booking(
    booking_id: str,
    booking_edit: schemas_booking.BookingEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Edit a booking.

    **Only usable by a user in the manager group of the booking or applicant before decision**
    """
    booking: models_booking.Booking = await cruds_booking.get_booking_by_id(
        db=db, booking_id=booking_id
    )

    if not (
        (user.id == booking.applicant_id and booking.decision == Decision.pending)
        or is_user_member_of_an_allowed_group(user, [booking.room.manager.group_id])
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to edit this booking",
        )

    try:
        await cruds_booking.edit_booking(
            booking_id=booking_id, booking=booking_edit, db=db
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.patch(
    "/booking/bookings/{booking_id}/reply/{decision}",
    status_code=204,
    tags=[Tags.booking],
)
async def confirm_booking(
    booking_id: str,
    decision: Decision,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Give a decision to a booking.

    **Only usable by a user in the manager group of the booking**
    """

    booking: models_booking.Booking = await cruds_booking.get_booking_by_id(
        db=db, booking_id=booking_id
    )

    if is_user_member_of_an_allowed_group(user, [booking.room.manager.group_id]):
        await cruds_booking.confirm_booking(
            booking_id=booking_id, decision=decision, db=db
        )
    else:
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to delete this booking",
        )


@router.delete(
    "/booking/bookings/{booking_id}",
    status_code=204,
    tags=[Tags.booking],
)
async def delete_booking(
    booking_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Remove a booking.

    **Only usable by the applicant before decision**
    """

    booking: models_booking.Booking = await cruds_booking.get_booking_by_id(
        db=db, booking_id=booking_id
    )

    if user.id == booking.applicant_id and booking.decision == Decision.pending:
        await cruds_booking.delete_booking(booking_id=booking_id, db=db)

    else:
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to delete this booking",
        )


@router.get(
    "/booking/rooms",
    response_model=list[schemas_booking.RoomComplete],
    status_code=200,
    tags=[Tags.booking],
)
async def get_rooms(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get all rooms.

    **The user must be authenticated to use this endpoint**
    """

    return await cruds_booking.get_rooms(db=db)


@router.post(
    "/booking/rooms",
    response_model=schemas_booking.RoomComplete,
    status_code=201,
    tags=[Tags.booking],
)
async def create_room(
    room: schemas_booking.RoomBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Create a new room in database.

    **This endpoint is only usable by admins**
    """

    try:
        room_db = models_booking.Room(
            id=str(uuid.uuid4()),
            **room.dict(),
        )
        return await cruds_booking.create_room(db=db, room=room_db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.patch(
    "/booking/rooms/{room_id}",
    status_code=204,
    tags=[Tags.booking],
)
async def edit_room(
    room_id: str,
    room: schemas_booking.RoomBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Edit a room.

    **This endpoint is only usable by admins**
    """

    await cruds_booking.edit_room(db=db, room_id=room_id, room=room)


@router.delete(
    "/booking/rooms/{room_id}",
    status_code=204,
    tags=[Tags.booking],
)
async def delete_room(
    room_id: str,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Delete a room only if there are not future or ongoing bookings of this room

    **This endpoint is only usable by admins**
    """
    room = await cruds_booking.get_room_by_id(db=db, room_id=room_id)
    if all(
        map(
            lambda b: b.end.replace(tzinfo=ZoneInfo(settings.TIMEZONE))
            < datetime.now(timezone.utc),
            room.bookings,
        )
    ):
        await cruds_booking.delete_room(db=db, room_id=room_id)
    else:
        raise HTTPException(
            status_code=403,
            detail=str("There are still future or ongoing bookings of this room"),
        )
