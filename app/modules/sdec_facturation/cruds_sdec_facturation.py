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
#                                     Mandate                                  #
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
#                                  Association                                 #
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
        modified_date=association_db.modified_date,
        visible=association_db.visible,
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
    product: schemas_sdec_facturation.ProductAndPriceBase,
    db: AsyncSession,
) -> schemas_sdec_facturation.ProductAndPriceComplete:
    """Create a new product in the database"""

    product_db = models_sdec_facturation.Product(
        id=uuid.uuid4(),
        code=product.code,
        name=product.name,
        category=product.category,
        for_sale=product.for_sale,
        creation_date=datetime.now(tz=UTC),
    )
    db.add(product_db)
    await db.flush()

    price_db = models_sdec_facturation.ProductPrice(
        id=uuid.uuid4(),
        product_id=product_db.id,
        individual_price=product.individual_price,
        association_price=product.association_price,
        ae_price=product.ae_price,
        effective_date=datetime.now(tz=UTC),
    )
    db.add(price_db)
    await db.flush()
    return schemas_sdec_facturation.ProductAndPriceComplete(
        id=product_db.id,
        code=product_db.code,
        name=product_db.name,
        individual_price=price_db.individual_price,
        association_price=price_db.association_price,
        ae_price=price_db.ae_price,
        category=product_db.category,
        for_sale=product_db.for_sale,
        creation_date=product_db.creation_date,
        effective_date=price_db.effective_date,
    )


async def update_product(
    product_id: uuid.UUID,
    product_edit: schemas_sdec_facturation.ProductUpdate,
    db: AsyncSession,
):
    """Update a product in the database"""

    update_values = {
        key: value
        for key, value in product_edit.model_dump().items()
        if value is not None
    }
    await db.execute(
        update(models_sdec_facturation.Product)
        .where(models_sdec_facturation.Product.id == product_id)
        .values(**update_values),
    )
    await db.flush()


async def create_price(
    product_id: uuid.UUID,
    price_edit: schemas_sdec_facturation.ProductPriceUpdate,
    db: AsyncSession,
) -> schemas_sdec_facturation.ProductPriceComplete:
    """Minor update of a product in the database"""

    price_db = models_sdec_facturation.ProductPrice(
        id=uuid.uuid4(),
        product_id=product_id,
        individual_price=price_edit.individual_price,
        association_price=price_edit.association_price,
        ae_price=price_edit.ae_price,
        effective_date=datetime.now(tz=UTC),
    )

    db.add(price_db)
    await db.flush()

    return schemas_sdec_facturation.ProductPriceComplete(
        id=price_db.id,
        product_id=price_db.product_id,
        individual_price=price_db.individual_price,
        association_price=price_db.association_price,
        ae_price=price_db.ae_price,
        effective_date=price_db.effective_date,
    )


async def update_price(
    product_id: uuid.UUID,
    price_edit: schemas_sdec_facturation.ProductPriceUpdate,
    db: AsyncSession,
):
    """Update the price of a product in the database"""
    current_date = datetime.now(tz=UTC)
    await db.execute(
        update(models_sdec_facturation.ProductPrice)
        .where(models_sdec_facturation.ProductPrice.id == product_id)
        .where(models_sdec_facturation.ProductPrice.effective_date == current_date)
        .values(**price_edit.model_dump()),
    )
    await db.flush()


async def delete_product(
    product_id: uuid.UUID,
    db: AsyncSession,
):
    """Delete a product from the database"""

    await db.execute(
        update(models_sdec_facturation.Product)
        .where(models_sdec_facturation.Product.id == product_id)
        .values(
            for_sale=False,
        ),
    )
    await db.flush()


