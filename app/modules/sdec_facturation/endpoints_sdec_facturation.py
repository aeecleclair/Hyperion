import logging
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

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
    "/sdec_facturation/member/",
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
    "/sdec_facturation/member/",
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

    if (member.mandate < 2000) or (member.mandate > datetime.now(tz=UTC).year + 1):
        raise HTTPException(
            status_code=400,
            detail="Mandate year is not valid",
        )

    return await cruds_sdec_facturation.create_member(member, db)


@module.router.patch(
    "/sdec_facturation/member/{member_id}",
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

    if (member_edit.mandate < 2000) or (
        member_edit.mandate > datetime.now(tz=UTC).year + 1
    ):
        raise HTTPException(
            status_code=400,
            detail="Mandate year is not valid",
        )

    await cruds_sdec_facturation.update_member(
        member_id,
        member_edit,
        db,
    )


@module.router.delete(
    "/sdec_facturation/member/{member_id}",
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
    "/sdec_facturation/mandate/",
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
    "/sdec_facturation/mandate/",
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
    "/sdec_facturation/mandate/{mandate_year}",
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
    "/sdec_facturation/mandate/{mandate_year}",
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
    response_model=list[schemas_sdec_facturation.ProductAndPriceComplete],
    status_code=200,
)
async def get_all_products(
    db: AsyncSession = Depends(get_db),
    _=Depends(is_user()),
) -> Sequence[schemas_sdec_facturation.ProductAndPriceComplete]:
    """Get all product items from the database"""
    return await cruds_sdec_facturation.get_all_products_and_price(db)


@module.router.post(
    "/sdec_facturation/product/",
    response_model=schemas_sdec_facturation.ProductComplete,
    status_code=201,
)
async def create_product(
    product: schemas_sdec_facturation.ProductAndPriceBase,
    db: AsyncSession = Depends(get_db),
    _=Depends(is_user_in([GroupType.sdec_facturation_admin])),
) -> schemas_sdec_facturation.ProductAndPriceComplete:
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

    product_db = await cruds_sdec_facturation.get_product_by_id(
        product_id,
        db,
    )
    if product_db is None:
        raise HTTPException(
            status_code=404,
            detail="Product item not found",
        )

    if (
        product_edit.name is not None
        and (await cruds_sdec_facturation.get_product_by_name(product_edit.name, db))
        is not None
        and product_edit.name != product_db.name
    ):
        raise HTTPException(
            status_code=400,
            detail="Product item name already used",
        )

    await cruds_sdec_facturation.update_product(
        product_db.id,
        product_edit,
        db,
    )


@module.router.patch(
    "/sdec_facturation/product/price/{product_id}",
    status_code=200,
)
async def update_price(
    product_id: uuid.UUID,
    price_edit: schemas_sdec_facturation.ProductPriceUpdate,
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

    price_db = await cruds_sdec_facturation.get_prices_by_product_id_and_date(
        product_id,
        db,
    )
    current_date = datetime.now(tz=UTC)
    if price_db is not None and current_date <= price_db.effective_date:
        raise HTTPException(
            status_code=400,
            detail="New price effective date must be after the current one",
        )
    if price_db is not None and current_date == price_db.effective_date:
        await cruds_sdec_facturation.update_price(
            product_db.id,
            price_edit,
            db,
        )

    await cruds_sdec_facturation.create_price(
        product_db.id,
        price_edit,
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

    await cruds_sdec_facturation.delete_product(product_id, db)


# ---------------------------------------------------------------------------- #
#                                   Order                                   #
# ---------------------------------------------------------------------------- #


@module.router.get(
    "/sdec_facturation/order/",
    response_model=list[schemas_sdec_facturation.OrderComplete],
    status_code=200,
)
async def get_all_orders(
    db: AsyncSession = Depends(get_db),
    _=Depends(is_user()),
) -> Sequence[schemas_sdec_facturation.OrderComplete]:
    """Get all orders from the database"""
    return await cruds_sdec_facturation.get_all_orders(db)


@module.router.post(
    "/sdec_facturation/order/",
    response_model=schemas_sdec_facturation.OrderComplete,
    status_code=201,
)
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


@module.router.patch(
    "/sdec_facturation/order/{order_id}",
    status_code=200,
)
async def update_order(
    order_id: uuid.UUID,
    order_edit: schemas_sdec_facturation.OrderUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(is_user_in([GroupType.sdec_facturation_admin])),
) -> None:
    """
    Update an order in the database
    **This endpoint is only usable by SDEC Facturation admins**
    """

    order_db = await cruds_sdec_facturation.get_order_by_id(
        order_id,
        db,
    )
    if order_db is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found",
        )

    await cruds_sdec_facturation.update_order(
        order_id,
        order_edit,
        db,
    )


@module.router.delete(
    "/sdec_facturation/order/{order_id}",
    status_code=204,
)
async def delete_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(is_user_in([GroupType.sdec_facturation_admin])),
) -> None:
    """
    Delete an order from the database
    **This endpoint is only usable by SDEC Facturation admins**
    """
    order_db = await cruds_sdec_facturation.get_order_by_id(
        order_id,
        db,
    )
    if order_db is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found",
        )

    await cruds_sdec_facturation.delete_order(order_id, db)


