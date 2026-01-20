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

    from app.modules.sport_competition import schemas_sport_competition

hyperion_error_logger = logging.getLogger("hyperion.error")

FIXED_COLUMNS: list[str] = [
    "Nom",
    "Prénom",
    "Email",
    "École",
    "Statut",
    "Sport",
    "Équipe",
]


def build_data_rows(
    captains: list[schemas_sport_competition.ParticipantComplete],
    sports: list[schemas_sport_competition.Sport],
) -> tuple[list[list], list[int]]:
    data_rows = []
    thick_columns = [len(FIXED_COLUMNS) - 1]  # Last column index

    sport_dict = {sport.id: sport for sport in sports}

    for captain in captains:
        try:
            sport = sport_dict[captain.sport_id]
        except KeyError as e:
            hyperion_error_logger.exception(
                f"Missing data for captain {captain.user.user.id}: sport {captain.sport_id} not found",
            )
            raise MissingDataError(  # noqa: TRY003
                f"Missing related data for captain {captain.user.user.id}",
            ) from e

        row = [
            captain.user.user.name,
            captain.user.user.firstname,
            captain.user.user.email,
            captain.user.user.school.name if captain.user.user.school else "",
            (captain.user.validated and "OUI") or "NON",
            sport.name,
            captain.team.name,
        ]
        data_rows.append(row)

    return data_rows, thick_columns


def write_fixed_headers(
    worksheet: xlsxwriter.Workbook.worksheet_class,
    formats: dict,
):
    for col, title in enumerate(FIXED_COLUMNS):
        worksheet.merge_range(0, col, 1, col, title, formats["header"]["base"])


def write_data_rows(
    worksheet: xlsxwriter.Workbook.worksheet_class,
    data_rows: list,
    thick_columns: list[int],
    formats: dict,
    columns_max_length: list[int],
):
    for row_idx, row in enumerate(data_rows, start=1):
        is_last_row = row_idx == len(data_rows)
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


def write_to_excel(
    workbook: xlsxwriter.Workbook,
    worksheet_name: str,
    data_rows: list,
    thick_columns: list[int],
    formats: dict,
):
    worksheet = workbook.add_worksheet(worksheet_name)
    columns_max_length = [len(c) for c in FIXED_COLUMNS]
    write_fixed_headers(worksheet, formats)
    write_data_rows(
        worksheet,
        data_rows,
        thick_columns,
        formats,
        columns_max_length,
    )
    autosize_columns(worksheet, columns_max_length)


def construct_captain_excel(
    sports: list[schemas_sport_competition.Sport],
    captains: list[schemas_sport_competition.ParticipantComplete],
    export_io: BytesIO,
):
    data_rows, thick_columns = build_data_rows(
        captains,
        sports,
    )

    workbook = xlsxwriter.Workbook(export_io)
    formats = generate_format(workbook)

    write_to_excel(
        workbook,
        "Données",
        data_rows,
        thick_columns,
        formats,
    )
    workbook.close()
