import logging
from io import BytesIO

import xlsxwriter

from app.modules.sport_competition import schemas_sport_competition
from app.modules.sport_competition.utils.data_exporter.commons import (
    autosize_columns,
    generate_format,
    write_data_rows,
)
from app.types.exceptions import MissingDataError

hyperion_error_logger = logging.getLogger("hyperion.error")


GENERAL_COLUMNS: list[str] = [
    "Type de Quota",
    "Quota",
]
SPORT_COLUMNS: list[str] = ["Sport", "Quota Sportif", "Quota Équipe"]
PRODUCT_COLUMNS: list[str] = [
    "Produit",
    "Quota",
]


def build_data_rows(
    school_sports_quotas: list[schemas_sport_competition.SchoolSportQuota],
    school_general_quotas: schemas_sport_competition.SchoolGeneralQuota | None,
    school_product_quotas: list[schemas_sport_competition.SchoolProductQuota],
    sports: list[schemas_sport_competition.Sport],
    products: list[schemas_sport_competition.ProductComplete],
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
        ).items():
            row = [
                attribute_mapping[quota[0]],
                quota[1] if quota[1] is not None else "Aucun",
            ]
            data_rows[0].append(row)
        thick_columns[0].append(len(GENERAL_COLUMNS) - 1)

    for quota in school_sports_quotas:
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
    thick_columns[1].append(len(SPORT_COLUMNS) - 1)

    for quota in school_product_quotas:
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
    thick_columns[2].append(len(PRODUCT_COLUMNS) - 1)

    return data_rows, thick_columns


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


def construct_school_quotas_excel(
    sports: list[schemas_sport_competition.Sport],
    products: list[schemas_sport_competition.ProductComplete],
    school_sports_quotas: list[schemas_sport_competition.SchoolSportQuota],
    school_general_quotas: schemas_sport_competition.SchoolGeneralQuota | None,
    school_product_quotas: list[schemas_sport_competition.SchoolProductQuota],
    export_io: BytesIO,
):
    sports.sort(
        key=lambda sport: sport.name.lower(),
    )
    products.sort(
        key=lambda product: product.name.lower(),
    )
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
