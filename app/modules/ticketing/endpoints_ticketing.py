from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.groups_type import GroupType
from app.core.permissions.type_permissions import ModulePermissions
from app.core.users import models_users
from app.dependencies import get_db, get_redis_client, is_user, is_user_allowed_to
from app.modules.ticketing import cache_ticketing, cruds_ticketing, schemas_ticketing
from app.modules.ticketing.factory_ticketing import TicketingFactory
from app.types.module import Module


class TicketingPermissions(ModulePermissions):
    access_ticketing = "access_ticketing"
    manage_events = "manage_events"


router = APIRouter(tags=["Ticketing"])

module = Module(
    root="ticketing",
    tag="Ticketing",
    router=router,
    factory=TicketingFactory(),
)


@module.router.get(
    "/ticketing/organisers/",
    response_model=list[schemas_ticketing.OrganiserComplete],
    status_code=200,
)
async def get_organisers(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([TicketingPermissions.access_ticketing]),
    ),
):
    """
    Get all organisers.
    """
    return await cruds_ticketing.get_organisers(db=db)


@module.router.get(
    "/ticketing/organisers/{organiser_id}",
    response_model=schemas_ticketing.OrganiserComplete,
    status_code=200,
)
async def get_organiser(
    organiser_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([TicketingPermissions.access_ticketing]),
    ),
) -> schemas_ticketing.OrganiserComplete:
    """
    Get an Organiser by its id.
    """
    organiser = await cruds_ticketing.get_organiser_by_id(
        db=db,
        organiser_id=organiser_id,
    )
    if organiser is None:
        raise HTTPException(status_code=404, detail="Organiser not found")
    return organiser


# @module.router.post(
#     "/ticketing/organisers/",
#     response_model=schemas_ticketing.OrganiserComplete,
#     status_code=201,
# )
# async def create_organiser(
#     organiser: schemas_ticketing.OrganiserBase,
#     db: AsyncSession = Depends(get_db),
#     user: models_users.CoreUser = Depends(
#         is_user_allowed_to([TicketingPermissions.access_ticketing])),

# ) -> None:
#     """Create an organiser"""
#     await cruds_ticketing.create_organiser(
#         organiser=schemas_ticketing.OrganiserComplete(
#             id=uuid4(),
#             group_id=
#             store_id=
#             name=organiser.name,
#         ))


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
    "/ticketing/events/{event_id}/quota/",
    summary="Get the remaining quota for an event",
    response_model=int,
    status_code=200,
)
async def get_event_remaining_quota(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    redis: Redis | None = Depends(get_redis_client),
) -> int:
    """Get the remaining quota for an event."""
    quota = await cache_ticketing.get_event_remaining_quota_with_cache(
        redis=redis,
        db=db,
        event_id=event_id,
    )
    if quota is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return quota


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
    redis: Redis | None = Depends(get_redis_client),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([TicketingPermissions.manage_events]),
    ),
) -> None:
    """Update an existing event."""
    used_quota = await cruds_ticketing.get_event_used_quota(db=db, event_id=event_id)
    if used_quota is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if event_update.quota is not None and used_quota > event_update.quota:
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
    used_quota = await cruds_ticketing.get_event_used_quota(db=db, event_id=event_id)
    if used_quota is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if used_quota > 0:
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
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([TicketingPermissions.access_ticketing]),
    ),
) -> schemas_ticketing.SessionComplete | None:
    """Get a session by its ID."""
    session = await cruds_ticketing.get_session_by_id(
        session_id=session_id,
        db=db,
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@module.router.get(
    "/ticketing/sessions/{session_id}/quota/",
    summary="Get the remaining quota for a session",
    response_model=int,
    status_code=200,
)
async def get_session_remaining_quota(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    redis: Redis | None = Depends(get_redis_client),
) -> int:
    """Get the remaining quota for a session."""
    quota = await cache_ticketing.get_session_remaining_quota_with_cache(
        redis=redis,
        db=db,
        session_id=session_id,
    )
    if quota is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return quota


@module.router.get(
    "/ticketing/events/{event_id}/sessions/",
    summary="Get all sessions for a specific event",
    response_model=list[schemas_ticketing.SessionComplete],
    status_code=200,
)
async def get_sessions_by_event_id(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([TicketingPermissions.access_ticketing]),
    ),
) -> list[schemas_ticketing.SessionComplete]:
    """Get all sessions for a specific event."""
    return await cruds_ticketing.get_sessions_by_event_id(event_id=event_id, db=db)


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
        disabled=False,
    )
    # Verify that the event exists before
    event = await cruds_ticketing.get_event_by_id(
        event_id=session_simple.event_id,
        db=db,
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.open_date is not None and session.date < event.open_date:
        raise HTTPException(
            status_code=400,
            detail="Session date cannot be before event open date",
        )
    if event.close_date is not None and session.date > event.close_date:
        raise HTTPException(
            status_code=400,
            detail="Session date cannot be after event close date",
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
    used_quota = await cruds_ticketing.get_session_used_quota(
        db=db,
        session_id=session_id,
    )
    if used_quota is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session_update.quota is not None and used_quota > session_update.quota:
        raise HTTPException(
            status_code=400,
            detail="Cannot set quota less than used quota",
        )
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
    used_quota = await cruds_ticketing.get_session_used_quota(
        db=db,
        session_id=session_id,
    )
    if used_quota is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if used_quota > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a session with used quota",
        )
    categories = await cruds_ticketing.get_categories_by_session_id(
        session_id=session_id,
        db=db,
    )
    if len(categories) > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a session with associated categories",
        )
    tickets = await cruds_ticketing.get_tickets_by_session_id(
        session_id=session_id,
        db=db,
    )
    if len(tickets) > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a session with associated tickets",
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


