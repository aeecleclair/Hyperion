import logging
from io import BytesIO

import xlsxwriter

from app.modules.sport_competition import schemas_sport_competition
from app.modules.sport_competition.types_sport_competition import ExcelExportParams
from app.types.exceptions import MissingDataError

FIXED_COLUMNS = ["Nom", "Prénom", "Email", "École", "Type", "Statut"]
PARTICIPANTS_COLUMNS = ["Sport", "Licence", "Licence valide", "Équipe"]
PAYMENTS_COLUMNS = ["Total à payer", "Total payé", "Tout payé"]

hyperion_error_logger = logging.getLogger("hyperion.error")


def generate_format(workbook: xlsxwriter.Workbook):
    def make_format(
        workbook: xlsxwriter.Workbook,
        *,
        color: str | None = None,
        bold: bool = False,
        align: str = "center",
        font: str = "Raleway",
        right: int | None = None,
        left: int | None = None,
        bottom: int | None = None,
        bg_color: str | None = None,
        font_color: str | None = None,
    ):
        fmt_dict: dict[str, str | int | bool] = {
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
    products: list[schemas_sport_competition.ProductComplete],
):
    col_idx = 0

    product_structure = []
    for product in products:
        variants_info = []
        for variant in product.variants:
            qty_col = col_idx
            valid_col = col_idx + 1
            col_idx += 2
            variants_info.append(
                {
                    "variant": variant,
                    "qty_col": qty_col,
                    "valid_col": valid_col,
                },
            )

        product_structure.append(
            {
                "product": product,
                "variants_info": variants_info,
            },
        )

    return product_structure, col_idx


def get_user_types(user: schemas_sport_competition.CompetitionUser) -> list[str]:
    types = []
    if user.is_athlete:
        types.append("Athlète")
    if user.is_pompom:
        types.append("Pom-pom")
    if user.is_cameraman:
        types.append("Cameraman")
    if user.is_fanfare:
        types.append("Fanfare")
    if user.is_volunteer:
        types.append("Bénévole")
    return types


def build_data_rows(
    parameters: list[ExcelExportParams],
    users: list[schemas_sport_competition.CompetitionUser],
    schools: list[schemas_sport_competition.SchoolExtension],
    sports: list[schemas_sport_competition.Sport],
    users_participant: dict[str, schemas_sport_competition.ParticipantComplete] | None,
    users_purchases: dict[str, list[schemas_sport_competition.PurchaseComplete]],
    users_payments: dict[str, list[schemas_sport_competition.PaymentComplete]] | None,
    product_structure: tuple[list, int] | None,
    col_idx: int,
) -> tuple[list[list[str | int]], list[int]]:
    data_rows: list[list[str | int]] = []
    for user in users:
        user_purchases = users_purchases.get(user.user.id, [])
        row: list[str | int] = [""] * col_idx
        row[0] = user.user.name
        row[1] = user.user.firstname
        row[2] = user.user.email
        row[3] = next(
            (s.school.name for s in schools if s.school_id == user.user.school_id),
            str(user.user.school_id),
        )
        row[4] = ", ".join(get_user_types(user))
        if user.validated and all(p.validated for p in user_purchases):
            row[5] = "Validé et payé"
        elif user.validated:
            row[5] = "Validé mais non payé"
        else:
            row[5] = "Non validé"
        thick_columns = [5]
        purchases_map = {
            p.product_variant_id: p for p in users_purchases.get(user.user.id, [])
        }
        if ExcelExportParams.participants in parameters and users_participant:
            participant = users_participant.get(user.user.id, None)
            if participant:
                sport = next(s for s in sports if s.id == participant.sport_id)
                row[6] = sport.name
                row[7] = participant.license if participant.license else "N/A"
                row[8] = participant.is_license_valid
                row[9] = (
                    f"{participant.team.name}{' (capitaine)' if participant.team.captain_id == user.user.id else ''}"
                )
            else:
                row[6] = ""
                row[7] = ""
                row[8] = ""
                row[9] = ""
            thick_columns.append(9)

        if ExcelExportParams.purchases in parameters and product_structure is not None:
            offset = 10 if ExcelExportParams.participants in parameters else 7
            for prod_struct in product_structure[0]:
                for vinfo in prod_struct["variants_info"]:
                    p = purchases_map.get(vinfo["variant"].id, None)
                    if p and p.quantity > 0:
                        row[vinfo["qty_col"] + offset] = p.quantity
                        row[vinfo["valid_col"] + offset] = (
                            "OUI" if p.validated else "NON"
                        )
            thick_columns.append(
                offset + product_structure[1] - 1,
            )

        if ExcelExportParams.payments in parameters and users_payments is not None:
            user_payments = users_payments.get(user.user.id, [])
            offset = 6
            if ExcelExportParams.participants in parameters:
                offset += 4
            if (
                ExcelExportParams.purchases in parameters
                and product_structure is not None
            ):
                offset += sum(
                    len(prod_struct["variants_info"]) * 2
                    for prod_struct in product_structure[0]
                )
            total = sum(p.quantity * p.product_variant.price for p in user_purchases)
            paid = sum(p.total for p in user_payments)
            row[offset] = str(total / 100)
            row[offset + 1] = str(paid / 100)
            row[offset + 2] = "OUI" if total == paid else "NON"
            thick_columns.append(offset + 2)

        data_rows.append(row)

    return data_rows, thick_columns


