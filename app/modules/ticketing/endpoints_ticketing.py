from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions.type_permissions import ModulePermissions
from app.core.users import models_users
from app.dependencies import get_db, get_redis_client, is_user, is_user_allowed_to
from app.modules.ticketing import cache_ticketing, cruds_ticketing, schemas_ticketing
from app.modules.ticketing.factory_ticketing import TicketingFactory
from app.types.module import Module


class TicketingPermissions(ModulePermissions):
    acess_ticketing = "acess_ticketing"
    manage_events = "manage_events"


router = APIRouter(tags=["Ticketing"])

module = Module(
    root="ticketing",
    tag="Ticketing",
    router=router,
    factory=TicketingFactory(),
)


@module.router.get(
    "/ticketing/events/",
    summary="Get all events",
    response_model=list[schemas_ticketing.EventSimple],
    status_code=200,
)
async def get_events(
    db: AsyncSession = Depends(get_db),
) -> list[schemas_ticketing.EventSimple]:
    """Get all events."""
    return await cruds_ticketing.get_events(db=db)


@module.router.get(
    "/ticketing/events/{event_id}",
    summary="Get an event by its ID",
    response_model=schemas_ticketing.EventComplete,
    status_code=200,
)
async def get_event_by_id(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> schemas_ticketing.EventComplete:
    """Get an event by its ID."""
    event = await cruds_ticketing.get_event_by_id(event_id=event_id, db=db)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@module.router.post(
    "/ticketing/events/",
    summary="Create a new event",
    response_model=schemas_ticketing.EventComplete,
    status_code=201,
)
async def create_event(
    event: schemas_ticketing.EventBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([TicketingPermissions.manage_events]),
    ),
) -> schemas_ticketing.EventComplete:
    """Create a new event."""
    stored = await cruds_ticketing.get_event_by_name(name=event.name, db=db)
    if stored is not None:
        raise HTTPException(status_code=400, detail="Event already exists")
    event = schemas_ticketing.EventSimple(
        **event.model_dump(),
        id=uuid4(),
        creator_id=user.id,
        used_quota=0,
        disabled=False,
    )
    await cruds_ticketing.create_event(event=event, db=db)
    event_complete = await cruds_ticketing.get_event_by_id(event_id=event.id, db=db)
    if event_complete is None:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Event creation failed")
    return event_complete


@module.router.patch(
    "/ticketing/events/{event_id}",
    summary="Update an existing event",
    response_model=None,
    status_code=204,
)
async def update_event(
    event_id: UUID,
    event_update: schemas_ticketing.EventUpdate,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([TicketingPermissions.manage_events]),
    ),
) -> None:
    """Update an existing event."""
    stored = await cruds_ticketing.get_event_by_id(event_id=event_id, db=db)
    if stored is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if event_update.quota is not None and stored.used_quota > event_update.quota:
        raise HTTPException(
            status_code=400,
            detail="Cannot set quota less than used quota",
        )
    await cruds_ticketing.update_event(
        event_id=event_id,
        event_update=event_update,
        db=db,
    )


@module.router.delete(
    "/ticketing/events/{event_id}",
    summary="Delete an existing event",
    response_model=None,
    status_code=204,
)
async def delete_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([TicketingPermissions.manage_events]),
    ),
) -> None:
    """Delete an existing event."""
    stored = await cruds_ticketing.get_event_by_id(event_id=event_id, db=db)
    if stored is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if stored.used_quota > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete an event with used quota",
        )
    await cruds_ticketing.delete_event(event_id=event_id, db=db)


@module.router.get(
    "/ticketing/sessions/{session_id}",
    summary="Get a session by its ID",
    response_model=schemas_ticketing.SessionComplete,
    status_code=200,
)
async def get_session_by_id(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> schemas_ticketing.SessionComplete | None:
    """Get a session by its ID."""
    session = await cruds_ticketing.get_session_by_id(session_id=session_id, db=db)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@module.router.post(
    "/ticketing/sessions/",
    summary="Create a new session",
    response_model=schemas_ticketing.SessionComplete,
    status_code=201,
)
async def create_session(
    session: schemas_ticketing.SessionBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([TicketingPermissions.manage_events]),
    ),
) -> schemas_ticketing.SessionComplete:
    """Create a new session."""
    session_simple = schemas_ticketing.SessionSimple(
        **session.model_dump(),
        id=uuid4(),
        used_quota=0,
        disabled=False,
    )
    await cruds_ticketing.create_session(session=session_simple, db=db)
    session_complete = await cruds_ticketing.get_session_by_id(
        session_id=session_simple.id,
        db=db,
    )
    if session_complete is None:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Session creation failed")
    return session_complete


