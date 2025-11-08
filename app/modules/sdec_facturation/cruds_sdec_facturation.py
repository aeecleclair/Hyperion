"""File defining the functions called by the endpoints, making queries to the table using the models"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sdec_facturation import (
    models_sdec_facturation,
    schemas_sdec_facturation,
)

# ---------------------------------------------------------------------------- #
#                                     Member                                   #
# ---------------------------------------------------------------------------- #


async def create_member(
    member: schemas_sdec_facturation.MemberBase,
    db: AsyncSession,
) -> schemas_sdec_facturation.MemberComplete:
    """Create a new member in the database"""

    member_db = models_sdec_facturation.Member(
        id=uuid.uuid4(),
        name=member.name,
        mandate=member.mandate,
        role=member.role,
        visible=member.visible,
        modified_date=datetime.now(tz=UTC),
    )
    db.add(member_db)
    await db.flush()
    return schemas_sdec_facturation.MemberComplete(
        id=member_db.id,
        name=member_db.name,
        mandate=member.mandate,
        role=member.role,
        visible=member.visible,
        modified_date=member_db.modified_date,
    )


async def update_member(
    member_id: uuid.UUID,
    member_edit: schemas_sdec_facturation.MemberBase,
    db: AsyncSession,
):
    """Update a member in the database"""

    await db.execute(
        update(models_sdec_facturation.Member)
        .where(models_sdec_facturation.Member.id == member_id)
        .values(**member_edit.model_dump(), modified_date=datetime.now(tz=UTC)),
    )
    await db.flush()


async def delete_member(
    member_id: uuid.UUID,
    db: AsyncSession,
):
    """Delete a member from the database"""

    await db.execute(
        update(models_sdec_facturation.Member)
        .where(models_sdec_facturation.Member.id == member_id)
        .values(
            visible=False,
        ),
    )
    await db.flush()


async def get_all_members(
    db: AsyncSession,
) -> Sequence[schemas_sdec_facturation.MemberComplete]:
    """Get all members from the database"""
    result = await db.execute(select(models_sdec_facturation.Member))
    members = result.scalars().all()
    return [
        schemas_sdec_facturation.MemberComplete(
            id=member.id,
            name=member.name,
            mandate=member.mandate,
            role=member.role,
            visible=member.visible,
            modified_date=member.modified_date,
        )
        for member in members
    ]


async def get_member_by_id(
    member_id: uuid.UUID,
    db: AsyncSession,
) -> schemas_sdec_facturation.MemberComplete | None:
    """Get a specific member by its ID from the database"""
    result = (
        (
            await db.execute(
                select(models_sdec_facturation.Member).where(
                    models_sdec_facturation.Member.id == member_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_sdec_facturation.MemberComplete(
            id=result.id,
            name=result.name,
            mandate=result.mandate,
            role=result.role,
            visible=result.visible,
            modified_date=result.modified_date,
        )
        if result
        else None
    )


async def get_member_by_name(
    member_name: str,
    db: AsyncSession,
) -> schemas_sdec_facturation.MemberComplete | None:
    """Get a specific member by its name from the database"""
    result = (
        (
            await db.execute(
                select(models_sdec_facturation.Member).where(
                    models_sdec_facturation.Member.name == member_name,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_sdec_facturation.MemberComplete(
            id=result.id,
            name=result.name,
            mandate=result.mandate,
            role=result.role,
            visible=result.visible,
            modified_date=result.modified_date,
        )
        if result
        else None
    )


# ---------------------------------------------------------------------------- #
#                                     Mandat                                  #
# ---------------------------------------------------------------------------- #
async def create_mandate(
    mandate: schemas_sdec_facturation.MandateComplete,
    db: AsyncSession,
) -> schemas_sdec_facturation.MandateComplete:
    """Create a new mandate in the database"""

    mandate_db = models_sdec_facturation.Mandate(
        year=mandate.year,
        name=mandate.name,
    )
    db.add(mandate_db)
    await db.flush()
    return schemas_sdec_facturation.MandateComplete(
        year=mandate_db.year,
        name=mandate_db.name,
    )


async def update_mandate(
    year: int,
    mandate_edit: schemas_sdec_facturation.MandateUpdate,
    db: AsyncSession,
):
    """Update a mandate in the database"""

    await db.execute(
        update(models_sdec_facturation.Mandate)
        .where(models_sdec_facturation.Mandate.year == year)
        .values(
            name=mandate_edit.name,
        ),
    )
    await db.flush()


async def delete_mandate(
    year: int,
    db: AsyncSession,
):
    """Delete a mandate from the database"""

    await db.execute(
        delete(models_sdec_facturation.Mandate).where(
            models_sdec_facturation.Mandate.year == year,
        ),
    )
    await db.flush()


async def get_all_mandates(
    db: AsyncSession,
) -> Sequence[schemas_sdec_facturation.MandateComplete]:
    """Get all mandates from the database"""
    result = await db.execute(select(models_sdec_facturation.Mandate))
    mandats = result.scalars().all()
    return [
        schemas_sdec_facturation.MandateComplete(
            year=mandate.year,
            name=mandate.name,
        )
        for mandate in mandats
    ]


async def get_mandate_by_year(
    year: int,
    db: AsyncSession,
) -> schemas_sdec_facturation.MandateComplete | None:
    """Get a specific mandate by its year from the database"""
    result = (
        (
            await db.execute(
                select(models_sdec_facturation.Mandate).where(
                    models_sdec_facturation.Mandate.year == year,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_sdec_facturation.MandateComplete(
            year=result.year,
            name=result.name,
        )
        if result
        else None
    )


# ---------------------------------------------------------------------------- #
#                                  Associationciation                                 #
# ---------------------------------------------------------------------------- #


async def create_association(
    association: schemas_sdec_facturation.AssociationBase,
    db: AsyncSession,
) -> schemas_sdec_facturation.AssociationComplete:
    """Create a new associationciation in the database"""

    association_db = models_sdec_facturation.Association(
        id=uuid.uuid4(),
        name=association.name,
        type=association.type,
        structure=association.structure,
        modified_date=datetime.now(tz=UTC),
        visible=association.visible,
    )
    db.add(association_db)
    await db.flush()
    return schemas_sdec_facturation.AssociationComplete(
        id=association_db.id,
        name=association_db.name,
        type=association_db.type,
        structure=association_db.structure,
        visible=association_db.visible,
        modified_date=association_db.modified_date,
    )


async def delete_association(
    association_id: uuid.UUID,
    db: AsyncSession,
):
    """Delete an associationciation from the database"""

    await db.execute(
        update(models_sdec_facturation.Association)
        .where(models_sdec_facturation.Association.id == association_id)
        .values(
            visible=False,
        ),
    )
    await db.flush()


async def update_association(
    association_id: uuid.UUID,
    association_edit: schemas_sdec_facturation.AssociationBase,
    db: AsyncSession,
):
    """Update an associationciation in the database"""

    await db.execute(
        update(models_sdec_facturation.Association)
        .where(models_sdec_facturation.Association.id == association_id)
        .values(**association_edit.model_dump(), modified_date=datetime.now(tz=UTC)),
    )
    await db.flush()


async def get_all_associations(
    db: AsyncSession,
) -> Sequence[schemas_sdec_facturation.AssociationComplete]:
    """Get all associationciations from the database"""
    result = await db.execute(select(models_sdec_facturation.Association))
    association = result.scalars().all()
    return [
        schemas_sdec_facturation.AssociationComplete(
            id=association.id,
            name=association.name,
            type=association.type,
            structure=association.structure,
            visible=association.visible,
            modified_date=association.modified_date,
        )
        for association in association
    ]


async def get_association_by_id(
    association_id: uuid.UUID,
    db: AsyncSession,
) -> schemas_sdec_facturation.AssociationComplete | None:
    """Get a specific associationciation by its ID from the database"""
    result = (
        (
            await db.execute(
                select(models_sdec_facturation.Association).where(
                    models_sdec_facturation.Association.id == association_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_sdec_facturation.AssociationComplete(
            id=result.id,
            name=result.name,
            type=result.type,
            structure=result.structure,
            visible=result.visible,
            modified_date=result.modified_date,
        )
        if result
        else None
    )


async def get_association_by_name(
    association_name: str,
    db: AsyncSession,
) -> schemas_sdec_facturation.AssociationComplete | None:
    """Get a specific associationciation by its name from the database"""
    result = (
        (
            await db.execute(
                select(models_sdec_facturation.Association).where(
                    models_sdec_facturation.Association.name == association_name,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_sdec_facturation.AssociationComplete(
            id=result.id,
            name=result.name,
            type=result.type,
            structure=result.structure,
            visible=result.visible,
            modified_date=result.modified_date,
        )
        if result
        else None
    )


# ---------------------------------------------------------------------------- #
#                                     Product                                 #
# ---------------------------------------------------------------------------- #


async def create_product(
    product: schemas_sdec_facturation.ProductBase,
    db: AsyncSession,
) -> schemas_sdec_facturation.ProductComplete:
    """Create a new product in the database"""

    product_db = models_sdec_facturation.Product(
        id=uuid.uuid4(),
        code=product.code,
        name=product.name,
        individual_price=product.individual_price,
        association_price=product.association_price,
        ae_price=product.ae_price,
        category=product.category,
        for_sale=product.for_sale,
        creation_date=datetime.now(tz=UTC),
    )
    db.add(product_db)
    await db.flush()
    return schemas_sdec_facturation.ProductComplete(
        id=product_db.id,
        code=product_db.code,
        name=product_db.name,
        individual_price=product_db.individual_price,
        association_price=product_db.association_price,
        ae_price=product_db.ae_price,
        category=product_db.category,
        for_sale=product_db.for_sale,
        creation_date=product_db.creation_date,
    )


async def update_product(
    product_code: str,
    product_edit: schemas_sdec_facturation.ProductBase,
    db: AsyncSession,
):
    """Update a product in the database"""

    product_db = models_sdec_facturation.Product(
        id=uuid.uuid4(),
        code=product_code,
        name=product_edit.name,
        individual_price=product_edit.individual_price,
        association_price=product_edit.association_price,
        ae_price=product_edit.ae_price,
        category=product_edit.category,
        for_sale=product_edit.for_sale,
        creation_date=datetime.now(tz=UTC),
    )
    db.add(product_db)
    await db.flush()
    return schemas_sdec_facturation.ProductComplete(
        id=product_db.id,
        code=product_db.code,
        name=product_db.name,
        individual_price=product_db.individual_price,
        association_price=product_db.association_price,
        ae_price=product_db.ae_price,
        category=product_db.category,
        for_sale=product_db.for_sale,
        creation_date=product_db.creation_date,
    )


async def minor_update_product(
    product_code: str,
    product_edit: schemas_sdec_facturation.ProductMinorUpdate,
    db: AsyncSession,
):
    """Minor update of a product in the database"""

    update_values = {
        key: value
        for key, value in product_edit.model_dump().items()
        if value is not None
    }

    await db.execute(
        update(models_sdec_facturation.Product)
        .where(models_sdec_facturation.Product.code == product_code)
        .values(**update_values),
    )
    await db.flush()


async def delete_product(
    product_code: str,
    db: AsyncSession,
):
    """Delete a product from the database"""

    await db.execute(
        update(models_sdec_facturation.Product)
        .where(models_sdec_facturation.Product.code == product_code)
        .values(
            for_sale=False,
        ),
    )
    await db.flush()


async def get_all_products(
    db: AsyncSession,
) -> Sequence[schemas_sdec_facturation.ProductComplete]:
    """Get all products from the database"""
    result = await db.execute(select(models_sdec_facturation.Product))
    products = result.scalars().all()
    return [
        schemas_sdec_facturation.ProductComplete(
            id=product.id,
            code=product.code,
            name=product.name,
            individual_price=product.individual_price,
            association_price=product.association_price,
            ae_price=product.ae_price,
            category=product.category,
            for_sale=product.for_sale,
            creation_date=product.creation_date,
        )
        for product in products
    ]


async def get_product_by_id(
    product_id: uuid.UUID,
    db: AsyncSession,
) -> schemas_sdec_facturation.ProductComplete | None:
    """Get a specific product by its ID from the database"""
    result = (
        (
            await db.execute(
                select(models_sdec_facturation.Product).where(
                    models_sdec_facturation.Product.id == product_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_sdec_facturation.ProductComplete(
            id=result.id,
            code=result.code,
            name=result.name,
            individual_price=result.individual_price,
            association_price=result.association_price,
            ae_price=result.ae_price,
            category=result.category,
            for_sale=result.for_sale,
            creation_date=result.creation_date,
        )
        if result
        else None
    )


async def get_product_by_code(
    product_code: str,
    db: AsyncSession,
) -> schemas_sdec_facturation.ProductComplete | None:
    """Get a specific product by its code from the database"""
    result = (
        (
            await db.execute(
                select(models_sdec_facturation.Product).where(
                    models_sdec_facturation.Product.code == product_code,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_sdec_facturation.ProductComplete(
            id=result.id,
            code=result.code,
            name=result.name,
            individual_price=result.individual_price,
            association_price=result.association_price,
            ae_price=result.ae_price,
            category=result.category,
            for_sale=result.for_sale,
            creation_date=result.creation_date,
        )
        if result
        else None
    )


async def get_product_by_name(
    product_name: str,
    db: AsyncSession,
) -> schemas_sdec_facturation.ProductComplete | None:
    """Get a specific product by its name from the database"""
    result = (
        (
            await db.execute(
                select(models_sdec_facturation.Product).where(
                    models_sdec_facturation.Product.name == product_name,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_sdec_facturation.ProductComplete(
            id=result.id,
            code=result.code,
            name=result.name,
            individual_price=result.individual_price,
            association_price=result.association_price,
            ae_price=result.ae_price,
            category=result.category,
            for_sale=result.for_sale,
            creation_date=result.creation_date,
        )
        if result
        else None
    )


# ---------------------------------------------------------------------------- #
#                                   Order                                   #
# ---------------------------------------------------------------------------- #


async def create_order(
    order: schemas_sdec_facturation.OrderBase,
    db: AsyncSession,
) -> schemas_sdec_facturation.OrderComplete:
    """Create a new order in the database"""

    order_db = models_sdec_facturation.Order(
        id=uuid.uuid4(),
        association_id=order.association_id,
        member_id=order.member_id,
        order=order.order,
        creation_date=datetime.now(tz=UTC),
        valid=order.valid,
    )
    db.add(order_db)
    await db.flush()
    return schemas_sdec_facturation.OrderComplete(
        id=order_db.id,
        association_id=order_db.association_id,
        member_id=order_db.member_id,
        order=order_db.order,
        creation_date=order_db.creation_date,
        valid=order_db.valid,
    )


async def update_order(
    order_id: uuid.UUID,
    order_edit: schemas_sdec_facturation.OrderUpdate,
    db: AsyncSession,
):
    """Update an order in the database"""

    await db.execute(
        update(models_sdec_facturation.Order)
        .where(models_sdec_facturation.Order.id == order_id)
        .values(valid=order_edit.valid, order=order_edit.order),
    )
    await db.flush()


async def get_all_orders(
    db: AsyncSession,
) -> Sequence[schemas_sdec_facturation.OrderComplete]:
    """Get all orders from the database"""
    result = await db.execute(select(models_sdec_facturation.Order))
    orders = result.scalars().all()
    return [
        schemas_sdec_facturation.OrderComplete(
            id=order.id,
            association_id=order.association_id,
            member_id=order.member_id,
            order=order.order,
            creation_date=order.creation_date,
            valid=order.valid,
        )
        for order in orders
    ]


async def get_order_by_id(
    order_id: uuid.UUID,
    db: AsyncSession,
) -> schemas_sdec_facturation.OrderComplete | None:
    """Get a specific order by its ID from the database"""
    result = (
        (
            await db.execute(
                select(models_sdec_facturation.Order).where(
                    models_sdec_facturation.Order.id == order_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_sdec_facturation.OrderComplete(
            id=result.id,
            association_id=result.association_id,
            member_id=result.member_id,
            order=result.order,
            creation_date=result.creation_date,
            valid=result.valid,
        )
        if result
        else None
    )


# ---------------------------------------------------------------------------- #
#                                 Facture Association                                #
# ---------------------------------------------------------------------------- #
async def create_facture_association(
    facture_association: schemas_sdec_facturation.FactureAssociationBase,
    db: AsyncSession,
) -> schemas_sdec_facturation.FactureAssociationComplete:
    """Create a new associationciation invoice in the database"""

    facture_association_db = models_sdec_facturation.FactureAssociation(
        id=uuid.uuid4(),
        facture_number=facture_association.facture_number,
        member_id=facture_association.member_id,
        association_id=facture_association.association_id,
        association_order=",".join(
            [str(cmd_id) for cmd_id in facture_association.association_order],
        ),
        price=facture_association.price,
        facture_date=datetime.now(tz=UTC),
        valid=facture_association.valid,
        paid=facture_association.paid,
        payment_date=facture_association.payment_date,
    )
    db.add(facture_association_db)
    await db.flush()
    return schemas_sdec_facturation.FactureAssociationComplete(
        id=facture_association_db.id,
        facture_number=facture_association_db.facture_number,
        member_id=facture_association_db.member_id,
        association_id=facture_association_db.association_id,
        association_order=[
            int(cmd_id)
            for cmd_id in facture_association_db.association_order.split(",")
        ],
        price=facture_association_db.price,
        facture_date=facture_association_db.facture_date,
        valid=facture_association_db.valid,
        paid=facture_association_db.paid,
        payment_date=facture_association_db.payment_date,
    )


async def upfacture_date_association(
    facture_association_id: uuid.UUID,
    facture_association_edit: schemas_sdec_facturation.FactureAssociationBase,
    db: AsyncSession,
):
    """Update an associationciation invoice in the database"""

    await db.execute(
        update(models_sdec_facturation.FactureAssociation)
        .where(models_sdec_facturation.FactureAssociation.id == facture_association_id)
        .values(
            valid=facture_association_edit.valid,
            paid=facture_association_edit.paid,
            payment_date=facture_association_edit.payment_date,
        ),
    )
    await db.flush()


async def get_all_factures_association(
    db: AsyncSession,
) -> Sequence[schemas_sdec_facturation.FactureAssociationComplete]:
    """Get all associationciation invoices from the database"""
    result = await db.execute(select(models_sdec_facturation.FactureAssociation))
    factures_association = result.scalars().all()
    return [
        schemas_sdec_facturation.FactureAssociationComplete(
            id=facture_association.id,
            facture_number=facture_association.facture_number,
            member_id=facture_association.member_id,
            association_id=facture_association.association_id,
            association_order=[
                int(cmd_id)
                for cmd_id in facture_association.association_order.split(",")
            ],
            price=facture_association.price,
            facture_date=facture_association.facture_date,
            valid=facture_association.valid,
            paid=facture_association.paid,
            payment_date=facture_association.payment_date,
        )
        for facture_association in factures_association
    ]


async def get_facture_association_by_id(
    facture_association_id: uuid.UUID,
    db: AsyncSession,
) -> schemas_sdec_facturation.FactureAssociationComplete | None:
    """Get a specific associationciation invoice by its ID from the database"""
    result = (
        (
            await db.execute(
                select(models_sdec_facturation.FactureAssociation).where(
                    models_sdec_facturation.FactureAssociation.id
                    == facture_association_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_sdec_facturation.FactureAssociationComplete(
            id=result.id,
            facture_number=result.facture_number,
            member_id=result.member_id,
            association_id=result.association_id,
            association_order=[
                int(cmd_id) for cmd_id in result.association_order.split(",")
            ],
            price=result.price,
            facture_date=result.facture_date,
            valid=result.valid,
            paid=result.paid,
            payment_date=result.payment_date,
        )
        if result
        else None
    )


# ---------------------------------------------------------------------------- #
#                               Facture Individual                             #
# ---------------------------------------------------------------------------- #
async def create_facture_particulier(
    facture_particulier: schemas_sdec_facturation.FactureIndividualBase,
    db: AsyncSession,
) -> schemas_sdec_facturation.FactureIndividualComplete:
    """Create a new individual invoice in the database"""

    facture_particulier_db = models_sdec_facturation.FactureIndividual(
        id=uuid.uuid4(),
        facture_number=facture_particulier.facture_number,
        member_id=facture_particulier.member_id,
        individual_order=facture_particulier.individual_order,
        individual_category=facture_particulier.individual_category,
        price=facture_particulier.price,
        facture_date=datetime.now(tz=UTC),
        firstname=facture_particulier.firstname,
        lastname=facture_particulier.lastname,
        adresse=facture_particulier.adresse,
        postal_code=facture_particulier.postal_code,
        city=facture_particulier.city,
        country=facture_particulier.country,
        valid=facture_particulier.valid,
        paid=facture_particulier.paid,
        payment_date=facture_particulier.payment_date,
    )
    db.add(facture_particulier_db)
    await db.flush()
    return schemas_sdec_facturation.FactureIndividualComplete(
        id=facture_particulier_db.id,
        facture_number=facture_particulier_db.facture_number,
        member_id=facture_particulier_db.member_id,
        individual_order=facture_particulier_db.individual_order,
        individual_category=facture_particulier_db.individual_category,
        price=facture_particulier_db.price,
        facture_date=facture_particulier_db.facture_date,
        firstname=facture_particulier_db.firstname,
        lastname=facture_particulier_db.lastname,
        adresse=facture_particulier_db.adresse,
        postal_code=facture_particulier_db.postal_code,
        city=facture_particulier_db.city,
        country=facture_particulier_db.country,
        valid=facture_particulier_db.valid,
        paid=facture_particulier_db.paid,
        payment_date=facture_particulier_db.payment_date,
    )


async def up_date_facture_particulier(
    facture_particulier_id: uuid.UUID,
    facture_particulier_edit: schemas_sdec_facturation.FactureIndividualBase,
    db: AsyncSession,
):
    """Update an individual invoice in the database"""

    await db.execute(
        update(models_sdec_facturation.FactureIndividual)
        .where(models_sdec_facturation.FactureIndividual.id == facture_particulier_id)
        .values(
            firstname=facture_particulier_edit.firstname,
            lastname=facture_particulier_edit.lastname,
            adresse=facture_particulier_edit.adresse,
            postal_code=facture_particulier_edit.postal_code,
            city=facture_particulier_edit.city,
            valid=facture_particulier_edit.valid,
            paid=facture_particulier_edit.paid,
            payment_date=facture_particulier_edit.payment_date,
        ),
    )
    await db.flush()


async def get_all_factures_particulier(
    db: AsyncSession,
) -> Sequence[schemas_sdec_facturation.FactureIndividualComplete]:
    """Get all individual invoices from the database"""
    result = await db.execute(select(models_sdec_facturation.FactureIndividual))
    factures_particulier = result.scalars().all()
    return [
        schemas_sdec_facturation.FactureIndividualComplete(
            id=facture_particulier.id,
            facture_number=facture_particulier.facture_number,
            member_id=facture_particulier.member_id,
            individual_order=facture_particulier.individual_order,
            individual_category=facture_particulier.individual_category,
            price=facture_particulier.price,
            facture_date=facture_particulier.facture_date,
            firstname=facture_particulier.firstname,
            lastname=facture_particulier.lastname,
            adresse=facture_particulier.adresse,
            postal_code=facture_particulier.postal_code,
            city=facture_particulier.city,
            country=facture_particulier.country,
            valid=facture_particulier.valid,
            paid=facture_particulier.paid,
            payment_date=facture_particulier.payment_date,
        )
        for facture_particulier in factures_particulier
    ]


async def get_facture_particulier_by_id(
    facture_particulier_id: uuid.UUID,
    db: AsyncSession,
) -> schemas_sdec_facturation.FactureIndividualComplete | None:
    """Get a specific individual invoice by its ID from the database"""
    result = (
        (
            await db.execute(
                select(models_sdec_facturation.FactureIndividual).where(
                    models_sdec_facturation.FactureIndividual.id
                    == facture_particulier_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_sdec_facturation.FactureIndividualComplete(
            id=result.id,
            facture_number=result.facture_number,
            member_id=result.member_id,
            individual_order=result.individual_order,
            individual_category=result.individual_category,
            price=result.price,
            facture_date=result.facture_date,
            firstname=result.firstname,
            lastname=result.lastname,
            adresse=result.adresse,
            postal_code=result.postal_code,
            city=result.city,
            country=result.country,
            valid=result.valid,
            paid=result.paid,
            payment_date=result.payment_date,
        )
        if result
        else None
    )
