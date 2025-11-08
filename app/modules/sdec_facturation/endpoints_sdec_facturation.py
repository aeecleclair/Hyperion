import logging
import uuid
from collections.abc import Sequence

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.groups_type import GroupType
from app.dependencies import (
    get_db,
    is_user,
    is_user_in,
)
from app.modules.sdec_facturation import (
    cruds_sdec_facturation,
    schemas_sdec_facturation,
)
from app.types.module import Module

module = Module(
    root="sdec_facturation",
    tag="sdec_facturation",
    factory=None,
)


hyperion_error_logger = logging.getLogger("hyperion.error")

# ---------------------------------------------------------------------------- #
#                                     Member                                   #
# ---------------------------------------------------------------------------- #


@module.router.get(
    "/sdec_facturation/members/",
    response_model=list[schemas_sdec_facturation.MemberComplete],
    status_code=200,
)
async def get_all_members(
    db: AsyncSession = Depends(get_db),
    _=Depends(is_user()),
) -> Sequence[schemas_sdec_facturation.MemberComplete]:
    """Get all members from the database"""
    return await cruds_sdec_facturation.get_all_members(db)


@module.router.post(
    "/sdec_facturation/members/",
    response_model=schemas_sdec_facturation.MemberComplete,
    status_code=201,
)
async def create_member(
    member: schemas_sdec_facturation.MemberBase,
    db: AsyncSession = Depends(get_db),
    _=Depends(is_user_in([GroupType.sdec_facturation_admin])),
) -> schemas_sdec_facturation.MemberComplete:
    """
    Create a new member in the database
    **This endpoint is only usable by SDEC Facturation admins**
    """
    if (
        await cruds_sdec_facturation.get_member_by_name(
            member.name,
            db,
        )
    ) is not None:
        raise HTTPException(
            status_code=400,
            detail="User is already a member",
        )

    return await cruds_sdec_facturation.create_member(member, db)


@module.router.patch(
    "/sdec_facturation/members/{member_id}",
    status_code=200,
)
async def update_member(
    member_id: uuid.UUID,
    member_edit: schemas_sdec_facturation.MemberBase,
    db: AsyncSession = Depends(get_db),
    _=Depends(is_user_in([GroupType.sdec_facturation_admin])),
) -> None:
    """
    Update a member in the database
    **This endpoint is only usable by SDEC Facturation admins**
    """

    member_db = await cruds_sdec_facturation.get_member_by_id(
        member_id,
        db,
    )
    if member_db is None:
        raise HTTPException(
            status_code=404,
            detail="Member not found",
        )

    if (
        await cruds_sdec_facturation.get_member_by_name(
            member_edit.name,
            db,
        )
    ) is not None and member_edit.name != member_db.name:
        raise HTTPException(
            status_code=400,
            detail="User is already a member",
        )

    await cruds_sdec_facturation.update_member(
        member_id,
        member_edit,
        db,
    )


@module.router.delete(
    "/sdec_facturation/members/{member_id}",
    status_code=204,
)
async def delete_member(
    member_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(is_user_in([GroupType.sdec_facturation_admin])),
) -> None:
    """
    Delete a member from the database
    **This endpoint is only usable by SDEC Facturation admins**
    """
    member_db = await cruds_sdec_facturation.get_member_by_id(
        member_id,
        db,
    )
    if member_db is None:
        raise HTTPException(
            status_code=404,
            detail="Member not found",
        )

    await cruds_sdec_facturation.delete_member(member_id, db)


# ---------------------------------------------------------------------------- #
#                                     Mandate                                  #
# ---------------------------------------------------------------------------- #
@module.router.get(
    "/sdec_facturation/mandates/",
    response_model=list[schemas_sdec_facturation.MandateComplete],
    status_code=200,
)
async def get_all_mandates(
    db: AsyncSession = Depends(get_db),
    _=Depends(is_user()),
) -> Sequence[schemas_sdec_facturation.MandateComplete]:
    """Get all mandates from the database"""
    return await cruds_sdec_facturation.get_all_mandates(db)


@module.router.post(
    "/sdec_facturation/mandates/",
    response_model=schemas_sdec_facturation.MandateComplete,
    status_code=201,
)
async def create_mandate(
    mandate: schemas_sdec_facturation.MandateComplete,
    db: AsyncSession = Depends(get_db),
    _=Depends(is_user_in([GroupType.sdec_facturation_admin])),
) -> schemas_sdec_facturation.MandateComplete:
    """
    Create a new mandate in the database
    **This endpoint is only usable by SDEC Facturation admins**
    """
    if (
        await cruds_sdec_facturation.get_mandate_by_year(
            mandate.year,
            db,
        )
    ) is not None:
        raise HTTPException(
            status_code=400,
            detail="Mandate year already exists",
        )

    return await cruds_sdec_facturation.create_mandate(mandate, db)


