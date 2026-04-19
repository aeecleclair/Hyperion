import uuid
from collections.abc import Sequence
from uuid import UUID

from fastapi import (
    HTTPException,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.mypayment import utils_mypayment
from app.core.tickets import cruds_tickets, schemas_tickets


async def mypayment_callback_callback(
    checkout_id: UUID,
    db: AsyncSession,
) -> None:
    """
    Callback called by MyPayment when the payment status of a checkout changes.

    It will update the checkout and the associated tickets status according to the payment status.
    """
    await cruds_tickets.mark_checkout_as_paid(
        checkout_id=checkout_id,
        db=db,
    )


async def is_event_sold_out(
    event_id: UUID,
    quota: int | None,
    db: AsyncSession,
) -> bool:
    if quota is None:
        return False

    nb_valid_checkouts_and_tickets_by_event_id = (
        await cruds_tickets.count_valid_checkouts_and_tickets_by_event_id(
            event_id=event_id,
            db=db,
        )
    )

    return nb_valid_checkouts_and_tickets_by_event_id >= quota


async def is_category_sold_out(
    category_id: UUID,
    quota: int | None,
    db: AsyncSession,
) -> bool:
    if quota is None:
        return False

    nb_valid_checkouts_and_tickets_by_category_id = (
        await cruds_tickets.count_valid_checkouts_and_tickets_by_category_id(
            category_id=category_id,
            db=db,
        )
    )

    return nb_valid_checkouts_and_tickets_by_category_id >= quota


async def is_session_sold_out(
    session_id: UUID,
    quota: int | None,
    db: AsyncSession,
) -> bool:
    if quota is None:
        return False

    nb_valid_checkouts_and_tickets_by_session_id = (
        await cruds_tickets.count_valid_checkouts_and_tickets_by_session_id(
            session_id=session_id,
            db=db,
        )
    )

    return nb_valid_checkouts_and_tickets_by_session_id >= quota


async def convert_to_event_admin(
    event: schemas_tickets.EventComplete,
    db: AsyncSession,
):
    return schemas_tickets.EventAdmin(
        id=event.id,
        name=event.name,
        store_id=event.store_id,
        open_datetime=event.open_datetime,
        close_datetime=event.close_datetime,
        sessions=[
            schemas_tickets.SessionAdmin(
                id=session.id,
                event_id=session.event_id,
                name=session.name,
                start_datetime=session.start_datetime,
                quota=session.quota,
                disabled=session.disabled,
                tickets_in_checkout=await cruds_tickets.count_valid_checkouts_by_event_id(
                    event_id=event.id,
                    db=db,
                ),
                tickets_sold=await cruds_tickets.count_tickets_by_event_id(
                    event_id=event.id,
                    db=db,
                ),
            )
            for session in event.sessions
        ],
        categories=[
            schemas_tickets.CategoryAdmin(
                id=category.id,
                event_id=category.event_id,
                name=category.name,
                price=category.price,
                required_membership=category.required_membership,
                quota=category.quota,
                disabled=category.disabled,
                tickets_in_checkout=await cruds_tickets.count_valid_checkouts_by_category_id(
                    category_id=category.id,
                    db=db,
                ),
                tickets_sold=await cruds_tickets.count_tickets_by_category_id(
                    category_id=category.id,
                    db=db,
                ),
            )
            for category in event.categories
        ],
        questions=[
            schemas_tickets.QuestionAdmin(
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
        quota=event.quota,
        disabled=event.disabled,
        tickets_in_checkout=await cruds_tickets.count_valid_checkouts_by_event_id(
            event_id=event.id,
            db=db,
        ),
        tickets_sold=await cruds_tickets.count_tickets_by_event_id(
            event_id=event.id,
            db=db,
        ),
    )


async def get_events_from_store(
    store_id: uuid.UUID,
    user_id: str,
    db: AsyncSession,
) -> Sequence[schemas_tickets.EventSimple]:
    if not await utils_mypayment.can_user_manage_events(
        user_id=user_id,
        store_id=store_id,
        db=db,
    ):
        raise HTTPException(
            status_code=403,
            detail="User is not authorized to manage store events",
        )

    return await cruds_tickets.get_events_by_store_id(
        store_id=store_id,
        db=db,
    )


async def check_answer_validity_and_calculate_price(
    event_id: UUID,
    checkout: schemas_tickets.Checkout,
    db: AsyncSession,
) -> int:
    price = 0

    questions = await cruds_tickets.get_questions_by_event_id(
        event_id=event_id,
        db=db,
    )
    questions_dict = {question.id: question for question in questions}
    required_questions_ids = {
        question.id for question in questions if question.required
    }
    answered_questions_ids = set()

    for answer in checkout.answers:
        if answer.question_id in answered_questions_ids:
            raise HTTPException(
                400,
                f"Question with id {answer.question_id} is answered multiple times",
            )
        answered_questions_ids.add(answer.question_id)
        required_questions_ids.discard(answer.question_id)

        question = questions_dict.get(answer.question_id)
        if question is None:
            raise HTTPException(
                400,
                f"Question with id {answer.question_id} not found for this event",
            )
        if question.disabled:
            raise HTTPException(
                400,
                f"Question with id {answer.question_id} is disabled",
            )

        if question.answer_type != answer.answer.answer_type:
            raise HTTPException(
                400,
                f"Answer type for question with id {answer.question_id} should be {question.answer_type.value}",
            )

        if question.price is not None:
            price += question.price

    if len(required_questions_ids) > 0:
        raise HTTPException(
            400,
            f"Answers for questions {', '.join(str(q) for q in required_questions_ids)} are required",
        )

    return price
