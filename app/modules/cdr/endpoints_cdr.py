import logging
import uuid

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core
from app.core.groups.groups_type import GroupType
from app.core.module import Module
from app.dependencies import (
    get_db,
    get_request_id,
    hyperion_access_logger,
    is_user_a_member,
    is_user_a_member_of,
)
from app.modules.cdr import cruds_cdr, models_cdr, schemas_cdr
from app.modules.cdr.types_cdr import AvailableMembership, CdrStatus
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


async def is_user_a_seller(
    user: models_core.CoreUser = Depends(
        is_user_a_member,
    ),
    request_id: str = Depends(get_request_id),
    db: AsyncSession = Depends(get_db),
) -> models_core.CoreUser:
    sellers = await cruds_cdr.get_sellers(db)

    sellers_groups = [str(seller.group_id) for seller in sellers]
    sellers_groups.append(GroupType.admin_cdr)

    if is_user_member_of_an_allowed_group(
        user=user,
        allowed_groups=sellers_groups,
    ):
        return user

    hyperion_access_logger.warning(
        f"Is_user_a_member_of: Unauthorized, user is not a seller ({request_id})",
    )

    raise HTTPException(
        status_code=403,
        detail="Unauthorized, user is not a seller.",
    )


async def is_user_in_a_seller_group(
    seller_id: uuid.UUID,
    user: models_core.CoreUser = Depends(
        is_user_a_member,
    ),
    request_id: str = Depends(get_request_id),
    db: AsyncSession = Depends(get_db),
):
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


@module.router.get(
    "/cdr/sellers/",
    response_model=list[schemas_cdr.SellerComplete],
    status_code=200,
)
async def get_sellers(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    return await cruds_cdr.get_sellers(db)


@module.router.get(
    "/cdr/users/me/sellers/",
    response_model=list[schemas_cdr.SellerComplete],
    status_code=200,
)
async def get_sellers_of_user(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_seller),
):
    return await cruds_cdr.get_sellers_by_group_ids(
        db,
        [uuid.UUID(x.id) for x in user.groups],
    )


@module.router.get(
    "/cdr/groups/{group_id}/sellers/",
    response_model=list[schemas_cdr.SellerComplete],
    status_code=200,
)
async def get_sellers_by_group_id(
    group_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    return await cruds_cdr.get_sellers_by_group_id(db, group_id)


@module.router.get(
    "/cdr/sellers/{seller_id}/",
    response_model=schemas_cdr.SellerComplete,
    status_code=200,
)
async def get_seller_by_id(
    seller_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_seller),
):
    seller = await cruds_cdr.get_seller_by_id(db, seller_id)
    if not seller:
        raise HTTPException(
            status_code=404,
            detail="Seller not found.",
        )
    if not is_user_member_of_an_allowed_group(
        user,
        [GroupType.admin_cdr, str(seller.group_id)],
    ):
        raise HTTPException(
            status_code=403,
            detail="Access forbidden : you must be part of this seller group or be cdr admin.",
        )

    return seller


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
    db_seller = models_cdr.Seller(
        id=str(uuid.uuid4()),
        **seller.model_dump(),
    )
    try:
        await cruds_cdr.create_seller(db, db_seller)
        await db.commit()
        return db_seller
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(error))


