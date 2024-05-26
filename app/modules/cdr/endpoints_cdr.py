import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core
from app.core.groups.groups_type import GroupType
from app.dependencies import (
    get_db,
    get_request_id,
    hyperion_access_logger,
    is_user_a_member,
    is_user_a_member_of,
)
from app.modules.cdr import cruds_cdr, models_cdr, schemas_cdr
from app.modules.cdr.types_cdr import (
    CdrLogActionType,
    CdrStatus,
    DocumentSignatureType,
)
from app.types.module import Module
from app.utils.tools import (
    get_core_data,
    is_user_member_of_an_allowed_group,
    set_core_data,
)

module = Module(
    root="cdr",
    tag="Cdr",
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
    if await cruds_cdr.get_products_by_seller_id(db=db, seller_id=seller_id):
        raise HTTPException(
            status_code=403,
            detail="Please delete all this seller products first.",
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
        **product.model_dump(),
    )
    try:
        cruds_cdr.create_product(db, db_product)
        await db.commit()
        return await cruds_cdr.get_product_by_id(db, db_product.id)
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))


@module.router.post(
    "/cdr/sellers/{seller_id}/products/{product_id}/document_constraints/{document_id}/",
    response_model=schemas_cdr.ProductComplete,
    status_code=201,
)
async def create_document_constraint(
    seller_id: UUID,
    product_id: UUID,
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Add a document in a product's document constraints.

    **User must be part of the seller's group to use this endpoint**
    """
    await is_user_in_a_seller_group(
        seller_id,
        user,
        db=db,
    )
    await check_request_consistency(
        db=db,
        seller_id=seller_id,
        product_id=product_id,
        document_id=document_id,
    )

    status = await get_core_data(schemas_cdr.Status, db)
    if status.status == CdrStatus.closed:
        raise HTTPException(
            status_code=403,
            detail="CDR is closed. You cant add a new constraint.",
        )
    db_document_constraint = models_cdr.DocumentConstraint(
        document_id=document_id,
        product_id=product_id,
    )
    try:
        cruds_cdr.create_document_constraint(db, db_document_constraint)
        await db.commit()
        return await cruds_cdr.get_product_by_id(product_id=product_id, db=db)
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))


@module.router.post(
    "/cdr/sellers/{seller_id}/products/{product_id}/product_constraints/{constraint_id}/",
    response_model=schemas_cdr.ProductComplete,
    status_code=201,
)
async def create_product_constraint(
    seller_id: UUID,
    product_id: UUID,
    constraint_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Add a product in a product's product constraints.

    **User must be part of the seller's group to use this endpoint**
    """
    await is_user_in_a_seller_group(
        seller_id,
        user,
        db=db,
    )
    db_product = await check_request_consistency(
        db=db,
        seller_id=seller_id,
        product_id=product_id,
    )
    db_constraint = await cruds_cdr.get_product_by_id(product_id=constraint_id, db=db)
    if not db_constraint:
        raise HTTPException(
            status_code=404,
            detail="Invalid constraint_id",
        )
    if product_id == constraint_id:
        raise HTTPException(
            status_code=403,
            detail="You can't add a product as a constraint for itself.",
        )

    status = await get_core_data(schemas_cdr.Status, db)
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
    db_product_constraint = models_cdr.ProductConstraint(
        product_id=product_id,
        product_constraint_id=constraint_id,
    )
    try:
        cruds_cdr.create_product_constraint(db, db_product_constraint)
        await db.commit()
        return await cruds_cdr.get_product_by_id(product_id=product_id, db=db)
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
    try:
        await cruds_cdr.delete_product(
            product_id=product_id,
            db=db,
        )
        await db.commit()
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))