@module.router.get(
    "/ticketing/categories/{category_id}/quota/",
    summary="Get the remaining quota for a category",
    response_model=int,
    status_code=200,
)
async def get_category_remaining_quota(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
    redis: Redis | None = Depends(get_redis_client),
) -> int:
    """Get the remaining quota for a category."""
    quota = await cache_ticketing.get_category_remaining_quota_with_cache(
        redis=redis,
        db=db,
        category_id=category_id,
    )
    if quota is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return quota


@module.router.get(
    "/ticketing/events/{event_id}/categories/",
    summary="Get all categories for an event",
    response_model=list[schemas_ticketing.CategorySimple],
    status_code=200,
)
async def get_categories_by_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> list[schemas_ticketing.CategorySimple]:
    """Get all categories for an event."""
    return await cruds_ticketing.get_categories_by_event_id(
        event_id=event_id,
        db=db,
    )


@module.router.get(
    "/ticketing/sessions/{session_id}/categories/",
    summary="Get all categories for a session",
    response_model=list[schemas_ticketing.CategorySimple],
    status_code=200,
)
async def get_categories_by_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> list[schemas_ticketing.CategorySimple]:
    """Get all categories for a session."""
    return await cruds_ticketing.get_categories_by_session_id(
        session_id=session_id,
        db=db,
    )