@module.router.patch(
    "/cdr/sellers/{seller_id}/",
    status_code=204,
)
async def update_seller(
    seller_id: uuid.UUID,
    seller: schemas_cdr.SellerEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    db_seller = await cruds_cdr.get_seller_by_id(seller_id=seller_id, db=db)
    if not db_seller:
        raise HTTPException(
            status_code=404,
            detail="Invalid seller_id",
        )
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
    seller_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    db_seller = await cruds_cdr.get_seller_by_id(seller_id=seller_id, db=db)
    if not db_seller:
        raise HTTPException(
            status_code=404,
            detail="Invalid seller_id",
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
    "/cdr/products/",
    response_model=list[schemas_cdr.ProductComplete],
    status_code=200,
)
async def get_products(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    return await cruds_cdr.get_products(db)


@module.router.get(
    "/cdr/sellers/{seller_id}/products/",
    response_model=list[schemas_cdr.ProductComplete],
    status_code=200,
)
async def get_products_by_seller_id(
    seller_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_seller),
):
    await is_user_in_a_seller_group(seller_id, user)
    return await cruds_cdr.get_products_by_seller_id(db, seller_id)


@module.router.get(
    "/cdr/products/available_online/",
    response_model=list[schemas_cdr.ProductComplete],
    status_code=200,
)
async def get_available_online_products(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    return await cruds_cdr.get_available_online_products(db)


@module.router.get(
    "/cdr/products/{product_id}/",
    response_model=schemas_cdr.ProductComplete,
    status_code=200,
)
async def get_product_by_id(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    return await cruds_cdr.get_product_by_id(db, product_id)


@module.router.post(
    "/cdr/products/",
    response_model=schemas_cdr.ProductComplete,
    status_code=201,
)
async def create_product(
    product: schemas_cdr.ProductBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_seller),
):
    await is_user_in_a_seller_group(
        product.seller_id,
        user,
    )
    status = await get_core_data(schemas_cdr.Status, db)
    if status.status == CdrStatus.closed:
        raise HTTPException(
            status_code=403,
            detail="CDR is closed. You cant add a new product.",
        )
    db_product = models_cdr.CdrProduct(
        id=str(uuid.uuid4()),
        **product.model_dump(),
    )
    try:
        await cruds_cdr.create_product(db, db_product)
        await db.commit()
        return db_product
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(error))


@module.router.post(
    "/cdr/products/{product_id}/document_constraint/{document_id}",
    response_model=schemas_cdr.ProductComplete,
    status_code=201,
)
async def create_document_constraint(
    product_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_seller),
):
    db_product = await cruds_cdr.get_product_by_id(product_id=product_id, db=db)
    if not db_product:
        raise HTTPException(
            status_code=404,
            detail="Invalid product_id",
        )
    db_document = await cruds_cdr.get_document_by_id(document_id=document_id, db=db)
    if not db_document:
        raise HTTPException(
            status_code=404,
            detail="Invalid document_id",
        )
    await is_user_in_a_seller_group(
        db_product.seller_id,
        user,
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
        await cruds_cdr.create_document_constraint(db, db_document_constraint)
        await db.commit()
        return await cruds_cdr.get_product_by_id(product_id=product_id, db=db)
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(error))


@module.router.post(
    "/cdr/products/{product_id}/product_constraint/{constraint_id}",
    response_model=schemas_cdr.ProductComplete,
    status_code=201,
)
async def create_product_constraint(
    product_id: uuid.UUID,
    constraint_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_seller),
):
    db_product = await cruds_cdr.get_product_by_id(product_id=product_id, db=db)
    if not db_product:
        raise HTTPException(
            status_code=404,
            detail="Invalid product_id",
        )
    db_constraint = await cruds_cdr.get_product_by_id(product_id=constraint_id, db=db)
    if not db_constraint:
        raise HTTPException(
            status_code=404,
            detail="Invalid document_id",
        )
    await is_user_in_a_seller_group(
        db_product.seller_id,
        user,
    )
    status = await get_core_data(schemas_cdr.Status, db)
    if status.status in [
        CdrStatus.onsite,
        CdrStatus.closed,
    ] or (status.status == CdrStatus.online and db_product.available_online):
        raise HTTPException(
            status_code=403,
            detail="This product can't be edited now. Please try creating a new product.",
        )
    db_product_constraint = models_cdr.ProductConstraint(
        product_id=product_id,
        product_constraint_id=constraint_id,
    )
    try:
        await cruds_cdr.create_product_constraint(db, db_product_constraint)
        await db.commit()
        return await cruds_cdr.get_product_by_id(product_id=product_id, db=db)
    except Exception as error:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(error))


