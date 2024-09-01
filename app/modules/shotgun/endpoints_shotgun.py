import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import (
    Depends,
    HTTPException,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core, schemas_core
from app.core.config import Settings
from app.core.groups.groups_type import GroupType
from app.core.payment.payment_tool import PaymentTool
from app.dependencies import (
    get_db,
    get_payment_tool,
    get_settings,
    is_user_a_member_of,
)
from app.modules.shotgun import cruds_shotgun, models_shotgun, schemas_shotgun
from app.modules.shotgun.utils_shotgun import (
    validate_payment,
)
from app.types.module import Module
from app.utils.tools import is_user_member_of_an_allowed_group

module = Module(
    root="shotgun",
    tag="Shotgun",
    payment_callback=validate_payment,
    default_allowed_groups_ids=[GroupType.AE],
)

hyperion_error_logger = logging.getLogger("hyperion.error")


@module.router.get(
    "/shotgun/organizers/",
    response_model=list[schemas_shotgun.OrganizerComplete],
    status_code=200,
)
async def get_organizers(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Get all organizers.

    **User must be Admin to use this endpoint**
    """
    return await cruds_shotgun.get_organizers(db)


@module.router.post(
    "/shotgun/organizers/",
    response_model=schemas_shotgun.OrganizerComplete,
    status_code=201,
)
async def create_organizer(
    organizer: schemas_shotgun.OrganizerBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Create an organizer.

    **User must be Admin to use this endpoint**
    """
    if await cruds_shotgun.get_organizers_by_group_ids(
        db=db,
        group_ids=[organizer.group_id],
    ):
        raise HTTPException(
            status_code=403,
            detail="This group is already a shotgun organizer.",
        )
    db_organizer = models_shotgun.ShotgunOrganizer(
        id=uuid4(),
        **organizer.model_dump(),
    )
    try:
        cruds_shotgun.create_organizer(db, db_organizer)
        await db.commit()
        return await cruds_shotgun.get_organizer_by_id(
            db=db,
            organizer_id=db_organizer.id,
        )
    except Exception:
        await db.rollback()
        raise


@module.router.delete(
    "/shotgun/organizers/{organizer_id}/",
    status_code=204,
)
async def delete_organizer(
    organizer_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Delete an organizer.

    **User must be Admin to use this endpoint**
    """
    if await cruds_shotgun.get_sessions_by_organizer_id(
        db=db,
        organizer_id=organizer_id,
    ):
        raise HTTPException(
            status_code=403,
            detail="Please delete all this organizer sessions first.",
        )
    await cruds_shotgun.delete_organizer(
        organizer_id=organizer_id,
        db=db,
    )
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise


@module.router.get(
    "/shotgun/sessions/",
    response_model=list[schemas_shotgun.SessionComplete],
    status_code=200,
)
async def get_sessions(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.AE)),
):
    """
    Get all sessions.

    **User must have an AEECL membership to use this endpoint**
    """
    return await cruds_shotgun.get_sessions(db)


@module.router.get(
    "/shotgun/organizers/{organizer_id}/sessions/",
    response_model=schemas_shotgun.SessionComplete,
    status_code=200,
)
async def get_sessions_by_id(
    organizer_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.AE)),
):
    """
    Get all sessions.

    **User must have an AEECL membership to use this endpoint**
    """
    organizer = await cruds_shotgun.get_organizer_by_id(
        db=db,
        organizer_id=organizer_id,
    )
    if not organizer:
        raise HTTPException(
            status_code=404,
            detail="Organizer not found.",
        )
    if not (
        organizer.group_id in [group.id for group in user.groups]
        or is_user_member_of_an_allowed_group(user, [GroupType.admin])
    ):
        raise HTTPException(
            status_code=403,
            detail="User must be part of the organizer group.",
        )

    return await cruds_shotgun.get_sessions_by_organizer_id(
        db,
        organizer_id=organizer_id,
    )


@module.router.post(
    "/shotgun/organizers/{organizer_id}/sessions/",
    response_model=list[schemas_shotgun.SessionComplete],
    status_code=201,
)
async def create_session(
    organizer_id: UUID,
    session: schemas_shotgun.SessionBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.AE)),
):
    """
    Get all sessions.

    **User must have an AEECL membership to use this endpoint**
    """
    organizer = await cruds_shotgun.get_organizer_by_id(
        db=db,
        organizer_id=organizer_id,
    )
    if not organizer:
        raise HTTPException(
            status_code=404,
            detail="Organizer not found.",
        )
    if not (
        organizer.group_id in [group.id for group in user.groups]
        or is_user_member_of_an_allowed_group(user, [GroupType.admin])
    ):
        raise HTTPException(
            status_code=403,
            detail="User must be part of the organizer group.",
        )

    db_session = models_shotgun.ShotgunSession(id=uuid4(), **session.model_dump())
    cruds_shotgun.create_session(db=db, session=db_session)

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return await cruds_shotgun.get_session_by_id(db, session_id=db_session.id)


@module.router.delete(
    "/shotgun/organizers/{organizer_id}/sessions/{session_id}/",
    status_code=204,
)
async def delete_session(
    organizer_id: UUID,
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.AE)),
):
    organizer = await cruds_shotgun.get_organizer_by_id(
        db=db,
        organizer_id=organizer_id,
    )
    if not organizer:
        raise HTTPException(
            status_code=404,
            detail="Organizer not found.",
        )
    if not (
        organizer.group_id in [group.id for group in user.groups]
        or is_user_member_of_an_allowed_group(user, [GroupType.admin])
    ):
        raise HTTPException(
            status_code=403,
            detail="User must be part of the organizer group.",
        )
    session = await cruds_shotgun.get_session_by_id(db=db, session_id=session_id)
    if not session or organizer_id != session.id:
        raise HTTPException(
            status_code=404,
            detail="No such session or session is unrelated to this organizer.",
        )

    tickets = await cruds_shotgun.get_session_tickets(db=db, session_id=session_id)
    for ticket in tickets:
        if ticket.scan_left > 0 and ticket.expiration < datetime.now(UTC):
            raise HTTPException(
                status_code=403,
                detail="You can't delete this session as tickets for this session are still usable.",
            )
    # As no ticket for this session are usable, we will delete this session with all the tickets and generators.
    await cruds_shotgun.delete_session(db=db, session_id=session_id)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise


@module.router.get(
    "/shotgun/organizers/{organizer_id}/sessions/{session_id}/generators/",
    response_model=list[schemas_shotgun.GeneratorComplete],
    status_code=200,
)
async def get_session_generators(
    organizer_id: UUID,
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.AE)),
):
    organizer = await cruds_shotgun.get_organizer_by_id(
        db=db,
        organizer_id=organizer_id,
    )
    if not organizer:
        raise HTTPException(
            status_code=404,
            detail="Organizer not found.",
        )
    if not (
        organizer.group_id in [group.id for group in user.groups]
        or is_user_member_of_an_allowed_group(user, [GroupType.admin])
    ):
        raise HTTPException(
            status_code=403,
            detail="User must be part of the organizer group.",
        )
    session = await cruds_shotgun.get_session_by_id(db=db, session_id=session_id)
    if not session or organizer_id != session.id:
        raise HTTPException(
            status_code=404,
            detail="No such session or session is unrelated to this organizer.",
        )
    return await cruds_shotgun.get_session_generators(db=db, session_id=session_id)


@module.router.post(
    "/shotgun/organizers/{organizer_id}/sessions/{session_id}/generators/",
    response_model=list[schemas_shotgun.GeneratorComplete],
    status_code=201,
)
async def create_generator(
    organizer_id: UUID,
    session_id: UUID,
    generator: schemas_shotgun.GeneratorBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.AE)),
):
    organizer = await cruds_shotgun.get_organizer_by_id(
        db=db,
        organizer_id=organizer_id,
    )
    if not organizer:
        raise HTTPException(
            status_code=404,
            detail="Organizer not found.",
        )
    if not (
        organizer.group_id in [group.id for group in user.groups]
        or is_user_member_of_an_allowed_group(user, [GroupType.admin])
    ):
        raise HTTPException(
            status_code=403,
            detail="User must be part of the organizer group.",
        )
    session = await cruds_shotgun.get_session_by_id(db=db, session_id=session_id)
    if not session or organizer_id != session.id:
        raise HTTPException(
            status_code=404,
            detail="No such session or session is unrelated to this organizer.",
        )

    db_generator = models_shotgun.ShotgunTicketGenerator(
        id=uuid4(),
        session_id=session_id,
        **generator.model_dump(),
    )
    cruds_shotgun.create_generator(db=db, generator=db_generator)

    # Create tickets for already paid purchases of this session
    purchases = await cruds_shotgun.get_paid_session_purchases(
        db=db,
        session_id=session_id,
    )
    for purchase in purchases:
        ticket = models_shotgun.ShotgunTicket(
            id=uuid4(),
            secret=uuid4(),
            generator_id=db_generator.id,
            session_id=session_id,
            user_id=purchase.user_id,
            name=db_generator.name,
            scan_left=db_generator.max_use,
            expiration=db_generator.expiration,
            tags="",
        )
        cruds_shotgun.create_ticket(db=db, ticket=ticket)

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise


@module.router.delete(
    "/shotgun/organizers/{organizer_id}/sessions/{session_id}/generators/{generator_id}/",
    status_code=204,
)
async def delete_generator(
    organizer_id: UUID,
    session_id: UUID,
    generator_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.AE)),
):
    organizer = await cruds_shotgun.get_organizer_by_id(
        db=db,
        organizer_id=organizer_id,
    )
    if not organizer:
        raise HTTPException(
            status_code=404,
            detail="Organizer not found.",
        )
    if not (
        organizer.group_id in [group.id for group in user.groups]
        or is_user_member_of_an_allowed_group(user, [GroupType.admin])
    ):
        raise HTTPException(
            status_code=403,
            detail="User must be part of the organizer group.",
        )
    session = await cruds_shotgun.get_session_by_id(db=db, session_id=session_id)
    if not session or organizer_id != session.id:
        raise HTTPException(
            status_code=404,
            detail="No such session or session is unrelated to this organizer.",
        )
    generator = await cruds_shotgun.get_generator_by_id(
        db=db,
        generator_id=generator_id,
    )
    if not generator or session_id != generator.id:
        raise HTTPException(
            status_code=404,
            detail="No such generator or generator is unrelated to this session.",
        )
    await cruds_shotgun.delete_generator(db=db, generator_id=generator_id)

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise


@module.router.get(
    "/shotgun/organizers/{organizer_id}/sessions/{session_id}/purchases/",
    status_code=200,
    response_model=list[schemas_shotgun.PurchaseComplete],
)
async def get_session_purchases(
    organizer_id: UUID,
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.AE)),
):
    organizer = await cruds_shotgun.get_organizer_by_id(
        db=db,
        organizer_id=organizer_id,
    )
    if not organizer:
        raise HTTPException(
            status_code=404,
            detail="Organizer not found.",
        )
    if not (
        organizer.group_id in [group.id for group in user.groups]
        or is_user_member_of_an_allowed_group(user, [GroupType.admin])
    ):
        raise HTTPException(
            status_code=403,
            detail="User must be part of the organizer group.",
        )
    session = await cruds_shotgun.get_session_by_id(db=db, session_id=session_id)
    if not session or organizer_id != session.id:
        raise HTTPException(
            status_code=404,
            detail="No such session or session is unrelated to this organizer.",
        )
    return await cruds_shotgun.get_paid_session_purchases(db=db, session_id=session_id)


@module.router.post(
    "/shotgun/organizers/{organizer_id}/sessions/{session_id}/purchases/",
    response_model=list[schemas_shotgun.PurchaseComplete],
    status_code=200,
)
async def create_purchase(
    organizer_id: UUID,
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    payment_tool: PaymentTool = Depends(get_payment_tool),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.AE)),
):
    organizer = await cruds_shotgun.get_organizer_by_id(
        db=db,
        organizer_id=organizer_id,
    )
    if not organizer:
        raise HTTPException(
            status_code=404,
            detail="Organizer not found.",
        )
    session = await cruds_shotgun.get_session_by_id_for_purchase(
        db=db,
        session_id=session_id,
    )
    if not session or organizer_id != session.id:
        raise HTTPException(
            status_code=404,
            detail="No such session or session is unrelated to this organizer.",
        )
    if session.quantity <= 0:
        raise HTTPException(
            status_code=403,
            detail="All tickets have been sold.",
        )

    await cruds_shotgun.remove_one_place_from_session(db=db, session_id=session_id)

    user_schema = schemas_core.CoreUser(**user.__dict__)
    checkout = await payment_tool.init_checkout(
        module=module.root,
        helloasso_slug="AEECL",
        checkout_amount=session.price,
        checkout_name="SHOTGUN - " + session.name,
        redirection_uri=settings.SHOTGUN_PAYMENT_REDIRECTION_URL or "",
        payer_user=user_schema,
        db=db,
    )
    hyperion_error_logger.info(f"CDR: Logging Checkout id {checkout.id}")

    db_purchase = models_shotgun.ShotgunPurchase(
        id=uuid4(),
        session_id=session_id,
        user_id=user.id,
        checkout_id=checkout.id,
        purchased_on=datetime.now(UTC),
        paid=False,
    )
    cruds_shotgun.create_purchase(db=db, purchase=db_purchase)

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise
