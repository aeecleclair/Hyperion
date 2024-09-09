import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pandas as pd
from fastapi import (
    HTTPException,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core
from app.core.groups.groups_type import GroupType
from app.core.payment import schemas_payment
from app.dependencies import (
    hyperion_access_logger,
)
from app.modules.cdr import cruds_cdr, models_cdr
from app.modules.cdr.types_cdr import (
    CdrLogActionType,
    PaymentType,
)
from app.utils.tools import (
    is_user_member_of_an_allowed_group,
)

hyperion_error_logger = logging.getLogger("hyperion.error")


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
        subject_id=checkout.user_id,
        action_type=CdrLogActionType.payment_add,
        action=str(checkout_payment.__dict__),
        timestamp=datetime.now(UTC),
    )
    try:
        cruds_cdr.create_payment(db=db, payment=db_payment)
        cruds_cdr.create_action(db=db, action=db_action)
        await db.commit()
    except Exception:
        await db.rollback()
        raise


async def is_user_in_a_seller_group(
    seller_id: UUID,
    user: models_core.CoreUser,
    db: AsyncSession,
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
        "Is_user_a_member_of: Unauthorized, user is not a seller",
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


def construct_dataframe_from_users_purchases(
    users_purchases: dict[str, list[models_cdr.Purchase]],
    users_answers: dict[str, list[models_cdr.CustomData]],
    users: list[models_core.CoreUser],
    products: list[models_cdr.CdrProduct],
    variants: list[models_cdr.ProductVariant],
    data_fields: dict[UUID, list[models_cdr.CustomDataField]],
) -> pd.DataFrame:
    """
    Construct a pandas DataFrame from a dict of users purchases.

    Args:
        users_purchases (dict[str, list[models_cdr.Purchase]]): A dict of users purchases.

    Returns:
        pd.DataFrame: A pandas DataFrame.
    """
    columns = ["Nom", "Prénom", "Surnom", "Email"]
    data = ["", "", "", "Prix"]
    field_to_column = {}
    variant_to_column = {}
    for product in products:
        product_variants = [
            variant for variant in variants if variant.product_id == product.id
        ]
        columns.extend(
            [f"{product.name_fr} : {variant.name_fr}" for variant in product_variants],
        )
        fields = data_fields.get(product.id, [])
        columns.extend(
            [f"{product.name_fr} : {field.name}" for field in fields],
        )
        data.extend([str(variant.price) for variant in product_variants])

        data.extend([" " for _ in fields])
        field_to_column.update(
            {field.id: f"{product.name_fr} : {field.name}" for field in fields},
        )
        variant_to_column.update(
            {
                variant.id: f"{product.name_fr} : {variant.name_fr}"
                for variant in product_variants
            },
        )
    columns.append("Panier payé")
    data.append(" ")
    columns.append("Commentaire")
    data.append(" ")
    df = pd.DataFrame(
        columns=columns,
    )
    df = pd.concat(
        [
            df,
            pd.DataFrame(
                data=[data],
                columns=columns,
            ),
        ],
    )
    for user_id, purchases in users_purchases.items():
        for purchase in purchases:
            df.loc[
                user_id,
                variant_to_column[purchase.product_variant_id],
            ] = purchase.quantity

    for user_id, answers in users_answers.items():
        for answer in answers:
            column = field_to_column.get(answer.field_id)
            if column:
                df.loc[
                    user_id,
                    field_to_column[answer.field_id],
                ] = answer.value

    for user_id in df.index:
        user = next((u for u in users if u.id == user_id), None)
        if user is None:
            continue
        df.loc[user_id, "Nom"] = user.name
        df.loc[user_id, "Prénom"] = user.firstname
        df.loc[user_id, "Surnom"] = user.nickname
        df.loc[user_id, "Email"] = user.email
        if all(purchase.validated for purchase in users_purchases[user_id]):
            df.loc[user_id, "Panier payé"] = True
        else:
            df.loc[user_id, "Panier payé"] = False
            df.loc[user_id, "Commentaire"] = "Manquant : \n-" + "\n-".join(
                variant_to_column[purchase.product_variant_id]
                for purchase in users_purchases[user_id]
                if not purchase.validated
            )
    df.fillna("", inplace=True)
    return df