@module.router.patch(
    "/cdr/products/{product_id}/",
    status_code=204,
)
async def update_product(
    product_id: uuid.UUID,
    product: schemas_cdr.ProductEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    status = await get_core_data(schemas_cdr.Status, db)
    db_product = await cruds_cdr.get_product_by_id(product_id=product_id, db=db)
    if not db_product:
        raise HTTPException(
            status_code=404,
            detail="Invalid product_id",
        )
    await is_user_in_a_seller_group(
        db_product.seller_id,
        user,
    )
    if status.status in [
        CdrStatus.onsite,
        CdrStatus.closed,
    ] or (status.status == CdrStatus.online and db_product.available_online):
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
    "/cdr/products/{product_id}/",
    status_code=204,
)
async def delete_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    status = await get_core_data(schemas_cdr.Status, db)
    db_product = await cruds_cdr.get_product_by_id(product_id=product_id, db=db)
    if not db_product:
        raise HTTPException(
            status_code=404,
            detail="Invalid product_id",
        )
    await is_user_in_a_seller_group(
        db_product.seller_id,
        user,
    )
    if status.status != CdrStatus.pending:
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
    "/cdr/products/{product_id}/document_constraint/{document_id}",
    status_code=204,
)
async def delete_document_constraint(
    product_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_seller),
):
    db_product = await cruds_cdr.get_product_by_id(product_id=product_id, db=db)
    if not db_product:
        raise HTTPException(
            status_code=404,
            detail="Invalid product_id",
        )
    await is_user_in_a_seller_group(
        db_product.seller_id,
        user,
    )
    status = await get_core_data(schemas_cdr.Status, db)
    if status.status != CdrStatus.pending:
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
    "/cdr/products/{product_id}/product_constraint/{constraint_id}",
    status_code=204,
)
async def delete_product_constraint(
    product_id: uuid.UUID,
    constraint_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_seller),
):
    db_product = await cruds_cdr.get_product_by_id(product_id=product_id, db=db)
    if not db_product:
        raise HTTPException(
            status_code=404,
            detail="Invalid product_id",
        )
    await is_user_in_a_seller_group(
        db_product.seller_id,
        user,
    )
    status = await get_core_data(schemas_cdr.Status, db)
    if status.status != CdrStatus.pending:
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


