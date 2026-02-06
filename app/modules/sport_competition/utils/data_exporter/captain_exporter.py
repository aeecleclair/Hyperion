import logging
from typing import TYPE_CHECKING

import xlsxwriter

from app.modules.sport_competition.utils.data_exporter.commons import (
    autosize_columns,
    generate_format,
    write_data_rows,
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
    "Téléphone",
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
    thick_columns = [len(FIXED_COLUMNS) - 1]

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
            captain.user.user.phone or "",
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


def write_to_excel(
    workbook: xlsxwriter.Workbook,
    data_rows: list,
    thick_columns: list[int],
    formats: dict,
):
    worksheet = workbook.add_worksheet("Données")
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


def construct_captains_excel(
    sports: list[schemas_sport_competition.Sport],
    captains: list[schemas_sport_competition.ParticipantComplete],
    export_io: BytesIO,
):
    captains.sort(
        key=lambda c: (
            next(s for s in sports if s.id == c.sport_id).name.lower(),
            c.user.user.name.lower(),
            c.user.user.firstname.lower(),
        ),
    )
    data_rows, thick_columns = build_data_rows(
        captains,
        sports,
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
