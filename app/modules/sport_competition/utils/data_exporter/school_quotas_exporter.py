import logging
from typing import TYPE_CHECKING

import xlsxwriter

from app.modules.sport_competition.utils.data_exporter.commons import (
    autosize_columns,
    generate_format,
)
from app.types.exceptions import MissingDataError

if TYPE_CHECKING:
    from io import BytesIO
    from uuid import UUID

    from app.modules.sport_competition import schemas_sport_competition

hyperion_error_logger = logging.getLogger("hyperion.error")


GENERAL_COLUMNS: list[str] = [
    "Type de Quota",
    "Quota",
]
SPORT_COLUMNS: list[str] = [
    "Sport",
]
PRODUCT_COLUMNS: list[str] = [
    "Produit",
    "Quota",
]


def build_data_rows(
    school_sports_quotas: dict[UUID, schemas_sport_competition.SchoolSportQuota],
    school_general_quotas: schemas_sport_competition.SchoolGeneralQuota | None,
    school_product_quotas: dict[UUID, schemas_sport_competition.SchoolProductQuota],
    sports: list[schemas_sport_competition.Sport],
    products: list[schemas_sport_competition.Product],
) -> tuple[list[list], list[list[int]]]:
    data_rows = [[], [], []]
    thick_columns = [[], [], []]  # First column index

    sport_dict = {sport.id: sport for sport in sports}
    product_dict = {product.id: product for product in products}

    if school_general_quotas:
        attribute_mapping = {
            "athlete_quota": "Quota Athlètes",
            "cameraman_quota": "Quota Cameramen",
            "pompom_quota": "Quota Pom-pom",
            "fanfare_quota": "Quota Fanfare",
            "athlete_cameraman_quota": "Quota Athlètes + Cameramen",
            "athlete_pompom_quota": "Quota Athlètes + Pom-pom",
            "athlete_fanfare_quota": "Quota Athlètes + Fanfare",
            "non_athlete_cameraman_quota": "Quota Non-Athlètes + Cameramen",
            "non_athlete_pompom_quota": "Quota Non-Athlètes + Pom-pom",
            "non_athlete_fanfare_quota": "Quota Non-Athlètes + Fanfare",
        }
        for quota in school_general_quotas.model_dump(
            exclude={"school_id", "edition_id"},
        ).values():
            row = [
                attribute_mapping[quota[0]],
                quota[1] if quota[1] is not None else "Aucun",
            ]
            data_rows[0].append(row)
        thick_columns[0].append(1)

    for quota in school_sports_quotas.values():
        try:
            sport = sport_dict[quota.sport_id]
        except KeyError as e:
            hyperion_error_logger.exception(
                f"Missing data for school quota {quota.sport_id}",
            )
            raise MissingDataError(  # noqa: TRY003
                f"Missing related data for school quota {quota.sport_id}",
            ) from e

        row = [
            sport.name,
            quota.participant_quota if quota.participant_quota is not None else "Aucun",
            quota.team_quota if quota.team_quota is not None else "Aucun",
        ]
        data_rows[1].append(row)
    thick_columns[1].append(2)

    for quota in school_product_quotas.values():
        try:
            product = product_dict[quota.product_id]
        except KeyError as e:
            hyperion_error_logger.exception(
                f"Missing data for school product quota {quota.product_id}",
            )
            raise MissingDataError(  # noqa: TRY003
                f"Missing related data for school product quota {quota.product_id}",
            ) from e

        row = [product.name, quota.quota]
        data_rows[2].append(row)
    thick_columns[2].append(1)

    return data_rows, thick_columns


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


def write_sports_headers(
    worksheet: xlsxwriter.Workbook.worksheet_class,
    formats: dict,
):
    for col_idx, column in enumerate(SPORT_COLUMNS):
        worksheet.write(0, col_idx, column, formats["header"]["base"])