@module.router.patch(
    "/sdec_facturation/mandates/{mandate_year}",
    status_code=200,
)
async def update_mandate(
    mandate_year: int,
    mandate_edit: schemas_sdec_facturation.MandateUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(is_user_in([GroupType.sdec_facturation_admin])),
) -> None:
    """
    Update a mandate in the database
    **This endpoint is only usable by SDEC Facturation admins**
    """

    mandate_db = await cruds_sdec_facturation.get_mandate_by_year(
        mandate_year,
        db,
    )
    if mandate_db is None:
        raise HTTPException(
            status_code=404,
            detail="Mandate not found",
        )

    await cruds_sdec_facturation.update_mandate(
        mandate_year,
        mandate_edit,
        db,
    )


@module.router.delete(
    "/sdec_facturation/mandates/{mandate_year}",
    status_code=204,
)
async def delete_mandate(
    mandate_year: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(is_user_in([GroupType.sdec_facturation_admin])),
) -> None:
    """
    Delete a mandate from the database
    **This endpoint is only usable by SDEC Facturation admins**
    """
    mandate_db = await cruds_sdec_facturation.get_mandate_by_year(
        mandate_year,
        db,
    )
    if mandate_db is None:
        raise HTTPException(
            status_code=404,
            detail="Mandate not found",
        )

    await cruds_sdec_facturation.delete_mandate(mandate_year, db)


# ---------------------------------------------------------------------------- #
#                                  Association                                 #
# ---------------------------------------------------------------------------- #


@module.router.get(
    "/sdec_facturation/association/",
    response_model=list[schemas_sdec_facturation.AssociationComplete],
    status_code=200,
)
async def get_all_associations(
    db: AsyncSession = Depends(get_db),
    _=Depends(is_user()),
) -> Sequence[schemas_sdec_facturation.AssociationComplete]:
    """Get all associations from the database"""
    return await cruds_sdec_facturation.get_all_associations(db)


@module.router.post(
    "/sdec_facturation/association/",
    response_model=schemas_sdec_facturation.AssociationComplete,
    status_code=201,
)
async def create_association(
    association: schemas_sdec_facturation.AssociationBase,
    db: AsyncSession = Depends(get_db),
    _=Depends(is_user_in([GroupType.sdec_facturation_admin])),
) -> schemas_sdec_facturation.AssociationComplete:
    """
    Create a new association in the database
    **This endpoint is only usable by SDEC Facturation admins**
    """
    if (
        await cruds_sdec_facturation.get_association_by_name(association.name, db)
    ) is not None:
        raise HTTPException(
            status_code=400,
            detail="Association name already used",
        )

    return await cruds_sdec_facturation.create_association(association, db)


@module.router.patch(
    "/sdec_facturation/association/{association_id}",
    status_code=200,
)
async def update_association(
    association_id: uuid.UUID,
    association_edit: schemas_sdec_facturation.AssociationBase,
    db: AsyncSession = Depends(get_db),
    _=Depends(is_user_in([GroupType.sdec_facturation_admin])),
) -> None:
    """
    Create a new association in the database
    **This endpoint is only usable by SDEC Facturation admins**
    """
    association_db = await cruds_sdec_facturation.get_association_by_id(
        association_id,
        db,
    )
    if association_db is None:
        raise HTTPException(
            status_code=404,
            detail="Association not found",
        )

    if (
        await cruds_sdec_facturation.get_association_by_name(association_edit.name, db)
    ) is not None and association_edit.name != association_db.name:
        raise HTTPException(
            status_code=400,
            detail="Association name already used",
        )

    await cruds_sdec_facturation.update_association(
        association_id,
        association_edit,
        db,
    )


@module.router.delete(
    "/sdec_facturation/association/{association_id}",
    status_code=204,
)
async def delete_association(
    association_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(is_user_in([GroupType.sdec_facturation_admin])),
) -> None:
    """
    Delete an association from the database
    **This endpoint is only usable by SDEC Facturation admins**
    """
    association_db = await cruds_sdec_facturation.get_association_by_id(
        association_id,
        db,
    )
    if association_db is None:
        raise HTTPException(
            status_code=404,
            detail="Association not found",
        )

    await cruds_sdec_facturation.delete_association(association_id, db)


# ---------------------------------------------------------------------------- #
#                                     Product                                 #
# ---------------------------------------------------------------------------- #


@module.router.get(
    "/sdec_facturation/product/",
    response_model=list[schemas_sdec_facturation.ProductComplete],
    status_code=200,
)
async def get_all_products(
    db: AsyncSession = Depends(get_db),
    _=Depends(is_user()),
) -> Sequence[schemas_sdec_facturation.ProductComplete]:
    """Get all product items from the database"""
    return await cruds_sdec_facturation.get_all_products(db)


