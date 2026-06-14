import csv
import logging
import uuid
from datetime import UTC, datetime
from io import StringIO
from uuid import UUID

import calypsso
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Response,
)
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.feed import schemas_feed, utils_feed
from app.core.memberships import utils_memberships
from app.core.mypayment import cruds_mypayment, schemas_mypayment, utils_mypayment
from app.core.mypayment.mypayment_tool import MyPaymentTool
from app.core.permissions.type_permissions import ModulePermissions
from app.core.tickets import cruds_tickets, schemas_tickets, utils_tickets
from app.core.tickets.factory_tickets import TicketsFactory
from app.core.users import schemas_users
from app.core.users.cruds_users import get_user_by_email
from app.core.users.models_users import CoreUser
from app.core.utils import security
from app.core.utils.config import Settings
from app.dependencies import (
    get_db,
    get_mail_templates,
    get_mypayment_tool,
    get_notification_tool,
    get_settings,
    is_user,
    is_user_allowed_to,
)
from app.types.exceptions import ObjectExpectedInDbNotFoundError
from app.types.module import CoreModule
from app.utils.communication.notifications import NotificationTool
from app.utils.mail.mailworker import send_email

router = APIRouter(tags=["Tickets"])


class TicketsPermissions(ModulePermissions):
    access_tickets = "access_tickets"


core_module = CoreModule(
    root="tickets",
    tag="Tickets",
    router=router,
    factory=TicketsFactory(),
    mypayment_callback=utils_tickets.mypayment_callback_callback,
    permissions=TicketsPermissions,
)


hyperion_error_logger = logging.getLogger("hyperion.error")
hyperion_security_logger = logging.getLogger("hyperion.security")
hyperion_mypayment_logger = logging.getLogger("hyperion.mypayment")


