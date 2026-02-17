from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.mypayment import schemas_mypayment
from app.modules.ticketing import models_ticketing, schemas_ticketing


async def get_events(
    db: AsyncSession,
) -> list[schemas_ticketing.EventSimple]:
    """Get all events."""

    events = await db.execute(select(models_ticketing.Event))
    return [
        schemas_ticketing.EventSimple(
            id=event.id,
            store_id=event.store_id,
            creator_id=event.creator_id,
            name=event.name,
            open_date=event.open_date,
            close_date=event.close_date,
            quota=event.quota,
            user_quota=event.user_quota,
            used_quota=event.used_quota,
            disabled=event.disabled,
            store=schemas_mypayment.StoreSimple(
                id=event.store.id,
                structure_id=event.store.structure_id,
                wallet_id=event.store.wallet_id,
                name=event.store.name,
                creation=event.store.creation,
            ),
        )
        for event in events.scalars().all()
    ]


async def get_event_by_id(
    db: AsyncSession,
    event_id: UUID,
) -> schemas_ticketing.EventComplete | None:
    """Get an event by its ID."""

    event = (
        (
            await db.execute(
                select(models_ticketing.Event).where(
                    models_ticketing.Event.id == event_id,
                ),
            )
        )
        .scalars()
        .first()
    )

    return (
        schemas_ticketing.EventComplete(
            id=event.id,
            store_id=event.store_id,
            creator_id=event.creator_id,
            name=event.name,
            open_date=event.open_date,
            close_date=event.close_date,
            quota=event.quota,
            user_quota=event.user_quota,
            used_quota=event.used_quota,
            disabled=event.disabled,
            store=schemas_mypayment.StoreSimple(
                id=event.store.id,
                structure_id=event.store.structure_id,
                wallet_id=event.store.wallet_id,
                name=event.store.name,
                creation=event.store.creation,
            ),
            sessions=event.sessions,
            categories=event.categories,
        )
        if event
        else None
    )


async def get_event_by_name(
    db: AsyncSession,
    name: str,
) -> schemas_ticketing.EventComplete | None:
    """Get an event by its name."""
    event = (
        (
            await db.execute(
                select(models_ticketing.Event).where(
                    models_ticketing.Event.name == name,
                ),
            )
        )
        .scalars()
        .first()
    )

    return (
        schemas_ticketing.EventComplete(
            id=event.id,
            store_id=event.store_id,
            creator_id=event.creator_id,
            name=event.name,
            open_date=event.open_date,
            close_date=event.close_date,
            quota=event.quota,
            user_quota=event.user_quota,
            used_quota=event.used_quota,
            disabled=event.disabled,
            store=schemas_mypayment.StoreSimple(
                id=event.store.id,
                structure_id=event.store.structure_id,
                wallet_id=event.store.wallet_id,
                name=event.store.name,
                creation=event.store.creation,
            ),
            sessions=event.sessions,
            categories=event.categories,
        )
        if event
        else None
    )


async def create_event(
    db: AsyncSession,
    event: schemas_ticketing.EventSimple,
) -> None:
    """Create a new event."""

    db.add(
        models_ticketing.Event(**event.model_dump()),
    )
    await db.flush()


async def update_event(
    db: AsyncSession,
    event_id: UUID,
    event_update: schemas_ticketing.EventUpdate,
) -> None:
    """Update an existing event."""

    await db.execute(
        update(models_ticketing.Event)
        .where(models_ticketing.Event.id == event_id)
        .values(**event_update.model_dump(exclude_unset=True)),
    )
    await db.flush()


async def increment_used_quota_event(
    db: AsyncSession,
    event_id: UUID,
) -> None:
    """Increment the used quota of an event, its sessions and its category if applicable."""
    await db.execute(
        update(models_ticketing.Event)
        # Only increment if the event has a quota and the quota is not already full
        # This prevents overbooking in case of concurrent ticket purchases across multiple workers
        .where(models_ticketing.Event.id == event_id and models_ticketing.Event.used_quota < models_ticketing.Event.quota)
        .values(used_quota=models_ticketing.Event.used_quota + 1),
    )

    await db.flush()