@module.router.post(
    "/ticketing/categories/",
    summary="Create a new category",
    response_model=schemas_ticketing.CategorySimple,
    status_code=201,
)
async def create_category(
    category: schemas_ticketing.CategoryCreate,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([TicketingPermissions.manage_events]),
    ),
) -> schemas_ticketing.CategorySimple:
    """Create a new category."""
    # Verify that the event exists before creating the category.
    event = await cruds_ticketing.get_event_by_id(
        event_id=category.event_id,
        db=db,
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    # Verify that the sessions exist before creating the category.
    if category.sessions is not None:
        sessions = await cruds_ticketing.get_sessions_by_event_id(
            db=db,
            event_id=category.event_id,
        )
        sessions_ids = [session.id for session in sessions]
        if sessions is None or any(
            session_id not in sessions_ids for session_id in category.sessions
        ):
            raise HTTPException(
                status_code=404,
                detail="One or more sessions not found",
            )
    category_simple = schemas_ticketing.CategorySimple(
        **category.model_dump(),
        id=uuid4(),
        disabled=False,
    )
    await cruds_ticketing.create_category(category=category_simple, db=db)
    return category_simple


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
    redis: Redis | None = Depends(get_redis_client),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([TicketingPermissions.manage_events]),
    ),
) -> None:
    """Update an existing category."""
    used_quota = await cruds_ticketing.get_category_used_quota(
        db=db,
        category_id=category_id,
    )
    if used_quota is None:
        raise HTTPException(status_code=404, detail="Category not found")
    if category_update.quota is not None and used_quota > category_update.quota:
        raise HTTPException(
            status_code=400,
            detail="Cannot set quota less than used quota",
        )
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
    used_quota = await cruds_ticketing.get_category_used_quota(
        db=db,
        category_id=category_id,
    )
    if used_quota is None:
        raise HTTPException(status_code=404, detail="Category not found")
    if used_quota > 0:
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
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([TicketingPermissions.access_ticketing]),
    ),
) -> schemas_ticketing.TicketComplete | None:
    """Get a ticket by its ID."""
    ticket = await cruds_ticketing.get_ticket_by_id(ticket_id=ticket_id, db=db)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    # Allow access if it's the user's own ticket or if they're an admin
    if ticket.user_id != user.id and GroupType.admin not in [
        group.id for group in user.groups
    ]:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found",
        )
    return ticket


@module.router.get(
    "/ticketing/tickets/",
    summary="Get all tickets",
    response_model=list[schemas_ticketing.TicketSimple],
    status_code=200,
)
async def get_all_tickets(
    db: AsyncSession = Depends(get_db),
) -> list[schemas_ticketing.TicketSimple]:
    """Get all tickets."""
    return await cruds_ticketing.get_tickets(db=db)


@module.router.get(
    "/ticketing/events/{event_id}/tickets/",
    summary="Get all tickets for an event",
    response_model=list[schemas_ticketing.TicketSimple],
    status_code=200,
)
async def get_tickets_by_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> list[schemas_ticketing.TicketSimple]:
    """Get all tickets for an event."""
    return await cruds_ticketing.get_tickets_by_event_id(event_id=event_id, db=db)


@module.router.get(
    "/ticketing/sessions/{session_id}/tickets/",
    summary="Get all tickets for a session",
    response_model=list[schemas_ticketing.TicketSimple],
    status_code=200,
)
async def get_tickets_by_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> list[schemas_ticketing.TicketSimple]:
    """Get all tickets for a session."""
    return await cruds_ticketing.get_tickets_by_session_id(
        session_id=session_id,
        db=db,
    )


@module.router.get(
    "/ticketing/categories/{category_id}/tickets/",
    summary="Get all tickets for a category",
    response_model=list[schemas_ticketing.TicketSimple],
    status_code=200,
)
async def get_tickets_by_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> list[schemas_ticketing.TicketSimple]:
    """Get all tickets for a category."""
    return await cruds_ticketing.get_tickets_by_category_id(
        category_id=category_id,
        db=db,
    )


@module.router.get(
    "/ticketing/users/{user_id}/tickets/",
    summary="Get all tickets for a user",
    response_model=list[schemas_ticketing.TicketSimple],
    status_code=200,
)
async def get_tickets_by_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[schemas_ticketing.TicketSimple]:
    """Get all tickets for a user."""
    return await cruds_ticketing.get_tickets_by_user_id(user_id=user_id, db=db)


@module.router.get(
    "/ticketing/users/me/tickets/",
    summary="Get all tickets for a user",
    response_model=list[schemas_ticketing.TicketSimple],
    status_code=200,
)
async def get_my_tickets(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
) -> list[schemas_ticketing.TicketSimple]:
    """Get all tickets for a user."""
    return await cruds_ticketing.get_tickets_by_user_id(user_id=user.id, db=db)


