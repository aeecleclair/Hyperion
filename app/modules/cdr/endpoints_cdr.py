import logging
import os
import re
from collections.abc import Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import (
    BackgroundTasks,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core, schemas_core
from app.core.config import Settings
from app.core.groups import cruds_groups
from app.core.groups.groups_type import GroupType
from app.core.payment.payment_tool import PaymentTool
from app.core.users import cruds_users
from app.core.users.cruds_users import get_user_by_id, get_users
from app.dependencies import (
    get_db,
    get_payment_tool,
    get_settings,
    get_websocket_connection_manager,
    is_user,
    is_user_a_member,
    is_user_a_member_of,
)
from app.modules.cdr import cruds_cdr, models_cdr, schemas_cdr
from app.modules.cdr.types_cdr import (
    CdrLogActionType,
    CdrStatus,
    DocumentSignatureType,
)
from app.modules.cdr.utils_cdr import (
    check_request_consistency,
    construct_dataframe_from_users_purchases,
    is_user_in_a_seller_group,
    validate_payment,
)
from app.types.membership import AvailableAssociationMembership
from app.types.module import Module
from app.types.scopes_type import ScopeType
from app.types.websocket import (
    ConnectionWSMessageModel,
    ConnectionWSMessageModelData,
    ConnectionWSMessageModelStatus,
    HyperionWebsocketsRoom,
    WebsocketConnectionManager,
)
from app.utils.auth import auth_utils

# from app.utils.mail.mailworker import send_email
from app.utils.tools import (
    create_and_send_email_migration,
    get_core_data,
    is_user_member_of_an_allowed_group,
    set_core_data,
)

module = Module(
    root="cdr",
    tag="Cdr",
    payment_callback=validate_payment,
    default_allowed_groups_ids=[GroupType.admin_cdr],
)

hyperion_error_logger = logging.getLogger("hyperion.error")


@module.router.get(
    "/cdr/users/",
    response_model=list[schemas_cdr.CdrUserPreview],
    status_code=200,
)
async def get_cdr_users(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get all users.

    **User must be part of a seller group to use this endpoint**
    """
    if not (
        is_user_member_of_an_allowed_group(user, [GroupType.admin_cdr])
        or await cruds_cdr.get_sellers_by_group_ids(
            db=db,
            group_ids=[g.id for g in user.groups],
        )
    ):
        raise HTTPException(
            status_code=403,
            detail="You must be a seller to use this endpoint.",
        )
    users = {u.id: u.__dict__ for u in await get_users(db=db)}
    curriculum = await cruds_cdr.get_cdr_users_curriculum(db)
    curriculum_complete = {c.id: c for c in await cruds_cdr.get_curriculums(db=db)}
    for c in curriculum:
        users[c.user_id]["curriculum"] = curriculum_complete[c.curriculum_id]

    return list(users.values())


@module.router.get(
    "/cdr/users/pending/",
    response_model=list[schemas_cdr.CdrUserPreview],
    status_code=200,
)
async def get_cdr_users_pending_validation(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get all users that have non-validated purchases.

    **User must be part of a seller group to use this endpoint**
    """
    if not (
        is_user_member_of_an_allowed_group(user, [GroupType.admin_cdr])
        or await cruds_cdr.get_sellers_by_group_ids(
            db=db,
            group_ids=[g.id for g in user.groups],
        )
    ):
        raise HTTPException(
            status_code=403,
            detail="You must be a seller to use this endpoint.",
        )
    core_users = await cruds_cdr.get_pending_validation_users(db=db)

    # We construct a dict of {curriculum_id: curriculum}
    curriculum_mapping = {c.id: c for c in await cruds_cdr.get_curriculums(db=db)}

    # We construct a dict of {user_id: curriculum}
    curriculum_memberships = await cruds_cdr.get_cdr_users_curriculum(db)
    curriculum_memberships_mapping = {
        membership.user_id: curriculum_mapping[membership.curriculum_id]
        for membership in curriculum_memberships
    }

    return [
        schemas_cdr.CdrUser(
            curriculum=curriculum_memberships_mapping.get(user.id, None),
            **user.__dict__,
        )
        for user in core_users
    ]


@module.router.get(
    "/cdr/users/{user_id}/",
    response_model=schemas_cdr.CdrUser,
    status_code=200,
)
async def get_cdr_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
):
    """
    Get a user.

    **User must be part of a seller group or trying to get itself to use this endpoint**
    """
    if user.id != user_id:
        if not (
            is_user_member_of_an_allowed_group(user, [GroupType.admin_cdr])
            or await cruds_cdr.get_sellers_by_group_ids(
                db=db,
                group_ids=[g.id for g in user.groups],
            )
        ):
            raise HTTPException(
                status_code=403,
                detail="You must be a seller to use this endpoint.",
            )
    user_db = await get_user_by_id(db, user_id)
    if not user_db:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )
    user_dict = user_db.__dict__
    curriculum = await cruds_cdr.get_cdr_user_curriculum(db, user_id)
    curriculum_complete = {c.id: c for c in await cruds_cdr.get_curriculums(db=db)}
    if curriculum:
        user_dict["curriculum"] = curriculum_complete[curriculum.curriculum_id]
    return schemas_cdr.CdrUser(**user_dict)


@module.router.patch(
    "/cdr/users/{user_id}/",
    status_code=204,
)
async def update_cdr_user(
    user_id: str,
    user_update: schemas_cdr.CdrUserUpdate,
    db: AsyncSession = Depends(get_db),
    seller_user: models_core.CoreUser = Depends(
        is_user_a_member_of(GroupType.admin_cdr),
    ),
    ws_manager: WebsocketConnectionManager = Depends(get_websocket_connection_manager),
    settings: Settings = Depends(get_settings),
):
    """
    Edit a user email, nickname and/or floor.

    An email will be send to the user, to confirm its new address.

    **User must be part of a seller group to use this endpoint**
    """
    user_db = await get_user_by_id(db, user_id)
    if not user_db:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    if user_update.email:
        if user_db.email != user_update.email:
            # We won't migrate the email if the email provided is the same as the current one
            if not re.match(
                r"^[\w\-.]*@((etu(-enise)?|enise)\.)?ec-lyon\.fr$",
                user_update.email,
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid ECL email address.",
                )

            existing_user = await cruds_users.get_user_by_email(
                db=db,
                email=user_update.email,
            )
            if existing_user is not None:
                raise HTTPException(
                    status_code=400,
                    detail="A user already exist with this email address",
                )

            await create_and_send_email_migration(
                user_id=user_db.id,
                new_email=user_update.email,
                old_email=user_db.email,
                # We make the user non external with this migration
                make_user_external=False,
                db=db,
                settings=settings,
            )

    try:
        if user_update.floor or user_update.nickname:
            await cruds_users.update_user(
                db=db,
                user_id=user_id,
                user_update=schemas_core.CoreUserUpdate(
                    nickname=user_update.nickname,
                    floor=user_update.floor,
                ),
            )
    except Exception:
        await db.rollback()
        raise

    user_db = await get_user_by_id(db, user_id)
    if not user_db:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    curriculum = await cruds_cdr.get_cdr_user_curriculum(db, user_id)

    cdr_status = await get_core_data(schemas_cdr.Status, db)
    if cdr_status.status == CdrStatus.onsite:
        try:
            await ws_manager.send_message_to_room(
                message=schemas_cdr.UpdateUserWSMessageModel(
                    data=schemas_cdr.CdrUser(
                        curriculum=schemas_cdr.CurriculumComplete(
                            **curriculum.__dict__,
                        ),
                        **user_db.__dict__,
                    ),
                ),
                room_id=HyperionWebsocketsRoom.CDR,
            )
        except Exception:
            hyperion_error_logger.exception(
                f"Error while sending a message to the room {HyperionWebsocketsRoom.CDR}",
            )


