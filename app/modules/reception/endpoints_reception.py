import logging
import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core
from app.core.groups.groups_type import GroupType
from app.core.module import Module
from app.dependencies import (
    get_db,
    is_user_a_member,
    is_user_a_member_of,
)
from app.modules.reception import schemas_reception
from app.modules.reception.types_reception import AvailableMembership

module = Module(
    root="cdr",
    tag="Reception",
    default_allowed_groups_ids=[GroupType.admin_cdr],
)

hyperion_error_logger = logging.getLogger("hyperion.error")


@module.router.get(
    "/reception/sellers/",
    response_model=list[schemas_reception.SellerComplete],
    status_code=200,
)
async def get_sellers(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.get(
    "/reception/groups/{group_id}/sellers/",
    response_model=list[schemas_reception.SellerComplete],
    status_code=200,
)
async def get_sellers_by_group_id(
    group_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.get(
    "/reception/sellers/{seller_id}/",
    response_model=schemas_reception.SellerComplete,
    status_code=200,
)
async def get_seller_by_id(
    seller_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.post(
    "/reception/sellers/",
    response_model=schemas_reception.SellerComplete,
    status_code=201,
)
async def create_seller(
    seller: schemas_reception.SellerBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.patch(
    "/reception/sellers/{seller_id}/",
    status_code=204,
)
async def update_seller(
    seller_id: uuid.UUID,
    seller: schemas_reception.SellerEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.delete(
    "/reception/sellers/{seller_id}/",
    status_code=204,
)
async def delete_seller(
    seller_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.get(
    "/reception/products/",
    response_model=list[schemas_reception.ProductComplete],
    status_code=200,
)
async def get_products(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.get(
    "/reception/sellers/{seller_id}/products/",
    response_model=list[schemas_reception.ProductComplete],
    status_code=200,
)
async def get_products_by_seller_id(
    seller_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.get(
    "/reception/products/public_displayed/",
    response_model=list[schemas_reception.ProductComplete],
    status_code=200,
)
async def get_public_displayed_products(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.get(
    "/reception/products/{product_id}/",
    response_model=schemas_reception.ProductComplete,
    status_code=200,
)
async def get_product_by_id(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.post(
    "/reception/products/",
    response_model=schemas_reception.ProductBase,
    status_code=201,
)
async def create_product(
    product: schemas_reception.ProductBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.patch(
    "/reception/products/{product_id}/",
    status_code=204,
)
async def update_product(
    product_id: uuid.UUID,
    product: schemas_reception.ProductEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.delete(
    "/reception/products/{product_id}/",
    status_code=204,
)
async def delete_product(
    seller_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.get(
    "/reception/products/{product_id}/variants/",
    response_model=list[schemas_reception.ProductVariantComplete],
    status_code=200,
)
async def get_product_variants(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.get(
    "/reception/products/{product_id}/variants/{variant_id}/",
    response_model=schemas_reception.ProductVariantComplete,
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
    "/reception/products/{product_id}/variants/enabled/",
    response_model=list[schemas_reception.ProductVariantComplete],
    status_code=200,
)
async def get_enabled_product_variants(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.post(
    "/reception/products/{product_id}/variants/",
    response_model=schemas_reception.ProductBase,
    status_code=201,
)
async def create_product_variant(
    product_id: uuid.UUID,
    product_variant: schemas_reception.ProductVariantBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.patch(
    "/reception/products/{product_id}/variants/{variant_id}/",
    status_code=204,
)
async def update_product_variant(
    product_id: uuid.UUID,
    variant_id: uuid.UUID,
    product_variant: schemas_reception.ProductVariantEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.delete(
    "/reception/products/{product_id}/variants/{variant_id}/",
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
    "/reception/documents/",
    response_model=list[schemas_reception.DocumentComplete],
    status_code=200,
)
async def get_documents(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.get(
    "/reception/documents/{document_id}/",
    response_model=schemas_reception.DocumentComplete,
    status_code=200,
)
async def get_document_by_id(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.post(
    "/reception/documents/",
    response_model=schemas_reception.DocumentComplete,
    status_code=201,
)
async def create_document(
    document: schemas_reception.DocumentBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.delete(
    "/reception/documents/{document_id}/",
    status_code=204,
)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.get(
    "/reception/purchases/",
    response_model=list[schemas_reception.PurchaseComplete],
    status_code=200,
)
async def get_purchases(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.get(
    "/reception/users/{user_id}/purchases/",
    response_model=list[schemas_reception.PurchaseComplete],
    status_code=200,
)
async def get_purchases_by_user_id(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.get(
    "/reception/purchases/{purchase_id}/",
    response_model=schemas_reception.PurchaseComplete,
    status_code=200,
)
async def get_purchase_by_id(
    purchase_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.post(
    "/reception/purchases/",
    response_model=schemas_reception.PurchaseComplete,
    status_code=201,
)
async def create_purchase(
    purchase: schemas_reception.PurchaseBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.patch(
    "/reception/purchases/{purchase_id}/",
    status_code=204,
)
async def update_purchase(
    purchase_id: uuid.UUID,
    purchase: schemas_reception.PurchaseEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.patch(
    "/reception/purchases/{purchase_id}/paid/",
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
    "/reception/purchases/{purchase_id}/",
    status_code=204,
)
async def delete_purchase(
    purchase_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.get(
    "/reception/signatures/",
    response_model=list[schemas_reception.Signature],
    status_code=200,
)
async def get_signatures(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    pass


@module.router.get(
    "/reception/users/{user_id}/signatures/",
    response_model=list[schemas_reception.Signature],
    status_code=200,
)
async def get_signatures_by_user_id(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.get(
    "/reception/documents/{document_id}/signatures/",
    response_model=list[schemas_reception.Signature],
    status_code=200,
)
async def get_signatures_by_document_id(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    pass


@module.router.post(
    "/reception/signatures/",
    response_model=schemas_reception.Signature,
    status_code=201,
)
async def create_signature(
    signature: schemas_reception.Signature,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.delete(
    "/reception/signatures/{signature_id}/",
    status_code=204,
)
async def delete_signature(
    signature_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    pass


@module.router.get(
    "/reception/curriculums/",
    response_model=list[schemas_reception.CurriculumComplete],
    status_code=200,
)
async def get_curriculums(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.get(
    "/reception/users/{user_id}/curriculums/",
    response_model=list[schemas_reception.CurriculumComplete],
    status_code=200,
)
async def get_curriculums_by_user_id(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.get(
    "/reception/curriculums/{curriculum_id}/",
    response_model=schemas_reception.CurriculumComplete,
    status_code=200,
)
async def get_curriculum_by_id(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.post(
    "/reception/curriculums/",
    response_model=schemas_reception.CurriculumComplete,
    status_code=201,
)
async def create_curriculum(
    curriculum: schemas_reception.CurriculumBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    pass


@module.router.patch(
    "/reception/curriculums/{curriculum_id}/",
    status_code=204,
)
async def update_curriculum(
    curriculum_id: uuid.UUID,
    curriculum: schemas_reception.CurriculumBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    pass


@module.router.delete(
    "/reception/curriculums/{curriculum_id}/",
    status_code=204,
)
async def delete_curriculum(
    curriculum_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    pass


@module.router.post(
    "/reception/users/{user_id}/curriculums/{curriculum_id}/",
    response_model=schemas_reception.CurriculumComplete,
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
    "/reception/users/{user_id}/curriculums/{curriculum_id}/",
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
    "/reception/payments/",
    response_model=list[schemas_reception.PaymentComplete],
    status_code=200,
)
async def get_payments(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    pass


@module.router.get(
    "/reception/users/{user_id}/payments/",
    response_model=list[schemas_reception.PaymentComplete],
    status_code=200,
)
async def get_payments_by_user_id(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.get(
    "/reception/payments/{payment_id}/",
    response_model=list[schemas_reception.PaymentComplete],
    status_code=200,
)
async def get_payment_by_id(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    pass


@module.router.post(
    "/reception/payments/",
    response_model=schemas_reception.PaymentComplete,
    status_code=201,
)
async def create_payment(
    curriculum: schemas_reception.PaymentBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.delete(
    "/reception/payments/{payment_id}/",
    status_code=204,
)
async def delete_payment(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    pass


@module.router.get(
    "/reception/memberships/",
    response_model=list[schemas_reception.MembershipComplete],
    status_code=200,
)
async def get_memberships(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    pass


@module.router.get(
    "/reception/memberships/type/{membership_type}/",
    response_model=list[schemas_reception.MembershipComplete],
    status_code=200,
)
async def get_memberships_by_type(
    membership_type: AvailableMembership,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    pass


@module.router.get(
    "/reception/users/{user_id}/memberships/",
    response_model=list[schemas_reception.MembershipComplete],
    status_code=200,
)
async def get_memberships_by_user_id(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.get(
    "/reception/memberships/{membership_id}/",
    response_model=schemas_reception.MembershipComplete,
    status_code=200,
)
async def get_memberships_by_id(
    membership_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    pass


@module.router.post(
    "/reception/memberships/",
    response_model=schemas_reception.MembershipComplete,
    status_code=201,
)
async def create_membership(
    membership: schemas_reception.MembershipBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.patch(
    "/reception/memberships/{membership_id}/",
    status_code=204,
)
async def update_membership(
    membership_id: uuid.UUID,
    membership: schemas_reception.MembershipEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.delete(
    "/reception/memberships/{membership_id}/",
    status_code=204,
)
async def delete_membership(
    membership_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    pass


@module.router.get(
    "/reception/status/",
    response_model=schemas_reception.Status,
    status_code=200,
)
async def get_status(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    pass


@module.router.patch(
    "/reception/memberships/",
    response_model=schemas_reception.Status,
    status_code=204,
)
async def update_status(
    status: schemas_reception.Status,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin_cdr)),
):
    pass
