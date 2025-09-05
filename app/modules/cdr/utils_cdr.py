import logging
from datetime import UTC, datetime
from io import BytesIO
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


def generate_format(workbook: xlsxwriter.Workbook):
    def make_format(
        workbook,
        *,
        color=None,
        bold=False,
        align="center",
        font="Raleway",
        right=None,
        left=None,
        bottom=None,
        bg_color=None,
        font_color=None,
    ):
        fmt_dict = {
            "align": align,
            "font_name": font,
        }
        if color:
            fmt_dict["font_color"] = color
        if font_color:
            fmt_dict["font_color"] = font_color
        if bg_color:
            fmt_dict["bg_color"] = bg_color
        if bold:
            fmt_dict["bold"] = True
        if right is not None:
            fmt_dict["right"] = right
        if left is not None:
            fmt_dict["right"] = left
        if bottom is not None:
            fmt_dict["bottom"] = bottom
        return workbook.add_format(fmt_dict)

    return {
        "header": {
            "base": make_format(
                workbook,
                bold=True,
                font_color="white",
                bg_color="#0D47A1",
            ),
            "right": make_format(
                workbook,
                bold=True,
                font_color="white",
                bg_color="#0D47A1",
                right=1,
            ),
            "left": make_format(
                workbook,
                bold=True,
                font_color="white",
                bg_color="#0D47A1",
                left=1,
            ),
            "left_right": make_format(
                workbook,
                bold=True,
                font_color="white",
                bg_color="#0D47A1",
                right=1,
                left=1,
            ),
            "right_thick": make_format(
                workbook,
                bold=True,
                font_color="white",
                bg_color="#0D47A1",
                right=2,
            ),
            "left_thick": make_format(
                workbook,
                bold=True,
                font_color="white",
                bg_color="#0D47A1",
                left=2,
            ),
            "left_right_thick": make_format(
                workbook,
                bold=True,
                font_color="white",
                bg_color="#0D47A1",
                right=2,
                left=2,
            ),
        },
        "validated": {
            "base": make_format(workbook, bold=True, font_color="green"),
            "right": make_format(workbook, bold=True, font_color="green", right=1),
            "thick": make_format(workbook, bold=True, font_color="green", right=2),
            "bottom": make_format(workbook, bold=True, font_color="green", bottom=2),
            "bottom_right": make_format(
                workbook,
                bold=True,
                font_color="green",
                bottom=2,
                right=1,
            ),
            "bottom_thick": make_format(
                workbook,
                bold=True,
                font_color="green",
                bottom=2,
                right=2,
            ),
        },
        "not_validated": {
            "base": make_format(workbook, bold=True, font_color="red"),
            "right": make_format(workbook, bold=True, font_color="red", right=1),
            "thick": make_format(workbook, bold=True, font_color="red", right=2),
            "bottom": make_format(workbook, bold=True, font_color="red", bottom=2),
            "bottom_right": make_format(
                workbook,
                bold=True,
                font_color="red",
                bottom=2,
                right=1,
            ),
            "bottom_thick": make_format(
                workbook,
                bold=True,
                font_color="red",
                bottom=2,
                right=2,
            ),
        },
        "other": {
            "base": make_format(workbook),
            "right": make_format(workbook, right=1),
            "thick": make_format(workbook, right=2),
            "bottom": make_format(workbook, bottom=2),
            "bottom_right": make_format(workbook, bottom=2, right=1),
            "bottom_thick": make_format(workbook, bottom=2, right=2),
        },
    }


def build_product_structure(
    products: list[models_cdr.CdrProduct],
    variants: list[models_cdr.ProductVariant],
    data_fields: dict[UUID, list[models_cdr.CustomDataField]],
):
    variants_by_product: dict[UUID, list[models_cdr.ProductVariant]] = {}
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

    return product_structure, col_idx


def filter_users_with_purchases(
    users: list[models_users.CoreUser],
    users_purchases: dict[str, list[models_cdr.Purchase]],
):
    return [
        u for u in users if any(p.quantity > 0 for p in users_purchases.get(u.id, []))
    ]


def build_data_rows(
    users: list[models_users.CoreUser],
    users_purchases: dict[str, list[models_cdr.Purchase]],
    users_answers: dict[str, list[models_cdr.CustomData]],
    product_structure: dict,
    col_idx: int,
):
    data_rows = []
    for user in users:
        row = [""] * col_idx
        row[0] = user.name
        row[1] = user.firstname
        row[2] = user.nickname if user.nickname else ""
        row[3] = user.email

        answers = users_answers.get(user.id, [])
        answers_map = {a.field_id: a.value for a in answers}
        purchases_map = {
            p.product_variant_id: p for p in users_purchases.get(user.id, [])
        }

        for prod_struct in product_structure:
            for vinfo in prod_struct["variants_info"]:
                p = purchases_map.get(vinfo["variant"].id, None)
                row[vinfo["qty_col"]] = str(p.quantity) if p and p.quantity > 0 else ""
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

    return data_rows


def write_fixed_headers(
    worksheet: xlsxwriter.Workbook.worksheet_class,
    fixed_columns: list[str],
    formats: dict,
):
    for col, title in enumerate(fixed_columns):
        worksheet.merge_range(0, col, 2, col, title, formats["header"]["base"])