@module.router.delete(
    "/cdr/sellers/{seller_id}/products/{product_id}/document_constraints/{document_id}/",
    status_code=204,
)
async def delete_document_constraint(
    seller_id: UUID,
    product_id: UUID,
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Remove a document from a product's document constraints.

    **User must be part of the seller's group to use this endpoint**
    """
    await is_user_in_a_seller_group(
        seller_id,
        user,
        db=db,
    )
    db_product = await check_request_consistency(
        db=db,
        seller_id=seller_id,
        product_id=product_id,
    )
    status = await get_core_data(schemas_cdr.Status, db)
    if status.status in [
        CdrStatus.onsite,
        CdrStatus.closed,
    ] or (
        db_product and status.status == CdrStatus.online and db_product.available_online
    ):
        raise HTTPException(
            status_code=403,
            detail="You can't delete a constraint once CDR has started.",
        )
    try:
        await cruds_cdr.delete_document_constraint(
            product_id=product_id,
            document_id=document_id,
            db=db,
        )
        await db.commit()
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))


@module.router.delete(
    "/cdr/sellers/{seller_id}/products/{product_id}/product_constraints/{constraint_id}/",
    status_code=204,
)
async def delete_product_constraint(
    seller_id: UUID,
    product_id: UUID,
    constraint_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Remove a product from a product's document constraints.

    **User must be part of the seller's group to use this endpoint**
    """
    await is_user_in_a_seller_group(
        seller_id,
        user,
        db=db,
    )
    db_product = await check_request_consistency(
        db=db,
        seller_id=seller_id,
        product_id=product_id,
    )
    status = await get_core_data(schemas_cdr.Status, db)
    if status.status in [
        CdrStatus.onsite,
        CdrStatus.closed,
    ] or (
        db_product and status.status == CdrStatus.online and db_product.available_online
    ):
        raise HTTPException(
            status_code=403,
            detail="You can't delete a constraint once CDR has started.",
        )
    try:
        await cruds_cdr.delete_product_constraint(
            product_id=product_id,
            product_constraint_id=constraint_id,
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
    await check_request_consistency(db=db, seller_id=seller_id, product_id=product_id)
    status = await get_core_data(schemas_cdr.Status, db)
    if status.status == CdrStatus.closed:
        raise HTTPException(
            status_code=403,
            detail="CDR is closed. You cant add a new product.",
        )
    db_product_variant = models_cdr.ProductVariant(
        id=uuid4(),
        product_id=product_id,
        **product_variant.model_dump(),
    )
    try:
        cruds_cdr.create_product_variant(db, db_product_variant)
        await db.commit()
        return db_product_variant
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
    try:
        await cruds_cdr.update_product_variant(
            variant_id=variant_id,
            product_variant=product_variant,
            db=db,
        )
        await db.commit()
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))


@module.router.post(
    "/cdr/sellers/{seller_id}/products/{product_id}/variants/{variant_id}/curriculums/{curriculum_id}/",
    response_model=schemas_cdr.ProductVariantComplete,
    status_code=201,
)
async def create_allowed_curriculum(
    seller_id: UUID,
    product_id: UUID,
    variant_id: UUID,
    curriculum_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Add a curriculum in a product variant's allowed curriculums.

    **User must be part of the seller's group to use this endpoint**
    """
    await is_user_in_a_seller_group(
        seller_id,
        user,
        db=db,
    )
    await check_request_consistency(
        db=db,
        seller_id=seller_id,
        product_id=product_id,
        variant_id=variant_id,
    )
    db_curriculum = await cruds_cdr.get_curriculum_by_id(
        curriculum_id=curriculum_id,
        db=db,
    )
    if not db_curriculum:
        raise HTTPException(
            status_code=404,
            detail="Invalid curriculum_id",
        )

    status = await get_core_data(schemas_cdr.Status, db)
    if status.status == CdrStatus.closed:
        raise HTTPException(
            status_code=403,
            detail="Cdr is closed.",
        )
    allowed_curriculum = models_cdr.AllowedCurriculum(
        product_variant_id=variant_id,
        curriculum_id=curriculum_id,
    )
    try:
        cruds_cdr.create_allowed_curriculum(db, allowed_curriculum)
        await db.commit()
        return await cruds_cdr.get_product_variant_by_id(variant_id=variant_id, db=db)
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))


@module.router.delete(
    "/cdr/sellers/{seller_id}/products/{product_id}/variants/{variant_id}/curriculums/{curriculum_id}/",
    status_code=204,
)
async def delete_allowed_curriculum(
    seller_id: UUID,
    product_id: UUID,
    variant_id: UUID,
    curriculum_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Remove a curriculum from a product variant's allowed curriculums.

    **User must be part of the seller's group to use this endpoint**
    """
    await is_user_in_a_seller_group(
        seller_id,
        user,
        db=db,
    )
    db_product = await check_request_consistency(
        db=db,
        seller_id=seller_id,
        product_id=product_id,
        variant_id=variant_id,
    )
    db_curriculum = await cruds_cdr.get_curriculum_by_id(
        curriculum_id=curriculum_id,
        db=db,
    )
    if not db_curriculum:
        raise HTTPException(
            status_code=404,
            detail="Invalid curriculum_id",
        )
    status = await get_core_data(schemas_cdr.Status, db)
    if status.status in [
        CdrStatus.onsite,
        CdrStatus.closed,
    ] or (
        db_product and status.status == CdrStatus.online and db_product.available_online
    ):
        raise HTTPException(
            status_code=403,
            detail="You can't delete a allowed curriculum once CDR has started.",
        )
    try:
        await cruds_cdr.delete_allowed_curriculum(
            variant_id=variant_id,
            curriculum_id=curriculum_id,
            db=db,
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
        return db_document
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))


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
    response_model=list[schemas_cdr.PurchaseComplete],
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
    return await cruds_cdr.get_purchases_by_user_id(db=db, user_id=user_id)