@module.router.post(
    "/sdec_facturation/product/",
    response_model=schemas_sdec_facturation.ProductComplete,
    status_code=201,
)
async def create_product(
    product: schemas_sdec_facturation.ProductBase,
    db: AsyncSession = Depends(get_db),
    _=Depends(is_user_in([GroupType.sdec_facturation_admin])),
) -> schemas_sdec_facturation.ProductComplete:
    """
    Create a new product item in the database
    **This endpoint is only usable by SDEC Facturation admins**
    """
    if (
        product.individual_price < 0
        or product.association_price < 0
        or product.ae_price < 0
    ):
        raise HTTPException(
            status_code=400,
            detail="Product item prices must be positive",
        )
    if (await cruds_sdec_facturation.get_product_by_code(product.code, db)) is not None:
        raise HTTPException(
            status_code=400,
            detail="Product item code already used",
        )
    if (await cruds_sdec_facturation.get_product_by_name(product.name, db)) is not None:
        raise HTTPException(
            status_code=400,
            detail="Product item name already used",
        )

    return await cruds_sdec_facturation.create_product(product, db)


@module.router.patch(
    "/sdec_facturation/product/{product_id}",
    status_code=200,
)
async def update_product(
    product_id: uuid.UUID,
    product_edit: schemas_sdec_facturation.ProductUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(is_user_in([GroupType.sdec_facturation_admin])),
) -> None:
    """
    Update a product item in the database
    **This endpoint is only usable by SDEC Facturation admins**
    """

    if (
        product_edit.individual_price < 0
        or product_edit.association_price < 0
        or product_edit.ae_price < 0
    ):
        raise HTTPException(
            status_code=400,
            detail="Product item prices must be positive",
        )

    product_db = await cruds_sdec_facturation.get_product_by_id(
        product_id,
        db,
    )
    if product_db is None:
        raise HTTPException(
            status_code=404,
            detail="Product item not found",
        )

    product_base = schemas_sdec_facturation.ProductBase(
        code=product_db.code,
        name=product_db.name,
        individual_price=product_edit.individual_price,
        association_price=product_edit.association_price,
        ae_price=product_edit.ae_price,
        category=product_db.category,
        for_sale=product_db.for_sale,
    )

    await cruds_sdec_facturation.update_product(
        product_db.code,
        product_base,
        db,
    )


@module.router.patch(
    "/sdec_facturation/product/minor/{product_id}",
    status_code=200,
)
async def minor_update_product(
    product_id: uuid.UUID,
    product_edit: schemas_sdec_facturation.ProductMinorUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(is_user_in([GroupType.sdec_facturation_admin])),
) -> None:
    """
    Minor update a product item in the database
    **This endpoint is only usable by SDEC Facturation admins**
    """

    product_db = await cruds_sdec_facturation.get_product_by_id(
        product_id,
        db,
    )
    if product_db is None:
        raise HTTPException(
            status_code=404,
            detail="Product item not found",
        )

    await cruds_sdec_facturation.minor_update_product(
        product_db.code,
        product_edit,
        db,
    )


@module.router.delete(
    "/sdec_facturation/product/{product_id}",
    status_code=204,
)
async def delete_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(is_user_in([GroupType.sdec_facturation_admin])),
) -> None:
    """
    Delete a product item from the database
    **This endpoint is only usable by SDEC Facturation admins**
    """
    product_db = await cruds_sdec_facturation.get_product_by_id(
        product_id,
        db,
    )
    if product_db is None:
        raise HTTPException(
            status_code=404,
            detail="Product item not found",
        )

    await cruds_sdec_facturation.delete_product(product_db.code, db)


# ---------------------------------------------------------------------------- #
#                                   Order                                   #
# ---------------------------------------------------------------------------- #


@module.router.get(
    "/sdec_facturation/orders/",
    response_model=list[schemas_sdec_facturation.OrderComplete],
    status_code=200,
)
async def get_all_orders(
    db: AsyncSession = Depends(get_db),
    _=Depends(is_user()),
) -> Sequence[schemas_sdec_facturation.OrderComplete]:
    """Get all orders from the database"""
    return await cruds_sdec_facturation.get_all_orders(db)


async def create_order(
    order: schemas_sdec_facturation.OrderBase,
    db: AsyncSession = Depends(get_db),
    _=Depends(is_user_in([GroupType.sdec_facturation_admin])),
) -> schemas_sdec_facturation.OrderComplete:
    """
    Create a new order in the database
    **This endpoint is only usable by SDEC Facturation admins**
    """
    if (
        await cruds_sdec_facturation.get_association_by_id(
            order.association_id,
            db,
        )
    ) is None:
        raise HTTPException(
            status_code=400,
            detail="Association does not exist",
        )

    if (
        await cruds_sdec_facturation.get_member_by_id(
            order.member_id,
            db,
        )
    ) is None:
        raise HTTPException(
            status_code=400,
            detail="Member does not exist",
        )
    return await cruds_sdec_facturation.create_order(order, db)


# ---------------------------------------------------------------------------- #
#                                 Facture Association                                #
# ---------------------------------------------------------------------------- #
