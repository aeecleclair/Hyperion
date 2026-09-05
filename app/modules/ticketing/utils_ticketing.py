from uuid import UUID

from fastapi import HTTPException
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.mypayment import cruds_mypayment
from app.core.users import models_users
from app.modules.ticketing import cache_ticketing, cruds_ticketing, schemas_ticketing


async def check_scan_permission_for_seller(
    db: AsyncSession,
    redis: Redis | None,
    user: models_users.CoreUser,
    ticket: schemas_ticketing.TicketComplete,
):
    """Check if the user has permission to scan the ticket."""
    cache_result = await cache_ticketing.get_scan_permission_for_seller_with_cache(
        redis=redis,
        user_id=user.id,
        event_id=ticket.event.id,
    )
    if cache_result is not None:
        if not cache_result:
            raise HTTPException(
                status_code=403,
                detail="User does not have permission to scan tickets for this organiser",
            )
        return  # User has permission, no need to check the database

    organiser = await cruds_ticketing.get_organiser_by_id(
        organiser_id=ticket.event.organiser_id,
        db=db,
    )
    if organiser is None:
        raise HTTPException(status_code=404, detail="Organiser not found")
    store = await cruds_mypayment.get_store(
        store_id=organiser.store_id,
        db=db,
    )
    if store is None:
        raise HTTPException(status_code=404, detail="Store not found")

    seller = await cruds_mypayment.get_seller(
        store_id=organiser.store_id,
        user_id=user.id,
        db=db,
    )

    if seller is None or not seller.can_bank:
        raise HTTPException(
            status_code=403,
            detail="User does not have permission to scan tickets for this organiser",
        )


async def check_manage_event_permission_for_user(
    db: AsyncSession,
    redis: Redis | None,
    user: models_users.CoreUser,
    event_id: UUID,
):
    """Check if the user has permission to manage the event."""
    # Use a cache layer to avoid multiple queries for the same event_id and user_id
    cache_result = await cache_ticketing.get_manage_event_permission_with_cache(
        redis=redis,
        user_id=user.id,
        event_id=event_id,
    )
    if cache_result is not None:
        if not cache_result:
            raise HTTPException(
                status_code=403,
                detail="User does not have permission to manage this event",
            )
        return  # User has permission, no need to check the database
    event = await cruds_ticketing.get_event_by_id(
        event_id=event_id,
        db=db,
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    await check_manage_event_for_organiser_by_user(
        db=db,
        user=user,
        organiser_id=event.organiser_id,
    )


async def check_manage_event_for_organiser_by_user(
    db: AsyncSession,
    user: models_users.CoreUser,
    organiser_id: UUID,
):
    """Check if the user has permission to manage the organiser."""
    organiser = await cruds_ticketing.get_organiser_by_id(
        organiser_id=organiser_id,
        db=db,
    )
    if organiser is None:
        raise HTTPException(status_code=404, detail="Organiser not found")
    store = await cruds_mypayment.get_store(
        store_id=organiser.store_id,
        db=db,
    )
    if store is None:
        raise HTTPException(status_code=404, detail="Store not found")

    seller = await cruds_mypayment.get_seller(
        store_id=organiser.store_id,
        user_id=user.id,
        db=db,
    )

    if seller is None:  # TODO: check if : or not seller.can_manage_events
        raise HTTPException(
            status_code=403,
            detail="User does not have permission to manage this organiser",
        )
