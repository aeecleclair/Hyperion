from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ticketing import cruds_ticketing
from app.modules.ticketing.schemas_ticketing import (
    CategorySimple,
    EventSimple,
    SessionSimple,
)


async def check_user_quotas(
    db: AsyncSession,
    user_id: str,
    event: EventSimple,
    category: CategorySimple,
    session: SessionSimple,
):
    """Check if the user has reached their quota for tickets."""
    # Check if the user has already reached the user quota for the event, category and session
    user_tickets = await cruds_ticketing.get_tickets_by_user_id(
        user_id=user_id,
        db=db,
    )
    user_event_tickets = [
        ticket for ticket in user_tickets if ticket.event_id == event.id
    ]
    user_category_tickets = [
        ticket for ticket in user_tickets if ticket.category_id == category.id
    ]
    user_session_tickets = [
        ticket for ticket in user_tickets if ticket.session_id == session.id
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
