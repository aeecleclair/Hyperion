import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

import xlsxwriter
from fastapi import (
    HTTPException,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.groups_type import GroupType
from app.core.payment import schemas_payment
from app.core.users import models_users
from app.dependencies import (
    hyperion_access_logger,
)
from app.modules.cdr import coredata_cdr, cruds_cdr, models_cdr
from app.modules.cdr.types_cdr import CdrLogActionType, PaymentType
from app.utils.tools import get_core_data, is_user_member_of_any_group

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

    # Retrieve current CDR year from core data instead of requiring it as a dependency
    cdr_year = await get_core_data(coredata_cdr.CdrYear, db)

    db_payment = models_cdr.Payment(
        id=uuid4(),
        user_id=checkout.user_id,
        total=paid_amount,
        payment_type=PaymentType.helloasso,
        year=cdr_year.year,
    )
    db_action = models_cdr.CdrAction(
        id=uuid4(),
        subject_id=checkout.user_id,
        action_type=CdrLogActionType.payment_add,
        action=str(checkout_payment.__dict__),
        timestamp=datetime.now(UTC),
    )

    cruds_cdr.create_payment(db=db, payment=db_payment)
    cruds_cdr.create_action(db=db, action=db_action)
    await db.flush()


async def is_user_in_a_seller_group(
    seller_id: UUID,
    user: models_users.CoreUser,
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

    if is_user_member_of_any_group(
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
    users: list[models_users.CoreUser],
    products: list[models_cdr.CdrProduct],
    variants: list[models_cdr.ProductVariant],
    data_fields: dict[UUID, list[models_cdr.CustomDataField]],
    export_path: str,
):
    variants_by_product = {}
    for v in variants:
        variants_by_product.setdefault(v.product_id, []).append(v)

    fixed_columns = ["Nom", "Prénom", "Surnom", "Email"]
    col_idx = len(fixed_columns)

    product_structure = []
    for product in products:
        product_variants = variants_by_product.get(product.id, [])
        fields = data_fields.get(product.id, [])
        needs_validation = getattr(product, "needs_validation", True)

        variants_info = []
        for variant in product_variants:
            qty_col = col_idx
            col_idx += 1
            valid_col = None
            if needs_validation:
                valid_col = col_idx
                col_idx += 1
            variants_info.append(
                {
                    "variant": variant,
                    "qty_col": qty_col,
                    "valid_col": valid_col,
                },
            )

        custom_cols = list(range(col_idx, col_idx + len(fields)))
        col_idx += len(fields)

        product_structure.append(
            {
                "product": product,
                "variants_info": variants_info,
                "fields": fields,
                "custom_cols": custom_cols,
                "needs_validation": needs_validation,
            },
        )

    users_to_write = []
    for user in users:
        purchases = users_purchases.get(user.id, [])
        if any(p.quantity > 0 for p in purchases):
            users_to_write.append(user)

    data_rows = []
    for user in users_to_write:
        row = [""] * col_idx
        row[0] = user.name
        row[1] = user.firstname
        row[2] = user.nickname
        row[3] = user.email

        answers = users_answers.get(user.id, [])
        answers_map = {a.field_id: a.value for a in answers}
        purchases_map = {
            p.product_variant_id: p for p in users_purchases.get(user.id, [])
        }

        for prod_struct in product_structure:
            for vinfo in prod_struct["variants_info"]:
                p = purchases_map.get(vinfo["variant"].id, None)
                row[vinfo["qty_col"]] = p.quantity if p and p.quantity > 0 else ""
                if prod_struct["needs_validation"] and vinfo["valid_col"] is not None:
                    row[vinfo["valid_col"]] = (
                        ("OUI" if p.validated else "NON")
                        if p and p.quantity > 0
                        else ""
                    )

            for field, ccol in zip(
                prod_struct["fields"],
                prod_struct["custom_cols"],
                strict=False,
            ):
                row[ccol] = answers_map.get(field.id, "")

        data_rows.append(row)

    workbook = xlsxwriter.Workbook(export_path)
    worksheet = workbook.add_worksheet("Ventes")

    header_fmt = workbook.add_format(
        {
            "bold": True,
            "font_name": "Raleway",
            "font_color": "white",
            "bg_color": "#0D47A1",
            "align": "center",
            "valign": "vcenter",
        },
    )

    oui_fmt = workbook.add_format(
        {
            "font_color": "green",
            "bold": True,
            "align": "center",
            "font_name": "Raleway",
        },
    )

    non_fmt = workbook.add_format(
        {
            "font_color": "red",
            "bold": True,
            "align": "center",
            "font_name": "Raleway",
        },
    )

    center_fmt = workbook.add_format(
        {
            "align": "center",
            "font_name": "Raleway",
        },
    )

    # Fine right border (for variant separation)
    center_fmt_right_border = workbook.add_format(
        {
            "align": "center",
            "right": 1,
            "font_name": "Raleway",
        },
    )

    # Thick right border (for product separation)
    center_fmt_thick_border = workbook.add_format(
        {
            "align": "center",
            "right": 2,  # 2 = épaisse
            "font_name": "Raleway",
        },
    )

    # Versions pour OUI/NON
    oui_fmt_thick = workbook.add_format(
        {
            "font_color": "green",
            "bold": True,
            "align": "center",
            "font_name": "Raleway",
            "right": 2,
        },
    )
    non_fmt_thick = workbook.add_format(
        {
            "font_color": "red",
            "bold": True,
            "align": "center",
            "font_name": "Raleway",
            "right": 2,
        },
    )

    # Versions pour OUI/NON
    oui_fmt_right = workbook.add_format(
        {
            "font_color": "green",
            "bold": True,
            "align": "center",
            "font_name": "Raleway",
            "right": 1,
        },
    )
    non_fmt_right = workbook.add_format(
        {
            "font_color": "red",
            "bold": True,
            "align": "center",
            "font_name": "Raleway",
            "right": 1,
        },
    )

    # Pour cellule normale avec ligne épaisse en bas
    center_fmt_bottom_border = workbook.add_format(
        {
            "align": "center",
            "font_name": "Raleway",
            "bottom": 2,
        },
    )

    # Variante avec bordure droite fine (variante + ligne)
    center_fmt_right_bottom_border = workbook.add_format(
        {
            "align": "center",
            "font_name": "Raleway",
            "right": 1,
            "bottom": 2,
        },
    )

    # Variante avec bordure droite épaisse (produit + ligne)
    center_fmt_thick_right_bottom_border = workbook.add_format(
        {
            "align": "center",
            "font_name": "Raleway",
            "right": 2,
            "bottom": 2,
        },
    )

    # OUI / NON avec ligne épaisse en bas
    oui_fmt_bottom = workbook.add_format(
        {
            "font_color": "green",
            "bold": True,
            "align": "center",
            "font_name": "Raleway",
            "bottom": 2,
        },
    )
    non_fmt_bottom = workbook.add_format(
        {
            "font_color": "red",
            "bold": True,
            "align": "center",
            "font_name": "Raleway",
            "bottom": 2,
        },
    )
    # Avec bordure droite
    oui_fmt_thick_bottom = workbook.add_format(
        {
            "font_color": "green",
            "bold": True,
            "align": "center",
            "font_name": "Raleway",
            "right": 2,
            "bottom": 2,
        },
    )
    non_fmt_thick_bottom = workbook.add_format(
        {
            "font_color": "red",
            "bold": True,
            "align": "center",
            "font_name": "Raleway",
            "right": 2,
            "bottom": 2,
        },
    )

    for col, title in enumerate(fixed_columns):
        worksheet.merge_range(0, col, 2, col, title, header_fmt)

    max_lens = [len(c) for c in fixed_columns] + [0] * (col_idx - len(fixed_columns))

    product_end_cols = [
        len(fixed_columns) - 1,
    ]  # Colonnes après lesquelles on mettra une bordure épaisse
    variant_end_cols = set()  # Colonnes après lesquelles on mettra une bordure fine

    for prod_struct in product_structure:
        product = prod_struct["product"]
        variants_info = prod_struct["variants_info"]
        fields = prod_struct["fields"]
        custom_cols = prod_struct["custom_cols"]
        needs_validation = prod_struct["needs_validation"]

        if variants_info:
            start_col = variants_info[0]["qty_col"]
            end_col = (
                variants_info[-1]["valid_col"]
                if (needs_validation and variants_info[-1]["valid_col"] is not None)
                else variants_info[-1]["qty_col"]
            )
        elif custom_cols:
            start_col = custom_cols[0]
        else:
            continue
        if custom_cols:
            end_col = custom_cols[-1]

        if start_col < end_col:
            worksheet.merge_range(0, start_col, 0, end_col, product.name_fr, header_fmt)
        else:
            worksheet.write(0, start_col, product.name_fr, header_fmt)

        product_end_cols.append(end_col)

        for vinfo in variants_info:
            qty_col = vinfo["qty_col"]
            if needs_validation:
                worksheet.merge_range(
                    1, qty_col, 1, qty_col + 1, vinfo["variant"].name_fr, header_fmt,
                )
            else:
                worksheet.write(1, qty_col, vinfo["variant"].name_fr, header_fmt)

            if needs_validation and vinfo["valid_col"] is not None:
                variant_end_cols.add(vinfo["valid_col"])
            else:
                variant_end_cols.add(vinfo["qty_col"])

        if custom_cols:
            if len(custom_cols) > 1:
                worksheet.merge_range(
                    1,
                    custom_cols[0],
                    1,
                    custom_cols[-1],
                    "Informations complémentaires",
                    header_fmt,
                )
            else:
                worksheet.write(
                    1, custom_cols[0], "Informations complémentaires", header_fmt,
                )

            info_comp_len = len("Informations complémentaires")
            for c in range(custom_cols[0], custom_cols[-1] + 1):
                max_lens[c] = max(max_lens[c], info_comp_len)

        for vinfo in variants_info:
            worksheet.write(2, vinfo["qty_col"], "Quantité", header_fmt)
            max_lens[vinfo["qty_col"]] = max(
                max_lens[vinfo["qty_col"]],
                len(vinfo["variant"].name_fr),
            )
            if needs_validation and vinfo["valid_col"] is not None:
                worksheet.write(2, vinfo["valid_col"], "Validé", header_fmt)
                max_lens[vinfo["valid_col"]] = max(
                    max_lens[vinfo["valid_col"]],
                    len("Validé"),
                )

        for i, field in enumerate(fields):
            worksheet.write(2, custom_cols[i], field.name, header_fmt)
            max_lens[custom_cols[i]] = max(max_lens[custom_cols[i]], len(field.name))

        for c in range(start_col, end_col + 1):
            max_lens[c] = max(max_lens[c], len(product.name_fr))

    start_row = 3
    for row_idx, row in enumerate(data_rows, start=start_row):
        apply_bottom_border = row_idx == start_row + len(data_rows) - 1 or row_idx == 2
        for col_idx_data, val in enumerate(row):
            if col_idx_data in product_end_cols:
                if val == "OUI":
                    cell_fmt = (
                        oui_fmt_thick_bottom if apply_bottom_border else oui_fmt_thick
                    )
                elif val == "NON":
                    cell_fmt = (
                        non_fmt_thick_bottom if apply_bottom_border else non_fmt_thick
                    )
                else:
                    cell_fmt = (
                        center_fmt_thick_right_bottom_border
                        if apply_bottom_border
                        else center_fmt_thick_border
                    )
            elif col_idx_data in variant_end_cols:
                if val == "OUI":
                    cell_fmt = oui_fmt_bottom if apply_bottom_border else oui_fmt_right
                elif val == "NON":
                    cell_fmt = non_fmt_bottom if apply_bottom_border else non_fmt_right
                else:
                    cell_fmt = (
                        center_fmt_right_bottom_border
                        if apply_bottom_border
                        else center_fmt_right_border
                    )
            elif val == "OUI":
                cell_fmt = oui_fmt_bottom if apply_bottom_border else oui_fmt
            elif val == "NON":
                cell_fmt = non_fmt_bottom if apply_bottom_border else non_fmt
            else:
                cell_fmt = (
                    center_fmt_bottom_border if apply_bottom_border else center_fmt
                )

            worksheet.write(row_idx, col_idx_data, val, cell_fmt)

            max_lens[col_idx_data] = max(max_lens[col_idx_data], len(str(val)))

    for i, length in enumerate(max_lens):
        worksheet.set_column(i, i, length + 3)

    worksheet.freeze_panes(3, len(fixed_columns))
    workbook.close()