# ---------------------------------------------------------------------------- #
#                              Facture Association                             #
# ---------------------------------------------------------------------------- #
@module.router.get(
    "/sdec_facturation/facture_association/",
    response_model=list[schemas_sdec_facturation.FactureAssociationComplete],
    status_code=200,
)
async def get_all_facture_associations(
    db: AsyncSession = Depends(get_db),
    _=Depends(is_user()),
) -> Sequence[schemas_sdec_facturation.FactureAssociationComplete]:
    """Get all facture associations from the database"""
    return await cruds_sdec_facturation.get_all_factures_association(db)


@module.router.post(
    "/sdec_facturation/facture_association/",
    response_model=schemas_sdec_facturation.FactureAssociationComplete,
    status_code=201,
)
async def create_facture_association(
    facture_association: schemas_sdec_facturation.FactureAssociationBase,
    db: AsyncSession = Depends(get_db),
    _=Depends(is_user_in([GroupType.sdec_facturation_admin])),
) -> schemas_sdec_facturation.FactureAssociationComplete:
    """
    Create a new facture association in the database
    **This endpoint is only usable by SDEC Facturation admins**
    """
    if (
        await cruds_sdec_facturation.get_facture_association_by_number(
            facture_association.facture_number,
            db,
        )
    ) is not None:
        raise HTTPException(
            status_code=400,
            detail="Facture number already used",
        )

    if (
        await cruds_sdec_facturation.get_member_by_id(
            facture_association.member_id,
            db,
        )
    ) is None:
        raise HTTPException(
            status_code=400,
            detail="Member does not exist",
        )

    if (
        await cruds_sdec_facturation.get_association_by_id(
            facture_association.association_id,
            db,
        )
    ) is None:
        raise HTTPException(
            status_code=400,
            detail="Association does not exist",
        )

    if facture_association.price < 0:
        raise HTTPException(
            status_code=400,
            detail="Facture price must be positive",
        )

    if facture_association.start_date >= facture_association.end_date:
        raise HTTPException(
            status_code=400,
            detail="Facture start date must be before end date",
        )

    return await cruds_sdec_facturation.create_facture_association(
        facture_association,
        db,
    )


@module.router.patch(
    "/sdec_facturation/facture_association/{facture_association_id}",
    status_code=200,
)
async def update_facture_association(
    facture_association_id: uuid.UUID,
    facture_association_edit: schemas_sdec_facturation.FactureAssociationUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(is_user_in([GroupType.sdec_facturation_admin])),
) -> None:
    """
    Update a facture association in the database
    **This endpoint is only usable by SDEC Facturation admins**
    """

    facture_association_db = await cruds_sdec_facturation.get_facture_association_by_id(
        facture_association_id,
        db,
    )
    if facture_association_db is None:
        raise HTTPException(
            status_code=404,
            detail="Facture association not found",
        )

    await cruds_sdec_facturation.update_facture_association(
        facture_association_id,
        facture_association_edit,
        db,
    )


@module.router.delete(
    "/sdec_facturation/facture_association/{facture_association_id}",
    status_code=204,
)
async def delete_facture_association(
    facture_association_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(is_user_in([GroupType.sdec_facturation_admin])),
) -> None:
    """
    Delete a facture association from the database
    **This endpoint is only usable by SDEC Facturation admins**
    """
    facture_association_db = await cruds_sdec_facturation.get_facture_association_by_id(
        facture_association_id,
        db,
    )
    if facture_association_db is None:
        raise HTTPException(
            status_code=404,
            detail="Facture association not found",
        )

    await cruds_sdec_facturation.delete_facture_association(
        facture_association_id,
        db,
    )