def write_generals_headers(
    worksheet: xlsxwriter.Workbook.worksheet_class,
    formats: dict,
):
    for col_idx, column in enumerate(GENERAL_COLUMNS):
        worksheet.write(0, col_idx, column, formats["header"]["base"])


def write_products_headers(
    worksheet: xlsxwriter.Workbook.worksheet_class,
    formats: dict,
):
    for col_idx, column in enumerate(PRODUCT_COLUMNS):
        worksheet.write(0, col_idx, column, formats["header"]["base"])


def write_general_quota_sheet(
    worksheet: xlsxwriter.Workbook.worksheet_class,
    data_rows: list,
    thick_columns: list[int],
    formats: dict,
):
    write_generals_headers(worksheet, formats)
    columns_max_length = [len(c) for c in SPORT_COLUMNS]
    write_data_rows(
        worksheet,
        data_rows,
        thick_columns,
        formats,
        columns_max_length,
        start_row=1,
    )
    autosize_columns(worksheet, columns_max_length)
    worksheet.freeze_panes(1, 0)


def write_sport_quota_sheet(
    worksheet: xlsxwriter.Workbook.worksheet_class,
    data_rows: list,
    thick_columns: list[int],
    formats: dict,
):
    write_sports_headers(worksheet, formats)
    columns_max_length = [len(c) for c in SPORT_COLUMNS]
    write_data_rows(
        worksheet,
        data_rows,
        thick_columns,
        formats,
        columns_max_length,
        start_row=1,
    )
    autosize_columns(worksheet, columns_max_length)
    worksheet.freeze_panes(1, 0)


def write_product_quota_sheet(
    worksheet: xlsxwriter.Workbook.worksheet_class,
    data_rows: list,
    thick_columns: list[int],
    formats: dict,
):
    write_products_headers(worksheet, formats)
    columns_max_length = [len(c) for c in SPORT_COLUMNS]
    write_data_rows(
        worksheet,
        data_rows,
        thick_columns,
        formats,
        columns_max_length,
        start_row=1,
    )
    autosize_columns(worksheet, columns_max_length)
    worksheet.freeze_panes(1, 0)


def write_to_excel(
    workbook: xlsxwriter.Workbook,
    data_rows: list[list],
    thick_columns: list[list[int]],
    formats: dict,
):
    if len(data_rows[0]) > 0:
        general_worksheet = workbook.add_worksheet("Quotas généraux")
        write_general_quota_sheet(
            general_worksheet,
            data_rows[0],
            thick_columns[0],
            formats,
        )

    if len(data_rows[1]) > 0:
        sport_worksheet = workbook.add_worksheet("Quotas par sport")
        write_sport_quota_sheet(
            sport_worksheet,
            data_rows[1],
            thick_columns[1],
            formats,
        )
    if len(data_rows[2]) > 0:
        product_worksheet = workbook.add_worksheet("Quotas par produit")
        write_product_quota_sheet(
            product_worksheet,
            data_rows[2],
            thick_columns[2],
            formats,
        )


def construct_users_excel_with_parameters(
    sports: list[schemas_sport_competition.Sport],
    products: list[schemas_sport_competition.Product],
    school_sports_quotas: dict[UUID, schemas_sport_competition.SchoolSportQuota],
    school_general_quotas: schemas_sport_competition.SchoolGeneralQuota | None,
    school_product_quotas: dict[UUID, schemas_sport_competition.SchoolProductQuota],
    export_io: BytesIO,
):
    sports.sort(key=lambda sport: sport.name)
    products.sort(key=lambda product: product.name)
    data_rows, thick_columns = build_data_rows(
        school_sports_quotas,
        school_general_quotas,
        school_product_quotas,
        sports,
        products,
    )

    workbook = xlsxwriter.Workbook(export_io)
    formats = generate_format(workbook)

    write_to_excel(
        workbook,
        data_rows,
        thick_columns,
        formats,
    )
    workbook.close()
