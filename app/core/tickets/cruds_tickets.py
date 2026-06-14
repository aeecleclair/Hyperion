import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, not_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.sql import delete, select

from app.core.tickets import models_tickets, schemas_tickets
from app.core.users import schemas_users


async def get_open_and_enabled_events(
    db: AsyncSession,
) -> Sequence[schemas_tickets.EventSimple]:
    """Return all open events from database"""

    time = datetime.now(UTC)

    result = await db.execute(
        select(models_tickets.TicketEvent).where(
            models_tickets.TicketEvent.open_datetime <= time,
            or_(
                models_tickets.TicketEvent.close_datetime.is_(None),
                models_tickets.TicketEvent.close_datetime > time,
            ),
            not_(models_tickets.TicketEvent.disabled),
        ),
    )
    return [
        schemas_tickets.EventSimple(
            id=association.id,
            name=association.name,
            store_id=association.store_id,
            open_datetime=association.open_datetime,
            close_datetime=association.close_datetime,
            disabled=association.disabled,
        )
        for association in result.scalars().all()
    ]


async def get_events_by_store_id(
    store_id: UUID,
    db: AsyncSession,
) -> Sequence[schemas_tickets.EventSimple]:
    """Return all open events from database"""

    result = await db.execute(
        select(models_tickets.TicketEvent).where(
            models_tickets.TicketEvent.store_id == store_id,
        ),
    )
    return [
        schemas_tickets.EventSimple(
            id=association.id,
            name=association.name,
            store_id=association.store_id,
            open_datetime=association.open_datetime,
            close_datetime=association.close_datetime,
            disabled=association.disabled,
        )
        for association in result.scalars().all()
    ]