@module.router.get(
    "/cdr/sellers/{seller_id}/users/{user_id}/purchases/",
    response_model=list[schemas_cdr.PurchaseComplete],
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
    if not (
        user_id == user.id
        or await is_user_in_a_seller_group(seller_id=seller_id, user=user, db=db)
    ):
        raise HTTPException(
            status_code=403,
            detail="You're not allowed to see other users purchases for this group.",
        )
    return await cruds_cdr.get_purchases_by_user_id_by_seller_id(
        db=db,
        user_id=user_id,
        seller_id=seller_id,
    )


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
    if not (
        (user_id == user.id and product.available_online)
        or await is_user_in_a_seller_group(product.seller_id, user=user, db=db)
    ):
        raise HTTPException(
            status_code=403,
            detail="You're not allowed to make this purchase for another user, or to buy a non online available product.",
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
        action=str(db_purchase),
        timestamp=datetime.now(UTC),
    )
    try:
        cruds_cdr.create_purchase(db, db_purchase)
        cruds_cdr.create_action(db, db_action)
        await db.commit()
        return db_purchase
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))


@module.router.patch(
    "/cdr/users/{user_id}/purchases/{product_variant_id}/",
    status_code=204,
)
async def update_purchase(
    user_id: str,
    product_variant_id: UUID,
    purchase: schemas_cdr.PurchaseEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Edit a purchase.

    **User must create a purchase for themself and for an online available product or be part of the seller's group to use this endpoint**
    """
    status = await get_core_data(schemas_cdr.Status, db)
    if status.status == CdrStatus.pending:
        raise HTTPException(
            status_code=403,
            detail="CDR hasn't started yet.",
        )
    db_purchase = await cruds_cdr.get_purchase_by_id(
        db=db,
        user_id=user_id,
        product_variant_id=product_variant_id,
    )
    if not db_purchase:
        raise HTTPException(
            status_code=404,
            detail="Invalid purchase.",
        )
    product_variant = await cruds_cdr.get_product_variant_by_id(
        db=db,
        variant_id=product_variant_id,
    )
    if not product_variant:
        raise HTTPException(
            status_code=404,
            detail="Invalid product variant.",
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
    if not (
        (user_id == user.id and product.available_online)
        or await is_user_in_a_seller_group(product.seller_id, user=user, db=db)
    ):
        raise HTTPException(
            status_code=403,
            detail="You're not allowed to make this purchase for another user, or to buy a non online available product.",
        )
    try:
        await cruds_cdr.update_purchase(
            db=db,
            user_id=user_id,
            product_variant_id=product_variant_id,
            purchase=purchase,
        )
        await db.commit()
        return db_purchase
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))


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
    try:
        await cruds_cdr.mark_purchase_as_validated(
            db=db,
            user_id=user_id,
            product_variant_id=product_variant_id,
            validated=validated,
        )
        await db.commit()
        return db_purchase
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))


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
    if not (
        (user_id == user.id and product.available_online)
        or await is_user_in_a_seller_group(product.seller_id, user=user, db=db)
    ):
        raise HTTPException(
            status_code=403,
            detail="You're not allowed to make this purchase for another user, or to buy a non online available product.",
        )
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
        action=str(db_purchase),
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
    if not (
        user_id == user.id
        or await is_user_in_a_seller_group(seller_id=seller_id, user=user, db=db)
    ):
        raise HTTPException(
            status_code=403,
            detail="You're not allowed to see other users signatures.",
        )
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
        return db_signature
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))


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
        return db_curriculum
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))


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
    try:
        curriculum_membership = models_cdr.CurriculumMembership(
            user_id=user_id,
            curriculum_id=curriculum_id,
        )
        cruds_cdr.create_curriculum_membership(
            db=db,
            curriculum_membership=curriculum_membership,
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
        action=str(db_payment),
        timestamp=datetime.now(UTC),
    )
    try:
        cruds_cdr.create_payment(db, db_payment)
        cruds_cdr.create_action(db, db_action)
        await db.commit()
        return db_payment
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))


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
        action=str(db_payment),
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
    "/cdr/memberships/",
    response_model=schemas_cdr.MembershipComplete,
    status_code=201,
)
async def create_membership(
    membership: schemas_cdr.MembershipBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    db_membership = models_cdr.Membership(
        id=uuid4(),
        **membership.model_dump(),
    )
    try:
        cruds_cdr.create_membership(db, db_membership)
        await db.commit()
        return db_membership
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(error))


@module.router.delete(
    "/cdr/memberships/{membership_id}/",
    status_code=204,
)
async def delete_membership(
    membership_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    db_membership = await cruds_cdr.get_membership_by_id(
        membership_id=membership_id,
        db=db,
    )
    if not db_membership:
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