@module.router.patch(
    "/ticketing/sessions/{session_id}",
    summary="Update an existing session",
    response_model=None,
    status_code=204,
)
async def update_session(
    session_id: UUID,
    session_update: schemas_ticketing.SessionUpdate,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([TicketingPermissions.manage_events]),
    ),
) -> None:
    """Update an existing session."""
    stored = await cruds_ticketing.get_session_by_id(session_id=session_id, db=db)
    if stored is None:
        raise HTTPException(status_code=404, detail="Session not found")
    await cruds_ticketing.update_session(
        session_id=session_id,
        session_update=session_update,
        db=db,
    )


@module.router.delete(
    "/ticketing/sessions/{session_id}",
    summary="Delete an existing session",
    response_model=None,
    status_code=204,
)
async def delete_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([TicketingPermissions.manage_events]),
    ),
) -> None:
    """Delete an existing session."""
    stored = await cruds_ticketing.get_session_by_id(session_id=session_id, db=db)
    if stored is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if stored.used_quota > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a session with used quota",
        )
    await cruds_ticketing.delete_session(session_id=session_id, db=db)


@module.router.get(
    "/ticketing/categories/{category_id}",
    summary="Get a category by its ID",
    response_model=schemas_ticketing.CategoryComplete,
    status_code=200,
)
async def get_category_by_id(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> schemas_ticketing.CategoryComplete | None:
    """Get a category by its ID."""
    category = await cruds_ticketing.get_category_by_id(category_id=category_id, db=db)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@module.router.post(
    "/ticketing/categories/",
    summary="Create a new category",
    response_model=schemas_ticketing.CategoryComplete,
    status_code=201,
)
async def create_category(
    category: schemas_ticketing.CategoryBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([TicketingPermissions.manage_events]),
    ),
) -> schemas_ticketing.CategoryComplete:
    """Create a new category."""
    category_complete = schemas_ticketing.CategoryComplete(
        **category.model_dump(),
        id=uuid4(),
        used_quota=0,
        disabled=False,
    )
    await cruds_ticketing.create_category(category=category_complete, db=db)
    return category_complete


@module.router.patch(
    "/ticketing/categories/{category_id}",
    summary="Update an existing category",
    response_model=None,
    status_code=204,
)
async def update_category(
    category_id: UUID,
    category_update: schemas_ticketing.CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([TicketingPermissions.manage_events]),
    ),
) -> None:
    """Update an existing category."""
    stored = await cruds_ticketing.get_category_by_id(category_id=category_id, db=db)
    if stored is None:
        raise HTTPException(status_code=404, detail="Category not found")
    await cruds_ticketing.update_category(
        category_id=category_id,
        category_update=category_update,
        db=db,
    )


@module.router.delete(
    "/ticketing/categories/{category_id}",
    summary="Delete an existing category",
    response_model=None,
    status_code=204,
)
async def delete_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([TicketingPermissions.manage_events]),
    ),
) -> None:
    """Delete an existing category."""
    stored = await cruds_ticketing.get_category_by_id(category_id=category_id, db=db)
    if stored is None:
        raise HTTPException(status_code=404, detail="Category not found")
    if stored.used_quota > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a category with used quota",
        )
    await cruds_ticketing.delete_category(category_id=category_id, db=db)


