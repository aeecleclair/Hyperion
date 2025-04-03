import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.groups_type import GroupType
from app.core.ticket import cruds_ticket, schemas_ticket
from app.core.users import models_users, schemas_users
from app.dependencies import (
    get_db,
    is_user,
    is_user_a_member,
)
from app.utils.tools import (
    is_user_member_of_any_group,
)

router = APIRouter(tags=["Tickets"])

hyperion_error_logger = logging.getLogger("hyperion.error")


@router.get(
    "/tickets/users/me/",
    response_model=list[schemas_ticket.Ticket],
    status_code=200,
)
async def get_my_tickets(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user),
):
    return await cruds_ticket.get_tickets_of_user(db=db, user_id=user.id)


@router.get(
    "/tickets/users/{user_id}/",
    response_model=list[schemas_ticket.Ticket],
    status_code=200,
)
async def get_tickets_of_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user),
):
    if not (
        is_user_member_of_any_group(user, [GroupType.admin_purchases])
        or user_id == user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="You can't get another user tickets.",
        )
    return await cruds_ticket.get_tickets_of_user(db=db, user_id=user_id)


@router.get(
    "/tickets/{ticket_id}/secret/",
    response_model=schemas_ticket.TicketSecret,
    status_code=200,
)
async def get_ticket_secret(
    ticket_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user),
):
    ticket = await cruds_ticket.get_ticket(db=db, ticket_id=ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found.",
        )
    if ticket.user_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="You can't get another user ticket secret.",
        )
    return schemas_ticket.TicketSecret(qr_code_secret=ticket.secret)


@router.get(
    "/tickets/generator/{generator_id}/{secret}/",
    response_model=schemas_ticket.Ticket,
    status_code=200,
)
async def get_ticket_by_secret(
    generator_id: UUID,
    secret: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_a_member),
):
    ticket_generator = await cruds_ticket.get_ticket_generator(
        db=db,
        ticket_generator_id=generator_id,
    )
    if not ticket_generator:
        raise HTTPException(
            status_code=404,
            detail="Ticket generator not found.",
        )
    if ticket_generator.scanner_group_id not in [group.id for group in user.groups]:
        raise HTTPException(
            status_code=403,
            detail="User is not allowed to scan this ticket.",
        )
    ticket = await cruds_ticket.get_ticket_by_secret(db=db, secret=secret)
    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found.",
        )
    if ticket.generator_id != generator_id:
        raise HTTPException(
            status_code=404,
            detail="This Ticket is not of the good type.",
        )
    return ticket


@router.patch(
    "/tickets/generator/{generator_id}/{secret}/",
    status_code=204,
)
async def scan_ticket(
    generator_id: UUID,
    secret: UUID,
    ticket_data: schemas_ticket.TicketScan,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_a_member),
):
    ticket_generator = await cruds_ticket.get_ticket_generator(
        db=db,
        ticket_generator_id=generator_id,
    )
    if not ticket_generator:
        raise HTTPException(
            status_code=404,
            detail="Ticket generator not found.",
        )
    if ticket_generator.scanner_group_id not in [group.id for group in user.groups]:
        raise HTTPException(
            status_code=403,
            detail="User is not allowed to scan this ticket.",
        )
    ticket = await cruds_ticket.get_ticket_by_secret(db=db, secret=secret)
    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found.",
        )
    if ticket.generator_id != generator_id:
        raise HTTPException(
            status_code=404,
            detail="This Ticket is not of the good type.",
        )
    if ticket.scan_left <= 0:
        raise HTTPException(
            status_code=403,
            detail="This ticket has already been used for the maximum amount.",
        )
    if ticket.expiration < datetime.now(tz=UTC):
        raise HTTPException(
            status_code=403,
            detail="This ticket has expired.",
        )
    try:
        await cruds_ticket.scan_ticket(
            db=db,
            ticket_id=ticket.id,
            scan=ticket.scan_left - 1,
            tags=ticket.tags + "," + ticket_data.tag
            if ticket.tags != ""
            else ticket_data.tag,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise


@router.get(
    "/tickets/generator/{generator_id}/lists/{tag}/",
    response_model=list[schemas_users.CoreUserSimple],
    status_code=200,
)
async def get_users_by_tag(
    generator_id: UUID,
    tag: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_a_member),
):
    ticket_generator = await cruds_ticket.get_ticket_generator(
        db=db,
        ticket_generator_id=generator_id,
    )
    if not ticket_generator:
        raise HTTPException(
            status_code=404,
            detail="Ticket generator not found.",
        )

    if ticket_generator.scanner_group_id not in [group.id for group in user.groups]:
        raise HTTPException(
            status_code=403,
            detail="User is not allowed to scan this ticket.",
        )

    tickets = await cruds_ticket.get_tickets_by_tag(
        db=db,
        generator_id=generator_id,
        tag=tag,
    )

    return [ticket.user for ticket in tickets]


@router.get(
    "/tickets/tags/generator/{generator_id}/",
    response_model=list[str],
    status_code=200,
)
async def get_tags_of_ticket(
    generator_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_a_member),
):
    ticket_generator = await cruds_ticket.get_ticket_generator(
        db=db,
        ticket_generator_id=generator_id,
    )
    if not ticket_generator:
        raise HTTPException(
            status_code=404,
            detail="Ticket generator not found.",
        )

    if ticket_generator.scanner_group_id not in [group.id for group in user.groups]:
        raise HTTPException(
            status_code=403,
            detail="User is not allowed to scan this ticket.",
        )

    tickets = await cruds_ticket.get_tickets_by_generator(
        db=db,
        generator_id=generator_id,
    )

    tags = set()
    for ticket in tickets:
        for tag in ticket.tags.split(","):
            tags.add(tag)
    return list(tags)