async def get_all_products_and_price(
    db: AsyncSession,
) -> Sequence[schemas_sdec_facturation.ProductAndPriceComplete]:
    """Get all products from the database"""

    query = select(
        models_sdec_facturation.Product,
        models_sdec_facturation.ProductPrice,
    ).outerjoin(
        models_sdec_facturation.ProductPrice,
        models_sdec_facturation.Product.id
        == models_sdec_facturation.ProductPrice.product_id,
    )
    result = await db.execute(query)
    rows = result.all()  # list of (Product, ProductPrice|None)

    products = []
    for product, product_price in rows:
        individual_price = product_price.individual_price if product_price else 0.0
        association_price = product_price.association_price if product_price else 0.0
        ae_price = product_price.ae_price if product_price else 0.0

        products.append(
            schemas_sdec_facturation.ProductAndPriceComplete(
                id=product.id,
                code=product.code,
                name=product.name,
                individual_price=individual_price,
                association_price=association_price,
                ae_price=ae_price,
                category=product.category,
                for_sale=product.for_sale,
                creation_date=product.creation_date,
                effective_date=product_price.effective_date if product_price else None,
            ),
        )

    return [
        schemas_sdec_facturation.ProductAndPriceComplete(
            id=product.id,
            code=product.code,
            name=product.name,
            individual_price=product.individual_price,
            association_price=product.association_price,
            ae_price=product.ae_price,
            category=product.category,
            for_sale=product.for_sale,
            creation_date=product.creation_date,
            effective_date=product_price.effective_date,
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
            category=result.category,
            for_sale=result.for_sale,
            creation_date=result.creation_date,
        )
        if result
        else None
    )