def write_product_headers(
    worksheet: xlsxwriter.Workbook.worksheet_class,
    product_structure: dict,
    fixed_columns: list[str],
    formats: dict,
    max_lens: list[int],
):
    product_end_cols = [
        len(fixed_columns) - 1,
    ]
    variant_end_cols = set()
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
            worksheet.merge_range(
                0,
                start_col,
                0,
                end_col,
                product.name_fr,
                formats["header"]["base"],
            )
        else:
            worksheet.write(0, start_col, product.name_fr, formats["header"]["base"])

        product_end_cols.append(end_col)

        for vinfo in variants_info:
            qty_col = vinfo["qty_col"]
            if needs_validation:
                worksheet.merge_range(
                    1,
                    qty_col,
                    1,
                    qty_col + 1,
                    vinfo["variant"].name_fr,
                    formats["header"]["base"],
                )
            else:
                worksheet.write(
                    1,
                    qty_col,
                    vinfo["variant"].name_fr,
                    formats["header"]["base"],
                )

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
                    formats["header"]["base"],
                )
            else:
                worksheet.write(
                    1,
                    custom_cols[0],
                    "Informations complémentaires",
                    formats["header"]["base"],
                )

            info_comp_len = len("Informations complémentaires")
            for c in range(custom_cols[0], custom_cols[-1] + 1):
                max_lens[c] = max(max_lens[c], info_comp_len)

        for vinfo in variants_info:
            worksheet.write(2, vinfo["qty_col"], "Quantité", formats["header"]["base"])
            max_lens[vinfo["qty_col"]] = max(
                max_lens[vinfo["qty_col"]],
                len("Quantité"),
            )
            if needs_validation and vinfo["valid_col"] is not None:
                worksheet.write(
                    2,
                    vinfo["valid_col"],
                    "Validé",
                    formats["header"]["base"],
                )
                max_lens[vinfo["valid_col"]] = max(
                    max_lens[vinfo["valid_col"]],
                    len("Validé"),
                )

        for i, field in enumerate(fields):
            worksheet.write(2, custom_cols[i], field.name, formats["header"]["base"])
            max_lens[custom_cols[i]] = max(max_lens[custom_cols[i]], len(field.name))

        for c in range(start_col, end_col + 1):
            max_lens[c] = max(max_lens[c], len(product.name_fr))

    return product_end_cols, variant_end_cols


def write_data_rows(
    worksheet: xlsxwriter.Workbook.worksheet_class,
    data_rows: list,
    product_end_cols: list[int],
    variant_end_cols: list[int],
    formats: dict,
    max_lens: list[int],
    start_row: int = 3,
):
    for row_idx, row in enumerate(data_rows, start=start_row):
        is_last_row = row_idx == start_row + len(data_rows) - 1
        for col_idx, val in enumerate(row):
            # Choix du format selon la colonne
            if col_idx in product_end_cols:
                base = (
                    formats["validated"]
                    if val == "OUI"
                    else formats["not_validated"]
                    if val == "NON"
                    else formats["other"]
                )
                fmt = base["bottom_thick"] if is_last_row else base["thick"]

            elif col_idx in variant_end_cols:
                base = (
                    formats["validated"]
                    if val == "OUI"
                    else formats["not_validated"]
                    if val == "NON"
                    else formats["other"]
                )
                fmt = base["bottom_right"] if is_last_row else base["right"]

            else:
                base = (
                    formats["validated"]
                    if val == "OUI"
                    else formats["not_validated"]
                    if val == "NON"
                    else formats["other"]
                )
                fmt = base["bottom"] if is_last_row else base["base"]

            worksheet.write(row_idx, col_idx, val, fmt)
            max_lens[col_idx] = max(max_lens[col_idx], len(str(val)))


def autosize_columns(
    worksheet: xlsxwriter.Workbook.worksheet_class,
    max_lens: list[int],
):
    for i, length in enumerate(max_lens):
        worksheet.set_column(i, i, length + 3)


def write_to_excel(
    workbook: xlsxwriter.Workbook,
    worksheet_name: str,
    fixed_columns: list[str],
    product_structure,
    data_rows: list,
    col_idx: int,
    formats: dict,
):
    worksheet = workbook.add_worksheet(worksheet_name)
    max_lens = [len(c) for c in fixed_columns] + [0] * (col_idx - len(fixed_columns))

    write_fixed_headers(worksheet, fixed_columns, formats)
    product_end_cols, variant_end_cols = write_product_headers(
        worksheet,
        product_structure,
        fixed_columns,
        formats,
        max_lens,
    )
    write_data_rows(
        worksheet,
        data_rows,
        product_end_cols,
        variant_end_cols,
        formats,
        max_lens,
    )
    autosize_columns(worksheet, max_lens)
    worksheet.freeze_panes(3, len(fixed_columns))


def construct_dataframe_from_users_purchases(
    users_purchases: dict[str, list[models_cdr.Purchase]],
    users_answers: dict[str, list[models_cdr.CustomData]],
    users: list[models_users.CoreUser],
    products: list[models_cdr.CdrProduct],
    variants: list[models_cdr.ProductVariant],
    data_fields: dict[UUID, list[models_cdr.CustomDataField]],
    export_io: BytesIO,
):
    fixed_columns = ["Nom", "Prénom", "Surnom", "Email"]

    product_structure, col_idx = build_product_structure(
        products,
        variants,
        data_fields,
    )
    users_to_write = filter_users_with_purchases(users, users_purchases)
    data_rows = build_data_rows(
        users_to_write,
        users_purchases,
        users_answers,
        product_structure,
        col_idx,
    )

    workbook = xlsxwriter.Workbook(export_io)
    formats = generate_format(workbook)

    write_to_excel(
        workbook,
        "Données",
        fixed_columns,
        product_structure,
        data_rows,
        col_idx,
        formats,
    )
    workbook.close()