@module.router.get(
    "/cdr/products/{product_id}/variants/",
    response_model=list[schemas_cdr.ProductVariantComplete],
    status_code=200,
)
async def get_product_variants(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.get(
    "/cdr/products/{product_id}/variants/{variant_id}/",
    response_model=schemas_cdr.ProductVariantComplete,
    status_code=200,
)
async def get_product_variant_by_id(
    product_id: uuid.UUID,
    variant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.get(
    "/cdr/products/{product_id}/variants/enabled/",
    response_model=list[schemas_cdr.ProductVariantComplete],
    status_code=200,
)
async def get_enabled_product_variants(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.post(
    "/cdr/products/{product_id}/variants/",
    response_model=schemas_cdr.ProductBase,
    status_code=201,
)
async def create_product_variant(
    product_id: uuid.UUID,
    product_variant: schemas_cdr.ProductVariantBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.patch(
    "/cdr/products/{product_id}/variants/{variant_id}/",
    status_code=204,
)
async def update_product_variant(
    product_id: uuid.UUID,
    variant_id: uuid.UUID,
    product_variant: schemas_cdr.ProductVariantEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.delete(
    "/cdr/products/{product_id}/variants/{variant_id}/",
    status_code=204,
)
async def delete_product_variant(
    product_id: uuid.UUID,
    variant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.get(
    "/cdr/documents/",
    response_model=list[schemas_cdr.DocumentComplete],
    status_code=200,
)
async def get_documents(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.get(
    "/cdr/documents/{document_id}/",
    response_model=schemas_cdr.DocumentComplete,
    status_code=200,
)
async def get_document_by_id(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.post(
    "/cdr/documents/",
    response_model=schemas_cdr.DocumentComplete,
    status_code=201,
)
async def create_document(
    document: schemas_cdr.DocumentBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.delete(
    "/cdr/documents/{document_id}/",
    status_code=204,
)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.get(
    "/cdr/purchases/",
    response_model=list[schemas_cdr.PurchaseComplete],
    status_code=200,
)
async def get_purchases(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.get(
    "/cdr/users/{user_id}/purchases/",
    response_model=list[schemas_cdr.PurchaseComplete],
    status_code=200,
)
async def get_purchases_by_user_id(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.get(
    "/cdr/purchases/{purchase_id}/",
    response_model=schemas_cdr.PurchaseComplete,
    status_code=200,
)
async def get_purchase_by_id(
    purchase_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.post(
    "/cdr/purchases/",
    response_model=schemas_cdr.PurchaseComplete,
    status_code=201,
)
async def create_purchase(
    purchase: schemas_cdr.PurchaseBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.patch(
    "/cdr/purchases/{purchase_id}/",
    status_code=204,
)
async def update_purchase(
    purchase_id: uuid.UUID,
    purchase: schemas_cdr.PurchaseEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.patch(
    "/cdr/purchases/{purchase_id}/paid/",
    status_code=204,
)
async def mark_purchase_as_paid(
    purchase_id: uuid.UUID,
    paid: bool,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    pass


@module.router.delete(
    "/cdr/purchases/{purchase_id}/",
    status_code=204,
)
async def delete_purchase(
    purchase_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.get(
    "/cdr/signatures/",
    response_model=list[schemas_cdr.Signature],
    status_code=200,
)
async def get_signatures(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    pass


@module.router.get(
    "/cdr/users/{user_id}/signatures/",
    response_model=list[schemas_cdr.Signature],
    status_code=200,
)
async def get_signatures_by_user_id(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.get(
    "/cdr/documents/{document_id}/signatures/",
    response_model=list[schemas_cdr.Signature],
    status_code=200,
)
async def get_signatures_by_document_id(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    pass


@module.router.post(
    "/cdr/signatures/",
    response_model=schemas_cdr.Signature,
    status_code=201,
)
async def create_signature(
    signature: schemas_cdr.Signature,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.delete(
    "/cdr/signatures/{signature_id}/",
    status_code=204,
)
async def delete_signature(
    signature_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    pass


@module.router.get(
    "/cdr/curriculums/",
    response_model=list[schemas_cdr.CurriculumComplete],
    status_code=200,
)
async def get_curriculums(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.get(
    "/cdr/users/{user_id}/curriculums/",
    response_model=list[schemas_cdr.CurriculumComplete],
    status_code=200,
)
async def get_curriculums_by_user_id(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.get(
    "/cdr/curriculums/{curriculum_id}/",
    response_model=schemas_cdr.CurriculumComplete,
    status_code=200,
)
async def get_curriculum_by_id(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


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
    pass


@module.router.patch(
    "/cdr/curriculums/{curriculum_id}/",
    status_code=204,
)
async def update_curriculum(
    curriculum_id: uuid.UUID,
    curriculum: schemas_cdr.CurriculumBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    pass


@module.router.delete(
    "/cdr/curriculums/{curriculum_id}/",
    status_code=204,
)
async def delete_curriculum(
    curriculum_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    pass


@module.router.post(
    "/cdr/users/{user_id}/curriculums/{curriculum_id}/",
    response_model=schemas_cdr.CurriculumComplete,
    status_code=201,
)
async def create_curriculum_membership(
    user_id: uuid.UUID,
    curriculum_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.delete(
    "/cdr/users/{user_id}/curriculums/{curriculum_id}/",
    status_code=204,
)
async def delete_curriculum_membership(
    user_id: uuid.UUID,
    curriculum_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.get(
    "/cdr/payments/",
    response_model=list[schemas_cdr.PaymentComplete],
    status_code=200,
)
async def get_payments(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    pass


@module.router.get(
    "/cdr/users/{user_id}/payments/",
    response_model=list[schemas_cdr.PaymentComplete],
    status_code=200,
)
async def get_payments_by_user_id(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.get(
    "/cdr/payments/{payment_id}/",
    response_model=list[schemas_cdr.PaymentComplete],
    status_code=200,
)
async def get_payment_by_id(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    pass


@module.router.post(
    "/cdr/payments/",
    response_model=schemas_cdr.PaymentComplete,
    status_code=201,
)
async def create_payment(
    curriculum: schemas_cdr.PaymentBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.delete(
    "/cdr/payments/{payment_id}/",
    status_code=204,
)
async def delete_payment(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    pass


@module.router.get(
    "/cdr/memberships/",
    response_model=list[schemas_cdr.MembershipComplete],
    status_code=200,
)
async def get_memberships(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    pass


@module.router.get(
    "/cdr/memberships/type/{membership_type}/",
    response_model=list[schemas_cdr.MembershipComplete],
    status_code=200,
)
async def get_memberships_by_type(
    membership_type: AvailableMembership,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    pass


@module.router.get(
    "/cdr/users/{user_id}/memberships/",
    response_model=list[schemas_cdr.MembershipComplete],
    status_code=200,
)
async def get_memberships_by_user_id(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.get(
    "/cdr/memberships/{membership_id}/",
    response_model=schemas_cdr.MembershipComplete,
    status_code=200,
)
async def get_memberships_by_id(
    membership_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    pass


@module.router.post(
    "/cdr/memberships/",
    response_model=schemas_cdr.MembershipComplete,
    status_code=201,
)
async def create_membership(
    membership: schemas_cdr.MembershipBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.patch(
    "/cdr/memberships/{membership_id}/",
    status_code=204,
)
async def update_membership(
    membership_id: uuid.UUID,
    membership: schemas_cdr.MembershipEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.delete(
    "/cdr/memberships/{membership_id}/",
    status_code=204,
)
async def delete_membership(
    membership_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    pass


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
