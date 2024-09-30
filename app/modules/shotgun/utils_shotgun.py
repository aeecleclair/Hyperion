import logging
from uuid import uuid4

from fastapi import (
    HTTPException,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core
from app.core.groups.groups_type import GroupType
from app.core.payment import schemas_payment
from app.dependencies import (
    hyperion_access_logger,
)
from app.modules.shotgun import cruds_shotgun, models_shotgun
from app.utils.tools import (
    is_user_member_of_an_allowed_group,
)

hyperion_error_logger = logging.getLogger("hyperion.error")


async def validate_payment(
    checkout_payment: schemas_payment.CheckoutPayment,
    db: AsyncSession,
) -> None:
    paid_amount = checkout_payment.paid_amount
    purchase_id = checkout_payment.checkout_id

    purchase = await cruds_shotgun.get_purchase_by_id(
        db=db,
        purchase_id=purchase_id,
    )
    if not purchase:
        hyperion_error_logger.error(
            f"Shotgun payment callback: user checkout {purchase_id} not found.",
        )
        raise ValueError(f"User checkout {purchase_id} not found.")  # noqa: TRY003

    await cruds_shotgun.mark_purchase_as_paid(db=db, purchase_id=purchase_id)

    session = await cruds_shotgun.get_session_by_id(
        db=db,
        session_id=purchase.session_id,
    )
    if not session:
        hyperion_error_logger.error(
            f"Shotgun payment callback: shotgun session {purchase.session_id} not found.",
        )
        raise ValueError(f"Shotgun session {purchase.session_id} not found.")  # noqa: TRY003

    if paid_amount != session.price:
        hyperion_error_logger.error(
            f"User paid the wrong price. Paid {paid_amount}, expected {session.price}.",
        )
        raise ValueError("User paid the wrong price.")  # noqa: TRY003

    generators = await cruds_shotgun.get_session_generators(
        db=db,
        session_id=purchase.session_id,
    )
    for generator in generators:
        ticket = models_shotgun.ShotgunTicket(
            id=uuid4(),
            secret=uuid4(),
            generator_id=generator.id,
            session_id=purchase.session_id,
            user_id=purchase.user_id,
            name=generator.name,
            scan_left=generator.max_use,
            tags="",
            expiration=generator.expiration,
        )
        cruds_shotgun.create_ticket(db=db, ticket=ticket)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise


async def is_user_an_organizer(
    user: models_core.CoreUser,
    db: AsyncSession,
):
    """
    Check if the user is in a group that is a Shotgun Organizer.
    """
    organizers = await cruds_shotgun.get_organizers_by_group_ids(
        db,
        group_ids=[group.id for group in user.groups],
    )

    if organizers == [] and not is_user_member_of_an_allowed_group(
        user=user,
        allowed_groups=[GroupType.admin],
    ):
        hyperion_access_logger.warning(
            "Is_user_a_member_of: Unauthorized, user is not a seller",
        )

        raise HTTPException(
            status_code=403,
            detail="User is not an organiser.",
        )

    return user
