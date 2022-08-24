import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_bdebooking
from app.dependencies import get_db, is_user_a_member, is_user_a_member_of
from app.models import models_core
from app.schemas import schemas_bdebooking
from app.utils.tools import is_user_member_of_an_allowed_group
from app.utils.types.bdebooking_type import Decision
from app.utils.types.groups_type import GroupType
from app.utils.types.tags import Tags

router = APIRouter()


@router.get(
    "bdebooking/rights",
    response_model=schemas_bdebooking.Rights,
    status_code=200,
    tags=[Tags.bdebooking],
)
async def get_rights(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    view = is_user_member_of_an_allowed_group(
        user, [GroupType.student, GroupType.staff]
    )
    manage = is_user_member_of_an_allowed_group(user, [GroupType.BDE])
    return schemas_bdebooking.Rights(view=view, manage=manage)


@router.get(
    "/bdebooking/bookings",
    response_model=list[schemas_bdebooking.BookingReturn],
    status_code=200,
    tags=[Tags.bdebooking],
)
async def get_confirmed_bookings(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.BDE)),
):
    bookings = await cruds_bdebooking.get_bookings(db=db, decision=Decision.approved)
    return bookings


@router.get(
    "/bdebooking/bookings/unconfirmed",
    response_model=list[schemas_bdebooking.BookingReturn],
    status_code=200,
    tags=[Tags.bdebooking],
)
async def get_unconfirmed_bookings(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.BDE)),
):
    bookings = await cruds_bdebooking.get_bookings(db=db, decision=Decision.pending)
    return bookings


@router.get(
    "/bdebooking/bookings/declined",
    response_model=list[schemas_bdebooking.BookingReturn],
    status_code=200,
    tags=[Tags.bdebooking],
)
async def get_declined_bookings(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.BDE)),
):
    bookings = await cruds_bdebooking.get_bookings(db=db, decision=Decision.declined)
    return bookings


@router.get(
    "/bdebooking/user/{applicant_id}",
    response_model=list[schemas_bdebooking.BookingReturn],
    status_code=200,
    tags=[Tags.bdebooking],
)
async def get_applicant_bookings(
    applicant_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    if user.id == applicant_id or is_user_member_of_an_allowed_group(
        user, [GroupType.BDE]
    ):
        bookings = await cruds_bdebooking.get_applicant_bookings(
            db=db, applicant_id=applicant_id
        )
        return bookings
    else:
        raise HTTPException(status_code=403)


@router.get(
    "/bdebooking/bookings/{booking_id}",
    response_model=schemas_bdebooking.BookingReturn,
    status_code=200,
    tags=[Tags.bdebooking],
)
async def get_booking_by_id(
    booking_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    booking = await cruds_bdebooking.get_booking_by_id(db=db, booking_id=booking_id)
    if booking is not None:
        if booking.applicant_id == user.id or is_user_member_of_an_allowed_group(
            user, [GroupType.BDE]
        ):
            return booking
        else:
            raise HTTPException(status_code=403)
    else:
        raise HTTPException(status_code=404)


@router.post("/bdebooking/bookings", status_code=201, tags=[Tags.bdebooking])
async def create_bookings(
    booking: schemas_bdebooking.BookingBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    db_booking = schemas_bdebooking.BookingComplete(
        id=str(uuid.uuid4()), decision=Decision.pending, **booking.dict()
    )
    try:
        await cruds_bdebooking.create_booking(booking=db_booking, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.patch("/bdebooking/bookings", status_code=204, tags=[Tags.bdebooking])
async def edit_bookings_id(
    booking: schemas_bdebooking.BookingEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.BDE)),
):

    try:
        await cruds_bdebooking.edit_booking(booking=booking, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.patch(
    "/bdebooking/bookings/{booking_id}/reply/{decision}",
    status_code=204,
    tags=[Tags.bdebooking],
)
async def confirm_booking(
    booking_id: str,
    decision: Decision,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.BDE)),
):
    await cruds_bdebooking.confirm_booking(
        booking_id=booking_id, decision=decision, db=db
    )


@router.delete(
    "/bdebooking/bookings/{booking_id}", status_code=204, tags=[Tags.bdebooking]
)
async def delete_bookings_id(
    booking_id,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.BDE)),
):
    await cruds_bdebooking.delete_booking(booking_id=booking_id, db=db)


@router.get(
    "/bdebooking/rooms",
    response_model=list[schemas_bdebooking.RoomComplete],
    status_code=200,
    tags=[Tags.bdebooking],
)
async def get_rooms(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    return await cruds_bdebooking.get_rooms(db=db)


@router.get(
    "/bdebooking/rooms/{room_id}",
    response_model=schemas_bdebooking.RoomComplete,
    status_code=200,
    tags=[Tags.bdebooking],
)
async def get_room_by_id(
    room_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.BDE)),
):
    return await cruds_bdebooking.get_room_by_id(db=db, room_id=room_id)


@router.post(
    "/bdebooking/rooms",
    response_model=schemas_bdebooking.RoomComplete,
    status_code=201,
    tags=[Tags.bdebooking],
)
async def create_room(
    room: schemas_bdebooking.RoomBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.BDE)),
):
    db_room = schemas_bdebooking.RoomComplete(id=str(uuid.uuid4()), **room.dict())
    await cruds_bdebooking.create_room(db=db, room=db_room)
    return db_room


@router.patch(
    "/bdebooking/rooms",
    status_code=204,
    tags=[Tags.bdebooking],
)
async def edit_room(
    room: schemas_bdebooking.RoomComplete,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.BDE)),
):
    await cruds_bdebooking.edit_room(db=db, room=room)


@router.delete(
    "/bdebooking/rooms/{room_id}",
    status_code=204,
    tags=[Tags.bdebooking],
)
async def delete_room(
    room_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.BDE)),
):
    await cruds_bdebooking.delete_room(db=db, room_id=room_id)
