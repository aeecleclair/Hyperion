from io import BytesIO

import xlsxwriter

from app.modules.sport_competition import schemas_sport_competition
from app.modules.sport_competition.types_sport_competition import ExcelExportParams
from app.modules.sport_competition.utils.data_exporter.commons import (
    autosize_columns,
    generate_format,
    get_user_types,
    write_data_rows,
)
from app.types.exceptions import MissingDataError

FIXED_COLUMNS = ["Nom", "Prénom", "Email", "École", "Type", "Statut"]
PARTICIPANTS_COLUMNS = ["Catégorie", "Sport", "Licence", "Licence valide", "Équipe"]
PAYMENTS_COLUMNS = ["Total à payer", "Total payé", "Tout payé"]


def build_product_structure(
    products: list[schemas_sport_competition.ProductComplete],
):
    col_idx = 0

    product_structure = []
    for product in products:
        if not product.variants:
            continue
        product.variants.sort(key=lambda v: v.name.lower())
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
        thick_columns = [len(FIXED_COLUMNS) - 1]
        purchases_map = {
            p.product_variant_id: p for p in users_purchases.get(user.user.id, [])
        }
        if ExcelExportParams.participants in parameters and users_participant:
            offset = len(FIXED_COLUMNS)
            participant = users_participant.get(user.user.id, None)
            if participant:
                sport = next(s for s in sports if s.id == participant.sport_id)
                row[offset] = participant.user.sport_category.value
                row[offset + 1] = sport.name
                row[offset + 2] = participant.license or "N/A"
                row[offset + 3] = participant.is_license_valid
                row[offset + 4] = (
                    f"{participant.team.name}{' (capitaine)' if participant.team.captain_id == user.user.id else ''}"
                )
            else:
                row[offset] = ""
                row[offset + 1] = ""
                row[offset + 2] = ""
                row[offset + 3] = ""
                row[offset + 4] = ""
            thick_columns.append(len(FIXED_COLUMNS) + len(PARTICIPANTS_COLUMNS) - 1)

        if ExcelExportParams.purchases in parameters and product_structure is not None:
            offset = 10 if ExcelExportParams.participants in parameters else 7
            for prod_struct in product_structure[0]:
                for vinfo in prod_struct["variants_info"]:
                    p = purchases_map.get(vinfo["variant"].id)
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
            offset = len(FIXED_COLUMNS)
            if ExcelExportParams.participants in parameters:
                offset += len(PARTICIPANTS_COLUMNS)
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
            thick_columns.append(offset + len(PAYMENTS_COLUMNS) - 1)

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
        len(FIXED_COLUMNS) + len(PARTICIPANTS_COLUMNS) - 1,
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

    if product_end_cols:
        worksheet.merge_range(
            0,
            start_index,
            0,
            product_end_cols[-1],
            "Produits",
            formats["header"]["base"],
        )

    return product_end_cols, list(variant_end_cols)


def write_to_excel(
    parameters: list[ExcelExportParams],
    workbook: xlsxwriter.Workbook,
    product_structure: tuple[list, int] | None,
    data_rows: list,
    thick_columns: list[int],
    col_idx: int,
    formats: dict,
):
    worksheet = workbook.add_worksheet("Données")
    columns_max_length = [len(c) for c in FIXED_COLUMNS] + [0] * (
        col_idx - len(FIXED_COLUMNS)
    )

    write_fixed_headers(worksheet, formats)
    if ExcelExportParams.participants in parameters:
        write_participant_headers(worksheet, formats, columns_max_length)
    if ExcelExportParams.purchases in parameters:
        if product_structure is None:
            raise TypeError(  # noqa: TRY003
                "product_structure is None but ExcelExportParams.purchases is set",
            )
        write_product_headers(
            worksheet,
            product_structure,
            formats,
            len(FIXED_COLUMNS)
            + (
                len(PARTICIPANTS_COLUMNS)
                if ExcelExportParams.participants in parameters
                else 0
            ),
            columns_max_length,
        )
    if ExcelExportParams.payments in parameters:
        start_index = len(FIXED_COLUMNS)
        if ExcelExportParams.participants in parameters:
            start_index += len(PARTICIPANTS_COLUMNS)
        if ExcelExportParams.purchases in parameters:
            if product_structure is None:
                raise TypeError(  # noqa: TRY003
                    "product_structure is None but ExcelExportParams.purchases is set",
                )
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
    worksheet.freeze_panes(len(FIXED_COLUMNS), 4)


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

    school_dict = {school.school_id: school for school in schools}

    users.sort(
        key=lambda u: (
            school_dict[u.user.school_id].school.name.lower(),
            u.user.name.lower(),
            u.user.firstname.lower(),
        ),
    )

    product_structure: tuple[list, int] | None = None
    col_idx = len(FIXED_COLUMNS)
    if ExcelExportParams.purchases in parameters and products is not None:
        products.sort(
            key=lambda product: product.name.lower(),
        )
        product_structure = build_product_structure(
            products,
        )
        col_idx += sum(
            len(prod_struct["variants_info"]) * 2
            for prod_struct in product_structure[0]
        )

    if ExcelExportParams.participants in parameters:
        col_idx += len(PARTICIPANTS_COLUMNS)
    if ExcelExportParams.payments in parameters:
        col_idx += len(PAYMENTS_COLUMNS)
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
        product_structure,
        data_rows,
        thick_columns,
        col_idx,
        formats,
    )
    workbook.close()
