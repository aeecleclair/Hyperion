import logging
import os
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import (
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core, schemas_core
from app.core.config import Settings
from app.core.groups.groups_type import GroupType
from app.core.payment import schemas_payment
from app.core.payment.payment_tool import PaymentTool
from app.core.users.cruds_users import get_user_by_id, get_users
from app.dependencies import (
    get_db,
    get_payment_tool,
    get_request_id,
    get_settings,
    get_websocket_connection_manager,
    hyperion_access_logger,
    is_user_a_member,
    is_user_a_member_of,
)
from app.modules.cdr import cruds_cdr, models_cdr, schemas_cdr
from app.modules.cdr.types_cdr import (
    CdrLogActionType,
    CdrStatus,
    DocumentSignatureType,
    PaymentType,
)
from app.types.module import Module
from app.types.websocket import HyperionWebsocketsRoom, WebsocketConnectionManager
from app.utils.tools import (
    get_core_data,
    is_user_member_of_an_allowed_group,
    set_core_data,
)


async def validate_payment(
    checkout_payment: schemas_payment.CheckoutPayment,
    db: AsyncSession,
) -> None:
    paid_amount = checkout_payment.paid_amount
    checkout_id = checkout_payment.checkout_id

    checkout = await cruds_cdr.get_checkout_by_checkout_id(
        db=db,
        checkout_id=checkout_id,
    )
    if not checkout:
        hyperion_error_logger.error(
            f"CDR payment callback: user checkout {checkout_id} not found.",
        )
        raise ValueError(f"User checkout {checkout_id} not found.")  # noqa: TRY003

    db_payment = models_cdr.Payment(
        id=uuid4(),
        user_id=checkout.user_id,
        total=paid_amount,
        payment_type=PaymentType.helloasso,
    )
    db_action = models_cdr.CdrAction(
        id=uuid4(),
        subject_id=checkout.id,
        action_type=CdrLogActionType.payment_add,
        action=str(checkout_payment.__dict__),
    )
    try:
        cruds_cdr.create_payment(db=db, payment=db_payment)
        cruds_cdr.create_action(db=db, action=db_action)
        await db.commit()
    except Exception:
        await db.rollback()
        raise


module = Module(
    root="cdr",
    tag="Cdr",
    payment_callback=validate_payment,
    default_allowed_groups_ids=[GroupType.admin_cdr],
)

hyperion_error_logger = logging.getLogger("hyperion.error")


async def is_user_in_a_seller_group(
    seller_id: UUID,
    user: models_core.CoreUser,
    db: AsyncSession,
    request_id: str = Depends(get_request_id),
):
    """
    Check if the user is in the group related to a seller or CDR Admin.
    """
    seller = await cruds_cdr.get_seller_by_id(db, seller_id=seller_id)

    if not seller:
        raise HTTPException(
            status_code=404,
            detail="Seller not found.",
        )

    if is_user_member_of_an_allowed_group(
        user=user,
        allowed_groups=[str(seller.group_id), GroupType.admin_cdr],
    ):
        return user

    hyperion_access_logger.warning(
        f"Is_user_a_member_of: Unauthorized, user is not a seller ({request_id})",
    )

    raise HTTPException(
        status_code=403,
        detail="Unauthorized, user is not in this seller group.",
    )


async def check_request_consistency(
    db: AsyncSession,
    seller_id: UUID | None = None,
    product_id: UUID | None = None,
    variant_id: UUID | None = None,
    document_id: UUID | None = None,
) -> models_cdr.CdrProduct | None:
    """
    Check that given ids are consistent, ie. product's seller_id is the given seller_id.
    """
    db_product: models_cdr.CdrProduct | None = None
    if seller_id:
        db_seller = await cruds_cdr.get_seller_by_id(db=db, seller_id=seller_id)
        if not db_seller:
            raise HTTPException(
                status_code=404,
                detail="Invalid seller_id",
            )
    if product_id:
        db_product = await cruds_cdr.get_product_by_id(db=db, product_id=product_id)
        if not db_product:
            raise HTTPException(
                status_code=404,
                detail="Invalid product_id",
            )
        if seller_id and seller_id != db_product.seller_id:
            raise HTTPException(
                status_code=403,
                detail="Product is not related to this seller.",
            )
    if variant_id:
        db_variant = await cruds_cdr.get_product_variant_by_id(
            db=db,
            variant_id=variant_id,
        )
        if not db_variant:
            raise HTTPException(
                status_code=404,
                detail="Invalid variant_id",
            )
        if product_id and product_id != db_variant.product_id:
            raise HTTPException(
                status_code=403,
                detail="Variant is not related to this product.",
            )
    if document_id:
        db_document = await cruds_cdr.get_document_by_id(db=db, document_id=document_id)
        if not db_document:
            raise HTTPException(
                status_code=404,
                detail="Invalid document_id",
            )
        if seller_id and seller_id != db_document.seller_id:
            raise HTTPException(
                status_code=403,
                detail="Document is not related to this seller.",
            )
    return db_product


@module.router.get(
    "/cdr/users/",
    response_model=list[schemas_cdr.CdrUser],
    status_code=200,
)
async def get_cdr_users(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get all sellers.

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
    "/cdr/users/{user_id}/",
    response_model=schemas_cdr.CdrUser,
    status_code=200,
)
async def get_cdr_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get a user.

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
    user_dict = (await get_user_by_id(db, user_id)).__dict__
    curriculum = await cruds_cdr.get_cdr_user_curriculum(db, user_id)
    curriculum_complete = {c.id: c for c in await cruds_cdr.get_curriculums(db=db)}
    if curriculum:
        user_dict["curriculum"] = curriculum_complete[curriculum.curriculum_id]
    return schemas_cdr.CdrUser(**user_dict)


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
    Get sellers user is part of the group.

    **User must be authenticated to use this endpoint**
    """
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
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get all sellers that has online available products.

    **User must be authenticated to use this endpoint**
    """
    return await cruds_cdr.get_online_sellers(db)


@module.router.get(
    "/cdr/online/products/",
    response_model=list[schemas_cdr.ProductComplete],
    status_code=200,
)
async def get_all_available_online_products(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
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
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    """
    Get a seller's online available products.

    **User must be authenticated to use this endpoint**
    """
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
    db_seller = models_cdr.Seller(
        id=uuid4(),
        **seller.model_dump(),
    )
    try:
        cruds_cdr.create_seller(db, db_seller)
        await db.commit()
        return await cruds_cdr.get_seller_by_id(db=db, seller_id=db_seller.id)
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))


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
    try:
        await cruds_cdr.update_seller(
            seller_id=seller_id,
            seller=seller,
            db=db,
        )
        await db.commit()
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))


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
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))


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
    user: models_core.CoreUser = Depends(is_user_a_member),
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
        **product.model_dump(exclude={"product_constraints", "document_constraints"}),
    )
    try:
        cruds_cdr.create_product(db, db_product)
        for p in product.product_constraints:
            cruds_cdr.create_product_constraint(
                db,
                models_cdr.ProductConstraint(
                    product_id=db_product.id,
                    product_constraint_id=p,
                ),
            )
        for d in product.document_constraints:
            cruds_cdr.create_document_constraint(
                db,
                models_cdr.DocumentConstraint(
                    product_id=db_product.id,
                    document_id=d,
                ),
            )
        await db.commit()
        return await cruds_cdr.get_product_by_id(db, db_product.id)
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))


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
            for d in product.product_constraints:
                cruds_cdr.create_product_constraint(
                    db,
                    models_cdr.ProductConstraint(
                        product_id=product_id,
                        product_constraint_id=d,
                    ),
                )
        if product.document_constraints is not None:
            await cruds_cdr.delete_document_constraints(db=db, product_id=product_id)
            for d in product.document_constraints:
                cruds_cdr.create_document_constraint(
                    db,
                    models_cdr.DocumentConstraint(
                        product_id=product_id,
                        document_id=d,
                    ),
                )
        await db.commit()
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))


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
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))


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
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))


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
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))


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
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))