# ---------------------------------------------------------------------------- #
#                               Facture Individual                             #
# ---------------------------------------------------------------------------- #
@module.router.get(
    "/sdec_facturation/facture_individual/",
    response_model=list[schemas_sdec_facturation.FactureIndividualComplete],
    status_code=200,
)
async def get_all_facture_individuals(
    db: AsyncSession = Depends(get_db),
    _=Depends(is_user()),
) -> Sequence[schemas_sdec_facturation.FactureIndividualComplete]:
    """Get all facture individuals from the database"""
    return await cruds_sdec_facturation.get_all_factures_individual(db)


@module.router.post(
    "/sdec_facturation/facture_individual/",
    response_model=schemas_sdec_facturation.FactureIndividualComplete,
    status_code=201,
)
async def create_facture_individual(
    facture_individual: schemas_sdec_facturation.FactureIndividualBase,
    db: AsyncSession = Depends(get_db),
    _=Depends(is_user_in([GroupType.sdec_facturation_admin])),
) -> schemas_sdec_facturation.FactureIndividualComplete:
    """
    Create a new facture individual in the database
    **This endpoint is only usable by SDEC Facturation admins**
    """
    if facture_individual.firstname.strip() == "":
        raise HTTPException(
            status_code=400,
            detail="Firstname cannot be empty",
        )
    if facture_individual.lastname.strip() == "":
        raise HTTPException(
            status_code=400,
            detail="Lastname cannot be empty",
        )
    if facture_individual.adresse.strip() == "":
        raise HTTPException(
            status_code=400,
            detail="Adresse cannot be empty",
        )
    if facture_individual.postal_code.strip() == "":
        raise HTTPException(
            status_code=400,
            detail="Postal code cannot be empty",
        )
    if facture_individual.city.strip() == "":
        raise HTTPException(
            status_code=400,
            detail="City cannot be empty",
        )

    if (
        await cruds_sdec_facturation.get_facture_individual_by_number(
            facture_individual.facture_number,
            db,
        )
    ) is not None:
        raise HTTPException(
            status_code=400,
            detail="Facture number already used",
        )

    if (
        await cruds_sdec_facturation.get_member_by_id(
            facture_individual.member_id,
            db,
        )
    ) is None:
        raise HTTPException(
            status_code=400,
            detail="Member does not exist",
        )

    if facture_individual.price < 0:
        raise HTTPException(
            status_code=400,
            detail="Facture price must be positive",
        )

    return await cruds_sdec_facturation.create_facture_individual(
        facture_individual,
        db,
    )


@module.router.patch(
    "/sdec_facturation/facture_individual/{facture_individual_id}",
    status_code=200,
)
async def update_facture_individual(
    facture_individual_id: uuid.UUID,
    facture_individual_edit: schemas_sdec_facturation.FactureIndividualUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(is_user_in([GroupType.sdec_facturation_admin])),
) -> None:
    """
    Update a facture individual in the database
    **This endpoint is only usable by SDEC Facturation admins**
    """

    facture_individual_db = await cruds_sdec_facturation.get_facture_individual_by_id(
        facture_individual_id,
        db,
    )
    if facture_individual_db is None:
        raise HTTPException(
            status_code=404,
            detail="Facture individual not found",
        )

    await cruds_sdec_facturation.update_facture_individual(
        facture_individual_id,
        facture_individual_edit,
        db,
    )


@module.router.delete(
    "/sdec_facturation/facture_individual/{facture_individual_id}",
    status_code=204,
)
async def delete_facture_individual(
    facture_individual_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(is_user_in([GroupType.sdec_facturation_admin])),
) -> None:
    """
    Delete a facture individual from the database
    **This endpoint is only usable by SDEC Facturation admins**
    """
    facture_individual_db = await cruds_sdec_facturation.get_facture_individual_by_id(
        facture_individual_id,
        db,
    )
    if facture_individual_db is None:
        raise HTTPException(
            status_code=404,
            detail="Facture individual not found",
        )

    await cruds_sdec_facturation.delete_facture_individual(
        facture_individual_id,
        db,
    )