@module.router.get(
    "/ticketing/tickets/{ticket_id}",
    summary="Get a ticket by its ID",
    response_model=schemas_ticketing.TicketComplete,
    status_code=200,
)
async def get_ticket_by_id(
    ticket_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> schemas_ticketing.TicketComplete | None:
    """Get a ticket by its ID."""
    ticket = await cruds_ticketing.get_ticket_by_id(ticket_id=ticket_id, db=db)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@module.router.get(
    "/ticketing/tickets/",
    summary="Get all tickets",
    response_model=list[schemas_ticketing.TicketComplete],
    status_code=200,
)
async def get_all_tickets(
    db: AsyncSession = Depends(get_db),
) -> list[schemas_ticketing.TicketComplete]:
    """Get all tickets."""
    return await cruds_ticketing.get_tickets(db=db)


@module.router.get(
    "/ticketing/users/{user_id}/tickets/",
    summary="Get all tickets for a user",
    response_model=list[schemas_ticketing.TicketComplete],
    status_code=200,
)
async def get_tickets_by_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[schemas_ticketing.TicketComplete]:
    """Get all tickets for a user."""
    return await cruds_ticketing.get_tickets_by_user_id(user_id=user_id, db=db)


@module.router.get(
    "/ticketing/users/me/tickets/",
    summary="Get all tickets for a user",
    response_model=list[schemas_ticketing.TicketComplete],
    status_code=200,
)
async def get_my_tickets(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
) -> list[schemas_ticketing.TicketComplete]:
    """Get all tickets for a user."""
    return await cruds_ticketing.get_tickets_by_user_id(user_id=user.id, db=db)


@module.router.post(
    "/ticketing/tickets/",
    summary="Create a new ticket",
    response_model=schemas_ticketing.TicketComplete,
    status_code=201,
)
async def create_ticket(
    ticket: schemas_ticketing.TicketBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
    redis_client: Redis | None = Depends(get_redis_client),
) -> schemas_ticketing.TicketComplete:
    """Create a new ticket."""
    ticket_simple = schemas_ticketing.TicketSimple(
        **ticket.model_dump(),
        id=uuid4(),
        user_id=user.id,
        status="pending",
        nb_scan=0,
    )

    # Verify that the event, category and session exist before creating the ticket to prevent creating tickets for non existing entities
    event = await cruds_ticketing.get_event_by_id(
        event_id=ticket_simple.event_id,
        db=db,
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    category = await cruds_ticketing.get_category_by_id(
        category_id=ticket_simple.category_id,
        db=db,
    )
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    session = await cruds_ticketing.get_session_by_id(
        session_id=ticket_simple.session_id,
        db=db,
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # TODO: Verify that the quota is not already full before creating the ticket to prevent overbooking in case of concurrent ticket purchases across multiple workers
    # First with redis cache and then with database queries as fallback if redis is not available
    if isinstance(redis_client, Redis):
        pass
    else:
        if event.quota is not None and event.used_quota >= event.quota:
            raise HTTPException(status_code=400, detail="Event quota exceeded")
        if category.quota is not None and category.used_quota >= category.quota:
            raise HTTPException(status_code=400, detail="Category quota exceeded")
        if session.quota is not None and session.used_quota >= session.quota:
            raise HTTPException(status_code=400, detail="Session quota exceeded")

    await cruds_ticketing.create_ticket(ticket=ticket_simple, db=db)

    # TODO: Add redis cache update for event quota
    if isinstance(redis_client, Redis):
        cache_ticketing.increment_quota_event(
            redis=redis_client,
            event_id=ticket_simple.event_id,
            amount=1,
        )
        cache_ticketing.increment_quota_category(
            redis=redis_client,
            category_id=ticket_simple.category_id,
            amount=1,
        )
        cache_ticketing.increment_quota_session(
            redis=redis_client,
            session_id=ticket_simple.session_id,
            amount=1,
        )

    await cruds_ticketing.increment_used_quota_event(
        event_id=ticket_simple.event_id,
        db=db,
    )
    await cruds_ticketing.increment_used_quota_category(
        category_id=ticket_simple.category_id,
        db=db,
    )
    await cruds_ticketing.increment_used_quota_session(
        session_id=ticket_simple.session_id,
        db=db,
    )
    ticket_complete = await cruds_ticketing.get_ticket_by_id(
        ticket_id=ticket_simple.id,
        db=db,
    )

    if ticket_complete is None:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Ticket creation failed")

    # TODO: Init MyECLPay Transfer

    return ticket_complete


@module.router.patch(
    "/ticketing/tickets/{ticket_id}",
    summary="Update an existing ticket",
    response_model=None,
    status_code=204,
)
async def update_ticket(
    ticket_id: UUID,
    ticket_update: schemas_ticketing.TicketBase,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Update an existing ticket."""
    stored = await cruds_ticketing.get_ticket_by_id(ticket_id=ticket_id, db=db)
    if stored is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    await cruds_ticketing.update_ticket(
        ticket_id=ticket_id,
        ticket_update=ticket_update,
        db=db,
    )

# Could be deleted if the user is the one who has created the ticket
# or if the user has the right permissions to manage events
@module.router.delete(
    "/ticketing/tickets/{ticket_id}",
    summary="Delete an existing ticket",
    response_model=None,
    status_code=204,
)
async def delete_ticket(
    ticket_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an existing ticket."""
    stored = await cruds_ticketing.get_ticket_by_id(ticket_id=ticket_id, db=db)
    if stored is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    # TODO: Add permission check to allow only the user who has created the ticket or users with manage_events permission to delete the ticket
    # Should it be a pending ticket?
    # Should we keep the ticket but mark it as cancelled to keep track of the quota and for historical data?
    await cruds_ticketing.delete_ticket(ticket_id=ticket_id, db=db)