@module.router.get(
    "/cdr/sellers/",
    response_model=list[schemas_cdr.SellerComplete],
    status_code=200,
)
async def get_sellers(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    """
    Get all sellers.

    **User must be CDR Admin to use this endpoint**
    """
    return await cruds_cdr.get_sellers(db)


@module.router.get(
    "/cdr/users/me/sellers/",
    response_model=list[schemas_cdr.SellerComplete],
    status_code=200,
)
async def get_sellers_by_user_id(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get sellers user is part of the group. If user is adminCDR, returns all sellers.

    **User must be authenticated to use this endpoint**
    """

    if is_user_member_of_an_allowed_group(
        user=user,
        allowed_groups=[GroupType.admin_cdr],
    ):
        return await cruds_cdr.get_sellers(db)
    return await cruds_cdr.get_sellers_by_group_ids(
        db,
        [x.id for x in user.groups],
    )


@module.router.get(
    "/cdr/online/sellers/",
    response_model=list[schemas_cdr.SellerComplete],
    status_code=200,
)
async def get_online_sellers(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
):
    """
    Get all sellers that has online available products.

    **User must be authenticated to use this endpoint**
    """
    return await cruds_cdr.get_online_sellers(db)


async def generate_and_send_results(
    seller_id: UUID,
    # emails: schemas_cdr.ResultRequest,
    db: AsyncSession,
    # settings: Settings,
) -> Path:
    seller = await cruds_cdr.get_seller_by_id(db, seller_id)
    if not seller:
        raise HTTPException(
            status_code=404,
            detail="Seller not found.",
        )
    seller_group = await cruds_groups.get_group_by_id(db, seller.group_id)
    if seller_group is None:
        raise HTTPException(
            status_code=404,
            detail="Seller group not found.",
        )
    products = await cruds_cdr.get_products_by_seller_id(db, seller_id)
    if len(products) == 0:
        raise HTTPException(
            status_code=400,
            detail="There is no products for this seller so there is no results to send.",
        )
    variants: list[models_cdr.ProductVariant] = []
    product_fields: dict[UUID, list[models_cdr.CustomDataField]] = {}
    for product in products:
        product_variants = await cruds_cdr.get_product_variants(db, product.id)
        variants.extend(product_variants)
        product_fields[product.id] = list(
            await cruds_cdr.get_product_customdata_fields(
                db,
                product.id,
            ),
        )
    variant_ids = [v.id for v in product_variants]
    purchases = await cruds_cdr.get_all_purchases(db)
    if len(purchases) == 0:
        raise HTTPException(
            status_code=400,
            detail="There is no purchases in the database so there is no results to send.",
        )
    purchases_by_users: dict[str, list[models_cdr.Purchase]] = {}
    users = await get_users(db)
    for purchase in purchases:
        if purchase.product_variant_id in variant_ids:
            if purchase.user_id not in purchases_by_users:
                purchases_by_users[purchase.user_id] = []
            purchases_by_users[purchase.user_id].append(purchase)
    users_answers = {}
    for each_user in users:
        users_answers[each_user.id] = list(
            await cruds_cdr.get_customdata_by_user_id(
                db,
                each_user.id,
            ),
        )
    hyperion_error_logger.info(
        f"Data for seller {seller.name} fetched. Starting to construct the dataframe.",
    )
    df = construct_dataframe_from_users_purchases(
        users_purchases=purchases_by_users,
        users=list(users),
        products=list(products),
        variants=variants,
        data_fields=product_fields,
        users_answers=users_answers,
    )
    hyperion_error_logger.info(
        f"Dataframe for seller {seller.name} constructed. Generating the Excel file.",
    )

    file_directory = "/app/data/cdr"
    file_uuid = uuid4()
    # file_name = f"CdR {datetime.now(tz=UTC).year} ventes {seller.name}.xlsx"

    Path.mkdir(Path(file_directory), parents=True, exist_ok=True)
    df.to_excel(
        Path(file_directory, str(file_uuid)),
        index=False,
        freeze_panes=(2, 3),
        engine="xlsxwriter",
    )
    return Path(file_directory, str(file_uuid))

    # Not working, we have to keep the file in the server
    # hyperion_error_logger.debug(
    #     f"Excel file for seller {seller.name} generated. Sending the email.",
    # )
    # send_email(
    #     recipient=emails.emails,
    #     subject=f"Résultats de ventes pour {seller.name}",
    #     content=f"Bonjour,\n\nVous trouverez en pièce jointe le fichier Excel contenant les résultats de ventes pour la CdR pour l'association {seller.name}.",
    #     settings=settings,
    #     file_directory=file_directory,
    #     file_uuid=file_uuid,
    #     file_name=file_name,
    #     main_type="text",
    #     sub_type="xlsx",
    # )
    # hyperion_error_logger.info(
    #     f"Results for seller {seller.name} sent to {emails.emails}",
    # )
    # Path.unlink(Path(file_directory, file_name))


@module.router.get(
    "/cdr/sellers/{seller_id}/results/",
    status_code=200,
    response_class=FileResponse,
)
async def send_seller_results(
    seller_id: UUID,
    # emails: schemas_cdr.ResultRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
    # settings: Settings = Depends(get_settings),
):
    """
    Get a seller's results.

    **User must be CDR Admin to use this endpoint**
    """
    # We don't use the emails parameter for now
    # background_tasks.add_task(
    #     generate_and_send_results,
    #     seller_id=seller_id,
    #     # emails=emails,
    #     db=db,
    #     # settings=settings,
    # )

    path = await generate_and_send_results(seller_id=seller_id, db=db)
    return FileResponse(path)


@module.router.get(
    "/cdr/online/products/",
    response_model=list[schemas_cdr.ProductComplete],
    status_code=200,
)
async def get_all_available_online_products(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
):
    """
    Get a seller's online available products.

    **User must be authenticated to use this endpoint**
    """
    return await cruds_cdr.get_online_products(db)


@module.router.get(
    "/cdr/products/",
    response_model=list[schemas_cdr.ProductComplete],
    status_code=200,
)
async def get_all_products(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get a seller's online available products.

    **User must be part of a seller group to use this endpoint**
    """
    sellers = await cruds_cdr.get_sellers_by_group_ids(
        db,
        [x.id for x in user.groups],
    )
    if not (sellers or is_user_member_of_an_allowed_group(user, [GroupType.admin_cdr])):
        raise HTTPException(
            status_code=403,
            detail="You must be a seller to get all documents.",
        )
    return await cruds_cdr.get_products(db)


@module.router.post(
    "/cdr/sellers/",
    response_model=schemas_cdr.SellerComplete,
    status_code=201,
)
async def create_seller(
    seller: schemas_cdr.SellerBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    """
    Create a seller.

    **User must be CDR Admin to use this endpoint**
    """
    if await cruds_cdr.get_sellers_by_group_ids(
        db=db,
        group_ids=[seller.group_id],
    ):
        raise HTTPException(
            status_code=403,
            detail="There is already a seller for this group.",
        )
    db_seller = models_cdr.Seller(
        id=uuid4(),
        **seller.model_dump(),
    )
    try:
        cruds_cdr.create_seller(db, db_seller)
        await db.commit()
        return await cruds_cdr.get_seller_by_id(db=db, seller_id=db_seller.id)
    except Exception:
        await db.rollback()
        raise


@module.router.patch(
    "/cdr/sellers/{seller_id}/",
    status_code=204,
)
async def update_seller(
    seller_id: UUID,
    seller: schemas_cdr.SellerEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    """
    Update a seller.

    **User must be CDR Admin to use this endpoint**
    """
    await check_request_consistency(db=db, seller_id=seller_id)

    if not bool(seller.model_fields_set):
        raise HTTPException(
            status_code=400,
            detail="You must specify at least one field to update",
        )

    try:
        await cruds_cdr.update_seller(
            seller_id=seller_id,
            seller=seller,
            db=db,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise


@module.router.delete(
    "/cdr/sellers/{seller_id}/",
    status_code=204,
)
async def delete_seller(
    seller_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    """
    Delete a seller.

    **User must be CDR Admin to use this endpoint**
    """
    await check_request_consistency(db=db, seller_id=seller_id)
    if await cruds_cdr.get_products_by_seller_id(
        db=db,
        seller_id=seller_id,
    ) or await cruds_cdr.get_documents_by_seller_id(db=db, seller_id=seller_id):
        raise HTTPException(
            status_code=403,
            detail="Please delete all this seller products and documents first.",
        )
    try:
        await cruds_cdr.delete_seller(
            seller_id=seller_id,
            db=db,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise


@module.router.get(
    "/cdr/sellers/{seller_id}/products/",
    response_model=list[schemas_cdr.ProductComplete],
    status_code=200,
)
async def get_products_by_seller_id(
    seller_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get a seller's products.

    **User must be part of the seller's group to use this endpoint**
    """
    await is_user_in_a_seller_group(seller_id, user=user, db=db)
    return await cruds_cdr.get_products_by_seller_id(db, seller_id)


@module.router.get(
    "/cdr/online/sellers/{seller_id}/products/",
    response_model=list[schemas_cdr.ProductComplete],
    status_code=200,
)
async def get_available_online_products(
    seller_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
):
    """
    Get a seller's online available products.

    **User must be authenticated to use this endpoint**
    """
    return await cruds_cdr.get_online_products_by_seller_id(db, seller_id)


@module.router.post(
    "/cdr/sellers/{seller_id}/products/",
    response_model=schemas_cdr.ProductComplete,
    status_code=201,
)
async def create_product(
    seller_id: UUID,
    product: schemas_cdr.ProductBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Create a product.

    **User must be part of the seller's group to use this endpoint**
    """
    await is_user_in_a_seller_group(
        seller_id,
        user=user,
        db=db,
    )
    status = await get_core_data(schemas_cdr.Status, db)
    if status.status == CdrStatus.closed:
        raise HTTPException(
            status_code=403,
            detail="CDR is closed. You cant add a new product.",
        )
    db_product = models_cdr.CdrProduct(
        id=uuid4(),
        seller_id=seller_id,
        **product.model_dump(
            exclude={"product_constraints", "document_constraints", "ticket"},
        ),
    )
    try:
        cruds_cdr.create_product(db, db_product)
        for constraint_id in product.product_constraints:
            cruds_cdr.create_product_constraint(
                db,
                models_cdr.ProductConstraint(
                    product_id=db_product.id,
                    product_constraint_id=constraint_id,
                ),
            )
        for constraint_id in product.document_constraints:
            cruds_cdr.create_document_constraint(
                db,
                models_cdr.DocumentConstraint(
                    product_id=db_product.id,
                    document_id=constraint_id,
                ),
            )
        for ticket in product.tickets:
            cruds_cdr.create_ticket_generator(
                db,
                models_cdr.TicketGenerator(id=uuid4(), **ticket.model_dump()),
            )
        await db.commit()
        return await cruds_cdr.get_product_by_id(db, db_product.id)
    except Exception:
        await db.rollback()
        raise


@module.router.patch(
    "/cdr/sellers/{seller_id}/products/{product_id}/",
    status_code=204,
)
async def update_product(
    seller_id: UUID,
    product_id: UUID,
    product: schemas_cdr.ProductEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Edit a product.

    **User must be part of the seller's group to use this endpoint**
    """

    if not bool(product.model_fields_set):
        # We verify that some fields are to be changed
        # These fields may be `product_constraints` or `document_constraints` that are updated manually
        raise HTTPException(
            status_code=400,
            detail="You must specify at least one field to update",
        )

    await is_user_in_a_seller_group(
        seller_id,
        user,
        db=db,
    )
    status = await get_core_data(schemas_cdr.Status, db)
    db_product = await check_request_consistency(
        db=db,
        seller_id=seller_id,
        product_id=product_id,
    )
    if status.status in [
        CdrStatus.onsite,
        CdrStatus.closed,
    ] or (
        db_product and status.status == CdrStatus.online and db_product.available_online
    ):
        raise HTTPException(
            status_code=403,
            detail="This product can't be edited now. Please try creating a new product.",
        )
    try:
        await cruds_cdr.update_product(
            product_id=product_id,
            product=product,
            db=db,
        )
        if product.product_constraints is not None:
            await cruds_cdr.delete_product_constraints(db=db, product_id=product_id)
            for constraint_id in product.product_constraints:
                cruds_cdr.create_product_constraint(
                    db,
                    models_cdr.ProductConstraint(
                        product_id=product_id,
                        product_constraint_id=constraint_id,
                    ),
                )
        if product.document_constraints is not None:
            await cruds_cdr.delete_document_constraints(db=db, product_id=product_id)
            for constraint_id in product.document_constraints:
                cruds_cdr.create_document_constraint(
                    db,
                    models_cdr.DocumentConstraint(
                        product_id=product_id,
                        document_id=constraint_id,
                    ),
                )
        await db.commit()
    except Exception:
        await db.rollback()
        raise


@module.router.delete(
    "/cdr/sellers/{seller_id}/products/{product_id}/",
    status_code=204,
)
async def delete_product(
    seller_id: UUID,
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Delete a product.

    **User must be part of the seller's group to use this endpoint**
    """
    await is_user_in_a_seller_group(
        seller_id,
        user,
        db=db,
    )
    status = await get_core_data(schemas_cdr.Status, db)
    db_product = await check_request_consistency(
        db=db,
        seller_id=seller_id,
        product_id=product_id,
    )
    if status.status in [
        CdrStatus.onsite,
        CdrStatus.closed,
    ] or (
        db_product and status.status == CdrStatus.online and db_product.available_online
    ):
        raise HTTPException(
            status_code=403,
            detail="You can't delete a product once CDR has started.",
        )
    variants = await cruds_cdr.get_product_variants(db=db, product_id=product_id)
    if variants:
        raise HTTPException(
            status_code=403,
            detail="You can't delete this product because some variants are related to it.",
        )
    try:
        await cruds_cdr.delete_product(
            product_id=product_id,
            db=db,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise


@module.router.post(
    "/cdr/sellers/{seller_id}/products/{product_id}/variants/",
    response_model=schemas_cdr.ProductVariantComplete,
    status_code=201,
)
async def create_product_variant(
    seller_id: UUID,
    product_id: UUID,
    product_variant: schemas_cdr.ProductVariantBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Create a product variant.

    **User must be part of the seller's group to use this endpoint**
    """
    await is_user_in_a_seller_group(
        seller_id,
        user,
        db=db,
    )
    product = await check_request_consistency(
        db=db,
        seller_id=seller_id,
        product_id=product_id,
    )
    status = await get_core_data(schemas_cdr.Status, db)
    if status.status == CdrStatus.closed:
        raise HTTPException(
            status_code=403,
            detail="CDR is closed. You cant add a new product.",
        )
    db_product_variant = models_cdr.ProductVariant(
        id=uuid4(),
        product_id=product_id,
        **product_variant.model_dump(exclude={"allowed_curriculum"}),
    )
    if (
        product
        and product.related_membership
        and not db_product_variant.related_membership_added_duration
    ):
        raise HTTPException(
            status_code=403,
            detail="This product has a related membership. Please specify a memberhsip duration for this variant.",
        )
    if (
        product
        and not product.related_membership
        and db_product_variant.related_membership_added_duration
    ):
        raise HTTPException(
            status_code=403,
            detail="This product has no related membership. You can't specify a membership duration.",
        )
    try:
        cruds_cdr.create_product_variant(db, db_product_variant)
        await db.commit()
        for c in product_variant.allowed_curriculum:
            cruds_cdr.create_allowed_curriculum(
                db,
                models_cdr.AllowedCurriculum(
                    product_variant_id=db_product_variant.id,
                    curriculum_id=c,
                ),
            )
        await db.commit()
        return await cruds_cdr.get_product_variant_by_id(
            db=db,
            variant_id=db_product_variant.id,
        )
    except Exception:
        await db.rollback()
        raise


@module.router.patch(
    "/cdr/sellers/{seller_id}/products/{product_id}/variants/{variant_id}/",
    status_code=204,
)
async def update_product_variant(
    seller_id: UUID,
    product_id: UUID,
    variant_id: UUID,
    product_variant: schemas_cdr.ProductVariantEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Edit a product variant.

    **User must be part of the seller's group to use this endpoint**
    """

    if not bool(product_variant.model_fields_set):
        raise HTTPException(
            status_code=400,
            detail="You must specify at least one field to update",
        )

    await is_user_in_a_seller_group(
        seller_id,
        user,
        db=db,
    )
    status = await get_core_data(schemas_cdr.Status, db)
    db_product = await check_request_consistency(
        db=db,
        seller_id=seller_id,
        product_id=product_id,
        variant_id=variant_id,
    )
    if product_variant.model_fields_set != {
        "enabled",
    }:
        if status.status in [
            CdrStatus.onsite,
            CdrStatus.closed,
        ] or (
            db_product
            and status.status == CdrStatus.online
            and db_product.available_online
        ):
            # We allow to update the enabled field even if CDR is onsite or closed
            raise HTTPException(
                status_code=403,
                detail="This product can't be edited now. Please try creating a new product.",
            )
    if (
        db_product
        and not db_product.related_membership
        and product_variant.related_membership_added_duration
    ):
        raise HTTPException(
            status_code=403,
            detail="This product has no related membership. You can't specify a membership duration.",
        )
    try:
        await cruds_cdr.update_product_variant(
            variant_id=variant_id,
            product_variant=product_variant,
            db=db,
        )
        if product_variant.allowed_curriculum is not None:
            await cruds_cdr.delete_allowed_curriculums(db=db, variant_id=variant_id)
            for c in product_variant.allowed_curriculum:
                cruds_cdr.create_allowed_curriculum(
                    db,
                    models_cdr.AllowedCurriculum(
                        product_variant_id=variant_id,
                        curriculum_id=c,
                    ),
                )
        await db.commit()
    except Exception:
        await db.rollback()
        raise


@module.router.delete(
    "/cdr/sellers/{seller_id}/products/{product_id}/variants/{variant_id}/",
    status_code=204,
)
async def delete_product_variant(
    seller_id: UUID,
    product_id: UUID,
    variant_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Delete a product variant.

    **User must be part of the seller's group to use this endpoint**
    """
    await is_user_in_a_seller_group(
        seller_id,
        user,
        db=db,
    )
    status = await get_core_data(schemas_cdr.Status, db)
    db_product = await check_request_consistency(
        db=db,
        seller_id=seller_id,
        product_id=product_id,
        variant_id=variant_id,
    )
    if status.status in [
        CdrStatus.onsite,
        CdrStatus.closed,
    ] or (
        db_product and status.status == CdrStatus.online and db_product.available_online
    ):
        raise HTTPException(
            status_code=403,
            detail="You can't delete a product once CDR has started.",
        )
    try:
        await cruds_cdr.delete_product_variant(
            variant_id=variant_id,
            db=db,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise


@module.router.get(
    "/cdr/sellers/{seller_id}/documents/",
    response_model=list[schemas_cdr.DocumentComplete],
    status_code=200,
)
async def get_seller_documents(
    seller_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get a seller's documents.

    **User must be part of the seller's group to use this endpoint**
    """
    await is_user_in_a_seller_group(
        seller_id,
        user,
        db=db,
    )
    return await cruds_cdr.get_documents_by_seller_id(db, seller_id=seller_id)


@module.router.get(
    "/cdr/documents/",
    response_model=list[schemas_cdr.DocumentComplete],
    status_code=200,
)
async def get_all_sellers_documents(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get a seller's documents.

    **User must be part of a seller's group to use this endpoint**
    """
    sellers = await cruds_cdr.get_sellers_by_group_ids(
        db,
        [x.id for x in user.groups],
    )
    if not (sellers or is_user_member_of_an_allowed_group(user, [GroupType.admin_cdr])):
        raise HTTPException(
            status_code=403,
            detail="You must be a seller to get all documents.",
        )

    return await cruds_cdr.get_all_documents(db)


@module.router.post(
    "/cdr/sellers/{seller_id}/documents/",
    response_model=schemas_cdr.DocumentComplete,
    status_code=201,
)
async def create_document(
    seller_id: UUID,
    document: schemas_cdr.DocumentBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Create a document.

    **User must be part of the seller's group to use this endpoint**
    """
    await is_user_in_a_seller_group(seller_id=seller_id, user=user, db=db)
    status = await get_core_data(schemas_cdr.Status, db)
    if status.status == CdrStatus.closed:
        raise HTTPException(
            status_code=403,
            detail="CDR is closed. You can't add a new document.",
        )
    await check_request_consistency(db=db, seller_id=seller_id)
    db_document = models_cdr.Document(
        id=uuid4(),
        seller_id=seller_id,
        name=document.name,
    )
    try:
        cruds_cdr.create_document(db, db_document)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    else:
        return db_document


@module.router.delete(
    "/cdr/sellers/{seller_id}/documents/{document_id}/",
    status_code=204,
)
async def delete_document(
    seller_id: UUID,
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Delete a document.

    **User must be part of the seller's group to use this endpoint**
    """
    await is_user_in_a_seller_group(seller_id=seller_id, user=user, db=db)
    await check_request_consistency(db=db, seller_id=seller_id, document_id=document_id)
    if await cruds_cdr.get_document_constraints_by_document_id(
        db=db,
        document_id=document_id,
    ):
        raise HTTPException(
            status_code=403,
            detail="You can't delete a document that is a constraint for a product.",
        )
    try:
        await cruds_cdr.delete_document(
            document_id=document_id,
            db=db,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise


@module.router.get(
    "/cdr/users/{user_id}/purchases/",
    response_model=list[schemas_cdr.PurchaseReturn],
    status_code=200,
)
async def get_purchases_by_user_id(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
):
    """
    Get a user's purchases.

    **User must get his own purchases or be CDR Admin to use this endpoint**
    """
    if not (
        user_id == user.id
        or is_user_member_of_an_allowed_group(user, [GroupType.admin_cdr])
    ):
        raise HTTPException(
            status_code=403,
            detail="You're not allowed to see other users purchases.",
        )
    purchases = await cruds_cdr.get_purchases_by_user_id(db=db, user_id=user_id)
    result = []
    for purchase in purchases:
        product_variant = await cruds_cdr.get_product_variant_by_id(
            db=db,
            variant_id=purchase.product_variant_id,
        )
        if product_variant:
            product = await cruds_cdr.get_product_by_id(
                db=db,
                product_id=product_variant.product_id,
            )
            if product:
                seller = await cruds_cdr.get_seller_by_id(
                    db=db,
                    seller_id=product.seller_id,
                )
                if seller:
                    result.append(
                        schemas_cdr.PurchaseReturn(
                            **purchase.__dict__,
                            price=product_variant.price,
                            product=product,
                            seller=seller,
                        ),
                    )
    return result


@module.router.get(
    "/cdr/me/purchases/",
    response_model=list[schemas_cdr.PurchaseReturn],
    status_code=200,
)
async def get_my_purchases(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
):
    return await get_purchases_by_user_id(user.id, db, user)


@module.router.get(
    "/cdr/sellers/{seller_id}/users/{user_id}/purchases/",
    response_model=list[schemas_cdr.PurchaseReturn],
    status_code=200,
)
async def get_purchases_by_user_id_by_seller_id(
    seller_id: UUID,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
):
    """
    Get a user's purchases.

    **User must get his own purchases or be part of the seller's group to use this endpoint**
    """
    if user_id != user.id:
        await is_user_in_a_seller_group(seller_id=seller_id, user=user, db=db)

    purchases = await cruds_cdr.get_purchases_by_user_id_by_seller_id(
        db=db,
        user_id=user_id,
        seller_id=seller_id,
    )
    result = []
    for purchase in purchases:
        product_variant = await cruds_cdr.get_product_variant_by_id(
            db=db,
            variant_id=purchase.product_variant_id,
        )
        if product_variant:
            product = await cruds_cdr.get_product_by_id(
                db=db,
                product_id=product_variant.product_id,
            )
            if product:
                seller = await cruds_cdr.get_seller_by_id(
                    db=db,
                    seller_id=product.seller_id,
                )
                if seller:
                    result.append(
                        schemas_cdr.PurchaseReturn(
                            **purchase.__dict__,
                            price=product_variant.price,
                            product=product,
                            seller=seller,
                        ),
                    )
    return result


@module.router.post(
    "/cdr/users/{user_id}/purchases/{product_variant_id}/",
    response_model=schemas_cdr.PurchaseComplete,
    status_code=201,
)
async def create_purchase(
    user_id: str,
    product_variant_id: UUID,
    purchase: schemas_cdr.PurchaseBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
):
    """
    Create a purchase.

    **User must create a purchase for themself and for an online available product or be part of the seller's group to use this endpoint**
    """
    status = await get_core_data(schemas_cdr.Status, db)
    if status.status in [CdrStatus.pending, CdrStatus.closed]:
        raise HTTPException(
            status_code=403,
            detail="CDR is closed.",
        )
    product_variant = await cruds_cdr.get_product_variant_by_id(
        db=db,
        variant_id=product_variant_id,
    )
    if not product_variant:
        raise HTTPException(
            status_code=404,
            detail="Invalid product_variant_id",
        )
    product = await cruds_cdr.get_product_by_id(
        db=db,
        product_id=product_variant.product_id,
    )
    if not product:
        raise HTTPException(
            status_code=404,
            detail="Invalid product.",
        )
    if not (user_id == user.id and product.available_online):
        await is_user_in_a_seller_group(product.seller_id, user=user, db=db)

    existing_db_purchase = await cruds_cdr.get_purchase_by_id(
        db=db,
        user_id=user_id,
        product_variant_id=product_variant_id,
    )

    db_purchase = models_cdr.Purchase(
        user_id=user_id,
        product_variant_id=product_variant_id,
        validated=False,
        quantity=purchase.quantity,
        purchased_on=datetime.now(UTC),
    )
    db_action = models_cdr.CdrAction(
        id=uuid4(),
        user_id=user.id,
        subject_id=db_purchase.user_id,
        action_type=CdrLogActionType.purchase_add,
        action=str(db_purchase.__dict__),
        timestamp=datetime.now(UTC),
    )
    if existing_db_purchase:
        try:
            await cruds_cdr.update_purchase(
                db=db,
                user_id=user_id,
                product_variant_id=product_variant_id,
                purchase=purchase,
            )
            cruds_cdr.create_action(db, db_action)
            await db.commit()
        except Exception:
            await db.rollback()
            raise
        else:
            return db_purchase

    try:
        cruds_cdr.create_purchase(db, db_purchase)
        cruds_cdr.create_action(db, db_action)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    else:
        return db_purchase


async def remove_existing_membership(
    existing_membership: models_core.CoreAssociationMembership,
    product_variant: models_cdr.ProductVariant,
    db: AsyncSession,
):
    if product_variant.related_membership_added_duration:
        if (
            existing_membership.end_date
            - product_variant.related_membership_added_duration
            <= existing_membership.start_date
        ):
            await cruds_cdr.delete_membership(
                db=db,
                membership_id=existing_membership.id,
            )
        else:
            await cruds_cdr.update_membership(
                db=db,
                membership_id=existing_membership.id,
                membership=schemas_cdr.MembershipEdit(
                    end_date=existing_membership.end_date
                    - product_variant.related_membership_added_duration,
                ),
            )


async def add_membership(
    memberships: Sequence[models_core.CoreAssociationMembership],
    user_id: str,
    product: models_cdr.CdrProduct,
    product_variant: models_cdr.ProductVariant,
    db: AsyncSession,
):
    if product_variant.related_membership_added_duration:
        existing_membership = next(
            (m for m in memberships if m.membership == product.related_membership),
            None,
        )
        if existing_membership:
            await cruds_cdr.update_membership(
                db=db,
                membership_id=existing_membership.id,
                membership=schemas_cdr.MembershipEdit(
                    end_date=existing_membership.end_date
                    + product_variant.related_membership_added_duration,
                ),
            )
        else:
            added_membership = models_core.CoreAssociationMembership(
                id=uuid4(),
                user_id=user_id,
                membership=product.related_membership,
                start_date=date(datetime.now(tz=UTC).date().year, 9, 1),
                end_date=date(datetime.now(tz=UTC).date().year, 9, 1)
                + product_variant.related_membership_added_duration,
            )
            cruds_cdr.create_membership(db=db, membership=added_membership)


@module.router.patch(
    "/cdr/users/{user_id}/purchases/{product_variant_id}/validated/",
    status_code=204,
)
async def mark_purchase_as_validated(
    user_id: str,
    product_variant_id: UUID,
    validated: bool,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    """
    Validate a purchase.

    **User must be CDR Admin to use this endpoint**
    """
    db_purchase = await cruds_cdr.get_purchase_by_id(
        db=db,
        user_id=user_id,
        product_variant_id=product_variant_id,
    )
    if not db_purchase:
        raise HTTPException(
            status_code=404,
            detail="Invalid purchase",
        )

    product_variant = await cruds_cdr.get_product_variant_by_id(
        db=db,
        variant_id=product_variant_id,
    )
    if not product_variant:
        raise HTTPException(
            status_code=404,
            detail="Invalid product_variant_id",
        )
    product = await cruds_cdr.get_product_by_id(
        db=db,
        product_id=product_variant.product_id,
    )
    if not product:
        raise HTTPException(
            status_code=404,
            detail="Invalid product.",
        )
    if validated:
        memberships = await cruds_cdr.get_actual_memberships_by_user_id(
            db=db,
            user_id=user_id,
        )
        for product_constraint in product.product_constraints:
            purchases = await cruds_cdr.get_purchases_by_ids(
                db=db,
                user_id=user_id,
                product_variant_id=[
                    variant.id for variant in product_constraint.variants
                ],
            )
            if not purchases:
                if product_constraint.related_membership:
                    if product_constraint.related_membership not in [
                        m.membership for m in memberships
                    ]:
                        raise HTTPException(
                            status_code=403,
                            detail=f"Product constraint {product_constraint.name_fr} not satisfied.",
                        )
                else:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Product constraint {product_constraint.name_fr} not satisfied.",
                    )
        for document_constraint in product.document_constraints:
            signature = await cruds_cdr.get_signature_by_id(
                db=db,
                user_id=user_id,
                document_id=document_constraint.id,
            )
            if not signature:
                raise HTTPException(
                    status_code=403,
                    detail=f"Document signature constraint {document_constraint.name} not satisfied.",
                )
        if product.related_membership:
            await add_membership(
                memberships=memberships,
                user_id=user_id,
                product=product,
                product_variant=product_variant,
                db=db,
            )
        for ticketgen in product.tickets:
            ticket = models_cdr.Ticket(
                id=uuid4(),
                secret=uuid4(),
                name=ticketgen.name,
                generator_id=ticketgen.id,
                product_variant_id=product_variant.id,
                user_id=user_id,
                scan_left=ticketgen.max_use,
                tags="",
                expiration=ticketgen.expiration,
            )
            cruds_cdr.create_ticket(db=db, ticket=ticket)
    else:
        if product.related_membership:
            memberships = await cruds_cdr.get_actual_memberships_by_user_id(
                db=db,
                user_id=user_id,
            )
            existing_membership = next(
                (m for m in memberships if m.membership == product.related_membership),
                None,
            )
            if existing_membership:
                await remove_existing_membership(
                    existing_membership=existing_membership,
                    product_variant=product_variant,
                    db=db,
                )

        if product.tickets:
            await cruds_cdr.delete_ticket_of_user(
                db=db,
                user_id=user_id,
                product_variant_id=product_variant_id,
            )
    await cruds_cdr.mark_purchase_as_validated(
        db=db,
        user_id=user_id,
        product_variant_id=product_variant_id,
        validated=validated,
    )
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    else:
        return db_purchase


@module.router.post(
    "/cdr/memberships/{membership_id}/add-batch/",
    status_code=201,
    response_model=list[schemas_cdr.MembershipUserMappingEmail],
)
async def add_batch_membership(
    membership_id: AvailableAssociationMembership,
    memberships: list[schemas_cdr.MembershipUserMappingEmail],
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    """
    Add a batch of user to a membership.

    Return the list of unknown users whose email is not in the database.

    **User must be CDR Admin to use this endpoint**
    """
    unknown_users: list[schemas_cdr.MembershipUserMappingEmail] = []
    for m in memberships:
        m_user = await cruds_users.get_user_by_email(db=db, email=m.user_email)
        if not m_user:
            unknown_users.append(m)
            continue
        stored = await cruds_cdr.get_actual_memberships_by_user_id(
            db=db,
            user_id=m_user.id,
        )
        if membership_id not in [m.membership for m in stored]:
            cruds_cdr.create_membership(
                db=db,
                membership=models_core.CoreAssociationMembership(
                    id=uuid4(),
                    user_id=m_user.id,
                    membership=membership_id,
                    start_date=m.start_date,
                    end_date=m.end_date,
                ),
            )
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return unknown_users


@module.router.delete(
    "/cdr/users/{user_id}/purchases/{product_variant_id}/",
    status_code=204,
)
async def delete_purchase(
    user_id: str,
    product_variant_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
):
    """
    Delete a purchase.

    **User must create a purchase for themself and for an online available product or be part of the seller's group to use this endpoint**
    """
    product_variant = await cruds_cdr.get_product_variant_by_id(
        db=db,
        variant_id=product_variant_id,
    )
    if not product_variant:
        raise HTTPException(
            status_code=404,
            detail="Invalid product_variant_id",
        )
    product = await cruds_cdr.get_product_by_id(
        db=db,
        product_id=product_variant.product_id,
    )
    if not product:
        raise HTTPException(
            status_code=404,
            detail="Invalid product.",
        )
    if not (user_id == user.id and product.available_online):
        await is_user_in_a_seller_group(product.seller_id, user=user, db=db)

    db_purchase = await cruds_cdr.get_purchase_by_id(
        user_id=user_id,
        product_variant_id=product_variant_id,
        db=db,
    )
    if not db_purchase:
        raise HTTPException(
            status_code=404,
            detail="Invalid purchase_id",
        )
    if db_purchase.validated:
        raise HTTPException(
            status_code=403,
            detail="You can't remove a validated purchase",
        )

    # Check if a validated purchase depends on this purchase
    user_purchases = await cruds_cdr.get_purchases_by_user_id(db=db, user_id=user_id)
    for purchase in user_purchases:
        if purchase.validated:
            purchased_product = await cruds_cdr.get_product_by_id(
                db=db,
                product_id=purchase.product_variant.product_id,
            )
            if purchased_product:
                if product in purchased_product.product_constraints:
                    memberships = await cruds_cdr.get_actual_memberships_by_user_id(
                        db=db,
                        user_id=user_id,
                    )
                    all_possible_purchases = await cruds_cdr.get_purchases_by_ids(
                        db=db,
                        user_id=user_id,
                        product_variant_id=[variant.id for variant in product.variants],
                    )
                    if all_possible_purchases:
                        all_possible_purchases = list(all_possible_purchases)
                        all_possible_purchases.remove(db_purchase)
                        if not all_possible_purchases:
                            if product.related_membership:
                                if product.related_membership not in [
                                    m.membership for m in memberships
                                ]:
                                    raise HTTPException(
                                        status_code=403,
                                        detail="You can't delete this purchase as a validated purchase depends on it.",
                                    )
                            else:
                                raise HTTPException(
                                    status_code=403,
                                    detail="You can't delete this purchase as a validated purchase depends on it.",
                                )

    db_action = models_cdr.CdrAction(
        id=uuid4(),
        user_id=user.id,
        subject_id=db_purchase.user_id,
        action_type=CdrLogActionType.purchase_delete,
        action=str(db_purchase.__dict__),
        timestamp=datetime.now(UTC),
    )
    try:
        await cruds_cdr.delete_purchase(
            user_id=user_id,
            product_variant_id=product_variant_id,
            db=db,
        )
        cruds_cdr.create_action(db, db_action)
        await db.commit()
    except Exception:
        await db.rollback()
        raise


@module.router.get(
    "/cdr/users/{user_id}/signatures/",
    response_model=list[schemas_cdr.SignatureComplete],
    status_code=200,
)
async def get_signatures_by_user_id(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
):
    """
    Get a user's signatures.

    **User must get his own signatures or be CDR Admin to use this endpoint**
    """
    if not (
        user_id == user.id
        or is_user_member_of_an_allowed_group(user, [GroupType.admin_cdr])
    ):
        raise HTTPException(
            status_code=403,
            detail="You're not allowed to see other users signatures.",
        )
    return await cruds_cdr.get_signatures_by_user_id(db=db, user_id=user_id)


@module.router.get(
    "/cdr/sellers/{seller_id}/users/{user_id}/signatures/",
    response_model=list[schemas_cdr.SignatureComplete],
    status_code=200,
)
async def get_signatures_by_user_id_by_seller_id(
    seller_id: UUID,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
):
    """
    Get a user's signatures for a single seller.

    **User must get his own signatures or be part of the seller's group to use this endpoint**
    """
    if user_id != user.id:
        await is_user_in_a_seller_group(seller_id=seller_id, user=user, db=db)

    return await cruds_cdr.get_signatures_by_user_id_by_seller_id(
        db=db,
        user_id=user_id,
        seller_id=seller_id,
    )


@module.router.post(
    "/cdr/users/{user_id}/signatures/{document_id}/",
    response_model=schemas_cdr.SignatureComplete,
    status_code=201,
)
async def create_signature(
    user_id: str,
    document_id: UUID,
    signature: schemas_cdr.SignatureBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
):
    """
    Create a signature.

    **User must sign numerically or be part of the seller's group to use this endpoint**
    """
    status = await get_core_data(schemas_cdr.Status, db)
    if status.status == CdrStatus.pending:
        raise HTTPException(
            status_code=403,
            detail="CDR hasn't started yet.",
        )
    document = await cruds_cdr.get_document_by_id(
        db=db,
        document_id=document_id,
    )
    if not document:
        raise HTTPException(
            status_code=404,
            detail="Invalid document_id",
        )
    sellers = await cruds_cdr.get_sellers(db)

    sellers_groups = [str(seller.group_id) for seller in sellers]
    sellers_groups.append(GroupType.admin_cdr)
    if not (
        (
            user_id == user.id
            and signature.signature_type == DocumentSignatureType.numeric
        )
        or is_user_member_of_an_allowed_group(user=user, allowed_groups=sellers_groups)
    ):
        raise HTTPException(
            status_code=403,
            detail="You're not allowed to make this signature.",
        )
    if (
        signature.signature_type == DocumentSignatureType.numeric
        and not signature.numeric_signature_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Numeric signature must include signature id.",
        )
    db_signature = models_cdr.Signature(
        user_id=user_id,
        document_id=document_id,
        **signature.model_dump(exclude_none=False),
    )
    try:
        cruds_cdr.create_signature(db, db_signature)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    else:
        return db_signature


@module.router.delete(
    "/cdr/users/{user_id}/signatures/{document_id}/",
    status_code=204,
)
async def delete_signature(
    user_id: str,
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    """
    Delete a signature.

    **User must be CDR Admin to use this endpoint**
    """
    db_signature = await cruds_cdr.get_signature_by_id(
        user_id=user_id,
        document_id=document_id,
        db=db,
    )
    if not db_signature:
        raise HTTPException(
            status_code=404,
            detail="Invalid signature",
        )
    try:
        await cruds_cdr.delete_signature(
            user_id=user_id,
            document_id=document_id,
            db=db,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise


@module.router.get(
    "/cdr/curriculums/",
    response_model=list[schemas_cdr.CurriculumComplete],
    status_code=200,
)
async def get_curriculums(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
):
    """
    Get all curriculums.

    **User be authenticated to use this endpoint**
    """
    return await cruds_cdr.get_curriculums(db)


@module.router.post(
    "/cdr/curriculums/",
    response_model=schemas_cdr.CurriculumComplete,
    status_code=201,
)
async def create_curriculum(
    curriculum: schemas_cdr.CurriculumBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    """
    Create a curriculum.

    **User must be CDR Admin to use this endpoint**
    """
    status = await get_core_data(schemas_cdr.Status, db)
    if status.status == CdrStatus.closed:
        raise HTTPException(
            status_code=403,
            detail="CDR is closed. You can't add a new curriculum.",
        )
    db_curriculum = models_cdr.Curriculum(
        id=uuid4(),
        name=curriculum.name,
    )
    try:
        cruds_cdr.create_curriculum(db, db_curriculum)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    else:
        return db_curriculum


@module.router.delete(
    "/cdr/curriculums/{curriculum_id}/",
    status_code=204,
)
async def delete_curriculum(
    curriculum_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    """
    Delete a curriculum.

    **User must be CDR Admin to use this endpoint**
    """
    db_curriculum = await cruds_cdr.get_curriculum_by_id(
        curriculum_id=curriculum_id,
        db=db,
    )
    if not db_curriculum:
        raise HTTPException(
            status_code=404,
            detail="Invalid curriculum_id",
        )
    try:
        await cruds_cdr.delete_curriculum(
            curriculum_id=curriculum_id,
            db=db,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise


@module.router.post(
    "/cdr/users/{user_id}/curriculums/{curriculum_id}/",
    status_code=201,
)
async def create_curriculum_membership(
    user_id: str,
    curriculum_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
    ws_manager: WebsocketConnectionManager = Depends(get_websocket_connection_manager),
):
    """
    Add a curriculum to a user.

    **User must add a curriculum to themself or be CDR Admin to use this endpoint**
    """
    if not (
        user_id == user.id
        or is_user_member_of_an_allowed_group(user, [GroupType.admin_cdr])
    ):
        raise HTTPException(
            status_code=403,
            detail="You can't remove a curriculum to another user.",
        )

    wanted_curriculum = await cruds_cdr.get_curriculum_by_id(
        db=db,
        curriculum_id=curriculum_id,
    )
    if not wanted_curriculum:
        raise HTTPException(
            status_code=404,
            detail="Invalid curriculum_id",
        )
    db_user = await get_user_by_id(db=db, user_id=user_id)
    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )
    curriculum = await cruds_cdr.get_curriculum_by_user_id(db=db, user_id=user_id)
    if curriculum:
        purchases = await cruds_cdr.get_purchases_by_user_id(db=db, user_id=user_id)
        if purchases:
            raise HTTPException(
                status_code=403,
                detail="You can't edit this curriculum if user has purchases.",
            )
        try:
            await cruds_cdr.delete_curriculum_membership(
                db=db,
                user_id=user_id,
                curriculum_id=curriculum.curriculum_id,
            )
            await db.commit()
        except Exception:
            await db.rollback()
            raise
    curriculum_membership = models_cdr.CurriculumMembership(
        user_id=user_id,
        curriculum_id=curriculum_id,
    )
    try:
        cruds_cdr.create_curriculum_membership(
            db=db,
            curriculum_membership=curriculum_membership,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    cdr_status = await get_core_data(schemas_cdr.Status, db)
    if cdr_status.status == CdrStatus.onsite:
        try:
            await ws_manager.send_message_to_room(
                message=schemas_cdr.NewUserWSMessageModel(
                    data=schemas_cdr.CdrUser(
                        curriculum=schemas_cdr.CurriculumComplete(
                            **wanted_curriculum.__dict__,
                        ),
                        **db_user.__dict__,
                    ),
                ),
                room_id=HyperionWebsocketsRoom.CDR,
            )
        except Exception:
            hyperion_error_logger.exception(
                f"Error while sending a message to the room {HyperionWebsocketsRoom.CDR}",
            )


@module.router.patch(
    "/cdr/users/{user_id}/curriculums/{curriculum_id}/",
    status_code=204,
)
async def update_curriculum_membership(
    user_id: str,
    curriculum_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
    ws_manager: WebsocketConnectionManager = Depends(get_websocket_connection_manager),
):
    """
    Update a curriculum membership.

    **User must add a curriculum to themself or be CDR Admin to use this endpoint**
    """
    if not (
        user_id == user.id
        or is_user_member_of_an_allowed_group(user, [GroupType.admin_cdr])
    ):
        raise HTTPException(
            status_code=403,
            detail="You can't remove a curriculum to another user.",
        )
    db_user = await get_user_by_id(db=db, user_id=user_id)
    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )
    curriculum = await cruds_cdr.get_curriculum_by_id(
        db=db,
        curriculum_id=curriculum_id,
    )
    if not curriculum:
        raise HTTPException(
            status_code=404,
            detail="Invalid curriculum_id",
        )
    try:
        await cruds_cdr.update_curriculum_membership(
            db=db,
            user_id=user_id,
            curriculum_id=curriculum_id,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    cdr_status = await get_core_data(schemas_cdr.Status, db)
    if cdr_status.status == CdrStatus.onsite:
        try:
            await ws_manager.send_message_to_room(
                message=schemas_cdr.UpdateUserWSMessageModel(
                    data=schemas_cdr.CdrUser(
                        curriculum=schemas_cdr.CurriculumComplete(
                            **curriculum.__dict__,
                        ),
                        **db_user.__dict__,
                    ),
                ),
                room_id=HyperionWebsocketsRoom.CDR,
            )
        except Exception:
            hyperion_error_logger.exception(
                f"Error while sending a message to the room {HyperionWebsocketsRoom.CDR}",
            )


@module.router.delete(
    "/cdr/users/{user_id}/curriculums/{curriculum_id}/",
    status_code=204,
)
async def delete_curriculum_membership(
    user_id: str,
    curriculum_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
    ws_manager: WebsocketConnectionManager = Depends(get_websocket_connection_manager),
):
    """
    Remove a curriculum from a user.

    **User must add a curriculum to themself or be CDR Admin to use this endpoint**
    """
    membership = await cruds_cdr.get_curriculum_by_id(
        db=db,
        curriculum_id=curriculum_id,
    )
    if not membership:
        raise HTTPException(
            status_code=404,
            detail="Invalid curriculum_id",
        )
    if not (
        user_id == user.id
        or is_user_member_of_an_allowed_group(user, [GroupType.admin_cdr])
    ):
        raise HTTPException(
            status_code=403,
            detail="You can't remove a curriculum to another user.",
        )
    db_user = await get_user_by_id(db=db, user_id=user_id)
    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )
    try:
        await cruds_cdr.delete_curriculum_membership(
            db=db,
            user_id=user_id,
            curriculum_id=curriculum_id,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    cdr_status = await get_core_data(schemas_cdr.Status, db)
    if cdr_status.status == CdrStatus.onsite:
        try:
            await ws_manager.send_message_to_room(
                message=schemas_cdr.UpdateUserWSMessageModel(
                    data=schemas_cdr.CdrUser(curriculum=None, **db_user.__dict__),
                ),
                room_id=HyperionWebsocketsRoom.CDR,
            )
        except Exception:
            hyperion_error_logger.exception(
                f"Error while sending a message to the room {HyperionWebsocketsRoom.CDR}",
            )


@module.router.get(
    "/cdr/users/{user_id}/payments/",
    response_model=list[schemas_cdr.PaymentComplete],
    status_code=200,
)
async def get_payments_by_user_id(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
):
    """
    Get a user's payments.

    **User must get his own payments or be CDR Admin to use this endpoint**
    """
    if not (
        user_id == user.id
        or is_user_member_of_an_allowed_group(user, [GroupType.admin_cdr])
    ):
        raise HTTPException(
            status_code=403,
            detail="You're not allowed to see other users payments.",
        )
    return await cruds_cdr.get_payments_by_user_id(db=db, user_id=user_id)


@module.router.post(
    "/cdr/users/{user_id}/payments/",
    response_model=schemas_cdr.PaymentComplete,
    status_code=201,
)
async def create_payment(
    user_id: str,
    payment: schemas_cdr.PaymentBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    """
    Create a payment.

    **User must be CDR Admin to use this endpoint**
    """
    status = await get_core_data(schemas_cdr.Status, db)
    if status.status == CdrStatus.pending:
        raise HTTPException(
            status_code=403,
            detail="CDR hasn't started yet.",
        )
    db_payment = models_cdr.Payment(
        id=uuid4(),
        user_id=user_id,
        **payment.model_dump(),
    )
    db_action = models_cdr.CdrAction(
        id=uuid4(),
        user_id=user.id,
        subject_id=user_id,
        action_type=CdrLogActionType.payment_add,
        action=str(db_payment.__dict__),
        timestamp=datetime.now(UTC),
    )
    try:
        cruds_cdr.create_payment(db, db_payment)
        cruds_cdr.create_action(db, db_action)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    else:
        return db_payment


@module.router.delete(
    "/cdr/users/{user_id}/payments/{payment_id}/",
    status_code=204,
)
async def delete_payment(
    user_id: str,
    payment_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    """
    Remove a payment.

    **User must be CDR Admin to use this endpoint**
    """
    db_payment = await cruds_cdr.get_payment_by_id(
        payment_id=payment_id,
        db=db,
    )
    if not db_payment:
        raise HTTPException(
            status_code=404,
            detail="Invalid payment_id",
        )
    if db_payment.user_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="user_id and payment are not related.",
        )
    db_action = models_cdr.CdrAction(
        id=uuid4(),
        user_id=user.id,
        subject_id=user_id,
        action_type=CdrLogActionType.payment_delete,
        action=str(db_payment.__dict__),
        timestamp=datetime.now(UTC),
    )
    try:
        await cruds_cdr.delete_payment(
            payment_id=payment_id,
            db=db,
        )
        cruds_cdr.create_action(db, db_action)
        await db.commit()
    except Exception:
        await db.rollback()
        raise


@module.router.post(
    "/cdr/pay/",
    response_model=schemas_cdr.PaymentUrl,
    status_code=200,
)
async def get_payment_url(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
    settings: Settings = Depends(get_settings),
    payment_tool: PaymentTool = Depends(get_payment_tool),
):
    """
    Get payment url
    """
    purchases = await cruds_cdr.get_purchases_by_user_id(db=db, user_id=user.id)
    payments = await cruds_cdr.get_payments_by_user_id(db=db, user_id=user.id)

    purchases_total = sum(
        purchase.product_variant.price * purchase.quantity for purchase in purchases
    )
    payments_total = sum(payment.total for payment in payments)

    amount = purchases_total - payments_total

    if amount < 100:
        raise HTTPException(
            status_code=403,
            detail="Please give an amount in cents, greater than 1€.",
        )
    user_schema = schemas_core.CoreUser(**user.__dict__)
    checkout = await payment_tool.init_checkout(
        module=module.root,
        helloasso_slug="AEECL",
        checkout_amount=amount,
        checkout_name="Chaine de rentrée",
        redirection_uri=settings.CDR_PAYMENT_REDIRECTION_URL or "",
        payer_user=user_schema,
        db=db,
    )
    hyperion_error_logger.info(f"CDR: Logging Checkout id {checkout.id}")
    cruds_cdr.create_checkout(
        db=db,
        checkout=models_cdr.Checkout(
            id=uuid4(),
            user_id=user.id,
            checkout_id=checkout.id,
        ),
    )
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return schemas_cdr.PaymentUrl(
        url=checkout.payment_url,
    )


@module.router.get(
    "/cdr/users/{user_id}/memberships/",
    response_model=list[schemas_cdr.MembershipComplete],
    status_code=200,
)
async def get_memberships_by_user_id(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
):
    if not (
        user_id == user.id
        or is_user_member_of_an_allowed_group(user, [GroupType.admin_cdr])
    ):
        raise HTTPException(
            status_code=403,
            detail="You're not allowed to see other users memberships.",
        )
    return await cruds_cdr.get_actual_memberships_by_user_id(db=db, user_id=user_id)


@module.router.post(
    "/cdr/users/{user_id}/memberships/",
    response_model=schemas_cdr.MembershipComplete,
    status_code=201,
)
async def create_membership(
    user_id: str,
    membership: schemas_cdr.MembershipBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    db_membership = models_core.CoreAssociationMembership(
        id=uuid4(),
        user_id=user_id,
        **membership.model_dump(),
    )
    try:
        cruds_cdr.create_membership(db, db_membership)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    else:
        return db_membership


@module.router.patch(
    "/cdr/users/{user_id}/memberships/{membership}/",
    status_code=204,
)
async def update_membership(
    user_id: str,
    membership: AvailableAssociationMembership,
    membership_edit: schemas_cdr.MembershipEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    db_membership = await cruds_cdr.get_membership_by_user_id_and_membership_name(
        user_id=user_id,
        membership=membership,
        db=db,
    )
    if db_membership is None:
        raise HTTPException(
            status_code=404,
            detail="This user doesn't have this membership",
        )
    try:
        await cruds_cdr.update_membership(
            membership_id=db_membership.id,
            membership=membership_edit,
            db=db,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise


@module.router.delete(
    "/cdr/users/{user_id}/memberships/{membership_id}/",
    status_code=204,
)
async def delete_membership(
    user_id: str,
    membership_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    db_membership = await cruds_cdr.get_membership_by_id(
        membership_id=membership_id,
        db=db,
    )
    if not db_membership or db_membership.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail="Invalid membership_id",
        )
    try:
        await cruds_cdr.delete_membership(
            membership_id=membership_id,
            db=db,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise


@module.router.get(
    "/cdr/status/",
    response_model=schemas_cdr.Status,
    status_code=200,
)
async def get_status(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
):
    return await get_core_data(schemas_cdr.Status, db)


@module.router.patch(
    "/cdr/status/",
    status_code=204,
)
async def update_status(
    status: schemas_cdr.Status,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    current_status = await get_core_data(schemas_cdr.Status, db)
    match status.status:
        case CdrStatus.pending:
            if current_status.status != CdrStatus.closed:
                raise HTTPException(
                    status_code=403,
                    detail="To set the status as pending, previous Cdr must be closed.",
                )
        case CdrStatus.online:
            if current_status.status != CdrStatus.pending:
                raise HTTPException(
                    status_code=403,
                    detail="To set the status as online, previous status must be pending.",
                )
        case CdrStatus.onsite:
            if current_status.status != CdrStatus.online:
                raise HTTPException(
                    status_code=403,
                    detail="To set the status as onsite, previous status must be online.",
                )
        case CdrStatus.closed:
            if current_status.status != CdrStatus.onsite:
                raise HTTPException(
                    status_code=403,
                    detail="To set the status as closed, previous status must be onsite.",
                )
    await set_core_data(status, db)


@module.router.get(
    "/cdr/users/me/tickets/",
    response_model=list[schemas_cdr.Ticket],
    status_code=200,
)
async def get_my_tickets(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
):
    return await cruds_cdr.get_tickets_of_user(db=db, user_id=user.id)


@module.router.get(
    "/cdr/users/{user_id}/tickets/",
    response_model=list[schemas_cdr.Ticket],
    status_code=200,
)
async def get_tickets_of_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
):
    if not (
        is_user_member_of_an_allowed_group(user, [GroupType.admin_cdr])
        or user_id == user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="You can't get another user tickets.",
        )
    return await cruds_cdr.get_tickets_of_user(db=db, user_id=user_id)


@module.router.get(
    "/cdr/users/me/tickets/{ticket_id}/secret/",
    response_model=schemas_cdr.TicketSecret,
    status_code=200,
)
async def get_ticket_secret(
    ticket_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
):
    ticket = await cruds_cdr.get_ticket(db=db, ticket_id=ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found.",
        )
    if ticket.user_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="You can't get another user ticket secret.",
        )
    return schemas_cdr.TicketSecret(qr_code_secret=ticket.secret)


@module.router.get(
    "/cdr/sellers/{seller_id}/products/{product_id}/tickets/{generator_id}/{secret}/",
    response_model=schemas_cdr.Ticket,
    status_code=200,
)
async def get_ticket_by_secret(
    seller_id: UUID,
    product_id: UUID,
    generator_id: UUID,
    secret: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    product = await check_request_consistency(
        db=db,
        seller_id=seller_id,
        product_id=product_id,
    )
    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found.",
        )
    await is_user_in_a_seller_group(seller_id=seller_id, user=user, db=db)
    ticket_generator = await cruds_cdr.get_ticket_generator(
        db=db,
        ticket_generator_id=generator_id,
    )
    if not ticket_generator:
        raise HTTPException(
            status_code=404,
            detail="Ticket generator not found.",
        )
    if ticket_generator.product_id != product_id:
        raise HTTPException(
            status_code=404,
            detail="This Ticket generator is not related to this product.",
        )
    ticket = await cruds_cdr.get_ticket_by_secret(db=db, secret=secret)
    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found.",
        )
    if ticket.generator_id != generator_id:
        raise HTTPException(
            status_code=404,
            detail="This Ticket is not related to this product.",
        )
    return ticket


@module.router.patch(
    "/cdr/sellers/{seller_id}/products/{product_id}/tickets/{generator_id}/{secret}/",
    status_code=204,
)
async def scan_ticket(
    seller_id: UUID,
    product_id: UUID,
    generator_id: UUID,
    secret: UUID,
    ticket_data: schemas_cdr.TicketScan,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    product = await check_request_consistency(
        db=db,
        seller_id=seller_id,
        product_id=product_id,
    )
    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found.",
        )
    await is_user_in_a_seller_group(seller_id=seller_id, user=user, db=db)
    ticket_generator = await cruds_cdr.get_ticket_generator(
        db=db,
        ticket_generator_id=generator_id,
    )
    if not ticket_generator:
        raise HTTPException(
            status_code=404,
            detail="Ticket generator not found.",
        )
    if ticket_generator.product_id != product_id:
        raise HTTPException(
            status_code=404,
            detail="This Ticket generator is not related to this product.",
        )
    ticket = await cruds_cdr.get_ticket_by_secret(db=db, secret=secret)
    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found.",
        )
    if ticket.generator_id != generator_id:
        raise HTTPException(
            status_code=404,
            detail="This Ticket is not related to this product.",
        )
    if ticket.scan_left <= 0:
        raise HTTPException(
            status_code=403,
            detail="This ticket has already been used for the maximum amount.",
        )
    if ticket.expiration < datetime.now(tz=UTC):
        raise HTTPException(
            status_code=403,
            detail="This ticket has expired.",
        )
    try:
        await cruds_cdr.scan_ticket(
            db=db,
            ticket_id=ticket.id,
            scan=ticket.scan_left - 1,
            tags=ticket.tags + "," + ticket_data.tag.strip(),
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise


@module.router.post(
    "/cdr/sellers/{seller_id}/products/{product_id}/tickets/",
    status_code=201,
    response_model=schemas_cdr.ProductComplete,
)
async def generate_ticket_for_product(
    seller_id: UUID,
    product_id: UUID,
    ticket_data: schemas_cdr.GenerateTicketBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    await is_user_in_a_seller_group(seller_id=seller_id, user=user, db=db)
    product = await check_request_consistency(
        db=db,
        seller_id=seller_id,
        product_id=product_id,
    )
    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found.",
        )
    ticketgen = models_cdr.TicketGenerator(
        id=uuid4(),
        product_id=product_id,
        **ticket_data.model_dump(),
    )
    cruds_cdr.create_ticket_generator(db=db, ticket=ticketgen)

    validated_purchases = await cruds_cdr.get_product_validated_purchases(
        db=db,
        product_id=ticketgen.product_id,
    )
    for purchase in validated_purchases:
        ticket = models_cdr.Ticket(
            id=uuid4(),
            secret=uuid4(),
            name=ticketgen.name,
            generator_id=ticketgen.id,
            product_variant_id=purchase.product_variant_id,
            user_id=purchase.user_id,
            scan_left=ticketgen.max_use,
            tags="",
            expiration=ticketgen.expiration,
        )
        cruds_cdr.create_ticket(db=db, ticket=ticket)
    try:
        await db.commit()
        return await cruds_cdr.get_product_by_id(db=db, product_id=product_id)
    except Exception:
        await db.rollback()
        raise


@module.router.delete(
    "/cdr/sellers/{seller_id}/products/{product_id}/tickets/{ticket_generator_id}",
    status_code=204,
)
async def delete_ticket_generator_for_product(
    seller_id: UUID,
    product_id: UUID,
    ticket_generator_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    await is_user_in_a_seller_group(seller_id=seller_id, user=user, db=db)
    product = await check_request_consistency(
        db=db,
        seller_id=seller_id,
        product_id=product_id,
    )
    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found.",
        )
    ticketgen = await cruds_cdr.get_ticket_generator(
        db=db,
        ticket_generator_id=ticket_generator_id,
    )
    if not ticketgen:
        raise HTTPException(
            status_code=404,
            detail="Product Ticket not found.",
        )
    await cruds_cdr.delete_ticket_generator(
        db=db,
        ticket_generator_id=ticket_generator_id,
    )
    await cruds_cdr.delete_product_generated_tickets(
        db=db,
        ticket_generator_id=ticket_generator_id,
    )
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise


@module.router.get(
    "/cdr/sellers/{seller_id}/products/{product_id}/data/",
    response_model=list[schemas_cdr.CustomDataFieldComplete],
    status_code=200,
)
async def get_custom_data_fields(
    seller_id: UUID,
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    await is_user_in_a_seller_group(
        seller_id,
        user,
        db=db,
    )
    await check_request_consistency(db=db, seller_id=seller_id, product_id=product_id)
    return await cruds_cdr.get_product_customdata_fields(db=db, product_id=product_id)


@module.router.post(
    "/cdr/sellers/{seller_id}/products/{product_id}/data/",
    response_model=schemas_cdr.CustomDataFieldComplete,
    status_code=201,
)
async def create_custom_data_field(
    seller_id: UUID,
    product_id: UUID,
    custom_data_field: schemas_cdr.CustomDataFieldBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    await is_user_in_a_seller_group(
        seller_id,
        user,
        db=db,
    )
    await check_request_consistency(db=db, seller_id=seller_id, product_id=product_id)
    db_data = models_cdr.CustomDataField(
        id=uuid4(),
        product_id=product_id,
        name=custom_data_field.name,
    )
    try:
        cruds_cdr.create_customdata_field(db, db_data)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    else:
        return db_data


@module.router.delete(
    "/cdr/sellers/{seller_id}/products/{product_id}/data/{field_id}/",
    status_code=204,
)
async def delete_customdata_field(
    seller_id: UUID,
    product_id: UUID,
    field_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    await is_user_in_a_seller_group(
        seller_id,
        user,
        db=db,
    )
    await check_request_consistency(db=db, seller_id=seller_id, product_id=product_id)
    db_field = await cruds_cdr.get_customdata_field(db=db, field_id=field_id)
    if db_field is None:
        raise HTTPException(
            status_code=404,
            detail="Field not found.",
        )
    if db_field.product_id != product_id:
        raise HTTPException(
            status_code=403,
            detail="Field does not belong to this product.",
        )
    try:
        await cruds_cdr.delete_customdata_field(
            field_id=field_id,
            db=db,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise


@module.router.get(
    "/cdr/sellers/{seller_id}/products/{product_id}/users/{user_id}/data/{field_id}/",
    response_model=schemas_cdr.CustomDataComplete,
    status_code=200,
)
async def get_customdata(
    seller_id: UUID,
    product_id: UUID,
    user_id: str,
    field_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    await is_user_in_a_seller_group(
        seller_id,
        user,
        db=db,
    )
    await check_request_consistency(db=db, seller_id=seller_id, product_id=product_id)
    db_data = await cruds_cdr.get_customdata(db=db, field_id=field_id, user_id=user_id)
    if db_data is None:
        raise HTTPException(
            status_code=404,
            detail="Field Data not found.",
        )

    return db_data


@module.router.post(
    "/cdr/sellers/{seller_id}/products/{product_id}/users/{user_id}/data/{field_id}/",
    response_model=schemas_cdr.CustomDataComplete,
    status_code=201,
)
async def create_custom_data(
    seller_id: UUID,
    product_id: UUID,
    user_id: str,
    field_id: UUID,
    custom_data: schemas_cdr.CustomDataBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    await is_user_in_a_seller_group(
        seller_id,
        user,
        db=db,
    )
    await check_request_consistency(db=db, seller_id=seller_id, product_id=product_id)
    db_field = await cruds_cdr.get_customdata_field(db=db, field_id=field_id)
    if db_field is None:
        raise HTTPException(
            status_code=404,
            detail="Field not found.",
        )
    if db_field.product_id != product_id:
        raise HTTPException(
            status_code=403,
            detail="Field does not belong to this product.",
        )
    db_data = models_cdr.CustomData(
        user_id=user_id,
        field_id=field_id,
        value=custom_data.value,
    )
    try:
        cruds_cdr.create_customdata(db, db_data)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    else:
        return await cruds_cdr.get_customdata(db=db, field_id=field_id, user_id=user_id)


@module.router.patch(
    "/cdr/sellers/{seller_id}/products/{product_id}/users/{user_id}/data/{field_id}/",
    status_code=204,
)
async def update_custom_data(
    seller_id: UUID,
    product_id: UUID,
    user_id: str,
    field_id: UUID,
    custom_data: schemas_cdr.CustomDataBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    await is_user_in_a_seller_group(
        seller_id,
        user,
        db=db,
    )
    await check_request_consistency(db=db, seller_id=seller_id, product_id=product_id)
    db_data = await cruds_cdr.get_customdata(db=db, field_id=field_id, user_id=user_id)
    if db_data is None:
        raise HTTPException(
            status_code=404,
            detail="Field Data not found.",
        )
    if db_data.field.product_id != product_id:
        raise HTTPException(
            status_code=403,
            detail="Field does not belong to this product.",
        )
    try:
        await cruds_cdr.update_customdata(
            db,
            field_id=field_id,
            user_id=user_id,
            value=custom_data.value,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise


@module.router.delete(
    "/cdr/sellers/{seller_id}/products/{product_id}/users/{user_id}/data/{field_id}/",
    status_code=204,
)
async def delete_customdata(
    seller_id: UUID,
    product_id: UUID,
    user_id: str,
    field_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    await is_user_in_a_seller_group(
        seller_id,
        user,
        db=db,
    )
    await check_request_consistency(db=db, seller_id=seller_id, product_id=product_id)
    db_data = await cruds_cdr.get_customdata(db=db, field_id=field_id, user_id=user_id)
    if db_data is None:
        raise HTTPException(
            status_code=404,
            detail="Field Data not found.",
        )
    if db_data.field.product_id != product_id:
        raise HTTPException(
            status_code=403,
            detail="Field does not belong to this product.",
        )
    try:
        await cruds_cdr.delete_customdata(
            field_id=field_id,
            user_id=user_id,
            db=db,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise


@module.router.websocket("/cdr/users/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    ws_manager: WebsocketConnectionManager = Depends(get_websocket_connection_manager),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    await websocket.accept()

    try:
        token_message = await websocket.receive_json()
        token = token_message.get("token", None)

        token_data = auth_utils.get_token_data(
            settings=settings,
            token=token,
            request_id="websocket",
        )

        user = await auth_utils.get_user_from_token_with_scopes(
            scopes=[[ScopeType.API]],
            db=db,
            token_data=token_data,
        )
    except Exception:
        await websocket.send_text(
            ConnectionWSMessageModel(
                data=ConnectionWSMessageModelData(
                    status=ConnectionWSMessageModelStatus.invalid,
                ),
            ).model_dump_json(),
        )
        await websocket.close()
        return

    hyperion_error_logger.debug(
        f"CDR: New websocket connection from {user.id} on worker {os.getpid()}",
    )

    await websocket.send_text(
        ConnectionWSMessageModel(
            data=ConnectionWSMessageModelData(
                status=ConnectionWSMessageModelStatus.connected,
            ),
        ).model_dump_json(),
    )

    # Add the user to the connection stack
    await ws_manager.add_connection_to_room(
        room_id=HyperionWebsocketsRoom.CDR,
        ws_connection=websocket,
    )

    try:
        while True:
            # TODO: we could use received messages from the websocket
            await websocket.receive_json()
    except WebSocketDisconnect:
        await ws_manager.remove_connection_from_room(
            room_id=HyperionWebsocketsRoom.CDR,
            connection=websocket,
        )
    except Exception:
        await ws_manager.remove_connection_from_room(
            room_id=HyperionWebsocketsRoom.CDR,
            connection=websocket,
        )
        raise