@router.get(
    "/tickets/events",
    response_model=list[schemas_tickets.EventSimple],
    status_code=200,
)
async def get_open_events(
    user: CoreUser = Depends(
        is_user_allowed_to(
            [TicketsPermissions.access_tickets],
        ),
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Return all open events.

    To be considered open, an event should have its opening date in the past and its closing date in the future or not defined. Moreover, we only return enabled events.
    """
    return await cruds_tickets.get_open_and_enabled_events(db=db)


@router.get(
    "/tickets/events/{event_id}",
    response_model=schemas_tickets.EventPublic,
    status_code=200,
)
async def get_event(
    event_id: UUID,
    user: CoreUser = Depends(
        is_user_allowed_to(
            [TicketsPermissions.access_tickets],
        ),
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get an event public details

    Only enabled sessions and categories are returned
    """
    event = await cruds_tickets.get_event_complete_by_id(event_id=event_id, db=db)

    if event is None:
        raise HTTPException(404, "Event not found")

    # TODO: do we return disabled events?
    if event.disabled:
        raise HTTPException(400, "Event is disabled")

    return schemas_tickets.EventPublic(
        id=event.id,
        name=event.name,
        store_id=event.store_id,
        sessions=[
            schemas_tickets.SessionPublic(
                event_id=session.event_id,
                id=session.id,
                name=session.name,
                start_datetime=session.start_datetime,
                sold_out=await utils_tickets.is_session_sold_out(
                    session_id=session.id,
                    quota=session.quota,
                    db=db,
                ),
                disabled=session.disabled,
            )
            for session in event.sessions
            if not session.disabled
        ],
        categories=[
            schemas_tickets.CategoryPublic(
                event_id=category.event_id,
                id=category.id,
                name=category.name,
                price=category.price,
                required_membership=category.required_membership,
                sold_out=await utils_tickets.is_category_sold_out(
                    category_id=category.id,
                    quota=category.quota,
                    db=db,
                ),
                disabled=category.disabled,
            )
            for category in event.categories
            if not category.disabled
        ],
        questions=[
            schemas_tickets.QuestionPublic(
                id=question.id,
                event_id=question.event_id,
                question=question.question,
                answer_type=question.answer_type,
                price=question.price,
                required=question.required,
                disabled=question.disabled,
            )
            for question in event.questions
        ],
        sold_out=await utils_tickets.is_event_sold_out(
            event_id=event.id,
            quota=event.quota,
            db=db,
        ),
        open_datetime=event.open_datetime,
        close_datetime=event.close_datetime,
        disabled=event.disabled,
    )


@router.post(
    "/tickets/events/{event_id}/checkout",
    response_model=schemas_tickets.CheckoutResponse,
    status_code=201,
)
async def create_checkout(
    event_id: UUID,
    checkout: schemas_tickets.Checkout,
    user: CoreUser = Depends(
        is_user_allowed_to(
            [TicketsPermissions.access_tickets],
        ),
    ),
    db: AsyncSession = Depends(get_db),
    mypayment_tool: MyPaymentTool = Depends(get_mypayment_tool),
):
    """
    Create a checkout for an open event
    """
    category = await cruds_tickets.get_category_by_id(
        category_id=checkout.category_id,
        db=db,
    )
    if category is None:
        raise HTTPException(404, "Category not found")
    if category.disabled:
        raise HTTPException(400, "Category is disabled")
    session = await cruds_tickets.get_session_by_id(
        session_id=checkout.session_id,
        db=db,
    )
    if session is None:
        raise HTTPException(404, "Session not found")
    if session.disabled:
        raise HTTPException(400, "Session is disabled")

    if category.event_id != event_id:
        raise HTTPException(400, "Category does not belong to the event")
    if session.event_id != event_id:
        raise HTTPException(400, "Session does not belong to the event")

    if category.required_membership is not None:
        membership = await utils_memberships.get_user_active_membership_to_association_membership(
            association_membership_id=category.required_membership,
            user_id=user.id,
            db=db,
        )
        if membership is None:
            raise HTTPException(
                400,
                "User does not have required membership to choose this category",
            )

    price = await utils_tickets.check_answer_validity_and_calculate_price(
        event_id=event_id,
        checkout=checkout,
        db=db,
    )

    # By putting this lock:
    # - we unsure that if an other endpoint execution acquired the lock before, this one will wait.
    # - we guarantee that any other endpoint execution that tries to acquire the lock will need to wait until the end of this transaction.
    # Two endpoints require this lock: create a checkout and convert a checkout to ticket (in a payment callback)
    event = await cruds_tickets.acquire_event_lock_for_update(
        event_id=event_id,
        db=db,
    )

    if event is None:
        raise ObjectExpectedInDbNotFoundError(
            object_name="Event",
            object_id=event_id,
        )

    if event.disabled:
        raise HTTPException(400, "Event is disabled")

    if event.open_datetime > datetime.now(UTC):
        raise HTTPException(400, "Event is not open yet")
    if event.close_datetime is not None and event.close_datetime <= datetime.now(UTC):
        raise HTTPException(400, "Event is closed")

    price += category.price

    if await utils_tickets.is_event_sold_out(
        event_id=event_id,
        quota=event.quota,
        db=db,
    ):
        raise HTTPException(400, "Event is sold out")
    if await utils_tickets.is_category_sold_out(
        category_id=category.id,
        quota=category.quota,
        db=db,
    ):
        raise HTTPException(400, "Category is sold out")
    if await utils_tickets.is_session_sold_out(
        session_id=session.id,
        quota=session.quota,
        db=db,
    ):
        raise HTTPException(400, "Session is sold out")

    checkout_id = uuid.uuid4()

    if price == 0:
        await cruds_tickets.mark_checkout_as_paid(
            checkout_id=checkout_id,
            db=db,
        )
        payment_request_info = None
        expiration = datetime.now(UTC)
        paid = True
    else:
        payment_request_info = await mypayment_tool.request_payment(
            request_type=checkout.mypayment_request_method,
            payment_info=schemas_mypayment.PaymentInfo(
                store_id=event.store_id,
                total=price,
                request_name=f"Event {event.name}",
                store_note=f"Ticket for {event.name} of {user.full_name}",
                module=core_module.root,
                object_id=checkout_id,
                redirect_url=checkout.mypayment_transfer_redirect_url,
            ),
            user=schemas_users.CoreUser(
                id=user.id,
                name=user.name,
                firstname=user.firstname,
                account_type=user.account_type,
                school_id=user.school_id,
                email=user.email,
            ),
        )
        expiration = payment_request_info.end_date
        paid = False

    await cruds_tickets.create_checkout(
        checkout_id=checkout_id,
        event_id=event_id,
        user_id=user.id,
        category_id=checkout.category_id,
        session_id=checkout.session_id,
        expiration=expiration,
        price=price,
        answers=checkout.answers,
        paid=paid,
        db=db,
    )

    return schemas_tickets.CheckoutResponse(
        price=price,
        expiration=expiration,
        payment_url=payment_request_info.checkout_url
        if payment_request_info is not None
        else None,
    )


@router.get(
    "/tickets/user/me/tickets",
    response_model=list[schemas_tickets.TicketComplete],
    status_code=200,
)
async def get_user_tickets(
    user: CoreUser = Depends(
        is_user_allowed_to(
            [TicketsPermissions.access_tickets],
        ),
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all tickets of the current user
    """
    return await cruds_tickets.get_paid_tickets_by_user_id(
        user_id=user.id,
        db=db,
    )


@router.post(
    "/tickets/user/me/tickets/change-over/request",
    status_code=204,
)
async def ticket_request_change_over(
    ticket_transfer: schemas_tickets.TicketChangeOverInvitation,
    background_tasks: BackgroundTasks,
    user: CoreUser = Depends(
        is_user_allowed_to(
            [TicketsPermissions.access_tickets],
        ),
    ),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    mail_templates: calypsso.MailTemplates = Depends(get_mail_templates),
):
    """
    Give its ticket to another user. The other user will receive an email with a link to accept the transfer.

    Using this endpoint will invalidate existing transfer invitations.
    """
    ticket = await cruds_tickets.get_ticket_by_id(
        ticket_id=ticket_transfer.ticket_id,
        db=db,
    )

    if ticket is None:
        raise HTTPException(404, "Ticket not found")

    if ticket.user_id != user.id:
        raise HTTPException(403, "User is not the owner of the ticket")

    event = await cruds_tickets.get_event_simple_by_id(
        event_id=ticket.event_id,
        db=db,
    )

    if event is None:
        raise ObjectExpectedInDbNotFoundError(
            object_name="Event",
            object_id=ticket.event_id,
        )

    await cruds_tickets.delete_ticket_change_over_invitation(
        ticket_id=ticket.id,
        db=db,
    )

    receiver_user = await get_user_by_email(
        email=ticket_transfer.email,
        db=db,
    )

    token = security.generate_token()

    if receiver_user is None:
        mail = mail_templates.get_mail_ticket_change_over_account_does_not_exist(
            event_name=event.name,
            giver_name=user.full_name,
        )

    else:
        await cruds_tickets.create_ticket_change_over_invitation(
            ticket_id=ticket.id,
            new_user_id=receiver_user.id,
            token=token,
            db=db,
        )

        confirmation_url = f"{settings.CLIENT_URL}tickets/user/me/tickets/change-over/accept?token={token}"

        mail = mail_templates.get_mail_ticket_change_over(
            event_name=event.name,
            giver_name=user.full_name,
            confirmation_url=confirmation_url,
        )

    background_tasks.add_task(
        send_email,
        recipient=ticket_transfer.email,
        subject=f"{settings.school.application_name} - Ticket transfer for {event.name}",
        content=mail,
        settings=settings,
    )


@router.get(
    "/tickets/user/me/tickets/change-over/accept",
    status_code=200,
)
async def ticket_accept_change_over(
    token: str,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    Accept a ticket transfer invitation. The user will become the new owner of the ticket.
    """
    invitation = await cruds_tickets.get_ticket_change_over_invitation_by_token(
        token=token,
        db=db,
    )

    if invitation is None:
        return RedirectResponse(
            url=settings.CLIENT_URL
            + calypsso.get_message_relative_url(
                message_type=calypsso.TypeMessage.ticket_change_over_invalid,
            ),
        )

    await cruds_tickets.delete_ticket_change_over_invitation(
        ticket_id=invitation.ticket_id,
        db=db,
    )

    await cruds_tickets.change_ticket_owner(
        ticket_id=invitation.ticket_id,
        new_user_id=invitation.new_user_id,
        db=db,
    )

    return RedirectResponse(
        url=settings.CLIENT_URL
        + calypsso.get_message_relative_url(
            message_type=calypsso.TypeMessage.ticket_change_over_success,
        ),
    )


@router.get(
    "/tickets/admin/events/{event_id}",
    response_model=schemas_tickets.EventAdmin,
    status_code=200,
)
async def get_event_admin(
    event_id: UUID,
    user: CoreUser = Depends(
        is_user(),
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get one event admin details

    **The user should have the right to manage the event seller**
    """
    event = await cruds_tickets.get_event_complete_by_id(event_id=event_id, db=db)
    if event is None:
        raise HTTPException(404, "Event not found")

    if not await utils_mypayment.can_user_manage_events(
        user_id=user.id,
        store_id=event.store_id,
        db=db,
    ):
        raise HTTPException(
            status_code=403,
            detail="User is not authorized to manage store events",
        )

    return await utils_tickets.convert_to_event_admin(
        event=event,
        db=db,
    )


@router.post(
    "/tickets/admin/events",
    response_model=schemas_tickets.EventAdmin,
    status_code=201,
)
async def create_event(
    event_create: schemas_tickets.EventCreate,
    user: CoreUser = Depends(
        is_user(),
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Create an event

    **The user should have the right to manage the event seller**
    """
    if not await utils_mypayment.can_user_manage_events(
        user_id=user.id,
        store_id=event_create.store_id,
        db=db,
    ):
        raise HTTPException(
            status_code=403,
            detail="User is not authorized to manage store events",
        )

    if len(event_create.sessions) == 0 or len(event_create.categories) == 0:
        raise HTTPException(
            status_code=400,
            detail="Event must have at least one session and one category",
        )

    event_id = uuid.uuid4()

    await cruds_tickets.create_event(
        event_id=event_id,
        event=event_create,
        db=db,
    )

    event_complete = await cruds_tickets.get_event_complete_by_id(
        event_id=event_id,
        db=db,
    )
    if event_complete is None:
        raise ObjectExpectedInDbNotFoundError(
            object_name="Event",
            object_id=event_id,
        )
    return await utils_tickets.convert_to_event_admin(
        event=event_complete,
        db=db,
    )


@router.patch(
    "/tickets/admin/events/{event_id}",
    status_code=204,
)
async def update_event(
    event_id: UUID,
    event_update: schemas_tickets.EventUpdate,
    user: CoreUser = Depends(
        is_user(),
    ),
    db: AsyncSession = Depends(get_db),
    notification_tool: NotificationTool = Depends(get_notification_tool),
):
    """
    Edit one event for admin
    """
    event = await cruds_tickets.get_event_simple_by_id(event_id=event_id, db=db)
    if event is None:
        raise HTTPException(404, "Event not found")

    if not await utils_mypayment.can_user_manage_events(
        user_id=user.id,
        store_id=event.store_id,
        db=db,
    ):
        raise HTTPException(
            status_code=403,
            detail="User is not authorized to manage store's events",
        )

    if event_update.open_datetime is not None:
        # We want to update the datetime in the feed
        await utils_feed.edit_feed_news(
            module=core_module.root,
            module_object_id=event.id,
            news_edit=schemas_feed.NewsEdit(
                action_start=event_update.open_datetime,
            ),
            require_feed_admin_approval=False,
            db=db,
            notification_tool=notification_tool,
        )

    await cruds_tickets.update_event(
        event_id=event_id,
        event_update=event_update,
        db=db,
    )


@router.post(
    "/tickets/admin/events/{event_id}/sessions",
    response_model=schemas_tickets.SessionComplete,
    status_code=201,
)
async def create_session(
    event_id: UUID,
    session_create: schemas_tickets.SessionCreate,
    user: CoreUser = Depends(
        is_user(),
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a session for an event

    **The user should have the right to manage the event seller**
    """
    event = await cruds_tickets.get_event_simple_by_id(event_id=event_id, db=db)
    if event is None:
        raise HTTPException(404, "Event not found")

    if not await utils_mypayment.can_user_manage_events(
        user_id=user.id,
        store_id=event.store_id,
        db=db,
    ):
        raise HTTPException(
            status_code=403,
            detail="User is not authorized to manage store's events",
        )

    session_id = uuid.uuid4()

    await cruds_tickets.create_event_session(
        session_id=session_id,
        event_id=event_id,
        session=session_create,
        db=db,
    )

    return await cruds_tickets.get_session_by_id(
        session_id=session_id,
        db=db,
    )


@router.patch(
    "/tickets/admin/events/{event_id}/sessions/{session_id}",
    status_code=204,
)
async def update_session(
    event_id: UUID,
    session_id: UUID,
    session_update: schemas_tickets.SessionUpdate,
    user: CoreUser = Depends(
        is_user(),
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Edit one event for admin
    """
    event = await cruds_tickets.get_event_simple_by_id(event_id=event_id, db=db)
    if event is None:
        raise HTTPException(404, "Event not found")

    if not await utils_mypayment.can_user_manage_events(
        user_id=user.id,
        store_id=event.store_id,
        db=db,
    ):
        raise HTTPException(
            status_code=403,
            detail="User is not authorized to manage store's events",
        )

    session = await cruds_tickets.get_session_by_id(session_id=session_id, db=db)
    if session is None or session.event_id != event_id:
        raise HTTPException(404, "Session not found")

    nb_checkouts = await cruds_tickets.count_valid_checkouts_by_session_id(
        session_id=session_id,
        db=db,
    )
    nb_tickets = await cruds_tickets.count_tickets_by_session_id(
        session_id=session_id,
        db=db,
    )
    if nb_checkouts + nb_tickets > 0:
        raise HTTPException(
            400,
            "Cannot update session with checkouts or tickets",
        )

    await cruds_tickets.update_session(
        session_id=session_id,
        session_update=session_update,
        db=db,
    )


@router.post(
    "/tickets/admin/events/{event_id}/categories",
    response_model=schemas_tickets.CategoryComplete,
    status_code=201,
)
async def create_category(
    event_id: UUID,
    category_create: schemas_tickets.CategoryCreate,
    user: CoreUser = Depends(
        is_user(),
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a category for an event

    **The user should have the right to manage the event seller**
    """
    event = await cruds_tickets.get_event_simple_by_id(event_id=event_id, db=db)
    if event is None:
        raise HTTPException(404, "Event not found")

    if not await utils_mypayment.can_user_manage_events(
        user_id=user.id,
        store_id=event.store_id,
        db=db,
    ):
        raise HTTPException(
            status_code=403,
            detail="User is not authorized to manage store's events",
        )

    category_id = uuid.uuid4()

    await cruds_tickets.create_event_category(
        category_id=category_id,
        event_id=event_id,
        category=category_create,
        db=db,
    )

    return await cruds_tickets.get_category_by_id(
        category_id=category_id,
        db=db,
    )


@router.patch(
    "/tickets/admin/events/{event_id}/categories/{category_id}",
    status_code=204,
)
async def update_category(
    event_id: UUID,
    category_id: UUID,
    category_update: schemas_tickets.CategoryUpdate,
    user: CoreUser = Depends(
        is_user(),
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Edit one event for admin
    """
    event = await cruds_tickets.get_event_simple_by_id(event_id=event_id, db=db)
    if event is None:
        raise HTTPException(404, "Event not found")

    if not await utils_mypayment.can_user_manage_events(
        user_id=user.id,
        store_id=event.store_id,
        db=db,
    ):
        raise HTTPException(
            status_code=403,
            detail="User is not authorized to manage store's events",
        )

    category = await cruds_tickets.get_category_by_id(category_id=category_id, db=db)
    if category is None or category.event_id != event_id:
        raise HTTPException(404, "Category not found")

    nb_checkouts = await cruds_tickets.count_valid_checkouts_by_category_id(
        category_id=category_id,
        db=db,
    )
    nb_tickets = await cruds_tickets.count_tickets_by_category_id(
        category_id=category_id,
        db=db,
    )
    if nb_checkouts + nb_tickets > 0:
        raise HTTPException(
            400,
            "Cannot update category with checkouts or tickets",
        )

    await cruds_tickets.update_category(
        category_id=category_id,
        category_update=category_update,
        db=db,
    )


@router.patch(
    "/tickets/admin/events/{event_id}/questions/{question_id}",
    status_code=204,
)
async def update_question(
    event_id: UUID,
    question_id: UUID,
    question_update: schemas_tickets.QuestionUpdate,
    user: CoreUser = Depends(
        is_user(),
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Edit one event for admin
    """
    event = await cruds_tickets.get_event_simple_by_id(event_id=event_id, db=db)
    if event is None:
        raise HTTPException(404, "Event not found")

    if not await utils_mypayment.can_user_manage_events(
        user_id=user.id,
        store_id=event.store_id,
        db=db,
    ):
        raise HTTPException(
            status_code=403,
            detail="User is not authorized to manage store's events",
        )

    question = await cruds_tickets.get_question_by_id(question_id=question_id, db=db)
    if question is None or question.event_id != event_id:
        raise HTTPException(404, "Question not found")

    nb_answers = await cruds_tickets.count_answers_by_question_id(
        question_id=question_id,
        db=db,
    )
    if nb_answers > 0:
        raise HTTPException(
            400,
            "Cannot update question with answers",
        )

    await cruds_tickets.update_question(
        question_id=question_id,
        question_update=question_update,
        db=db,
    )


@router.get(
    "/tickets/admin/events/{event_id}/tickets",
    response_model=list[schemas_tickets.Ticket],
    status_code=200,
)
async def get_event_tickets(
    event_id: UUID,
    user: CoreUser = Depends(
        is_user(),
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all tickets of an event

    **The user should have the right to manage the event seller**
    """
    event = await cruds_tickets.get_event_simple_by_id(event_id=event_id, db=db)
    if event is None:
        raise HTTPException(404, "Event not found")

    if not await utils_mypayment.can_user_manage_events(
        user_id=user.id,
        store_id=event.store_id,
        db=db,
    ):
        raise HTTPException(
            status_code=403,
            detail="User is not authorized to manage store events",
        )

    return await cruds_tickets.get_paid_tickets_by_event_id(event_id=event_id, db=db)


@router.get(
    "/tickets/admin/events/{event_id}/tickets/csv",
    response_class=FileResponse,
    status_code=200,
)
async def get_event_tickets_csv(
    event_id: UUID,
    user: CoreUser = Depends(
        is_user(),
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all tickets of an event as csv

    **The user should have the right to manage the event seller**
    """
    event = await cruds_tickets.get_event_simple_by_id(event_id=event_id, db=db)
    if event is None:
        raise HTTPException(404, "Event not found")

    if not await utils_mypayment.can_user_manage_events(
        user_id=user.id,
        store_id=event.store_id,
        db=db,
    ):
        raise HTTPException(
            status_code=403,
            detail="User is not authorized to manage store events",
        )

    csv_io = StringIO()

    writer = csv.writer(csv_io, delimiter=";", quoting=csv.QUOTE_MINIMAL)

    question_ids = []
    csv_headers = [
        "Ticket ID",
        "Session ID",
        "Session Name",
        "Category ID",
        "Category Name",
        "Price (€)",
        "Scanned",
        "User ID",
        "User Name",
        "User Firstname",
        "User Account Type",
        "User School ID",
    ]

    questions = await cruds_tickets.get_questions_by_event_id(
        event_id=event_id,
        db=db,
    )
    for question in questions:
        question_ids.append(question.id)
        csv_headers.append(f"Question: {question.question} ({question.price})")

    # Write csv_headers
    writer.writerow(csv_headers)

    tickets = await cruds_tickets.get_paid_tickets_by_event_id(event_id=event_id, db=db)
    for ticket in tickets:
        row = [
            ticket.id,
            ticket.session_id,
            ticket.session.name,
            ticket.category_id,
            ticket.category.name,
            f"{ticket.price / 100:.2f}€",
            ticket.scanned,
            ticket.user_id,
            ticket.user.name,
            ticket.user.firstname,
            ticket.user.account_type,
            ticket.user.school_id,
        ]
        answers_by_question_id: dict[UUID, schemas_tickets.Answer] = {}
        for answer in ticket.answers:
            answers_by_question_id[answer.question_id] = answer
        for question_id in question_ids:
            answer_associated_with_question = answers_by_question_id.get(question_id)
            if answer_associated_with_question is not None:
                row.append(answer_associated_with_question.answer.answer_value)
            else:
                row.append("")

        writer.writerow(row)

    csv_content = csv_io.getvalue()
    csv_io.close()

    filename = f"event_{event_id}_{datetime.now(UTC)}.csv"

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
    }
    return Response(
        csv_content,
        headers=headers,
        media_type="text/csv; charset=utf-8",
    )


@router.post(
    "/tickets/admin/tickets/{ticket_id}/check",
    response_model=schemas_tickets.Ticket,
    status_code=200,
)
async def check_ticket(
    ticket_id: UUID,
    user: CoreUser = Depends(
        is_user(),
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Check a ticket

    **The user should have the right to manage the event seller**
    """

    ticket = await cruds_tickets.get_ticket_by_id(ticket_id=ticket_id, db=db)
    if ticket is None:
        raise HTTPException(404, "Ticket not found")

    event = await cruds_tickets.get_event_simple_by_id(event_id=ticket.event_id, db=db)
    if event is None:
        raise ObjectExpectedInDbNotFoundError(
            object_name="Event",
            object_id=ticket.event_id,
        )

    if not await utils_mypayment.can_user_manage_events(
        user_id=user.id,
        store_id=event.store_id,
        db=db,
    ):
        raise HTTPException(
            status_code=403,
            detail="User is not authorized to manage store events",
        )

    return ticket


@router.post(
    "/tickets/admin/tickets/{ticket_id}/scan",
    status_code=204,
)
async def scan_ticket(
    ticket_id: UUID,
    user: CoreUser = Depends(
        is_user(),
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark a ticket as scanned

    **The user should have the right to manage the event seller**
    """

    ticket = await cruds_tickets.get_ticket_by_id(ticket_id=ticket_id, db=db)
    if ticket is None:
        raise HTTPException(404, "Ticket not found")

    event = await cruds_tickets.get_event_simple_by_id(event_id=ticket.event_id, db=db)
    if event is None:
        raise ObjectExpectedInDbNotFoundError(
            object_name="Event",
            object_id=ticket.event_id,
        )

    if not await utils_mypayment.can_user_manage_events(
        user_id=user.id,
        store_id=event.store_id,
        db=db,
    ):
        raise HTTPException(
            status_code=403,
            detail="User is not authorized to manage store events",
        )

    if ticket.scanned:
        raise HTTPException(
            status_code=400,
            detail="Ticket is already scanned",
        )

    await cruds_tickets.mark_ticket_as_scanned(ticket_id=ticket_id, db=db)


@router.get(
    "/tickets/admin/store/{store_id}/events",
    response_model=list[schemas_tickets.EventSimple],
    status_code=200,
)
async def get_events_by_store(
    store_id: UUID,
    user: CoreUser = Depends(
        is_user(),
    ),
    db: AsyncSession = Depends(get_db),
):
    store = await cruds_mypayment.get_store_by_id(
        store_id=store_id,
        db=db,
    )

    # TODO: maybe return an empty list
    if store is None:
        raise HTTPException(404, "Store not found")

    return await utils_tickets.get_events_from_store(
        store_id=store.id,
        user_id=user.id,
        db=db,
    )


@router.get(
    "/tickets/admin/association/{association_id}/events",
    response_model=list[schemas_tickets.EventSimple],
    status_code=200,
)
async def get_events_by_association(
    association_id: UUID,
    user: CoreUser = Depends(
        is_user(),
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all events of an association

    **The user should have the right to manage the event seller**
    """
    store = await cruds_mypayment.get_store_by_association_id(
        association_id=association_id,
        db=db,
    )

    # TODO: maybe return an empty list
    if store is None:
        raise HTTPException(400, "No store associated with this association")

    return await utils_tickets.get_events_from_store(
        store_id=store.id,
        user_id=user.id,
        db=db,
    )