def write_fixed_headers(
    worksheet: xlsxwriter.Workbook.worksheet_class,
    formats: dict,
):
    worksheet.merge_range(
        0,
        0,
        0,
        len(FIXED_COLUMNS) - 1,
        "Informations utilisateur",
        formats["header"]["base"],
    )
    for col, title in enumerate(FIXED_COLUMNS):
        worksheet.merge_range(1, col, 4, col, title, formats["header"]["base"])


def write_participant_headers(
    worksheet: xlsxwriter.Workbook.worksheet_class,
    formats: dict,
    columns_max_length: list[int],
):
    worksheet.merge_range(
        0,
        len(FIXED_COLUMNS),
        0,
        len(FIXED_COLUMNS) + 3,
        "Participants",
        formats["header"]["base"],
    )
    for i, title in enumerate(PARTICIPANTS_COLUMNS, start=len(FIXED_COLUMNS)):
        worksheet.merge_range(1, i, 4, i, title, formats["header"]["base"])
        columns_max_length[i] = max(columns_max_length[i], len(title))


def write_payment_headers(
    worksheet: xlsxwriter.Workbook.worksheet_class,
    formats: dict,
    start_index: int,
    columns_max_length: list[int],
):
    worksheet.merge_range(
        0,
        start_index,
        0,
        start_index + 2,
        "Paiements",
        formats["header"]["base"],
    )
    for i, title in enumerate(PAYMENTS_COLUMNS, start=start_index):
        worksheet.merge_range(1, i, 4, i, title, formats["header"]["base"])
        columns_max_length[i] = max(columns_max_length[i], len(title))


def write_product_headers(
    worksheet: xlsxwriter.Workbook.worksheet_class,
    product_structure: tuple[list, int],
    formats: dict,
    start_index: int,
    columns_max_length: list[int],
) -> tuple[list[int], list[int]]:
    product_end_cols: list[int] = []
    variant_end_cols: list[int] = []
    for prod_struct in product_structure[0]:
        product = schemas_sport_competition.Product.model_validate(
            prod_struct["product"],
        )
        variants_info = prod_struct["variants_info"]
        start_col = variants_info[0]["qty_col"] + start_index
        end_col = start_col + len(variants_info) * 2 - 1

        if start_col < end_col:
            worksheet.merge_range(
                1,
                start_col,
                1,
                end_col,
                product.name,
                formats["header"]["base"],
            )
        else:
            worksheet.write(0, start_col, product.name, formats["header"]["base"])

        product_end_cols.append(end_col)

        for vinfo in variants_info:
            worksheet.merge_range(
                2,
                vinfo["qty_col"] + start_index,
                2,
                vinfo["valid_col"] + start_index,
                vinfo["variant"].name,
                formats["header"]["base"],
            )
            worksheet.merge_range(
                3,
                vinfo["qty_col"] + start_index,
                3,
                vinfo["valid_col"] + start_index,
                str(vinfo["variant"].price / 100) + " €",
                formats["header"]["base"],
            )
            worksheet.write(
                4,
                vinfo["qty_col"] + start_index,
                "Quantité",
                formats["header"]["base"],
            )
            columns_max_length[vinfo["qty_col"]] = max(
                columns_max_length[vinfo["qty_col"]],
                len("Quantité"),
            )
            worksheet.write(
                4,
                vinfo["valid_col"] + start_index,
                "Validé",
                formats["header"]["base"],
            )
            columns_max_length[vinfo["valid_col"]] = max(
                columns_max_length[vinfo["valid_col"]],
                len("Validé"),
            )
            variant_end_cols.append(vinfo["valid_col"])

        for c in range(start_col, end_col + 1):
            columns_max_length[c] = max(columns_max_length[c], len(product.name))

    worksheet.merge_range(
        0,
        start_index,
        0,
        product_end_cols[-1],
        "Produits",
        formats["header"]["base"],
    )

    return product_end_cols, list(variant_end_cols)