async def delete_event(
    db: AsyncSession,
    event_id: UUID,
) -> None:
    """Delete an existing event."""

    await db.execute(
        delete(models_ticketing.Event).where(models_ticketing.Event.id == event_id),
    )
    await db.flush()


async def get_session_by_id(
    session_id: UUID,
    db: AsyncSession,
) -> schemas_ticketing.SessionComplete | None:
    """Get a session by its ID."""

    session = (
        (
            await db.execute(
                select(models_ticketing.Session).where(
                    models_ticketing.Session.id == session_id,
                ),
            )
        )
        .scalars()
        .first()
    )

    return (
        schemas_ticketing.SessionComplete(
            id=session.id,
            name=session.name,
            quota=session.quota,
            user_quota=session.user_quota,
            used_quota=session.used_quota,
            disabled=session.disabled,
            event_id=session.event_id,
            event=session.event,
        )
        if session
        else None
    )


async def create_session(
    db: AsyncSession,
    session: schemas_ticketing.SessionSimple,
) -> None:
    """Create a new session."""

    db.add(
        models_ticketing.Session(**session.model_dump()),
    )
    await db.flush()


async def update_session(
    db: AsyncSession,
    session_id: UUID,
    session_update: schemas_ticketing.SessionUpdate,
) -> None:
    """Update an existing session."""

    await db.execute(
        update(models_ticketing.Session)
        .where(models_ticketing.Session.id == session_id)
        .values(**session_update.model_dump(exclude_unset=True)),
    )
    await db.flush()


async def delete_session(
    db: AsyncSession,
    session_id: UUID,
) -> None:
    """Delete an existing session."""

    await db.execute(
        delete(models_ticketing.Session).where(
            models_ticketing.Session.id == session_id,
        ),
    )
    await db.flush()


async def increment_used_quota_session(
    db: AsyncSession,
    session_id: UUID,
) -> None:
    """Increment the used quota of a session."""
    await db.execute(
        update(models_ticketing.Session)
        # Only increment if the session has a quota and the quota is not already full
        # This prevents overbooking in case of concurrent ticket purchases across multiple workers
        .where(models_ticketing.Session.id == session_id and models_ticketing.Session.used_quota < models_ticketing.Session.quota)
        .values(used_quota=models_ticketing.Session.used_quota + 1),
    )

    await db.flush()


async def get_category_by_id(
    category_id: UUID,
    db: AsyncSession,
) -> schemas_ticketing.CategoryComplete | None:
    """Get a category by its ID."""

    category = (
        (
            await db.execute(
                select(models_ticketing.Category).where(
                    models_ticketing.Category.id == category_id,
                ),
            )
        )
        .scalars()
        .first()
    )

    return (
        schemas_ticketing.CategoryComplete(
            id=category.id,
            event_id=category.event_id,
            event=category.event,
            name=category.name,
            linked_sessions=category.linked_sessions,
            required_mebership=category.required_mebership,
            quota=category.quota,
            user_quota=category.user_quota,
            used_quota=category.used_quota,
            price=category.price,
            disabled=category.disabled,
        )
        if category
        else None
    )


async def create_category(
    db: AsyncSession,
    category: schemas_ticketing.CategorySimple,
) -> None:
    """Create a new category."""
    joined_sessions = (
        ",".join(str(session_id) for session_id in category.linked_sessions)
        if category.linked_sessions
        else None
    )
    category_model = category.model_dump()
    category_model["linked_sessions"] = joined_sessions
    db.add(
        models_ticketing.Category(**category_model),
    )
    await db.flush()


async def update_category(
    db: AsyncSession,
    category_id: UUID,
    category_update: schemas_ticketing.CategoryUpdate,
) -> None:
    """Update an existing category."""

    await db.execute(
        update(models_ticketing.Category)
        .where(models_ticketing.Category.id == category_id)
        .values(**category_update.model_dump(exclude_unset=True)),
    )
    await db.flush()


