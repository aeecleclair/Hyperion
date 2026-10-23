from app.core.users import schemas_users
from app.modules.ticketing import models_ticketing, schemas_ticketing


def model_to_ticket_complete_schema(
    ticket: models_ticketing.TicketingTicket,
) -> schemas_ticketing.TicketComplete:
    """
    Convert a TicketingTicket model to a TicketComplete schema.
    """
    return schemas_ticketing.TicketComplete(
        id=ticket.id,
        user_id=ticket.user_id,
        event_id=ticket.event_id,
        category_id=ticket.category_id,
        session_id=ticket.session_id,
        total=ticket.total,
        created_at=ticket.created_at,
        user=schemas_users.CoreUserSimple(
            id=ticket.user.id,
            name=ticket.user.name,
            firstname=ticket.user.firstname,
            nickname=ticket.user.nickname,
            account_type=ticket.user.account_type,
            school_id=ticket.user.school_id,
        ),
        event=schemas_ticketing.EventSimple(
            id=ticket.event.id,
            organiser_id=ticket.event.organiser_id,
            creator_id=ticket.event.creator_id,
            name=ticket.event.name,
            open_date=ticket.event.open_date,
            close_date=ticket.event.close_date,
            quota=ticket.event.quota,
            user_quota=ticket.event.user_quota,
            disabled=ticket.event.disabled,
        ),
        session=schemas_ticketing.SessionSimple(
            event_id=ticket.session.event_id,
            id=ticket.session.id,
            date=ticket.session.date,
            name=ticket.session.name,
            quota=ticket.session.quota,
            user_quota=ticket.session.user_quota,
            disabled=ticket.session.disabled,
        )
        if ticket.session
        else None,
        category=schemas_ticketing.CategorySimple(
            id=ticket.category.id,
            event_id=ticket.category.event_id,
            name=ticket.category.name,
            required_mebership=ticket.category.required_mebership,
            quota=ticket.category.quota,
            user_quota=ticket.category.user_quota,
            price=ticket.category.price,
            disabled=ticket.category.disabled,
        ),
        status=ticket.status,
        nb_scan=ticket.nb_scan,
    )


def model_to_ticket_simple_schema(
    ticket: models_ticketing.TicketingTicket,
) -> schemas_ticketing.TicketSimple:
    """
    Convert a TicketingTicket model to a TicketSimple schema.
    """
    return schemas_ticketing.TicketSimple(
        id=ticket.id,
        user_id=ticket.user_id,
        event_id=ticket.event_id,
        category_id=ticket.category_id,
        session_id=ticket.session_id,
        total=ticket.total,
        created_at=ticket.created_at,
        status=ticket.status,
        nb_scan=ticket.nb_scan,
        user=schemas_users.CoreUserSimple(
            id=ticket.user.id,
            name=ticket.user.name,
            firstname=ticket.user.firstname,
            nickname=ticket.user.nickname,
            account_type=ticket.user.account_type,
            school_id=ticket.user.school_id,
        ),
    )


def model_to_category_complete_schema(
    category: models_ticketing.TicketingCategory,
) -> schemas_ticketing.CategoryComplete:
    """
    Convert a TicketingCategory model to a CategoryComplete schema.
    """
    return schemas_ticketing.CategoryComplete(
        id=category.id,
        event_id=category.event_id,
        name=category.name,
        event=schemas_ticketing.EventSimple(
            id=category.event.id,
            organiser_id=category.event.organiser_id,
            creator_id=category.event.creator_id,
            name=category.event.name,
            open_date=category.event.open_date,
            close_date=category.event.close_date,
            quota=category.event.quota,
            user_quota=category.event.user_quota,
            disabled=category.event.disabled,
        ),
        sessions=[session.id for session in category.sessions],
        required_mebership=category.required_mebership,
        quota=category.quota,
        user_quota=category.user_quota,
        price=category.price,
        disabled=category.disabled,
    )


def model_to_event_complete_schema(
    event: models_ticketing.TicketingEvent,
) -> schemas_ticketing.EventComplete:
    return schemas_ticketing.EventComplete(
        id=event.id,
        organiser_id=event.organiser_id,
        creator_id=event.creator_id,
        name=event.name,
        open_date=event.open_date,
        close_date=event.close_date,
        quota=event.quota,
        user_quota=event.user_quota,
        disabled=event.disabled,
        organiser=schemas_ticketing.OrganiserComplete(
            id=event.organiser.id,
            name=event.organiser.name,
            store_id=event.organiser.store_id,
        ),
        sessions=[
            schemas_ticketing.SessionSimple(
                id=session.id,
                event_id=session.event_id,
                date=session.date,
                name=session.name,
                quota=session.quota,
                user_quota=session.user_quota,
                disabled=session.disabled,
            )
            for session in event.sessions
        ],
        categories=[
            schemas_ticketing.CategorySimple(
                id=category.id,
                event_id=category.event_id,
                name=category.name,
                required_mebership=category.required_mebership,
                quota=category.quota,
                user_quota=category.user_quota,
                price=category.price,
                disabled=category.disabled,
            )
            for category in event.categories
        ],
    )