def write_data_rows(
    worksheet: xlsxwriter.Workbook.worksheet_class,
    data_rows: list,
    thick_columns: list[int],
    formats: dict,
    columns_max_length: list[int],
    start_row: int = 5,
):
    for row_idx, row in enumerate(data_rows, start=start_row):
        is_last_row = row_idx == start_row + len(data_rows) - 1
        for col_idx, val in enumerate(row):
            # Choix du format selon la colonne
            if col_idx in thick_columns:
                base = (
                    formats["validated"]
                    if val == "OUI"
                    else formats["not_validated"]
                    if val == "NON"
                    else formats["other"]
                )
                fmt = base["bottom_thick"] if is_last_row else base["thick"]

            # elif col_idx in variant_end_cols:
            #     base = (
            #         formats["validated"]
            #         if val == "OUI"
            #         else formats["not_validated"]
            #         if val == "NON"
            #         else formats["other"]
            #     )
            #     fmt = base["bottom_right"] if is_last_row else base["right"]
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
            columns_max_length[col_idx] = max(
                columns_max_length[col_idx],
                len(str(val)),
            )


def autosize_columns(
    worksheet: xlsxwriter.Workbook.worksheet_class,
    columns_max_length: list[int],
):
    for i, length in enumerate(columns_max_length):
        worksheet.set_column(i, i, length + 3)


def write_to_excel(
    parameters: list[ExcelExportParams],
    workbook: xlsxwriter.Workbook,
    worksheet_name: str,
    product_structure: tuple[list, int],
    data_rows: list,
    thick_columns: list[int],
    col_idx: int,
    formats: dict,
):
    worksheet = workbook.add_worksheet(worksheet_name)
    columns_max_length = [len(c) for c in FIXED_COLUMNS] + [0] * (
        col_idx - len(FIXED_COLUMNS)
    )

    write_fixed_headers(worksheet, formats)
    if ExcelExportParams.participants in parameters:
        write_participant_headers(worksheet, formats, columns_max_length)
    if ExcelExportParams.purchases in parameters:
        write_product_headers(
            worksheet,
            product_structure,
            formats,
            len(FIXED_COLUMNS)
            + (4 if ExcelExportParams.participants in parameters else 0),
            columns_max_length,
        )
    if ExcelExportParams.payments in parameters:
        start_index = len(FIXED_COLUMNS)
        if ExcelExportParams.participants in parameters:
            start_index += 4
        if ExcelExportParams.purchases in parameters:
            start_index += product_structure[1]
        write_payment_headers(
            worksheet,
            formats,
            start_index,
            columns_max_length,
        )

    write_data_rows(
        worksheet,
        data_rows,
        thick_columns,
        formats,
        columns_max_length,
    )
    autosize_columns(worksheet, columns_max_length)
    worksheet.freeze_panes(5, 4)


def construct_users_excel_with_parameters(
    parameters: list[ExcelExportParams],
    sports: list[schemas_sport_competition.Sport],
    schools: list[schemas_sport_competition.SchoolExtension],
    users: list[schemas_sport_competition.CompetitionUser],
    users_participant: dict[str, schemas_sport_competition.ParticipantComplete] | None,
    users_purchases: dict[str, list[schemas_sport_competition.PurchaseComplete]],
    users_payments: dict[str, list[schemas_sport_competition.PaymentComplete]] | None,
    products: list[schemas_sport_competition.ProductComplete] | None,
    export_io: BytesIO,
):
    if products is None and ExcelExportParams.purchases in parameters:
        raise MissingDataError("products")
    if users_payments is None and ExcelExportParams.payments in parameters:
        raise MissingDataError("users_payments")
    if users_participant is None and ExcelExportParams.participants in parameters:
        raise MissingDataError("users_participant")

    product_structure: tuple = ()
    col_idx = len(FIXED_COLUMNS)
    if ExcelExportParams.purchases in parameters and products is not None:
        product_structure = build_product_structure(
            products,
        )
        col_idx += sum(
            len(prod_struct["variants_info"]) * 2
            for prod_struct in product_structure[0]
        )
        hyperion_error_logger.debug(f"Product structure: {product_structure}")

    if ExcelExportParams.participants in parameters:
        col_idx += 4
    if ExcelExportParams.payments in parameters:
        col_idx += 3
    data_rows, thick_columns = build_data_rows(
        parameters,
        users,
        schools,
        sports,
        users_participant,
        users_purchases,
        users_payments,
        product_structure,
        col_idx,
    )

    workbook = xlsxwriter.Workbook(export_io)
    formats = generate_format(workbook)

    write_to_excel(
        parameters,
        workbook,
        "Données",
        product_structure,
        data_rows,
        thick_columns,
        col_idx,
        formats,
    )
    workbook.close()
