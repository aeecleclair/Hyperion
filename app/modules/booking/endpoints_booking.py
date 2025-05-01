import logging
import uuid
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups import cruds_groups
from app.core.groups.groups_type import AccountType, GroupType
from app.core.notification.schemas_notification import Message
from app.core.users import models_users
from app.dependencies import (
    get_db,
    get_notification_tool,
    is_user_an_ecl_member,
    is_user_in,
)
from app.modules.booking import cruds_booking, models_booking, schemas_booking
from app.modules.booking.types_booking import Decision
from app.types.module import Module
from app.utils.communication.notifications import NotificationTool
from app.utils.tools import is_group_id_valid, is_user_member_of_any_group

module = Module(
    root="booking",
    tag="Booking",
    default_allowed_account_types=[AccountType.student, AccountType.staff],
)

hyperion_error_logger = logging.getLogger("hyperion.error")


@module.router.get(
    "/booking/managers",
    response_model=list[schemas_booking.Manager],
    status_code=200,
)
async def get_managers(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Get existing managers.

    **This endpoint is only usable by administrators**
    """

    return await cruds_booking.get_managers(db=db)


@module.router.post(
    "/booking/managers",
    response_model=schemas_booking.Manager,
    status_code=201,
)
async def create_manager(
    manager: schemas_booking.ManagerBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
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


@module.router.patch(
    "/booking/managers/{manager_id}",
    status_code=204,
)
async def update_manager(
    manager_id: str,
    manager_update: schemas_booking.ManagerUpdate,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Update a manager, the request should contain a JSON with the fields to change (not necessarily all fields) and their new value.

    **This endpoint is only usable by administrators**
    """

    # We need to check that manager.group_id is a valid group
    if manager_update.group_id is not None and not await is_group_id_valid(
        manager_update.group_id,
        db=db,
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid id, group_id must be a valid group id",
        )

    await cruds_booking.update_manager(
        manager_id=manager_id,
        manager_update=manager_update,
        db=db,
    )


@module.router.delete(
    "/booking/managers/{manager_id}",
    status_code=204,
)
async def delete_manager(
    manager_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Delete a manager only if the manager is not linked to any room

    **This endpoint is only usable by administrators**
    """

    manager = await cruds_booking.get_manager_by_id(db=db, manager_id=manager_id)
    if manager.rooms:
        raise HTTPException(
            status_code=403,
            detail="There are still rooms linked to this manager",
        )
    await cruds_booking.delete_manager(manager_id=manager_id, db=db)


@module.router.get(
    "/booking/managers/users/me",
    response_model=list[schemas_booking.Manager],
    status_code=200,
)
async def get_current_user_managers(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_an_ecl_member),
):
    """
    Return all managers the current user is a member.

    **The user must be authenticated to use this endpoint**
    """

    return await cruds_booking.get_user_managers(user=user, db=db)


@module.router.get(
    "/booking/bookings/users/me/manage",
    response_model=list[schemas_booking.BookingReturnApplicant],
    status_code=200,
)
async def get_bookings_for_manager(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_an_ecl_member),
):
    """
    Return all bookings a user can manage.

    **The user must be authenticated to use this endpoint**
    """

    user_managers = await cruds_booking.get_user_managers(user=user, db=db)
    managers_id = [manager.id for manager in user_managers]

    bookings = await cruds_booking.get_bookings(db=db)

    return [booking for booking in bookings if booking.room.manager_id in managers_id]


@module.router.get(
    "/booking/bookings/confirmed/users/me/manage",
    response_model=list[schemas_booking.BookingReturnApplicant],
    status_code=200,
)
async def get_confirmed_bookings_for_manager(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_an_ecl_member),
):
    """
    Return all confirmed bookings a user can manage.
    **The user must be authenticated to use this endpoint**
    """

    user_managers = await cruds_booking.get_user_managers(user=user, db=db)
    managers_id = [manager.id for manager in user_managers]

    bookings = await cruds_booking.get_confirmed_bookings(db=db)

    return [booking for booking in bookings if booking.room.manager_id in managers_id]


@module.router.get(
    "/booking/bookings/confirmed",
    response_model=list[schemas_booking.BookingReturnSimpleApplicant],
    status_code=200,
)
async def get_confirmed_bookings(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_an_ecl_member),
):
    """
    Return all confirmed bookings.

    **The user must be authenticated to use this endpoint**
    """

    return await cruds_booking.get_confirmed_bookings(db=db)



@module.router.get(
    "/booking/bookings/users/me",
    response_model=list[schemas_booking.BookingReturn],
    status_code=200,
)
async def get_applicant_bookings(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_an_ecl_member),
):
    """
    Get the user bookings.

    **Only usable by the user**
    """
    return await cruds_booking.get_applicant_bookings(db=db, applicant_id=user.id)


@module.router.post(
    "/booking/bookings",
    response_model=schemas_booking.BookingReturn,
    status_code=201,
)
async def create_booking(
    booking: schemas_booking.BookingBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_an_ecl_member),
    notification_tool: NotificationTool = Depends(get_notification_tool),
):
    """
    Create a booking.

    **The user must be authenticated to use this endpoint**
    """
    db_booking = schemas_booking.BookingComplete(
        id=str(uuid.uuid4()),
        decision=Decision.pending,
        applicant_id=user.id,
        **booking.model_dump(),
    )
    await cruds_booking.create_booking(booking=db_booking, db=db)
    result = await cruds_booking.get_booking_by_id(db=db, booking_id=db_booking.id)
    manager_group_id = result.room.manager_id
    manager = await cruds_booking.get_manager_by_id(
        db=db,
        manager_id=manager_group_id,
    )
    group = await cruds_groups.get_group_by_id(group_id=manager.group_id, db=db)

    local_start = result.start.astimezone(ZoneInfo("Europe/Paris"))
    applicant_nickname = user.nickname if user.nickname else user.firstname
    content = f"{applicant_nickname} - {result.room.name} {local_start.strftime('%m/%d/%Y, %H:%M')} - {result.reason}"
    # Setting time to Paris timezone in order to have the correct time in the notification

    if group:
        message = Message(
            title="📅 Réservations - Nouvelle réservation",
            content=content,
            action_module="booking",
        )

        await notification_tool.send_notification_to_users(
            user_ids=[user.id for user in group.members],
            message=message,
        )

    return result


@module.router.patch(
    "/booking/bookings/{booking_id}",
    status_code=204,
)
async def edit_booking(
    booking_id: str,
    booking_edit: schemas_booking.BookingEdit,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_an_ecl_member),
):
    """
    Edit a booking.

    **Only usable by a user in the manager group of the booking or applicant before decision**
    """
    booking: models_booking.Booking = await cruds_booking.get_booking_by_id(
        db=db,
        booking_id=booking_id,
    )

    if not (
        (user.id == booking.applicant_id and booking.decision == Decision.pending)
        or is_user_member_of_any_group(user, [booking.room.manager.group_id])
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to edit this booking",
        )

    try:
        await cruds_booking.edit_booking(
            booking_id=booking_id,
            booking=booking_edit,
            db=db,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@module.router.patch(
    "/booking/bookings/{booking_id}/reply/{decision}",
    status_code=204,
)
async def confirm_booking(
    booking_id: str,
    decision: Decision,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_an_ecl_member),
):
    """
    Give a decision to a booking.

    **Only usable by a user in the manager group of the booking**
    """

    booking: models_booking.Booking = await cruds_booking.get_booking_by_id(
        db=db,
        booking_id=booking_id,
    )

    if is_user_member_of_any_group(user, [booking.room.manager.group_id]):
        await cruds_booking.confirm_booking(
            booking_id=booking_id,
            decision=decision,
            db=db,
        )
    else:
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to give a decision to this booking",
        )


@module.router.delete(
    "/booking/bookings/{booking_id}",
    status_code=204,
)
async def delete_booking(
    booking_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_an_ecl_member),
):
    """
    Remove a booking.

    **Only usable by the applicant before decision**
    """

    booking: models_booking.Booking = await cruds_booking.get_booking_by_id(
        db=db,
        booking_id=booking_id,
    )

    if user.id == booking.applicant_id and booking.decision == Decision.pending:
        await cruds_booking.delete_booking(booking_id=booking_id, db=db)

    else:
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to delete this booking",
        )


@module.router.get(
    "/booking/rooms",
    response_model=list[schemas_booking.RoomComplete],
    status_code=200,
)
async def get_rooms(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_an_ecl_member),
):
    """
    Get all rooms.

    **The user must be authenticated to use this endpoint**
    """

    return await cruds_booking.get_rooms(db=db)


@module.router.post(
    "/booking/rooms",
    response_model=schemas_booking.RoomComplete,
    status_code=201,
)
async def create_room(
    room: schemas_booking.RoomBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Create a new room in database.

    **This endpoint is only usable by admins**
    """

    try:
        room_db = models_booking.Room(
            id=str(uuid.uuid4()),
            **room.model_dump(),
        )
        return await cruds_booking.create_room(db=db, room=room_db)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@module.router.patch(
    "/booking/rooms/{room_id}",
    status_code=204,
)
async def edit_room(
    room_id: str,
    room: schemas_booking.RoomBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Edit a room.

    **This endpoint is only usable by admins**
    """

    await cruds_booking.edit_room(db=db, room_id=room_id, room=room)


@module.router.delete(
    "/booking/rooms/{room_id}",
    status_code=204,
)
async def delete_room(
    room_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Delete a room only if there are not future or ongoing bookings of this room

    **This endpoint is only usable by admins**
    """
    room = await cruds_booking.get_room_by_id(db=db, room_id=room_id)
    if all(booking.end < datetime.now(UTC) for booking in room.bookings):
        await cruds_booking.delete_room(db=db, room_id=room_id)
    else:
        raise HTTPException(
            status_code=403,
            detail="There are still future or ongoing bookings of this room",
        )