async def get_event_complete_by_id(
    event_id: UUID,
    db: AsyncSession,
) -> schemas_tickets.EventComplete | None:
    """
    Return an EventComplete, loading complete sessions and categories objets from the database.

    If relationships are not needed, prefer `get_event_simple_by_id`
    If a FOR UPDATE lock is needed, prefer `acquire_event_lock_for_update`
    """
    result = await db.execute(
        select(models_tickets.TicketEvent)
        .where(
            models_tickets.TicketEvent.id == event_id,
        )
        .options(
            selectinload(models_tickets.TicketEvent.sessions),
            selectinload(models_tickets.TicketEvent.categories),
            selectinload(models_tickets.TicketEvent.questions),
        ),
    )

    event = result.scalars().first()
    if event is None:
        return None

    return schemas_tickets.EventComplete(
        id=event.id,
        name=event.name,
        open_datetime=event.open_datetime,
        close_datetime=event.close_datetime,
        quota=event.quota,
        disabled=event.disabled,
        store_id=event.store_id,
        sessions=[
            schemas_tickets.SessionComplete(
                id=session.id,
                name=session.name,
                start_datetime=session.start_datetime,
                event_id=session.event_id,
                quota=session.quota,
                disabled=session.disabled,
            )
            for session in event.sessions
        ],
        categories=[
            schemas_tickets.CategoryComplete(
                id=category.id,
                name=category.name,
                price=category.price,
                required_membership=category.required_membership,
                event_id=category.event_id,
                quota=category.quota,
                disabled=category.disabled,
            )
            for category in event.categories
        ],
        questions=[
            schemas_tickets.Question(
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
    )


async def get_event_simple_by_id(
    event_id: UUID,
    db: AsyncSession,
) -> schemas_tickets.EventSimple | None:
    """
    Return an EventSimple, loading only the basic event information from the database.

    If relationships are needed, prefer `get_event_complete_by_id`
    If a FOR UPDATE lock is needed, prefer `acquire_event_lock_for_update`
    """
    result = await db.execute(
        select(models_tickets.TicketEvent).where(
            models_tickets.TicketEvent.id == event_id,
        ),
    )

    event = result.scalars().first()
    if event is None:
        return None

    return schemas_tickets.EventSimple(
        id=event.id,
        name=event.name,
        open_datetime=event.open_datetime,
        close_datetime=event.close_datetime,
        store_id=event.store_id,
        disabled=event.disabled,
    )


async def acquire_event_lock_for_update(
    event_id: UUID,
    db: AsyncSession,
) -> schemas_tickets.EventWithoutSessionsAndCategories | None:
    """
    Acquire a lock FOR UPDATE on the event row.
    Until the end of the transaction, other:
    - update
    - delete
    - and select FOR UPDATE
    queries on the same row will be blocked until the lock is released.

    > FOR UPDATE causes the rows retrieved by the SELECT statement to be locked as though for update. This prevents them from being locked, modified or deleted by other transactions until the current transaction ends.

    By putting this lock on the beginning of an endpoint,
    we unsure that all endpoint trying to acquire the same lock
    will wait for the first lock to be released
    """
    result = await db.execute(
        select(models_tickets.TicketEvent)
        .where(
            models_tickets.TicketEvent.id == event_id,
        )
        .with_for_update(),
    )

    event = result.scalars().first()
    if event is None:
        return None

    return schemas_tickets.EventWithoutSessionsAndCategories(
        id=event.id,
        name=event.name,
        open_datetime=event.open_datetime,
        close_datetime=event.close_datetime,
        quota=event.quota,
        disabled=event.disabled,
        store_id=event.store_id,
    )


async def get_question_by_id(
    question_id: UUID,
    db: AsyncSession,
) -> schemas_tickets.Question | None:
    result = await db.execute(
        select(models_tickets.Question).where(
            models_tickets.Question.id == question_id,
        ),
    )

    question = result.scalars().first()
    if question is None:
        return None

    return schemas_tickets.Question(
        id=question.id,
        event_id=question.event_id,
        question=question.question,
        answer_type=question.answer_type,
        price=question.price,
        required=question.required,
        disabled=question.disabled,
    )


async def get_questions_by_event_id(
    event_id: UUID,
    db: AsyncSession,
) -> Sequence[schemas_tickets.Question]:
    result = await db.execute(
        select(models_tickets.Question).where(
            models_tickets.Question.event_id == event_id,
        ),
    )

    return [
        schemas_tickets.Question(
            id=question.id,
            event_id=question.event_id,
            question=question.question,
            answer_type=question.answer_type,
            price=question.price,
            required=question.required,
            disabled=question.disabled,
        )
        for question in result.scalars().all()
    ]


async def create_event(
    event_id: UUID,
    event: schemas_tickets.EventCreate,
    db: AsyncSession,
):
    db_event = models_tickets.TicketEvent(
        id=event_id,
        store_id=event.store_id,
        name=event.name,
        quota=event.quota,
        disabled=False,
        open_datetime=event.open_datetime,
        close_datetime=event.close_datetime,
        sessions=[
            models_tickets.EventSession(
                id=uuid.uuid4(),
                event_id=event_id,
                name=session.name,
                start_datetime=session.start_datetime,
                quota=session.quota,
                disabled=False,
            )
            for session in event.sessions
        ],
        categories=[
            models_tickets.Category(
                id=uuid.uuid4(),
                event_id=event_id,
                name=category.name,
                quota=category.quota,
                price=category.price,
                required_membership=category.required_membership,
                disabled=False,
            )
            for category in event.categories
        ],
        questions=[
            models_tickets.Question(
                id=uuid.uuid4(),
                event_id=event_id,
                question=question.question,
                answer_type=question.answer_type,
                price=question.price,
                required=question.required,
                disabled=False,
            )
            for question in event.questions
        ],
    )
    db.add(db_event)


async def create_event_session(
    session_id: UUID,
    event_id: UUID,
    session: schemas_tickets.SessionCreate,
    db: AsyncSession,
):
    db_session = models_tickets.EventSession(
        id=session_id,
        event_id=event_id,
        name=session.name,
        start_datetime=session.start_datetime,
        quota=session.quota,
        disabled=False,
    )
    db.add(db_session)


async def create_event_category(
    category_id: UUID,
    event_id: UUID,
    category: schemas_tickets.CategoryCreate,
    db: AsyncSession,
):
    db_category = models_tickets.Category(
        id=category_id,
        event_id=event_id,
        name=category.name,
        quota=category.quota,
        price=category.price,
        required_membership=category.required_membership,
        disabled=False,
    )
    db.add(db_category)


async def get_category_by_id(
    category_id: UUID,
    db: AsyncSession,
) -> schemas_tickets.CategoryComplete | None:
    """Return one category from database"""

    result = await db.execute(
        select(models_tickets.Category).where(
            models_tickets.Category.id == category_id,
        ),
    )

    category = result.scalars().first()
    if category is None:
        return None

    return schemas_tickets.CategoryComplete(
        id=category.id,
        name=category.name,
        price=category.price,
        required_membership=category.required_membership,
        event_id=category.event_id,
        quota=category.quota,
        disabled=category.disabled,
    )


async def get_session_by_id(
    session_id: UUID,
    db: AsyncSession,
) -> schemas_tickets.SessionComplete | None:
    """Return one session from database"""

    result = await db.execute(
        select(models_tickets.EventSession).where(
            models_tickets.EventSession.id == session_id,
        ),
    )

    session = result.scalars().first()
    if session is None:
        return None

    return schemas_tickets.SessionComplete(
        id=session.id,
        name=session.name,
        start_datetime=session.start_datetime,
        event_id=session.event_id,
        quota=session.quota,
        disabled=session.disabled,
    )


async def create_checkout(
    checkout_id: UUID,
    user_id: str,
    event_id: UUID,
    category_id: UUID,
    session_id: UUID,
    price: int,
    expiration: datetime,
    answers: list[schemas_tickets.AnswerCreate],
    paid: bool,
    db: AsyncSession,
):
    db_checkout = models_tickets.Checkout(
        id=checkout_id,
        event_id=event_id,
        user_id=user_id,
        category_id=category_id,
        session_id=session_id,
        price=price,
        expiration=expiration,
        answers=[
            models_tickets.Answer(
                id=uuid.uuid4(),
                question_id=answer.question_id,
                checkout_id=checkout_id,
                answer=answer.answer.answer_value,
            )
            for answer in answers
        ],
        scanned=False,
        paid=paid,
    )
    db.add(db_checkout)


async def mark_checkout_as_paid(
    checkout_id: UUID,
    db: AsyncSession,
):
    await db.execute(
        update(models_tickets.Checkout)
        .where(models_tickets.Checkout.id == checkout_id)
        .values(paid=True),
    )


async def get_paid_tickets_by_user_id(
    user_id: str,
    db: AsyncSession,
) -> Sequence[schemas_tickets.TicketComplete]:
    result = await db.execute(
        select(models_tickets.Checkout)
        .where(
            models_tickets.Checkout.user_id == user_id,
            models_tickets.Checkout.paid,
        )
        .options(
            joinedload(models_tickets.Checkout.category),
            joinedload(models_tickets.Checkout.session),
            joinedload(models_tickets.Checkout.event),
            joinedload(models_tickets.Checkout.user),
            selectinload(models_tickets.Checkout.answers).joinedload(
                models_tickets.Answer.question,
            ),
        ),
    )
    return [
        schemas_tickets.TicketComplete(
            id=ticket.id,
            category_id=ticket.category_id,
            session_id=ticket.session_id,
            event_id=ticket.event_id,
            scanned=ticket.scanned,
            category=schemas_tickets.Category(
                id=ticket.category.id,
                name=ticket.category.name,
                price=ticket.category.price,
                required_membership=ticket.category.required_membership,
                event_id=ticket.category.event_id,
                disabled=ticket.category.disabled,
            ),
            session=schemas_tickets.Session(
                id=ticket.session.id,
                name=ticket.session.name,
                start_datetime=ticket.session.start_datetime,
                event_id=ticket.session.event_id,
                disabled=ticket.session.disabled,
            ),
            user_id=ticket.user_id,
            user=schemas_users.CoreUserSimple(
                id=ticket.user.id,
                name=ticket.user.name,
                firstname=ticket.user.firstname,
                account_type=ticket.user.account_type,
                school_id=ticket.user.school_id,
            ),
            event=schemas_tickets.EventSimple(
                id=ticket.event.id,
                name=ticket.event.name,
                open_datetime=ticket.event.open_datetime,
                close_datetime=ticket.event.close_datetime,
                store_id=ticket.event.store_id,
                disabled=ticket.event.disabled,
            ),
            price=ticket.price,
            answers=[
                schemas_tickets.Answer.from_answer_value(
                    id_=answer.id,
                    question_id=answer.question_id,
                    answer_type=answer.question.answer_type,
                    value=answer.answer,
                )
                for answer in ticket.answers
            ],
        )
        for ticket in result.scalars().all()
    ]


async def get_paid_tickets_by_event_id(
    event_id: UUID,
    db: AsyncSession,
) -> Sequence[schemas_tickets.Ticket]:
    result = await db.execute(
        select(models_tickets.Checkout)
        .where(
            models_tickets.Checkout.event_id == event_id,
            models_tickets.Checkout.paid,
        )
        .options(
            joinedload(models_tickets.Checkout.category),
            joinedload(models_tickets.Checkout.session),
            joinedload(models_tickets.Checkout.user),
            selectinload(models_tickets.Checkout.answers).joinedload(
                models_tickets.Answer.question,
            ),
        ),
    )
    return [
        schemas_tickets.Ticket(
            id=ticket.id,
            category_id=ticket.category_id,
            session_id=ticket.session_id,
            event_id=ticket.event_id,
            scanned=ticket.scanned,
            category=schemas_tickets.Category(
                id=ticket.category.id,
                name=ticket.category.name,
                price=ticket.category.price,
                required_membership=ticket.category.required_membership,
                event_id=ticket.category.event_id,
                disabled=ticket.category.disabled,
            ),
            session=schemas_tickets.Session(
                id=ticket.session.id,
                name=ticket.session.name,
                start_datetime=ticket.session.start_datetime,
                event_id=ticket.session.event_id,
                disabled=ticket.session.disabled,
            ),
            user_id=ticket.user_id,
            user=schemas_users.CoreUserSimple(
                id=ticket.user.id,
                name=ticket.user.name,
                firstname=ticket.user.firstname,
                account_type=ticket.user.account_type,
                school_id=ticket.user.school_id,
            ),
            price=ticket.price,
            answers=[
                schemas_tickets.Answer.from_answer_value(
                    id_=answer.id,
                    question_id=answer.question_id,
                    answer_type=answer.question.answer_type,
                    value=answer.answer,
                )
                for answer in ticket.answers
            ],
        )
        for ticket in result.scalars().all()
    ]


async def get_ticket_by_id(
    ticket_id: UUID,
    db: AsyncSession,
) -> schemas_tickets.Ticket | None:
    result = await db.execute(
        select(models_tickets.Checkout)
        .where(models_tickets.Checkout.id == ticket_id)
        .options(
            joinedload(models_tickets.Checkout.category),
            joinedload(models_tickets.Checkout.session),
            joinedload(models_tickets.Checkout.user),
            selectinload(models_tickets.Checkout.answers).joinedload(
                models_tickets.Answer.question,
            ),
        ),
    )
    ticket = result.scalars().first()
    if ticket is None:
        return None

    return schemas_tickets.Ticket(
        id=ticket.id,
        category_id=ticket.category_id,
        session_id=ticket.session_id,
        event_id=ticket.event_id,
        scanned=ticket.scanned,
        category=schemas_tickets.Category(
            id=ticket.category.id,
            name=ticket.category.name,
            price=ticket.category.price,
            required_membership=ticket.category.required_membership,
            event_id=ticket.category.event_id,
            disabled=ticket.category.disabled,
        ),
        session=schemas_tickets.Session(
            id=ticket.session.id,
            name=ticket.session.name,
            start_datetime=ticket.session.start_datetime,
            event_id=ticket.session.event_id,
            disabled=ticket.session.disabled,
        ),
        user_id=ticket.user_id,
        user=schemas_users.CoreUserSimple(
            id=ticket.user.id,
            name=ticket.user.name,
            firstname=ticket.user.firstname,
            account_type=ticket.user.account_type,
            school_id=ticket.user.school_id,
        ),
        price=ticket.price,
        answers=[
            schemas_tickets.Answer.from_answer_value(
                id_=answer.id,
                question_id=answer.question_id,
                answer_type=answer.question.answer_type,
                value=answer.answer,
            )
            for answer in ticket.answers
        ],
    )


async def mark_ticket_as_scanned(
    ticket_id: UUID,
    db: AsyncSession,
):
    await db.execute(
        update(models_tickets.Checkout)
        .where(models_tickets.Checkout.id == ticket_id)
        .values(scanned=True),
    )


async def change_ticket_owner(
    ticket_id: UUID,
    new_user_id: str,
    db: AsyncSession,
):
    await db.execute(
        update(models_tickets.Checkout)
        .where(models_tickets.Checkout.id == ticket_id)
        .values(user_id=new_user_id),
    )


async def count_tickets_by_event_id(
    event_id: UUID,
    db: AsyncSession,
) -> int:
    result = await db.execute(
        select(func.count()).where(
            models_tickets.Checkout.event_id == event_id,
            models_tickets.Checkout.paid,
        ),
    )

    return result.scalar() or 0


async def count_tickets_by_category_id(
    category_id: UUID,
    db: AsyncSession,
) -> int:
    result = await db.execute(
        select(func.count()).where(
            models_tickets.Checkout.category_id == category_id,
            models_tickets.Checkout.paid,
        ),
    )

    return result.scalar() or 0


async def count_tickets_by_session_id(
    session_id: UUID,
    db: AsyncSession,
) -> int:
    result = await db.execute(
        select(func.count()).where(
            models_tickets.Checkout.session_id == session_id,
            models_tickets.Checkout.paid,
        ),
    )

    return result.scalar() or 0


async def count_valid_checkouts_by_event_id(
    event_id: UUID,
    db: AsyncSession,
) -> int:
    """
    Count only unpaid checkouts that are not expired
    """
    result = await db.execute(
        select(func.count()).where(
            models_tickets.Checkout.event_id == event_id,
            models_tickets.Checkout.expiration >= datetime.now(UTC),
            not_(models_tickets.Checkout.paid),
        ),
    )

    return result.scalar() or 0


async def count_valid_checkouts_by_category_id(
    category_id: UUID,
    db: AsyncSession,
) -> int:
    """
    Count only unpaid checkouts that are not expired
    """
    result = await db.execute(
        select(func.count()).where(
            models_tickets.Checkout.category_id == category_id,
            models_tickets.Checkout.expiration >= datetime.now(UTC),
            not_(models_tickets.Checkout.paid),
        ),
    )

    return result.scalar() or 0


async def count_valid_checkouts_by_session_id(
    session_id: UUID,
    db: AsyncSession,
) -> int:
    """
    Count only unpaid checkouts that are not expired
    """
    result = await db.execute(
        select(func.count()).where(
            models_tickets.Checkout.session_id == session_id,
            models_tickets.Checkout.expiration >= datetime.now(UTC),
            not_(models_tickets.Checkout.paid),
        ),
    )

    return result.scalar() or 0


async def count_valid_checkouts_and_tickets_by_event_id(
    event_id: UUID,
    db: AsyncSession,
) -> int:
    """
    Count unpaid checkouts that are not expired and paid tickets
    """
    result = await db.execute(
        select(func.count()).where(
            models_tickets.Checkout.event_id == event_id,
            or_(
                models_tickets.Checkout.paid,
                models_tickets.Checkout.expiration >= datetime.now(UTC),
            ),
        ),
    )

    return result.scalar() or 0


async def count_valid_checkouts_and_tickets_by_category_id(
    category_id: UUID,
    db: AsyncSession,
) -> int:
    """
    Count unpaid checkouts that are not expired and paid tickets
    """
    result = await db.execute(
        select(func.count()).where(
            models_tickets.Checkout.category_id == category_id,
            or_(
                models_tickets.Checkout.paid,
                models_tickets.Checkout.expiration >= datetime.now(UTC),
            ),
        ),
    )

    return result.scalar() or 0


async def count_valid_checkouts_and_tickets_by_session_id(
    session_id: UUID,
    db: AsyncSession,
) -> int:
    """
    Count unpaid checkouts that are not expired and paid tickets
    """
    result = await db.execute(
        select(func.count()).where(
            models_tickets.Checkout.session_id == session_id,
            or_(
                models_tickets.Checkout.paid,
                models_tickets.Checkout.expiration >= datetime.now(UTC),
            ),
        ),
    )

    return result.scalar() or 0


async def count_answers_by_question_id(
    question_id: UUID,
    db: AsyncSession,
) -> int:
    result = await db.execute(
        select(func.count()).where(
            models_tickets.Answer.question_id == question_id,
        ),
    )

    return result.scalar() or 0


async def update_event(
    event_id: UUID,
    event_update: schemas_tickets.EventUpdate,
    db: AsyncSession,
):
    await db.execute(
        update(models_tickets.TicketEvent)
        .where(models_tickets.TicketEvent.id == event_id)
        .values(**event_update.model_dump(exclude_unset=True)),
    )


async def update_session(
    session_id: UUID,
    session_update: schemas_tickets.SessionUpdate,
    db: AsyncSession,
):
    await db.execute(
        update(models_tickets.EventSession)
        .where(models_tickets.EventSession.id == session_id)
        .values(**session_update.model_dump(exclude_unset=True)),
    )


async def update_category(
    category_id: UUID,
    category_update: schemas_tickets.CategoryUpdate,
    db: AsyncSession,
):
    await db.execute(
        update(models_tickets.Category)
        .where(models_tickets.Category.id == category_id)
        .values(**category_update.model_dump(exclude_unset=True)),
    )


async def update_question(
    question_id: UUID,
    question_update: schemas_tickets.QuestionUpdate,
    db: AsyncSession,
):
    await db.execute(
        update(models_tickets.Question)
        .where(models_tickets.Question.id == question_id)
        .values(**question_update.model_dump(exclude_unset=True)),
    )


async def delete_ticket_change_over_invitation(
    ticket_id: UUID,
    db: AsyncSession,
):
    await db.execute(
        delete(models_tickets.TicketChangeOverInvitation).where(
            models_tickets.TicketChangeOverInvitation.ticket_id == ticket_id,
        ),
    )


async def create_ticket_change_over_invitation(
    ticket_id: UUID,
    new_user_id: str,
    token: str,
    db: AsyncSession,
):
    db_invitation = models_tickets.TicketChangeOverInvitation(
        ticket_id=ticket_id,
        new_user_id=new_user_id,
        token=token,
    )
    db.add(db_invitation)


async def get_ticket_change_over_invitation_by_token(
    token: str,
    db: AsyncSession,
) -> schemas_tickets.TicketChangeOverContent | None:
    result = await db.execute(
        select(models_tickets.TicketChangeOverInvitation).where(
            models_tickets.TicketChangeOverInvitation.token == token,
        ),
    )
    invitation = result.scalars().first()
    if invitation is None:
        return None

    return schemas_tickets.TicketChangeOverContent(
        ticket_id=invitation.ticket_id,
        new_user_id=invitation.new_user_id,
        token=invitation.token,
    )