@module.router.get(
    "/cdr/sellers/{seller_id}/documents/",
    response_model=list[schemas_cdr.DocumentComplete],
    status_code=200,
)
async def get_documents(
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
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))
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
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))


@module.router.get(
    "/cdr/users/{user_id}/purchases/",
    response_model=list[schemas_cdr.PurchaseReturn],
    status_code=200,
)
async def get_purchases_by_user_id(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
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
    "/cdr/sellers/{seller_id}/users/{user_id}/purchases/",
    response_model=list[schemas_cdr.PurchaseReturn],
    status_code=200,
)
async def get_purchases_by_user_id_by_seller_id(
    seller_id: UUID,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
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
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Create a purchase.

    **User must create a purchase for themself and for an online available product or be part of the seller's group to use this endpoint**
    """
    status = await get_core_data(schemas_cdr.Status, db)
    if status.status == CdrStatus.pending:
        raise HTTPException(
            status_code=403,
            detail="CDR hasn't started yet.",
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
        except Exception as error:
            await db.rollback()
            raise HTTPException(status_code=400, detail=str(error))
        else:
            return db_purchase

    try:
        cruds_cdr.create_purchase(db, db_purchase)
        cruds_cdr.create_action(db, db_action)
        await db.commit()
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))
    else:
        return db_purchase


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
                            detail=f"Product constraint {product_constraint} not satisfied.",
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
                    detail=f"Document signature constraint {document_constraint} not satisfied.",
                )
    try:
        await cruds_cdr.mark_purchase_as_validated(
            db=db,
            user_id=user_id,
            product_variant_id=product_variant_id,
            validated=validated,
        )
        await db.commit()
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))
    else:
        return db_purchase


@module.router.delete(
    "/cdr/users/{user_id}/purchases/{product_variant_id}/",
    status_code=204,
)
async def delete_purchase(
    user_id: str,
    product_variant_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
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
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))


@module.router.get(
    "/cdr/users/{user_id}/signatures/",
    response_model=list[schemas_cdr.SignatureComplete],
    status_code=200,
)
async def get_signatures_by_user_id(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
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
    user: models_core.CoreUser = Depends(is_user_a_member),
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
    user: models_core.CoreUser = Depends(is_user_a_member),
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
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))
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
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))


@module.router.get(
    "/cdr/curriculums/",
    response_model=list[schemas_cdr.CurriculumComplete],
    status_code=200,
)
async def get_curriculums(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
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
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))
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
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))


@module.router.post(
    "/cdr/users/{user_id}/curriculums/{curriculum_id}/",
    status_code=201,
)
async def create_curriculum_membership(
    user_id: str,
    curriculum_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
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
        except Exception as error:
            await db.rollback()
            raise HTTPException(status_code=400, detail=str(error))
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
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))


@module.router.patch(
    "/cdr/users/{user_id}/curriculums/{curriculum_id}/",
    status_code=204,
)
async def update_curriculum_membership(
    user_id: str,
    curriculum_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
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
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))


@module.router.delete(
    "/cdr/users/{user_id}/curriculums/{curriculum_id}/",
    status_code=204,
)
async def delete_curriculum_membership(
    user_id: str,
    curriculum_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
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
    try:
        await cruds_cdr.delete_curriculum_membership(
            db=db,
            user_id=user_id,
            curriculum_id=curriculum_id,
        )
        await db.commit()
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))


@module.router.get(
    "/cdr/users/{user_id}/payments/",
    response_model=list[schemas_cdr.PaymentComplete],
    status_code=200,
)
async def get_payments_by_user_id(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
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
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))
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
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))


@module.router.get(
    "/cdr/pay/{amount}",
    response_model=schemas_cdr.PaymentUrl,
    status_code=201,
)
async def get_payment_url(
    amount: int,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
    settings: Settings = Depends(get_settings),
    payment_tool: PaymentTool = Depends(get_payment_tool),
):
    """
    Get payment url
    """
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
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    if not (
        user_id == user.id
        or is_user_member_of_an_allowed_group(user, [GroupType.admin_cdr])
    ):
        raise HTTPException(
            status_code=403,
            detail="You're not allowed to see other users memberships.",
        )
    return await cruds_cdr.get_memberships_by_user_id(db=db, user_id=user_id)


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
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))
    else:
        return db_membership


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
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))


@module.router.get(
    "/cdr/status/",
    response_model=schemas_cdr.Status,
    status_code=200,
)
async def get_status(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
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


@module.router.websocket("/cdr/users/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    ws_manager: WebsocketConnectionManager = Depends(get_websocket_connection_manager),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    hyperion_error_logger.debug(
        f"CDR: New websocket connection from {user.id} on worker {os.getpid()}"
    )

    await websocket.accept()

    # Add the user to the connection stack
    await ws_manager.add_connection_to_room(
        room_id=HyperionWebsocketsRoom.CDR,
        ws_connection=websocket,
    )

    try:
        while True:
            # TODO: we could use received messages from the websocket
            res = await websocket.receive_json()
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


# TODO: remove this debug method
@module.router.get(
    "/cdr/ws/send/",
    status_code=200,
)
async def send_ws_message(
    ws_manager: WebsocketConnectionManager = Depends(get_websocket_connection_manager),
):
    await ws_manager.send_message_to_room("message", HyperionWebsocketsRoom.CDR)