async def delete_category(
    db: AsyncSession,
    category_id: UUID,
) -> None:
    """Delete an existing category."""

    await db.execute(
        delete(models_ticketing.Category).where(
            models_ticketing.Category.id == category_id,
        ),
    )
    await db.flush()


async def increment_used_quota_category(
    db: AsyncSession,
    category_id: UUID,
) -> None:
    """Increment the used quota of a category."""
    await db.execute(
        update(models_ticketing.Category)
        # Only increment if the category has a quota and the quota is not already full
        # This prevents overbooking in case of concurrent ticket purchases across multiple workers
        .where(models_ticketing.Category.id == category_id and models_ticketing.Category.used_quota < models_ticketing.Category.quota)
        .values(used_quota=models_ticketing.Category.used_quota + 1),
    )

    await db.flush()


async def get_tickets(
    db: AsyncSession,
) -> list[schemas_ticketing.TicketComplete]:
    """Get all tickets."""

    tickets = await db.execute(select(models_ticketing.Ticket))
    return [
        schemas_ticketing.TicketComplete(
            id=ticket.id,
            user_id=ticket.user_id,
            event_id=ticket.event_id,
            category_id=ticket.category_id,
            session_id=ticket.session_id,
            total=ticket.total,
            created_at=ticket.created_at,
            event=ticket.event,
            category=ticket.category,
            session=ticket.session,
            status=ticket.status,
            nb_scan=ticket.nb_scan,
        )
        for ticket in tickets.scalars().all()
    ]


async def get_tickets_by_user_id(
    user_id: str,
    db: AsyncSession,
) -> list[schemas_ticketing.TicketComplete]:
    """Get all tickets for a specific user."""

    tickets = await db.execute(
        select(models_ticketing.Ticket).where(
            models_ticketing.Ticket.user_id == user_id,
        ),
    )
    return [
        schemas_ticketing.TicketComplete(
            id=ticket.id,
            user_id=ticket.user_id,
            event_id=ticket.event_id,
            category_id=ticket.category_id,
            session_id=ticket.session_id,
            total=ticket.total,
            created_at=ticket.created_at,
            event=ticket.event,
            category=ticket.category,
            session=ticket.session,
            status=ticket.status,
            nb_scan=ticket.nb_scan,
        )
        for ticket in tickets.scalars().all()
    ]


async def get_ticket_by_id(
    ticket_id: UUID,
    db: AsyncSession,
) -> schemas_ticketing.TicketComplete | None:
    """Get a ticket by its ID."""

    ticket = (
        (
            await db.execute(
                select(models_ticketing.Ticket).where(
                    models_ticketing.Ticket.id == ticket_id,
                ),
            )
        )
        .scalars()
        .first()
    )

    return (
        schemas_ticketing.TicketComplete(
            id=ticket.id,
            user_id=ticket.user_id,
            event_id=ticket.event_id,
            category_id=ticket.category_id,
            session_id=ticket.session_id,
            total=ticket.total,
            created_at=ticket.created_at,
            event=ticket.event,
            category=ticket.category,
            session=ticket.session,
            status=ticket.status,
            nb_scan=ticket.nb_scan,
        )
        if ticket
        else None
    )


async def create_ticket(
    db: AsyncSession,
    ticket: schemas_ticketing.TicketSimple,
) -> None:
    """Create a new ticket."""

    db.add(
        models_ticketing.Ticket(**ticket.model_dump()),
    )
    await db.flush()


async def update_ticket(
    db: AsyncSession,
    ticket_id: UUID,
    ticket_update: schemas_ticketing.TicketBase,
) -> None:
    """Update an existing ticket."""

    await db.execute(
        update(models_ticketing.Ticket)
        .where(models_ticketing.Ticket.id == ticket_id)
        .values(**ticket_update.model_dump(exclude_unset=True)),
    )
    await db.flush()


async def delete_ticket(
    db: AsyncSession,
    ticket_id: UUID,
) -> None:
    """Delete an existing ticket."""

    await db.execute(
        delete(models_ticketing.Ticket).where(
            models_ticketing.Ticket.id == ticket_id,
        ),
    )
    await db.flush()
