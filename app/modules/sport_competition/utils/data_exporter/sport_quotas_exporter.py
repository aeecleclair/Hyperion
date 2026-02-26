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

FIXED_COLUMNS = [
    "École",
    "Quota Sportif",
    "Quota Équipe",
]

hyperion_error_logger = logging.getLogger("hyperion.error")


def build_data_rows(
    school_sports_quotas: list[schemas_sport_competition.SchoolSportQuota],
    schools: list[schemas_sport_competition.SchoolExtension],
) -> tuple[list, list[int]]:
    data_rows = []

    school_dict = {school.school_id: school.school for school in schools}

    for quota in school_sports_quotas:
        school = school_dict.get(quota.school_id)
        if not school:
            hyperion_error_logger.error(
                f"Missing school data for school ID {quota.school_id} "
                "while exporting school sports quotas.",
            )
            raise MissingDataError("Required school data is missing.")  # noqa: TRY003

        row = [
            school.name,
            quota.participant_quota,
            quota.team_quota,
        ]
        data_rows.append(row)

    thick_columns = [len(FIXED_COLUMNS) - 1]
    return data_rows, thick_columns


def write_fixed_headers(
    worksheet: xlsxwriter.Workbook.worksheet_class,
    formats: dict,
):
    for col_idx, column in enumerate(FIXED_COLUMNS):
        worksheet.write(0, col_idx, column, formats["header"]["base"])


def write_to_excel(
    workbook: xlsxwriter.Workbook,
    data_rows: list,
    thick_columns: list[int],
    formats: dict,
):
    worksheet = workbook.add_worksheet("Quotas")
    write_fixed_headers(worksheet, formats)
    columns_max_length = [len(c) for c in FIXED_COLUMNS]
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


def construct_sport_quotas_excel(
    schools: list[schemas_sport_competition.SchoolExtension],
    school_sports_quotas: list[schemas_sport_competition.SchoolSportQuota],
    export_io: BytesIO,
):
    schools.sort(
        key=lambda s: s.school.name.lower(),
    )
    data_rows, thick_columns = build_data_rows(
        school_sports_quotas,
        schools,
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