@module.router.post(
    "/ticketing/tickets/",
    summary="Create a new ticket",
    response_model=schemas_ticketing.TicketSimple,
    status_code=201,
)
async def create_ticket(
    ticket: schemas_ticketing.TicketBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
    redis_client: Redis | None = Depends(get_redis_client),
) -> schemas_ticketing.TicketSimple:
    """Create a new ticket."""

    if user.id != ticket.user_id and not await is_user_allowed_to(
        [TicketingPermissions.manage_events],
    )(user):
        raise HTTPException(
            status_code=403,
            detail="Users can only create tickets for themselves",
        )

    ticket_simple = schemas_ticketing.TicketSimple(
        **ticket.model_dump(),
        id=uuid4(),
        status="pending",
        nb_scan=0,
        created_at=datetime.now(UTC),
    )

    # Verify quota from cache given event_id, category_id and session_id to prevent overbooking in case of concurrent ticket purchases across multiple workers
    event_quota = await cache_ticketing.get_event_remaining_quota_with_cache(
        redis=redis_client,
        db=db,
        event_id=ticket_simple.event_id,
    )
    category_quota = await cache_ticketing.get_category_remaining_quota_with_cache(
        redis=redis_client,
        db=db,
        category_id=ticket_simple.category_id,
    )
    session_quota = await cache_ticketing.get_session_remaining_quota_with_cache(
        redis=redis_client,
        db=db,
        session_id=ticket_simple.session_id,
    )
    if event_quota is not None and event_quota <= 0:
        raise HTTPException(status_code=400, detail="Event quota exceeded")
    if category_quota is not None and category_quota <= 0:
        raise HTTPException(status_code=400, detail="Category quota exceeded")
    if session_quota is not None and session_quota <= 0:
        raise HTTPException(status_code=400, detail="Session quota exceeded")

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

    if category.event_id != event.id:
        raise HTTPException(
            status_code=400,
            detail="Category does not belong to event",
        )
    if session.event_id != event.id:
        raise HTTPException(
            status_code=400,
            detail="Session does not belong to event",
        )
    if category.sessions and session.id not in category.sessions:
        raise HTTPException(
            status_code=400,
            detail="Session is not available for category",
        )

    # Check if the user has already reached the user quota for the event, category and session
    user_tickets = await cruds_ticketing.get_tickets_by_user_id(
        user_id=ticket_simple.user_id,
        db=db,
    )
    user_event_tickets = [
        ticket for ticket in user_tickets if ticket.event_id == ticket_simple.event_id
    ]
    user_category_tickets = [
        ticket
        for ticket in user_tickets
        if ticket.category_id == ticket_simple.category_id
    ]
    user_session_tickets = [
        ticket
        for ticket in user_tickets
        if ticket.session_id == ticket_simple.session_id
    ]
    if event.user_quota is not None and len(user_event_tickets) >= event.user_quota:
        raise HTTPException(
            status_code=400,
            detail="User event quota exceeded",
        )
    if (
        category.user_quota is not None
        and len(user_category_tickets) >= category.user_quota
    ):
        raise HTTPException(
            status_code=400,
            detail="User category quota exceeded",
        )
    if (
        session.user_quota is not None
        and len(user_session_tickets) >= session.user_quota
    ):
        raise HTTPException(
            status_code=400,
            detail="User session quota exceeded",
        )

    await cruds_ticketing.create_ticket(ticket=ticket_simple, db=db)

    # TODO: Add redis cache update for event quota
    cache_ticketing.update_cache_for_new_ticket(
        redis=redis_client,
        event_id=ticket_simple.event_id,
        category_id=ticket_simple.category_id,
        session_id=ticket_simple.session_id,
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
        await cache_ticketing.update_cache_for_new_ticket(
            redis=redis_client,
            event_id=ticket_simple.event_id,
            category_id=ticket_simple.category_id,
            session_id=ticket_simple.session_id,
            amount=-1,
        )
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