async def get_prices_by_product_id_and_date(
    product_id: uuid.UUID,
    db: AsyncSession,
) -> schemas_sdec_facturation.ProductPriceComplete | None:
    """Get the price of a product by its ID and a specific date from the database"""
    date = datetime.now(tz=UTC)
    result = (
        (
            await db.execute(
                select(models_sdec_facturation.ProductPrice)
                .where(models_sdec_facturation.ProductPrice.product_id == product_id)
                .where(models_sdec_facturation.ProductPrice.effective_date == date),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_sdec_facturation.ProductPriceComplete(
            id=result.id,
            product_id=result.product_id,
            individual_price=result.individual_price,
            association_price=result.association_price,
            ae_price=result.ae_price,
            effective_date=result.effective_date,
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
        .values(order=order_edit.order),
    )
    await db.flush()


async def delete_order(
    order_id: uuid.UUID,
    db: AsyncSession,
):
    """Delete an order from the database"""

    await db.execute(
        update(models_sdec_facturation.Order)
        .where(models_sdec_facturation.Order.id == order_id)
        .values(valid=False),
    )


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
        start_date=facture_association.start_date,
        end_date=facture_association.end_date,
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
        start_date=facture_association.start_date,
        end_date=facture_association.end_date,
        price=facture_association_db.price,
        facture_date=facture_association_db.facture_date,
        valid=facture_association_db.valid,
        paid=facture_association_db.paid,
        payment_date=facture_association_db.payment_date,
    )


async def update_facture_association(
    facture_association_id: uuid.UUID,
    facture_association_edit: schemas_sdec_facturation.FactureAssociationUpdate,
    db: AsyncSession,
):
    """Update an associationciation invoice in the database"""
    current_date: datetime | None = datetime.now(tz=UTC)
    if not facture_association_edit.paid:
        current_date = None

    await db.execute(
        update(models_sdec_facturation.FactureAssociation)
        .where(models_sdec_facturation.FactureAssociation.id == facture_association_id)
        .values(
            paid=facture_association_edit.paid,
            payment_date=current_date,
        ),
    )
    await db.flush()


async def delete_facture_association(
    facture_association_id: uuid.UUID,
    db: AsyncSession,
):
    """Delete an associationciation invoice from the database"""

    await db.execute(
        update(models_sdec_facturation.FactureAssociation)
        .where(models_sdec_facturation.FactureAssociation.id == facture_association_id)
        .values(valid=False),
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
            start_date=facture_association.start_date,
            end_date=facture_association.end_date,
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
            start_date=result.start_date,
            end_date=result.end_date,
            price=result.price,
            facture_date=result.facture_date,
            valid=result.valid,
            paid=result.paid,
            payment_date=result.payment_date,
        )
        if result
        else None
    )


async def get_facture_association_by_number(
    facture_number: str,
    db: AsyncSession,
) -> schemas_sdec_facturation.FactureAssociationComplete | None:
    """Get specific associationciation invoices by their facture number from the database"""
    result = (
        (
            await db.execute(
                select(models_sdec_facturation.FactureAssociation).where(
                    models_sdec_facturation.FactureAssociation.facture_number
                    == facture_number,
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
            start_date=result.start_date,
            end_date=result.end_date,
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
async def create_facture_individual(
    facture_individual: schemas_sdec_facturation.FactureIndividualBase,
    db: AsyncSession,
) -> schemas_sdec_facturation.FactureIndividualComplete:
    """Create a new individual invoice in the database"""

    facture_individual_db = models_sdec_facturation.FactureIndividual(
        id=uuid.uuid4(),
        facture_number=facture_individual.facture_number,
        member_id=facture_individual.member_id,
        individual_order=facture_individual.individual_order,
        individual_category=facture_individual.individual_category,
        price=facture_individual.price,
        facture_date=datetime.now(tz=UTC),
        firstname=facture_individual.firstname,
        lastname=facture_individual.lastname,
        adresse=facture_individual.adresse,
        postal_code=facture_individual.postal_code,
        city=facture_individual.city,
        country=facture_individual.country,
    )
    db.add(facture_individual_db)
    await db.flush()
    return schemas_sdec_facturation.FactureIndividualComplete(
        id=facture_individual_db.id,
        facture_number=facture_individual_db.facture_number,
        member_id=facture_individual_db.member_id,
        individual_order=facture_individual_db.individual_order,
        individual_category=facture_individual_db.individual_category,
        price=facture_individual_db.price,
        facture_date=facture_individual_db.facture_date,
        firstname=facture_individual_db.firstname,
        lastname=facture_individual_db.lastname,
        adresse=facture_individual_db.adresse,
        postal_code=facture_individual_db.postal_code,
        city=facture_individual_db.city,
        country=facture_individual_db.country,
        valid=facture_individual_db.valid,
        paid=facture_individual_db.paid,
        payment_date=facture_individual_db.payment_date,
    )


async def update_facture_individual(
    facture_individual_id: uuid.UUID,
    facture_individual_edit: schemas_sdec_facturation.FactureIndividualUpdate,
    db: AsyncSession,
):
    """Update an individual invoice in the database"""
    current_date: datetime | None = datetime.now(tz=UTC)
    if not facture_individual_edit.paid:
        current_date = None

    await db.execute(
        update(models_sdec_facturation.FactureIndividual)
        .where(models_sdec_facturation.FactureIndividual.id == facture_individual_id)
        .values(
            firstname=facture_individual_edit.firstname,
            lastname=facture_individual_edit.lastname,
            adresse=facture_individual_edit.adresse,
            postal_code=facture_individual_edit.postal_code,
            city=facture_individual_edit.city,
            paid=facture_individual_edit.paid,
            payment_date=current_date,
        ),
    )
    await db.flush()


async def delete_facture_individual(
    facture_individual_id: uuid.UUID,
    db: AsyncSession,
):
    """Delete an individual invoice from the database"""

    await db.execute(
        update(models_sdec_facturation.FactureIndividual)
        .where(models_sdec_facturation.FactureIndividual.id == facture_individual_id)
        .values(valid=False),
    )
    await db.flush()


async def get_all_factures_individual(
    db: AsyncSession,
) -> Sequence[schemas_sdec_facturation.FactureIndividualComplete]:
    """Get all individual invoices from the database"""
    result = await db.execute(select(models_sdec_facturation.FactureIndividual))
    factures_individual = result.scalars().all()
    return [
        schemas_sdec_facturation.FactureIndividualComplete(
            id=facture_individual.id,
            facture_number=facture_individual.facture_number,
            member_id=facture_individual.member_id,
            individual_order=facture_individual.individual_order,
            individual_category=facture_individual.individual_category,
            price=facture_individual.price,
            facture_date=facture_individual.facture_date,
            firstname=facture_individual.firstname,
            lastname=facture_individual.lastname,
            adresse=facture_individual.adresse,
            postal_code=facture_individual.postal_code,
            city=facture_individual.city,
            country=facture_individual.country,
            valid=facture_individual.valid,
            paid=facture_individual.paid,
            payment_date=facture_individual.payment_date,
        )
        for facture_individual in factures_individual
    ]


async def get_facture_individual_by_id(
    facture_individual_id: uuid.UUID,
    db: AsyncSession,
) -> schemas_sdec_facturation.FactureIndividualComplete | None:
    """Get a specific individual invoice by its ID from the database"""
    result = (
        (
            await db.execute(
                select(models_sdec_facturation.FactureIndividual).where(
                    models_sdec_facturation.FactureIndividual.id
                    == facture_individual_id,
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


async def get_facture_individual_by_number(
    facture_number: str,
    db: AsyncSession,
) -> schemas_sdec_facturation.FactureIndividualComplete | None:
    """Get specific individual invoices by their facture number from the database"""
    result = (
        (
            await db.execute(
                select(models_sdec_facturation.FactureIndividual).where(
                    models_sdec_facturation.FactureIndividual.facture_number
                    == facture_number,
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
