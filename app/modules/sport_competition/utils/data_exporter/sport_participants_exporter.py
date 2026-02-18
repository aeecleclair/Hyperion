import logging
from io import BytesIO

import xlsxwriter

from app.modules.sport_competition import schemas_sport_competition
from app.modules.sport_competition.utils.data_exporter.commons import (
    autosize_columns,
    generate_format,
    get_user_types,
    write_data_rows,
)
from app.types.exceptions import MissingDataError

hyperion_error_logger = logging.getLogger("hyperion.error")


FIXED_COLUMNS = [
    "Nom",
    "Prénom",
    "Email",
    "École",
    "Type",
    "Statut",
    "Licence",
    "Licence valide",
    "Équipe",
]


def build_data_rows(
    schools: list[schemas_sport_competition.SchoolExtension],
    participants: list[schemas_sport_competition.ParticipantComplete],
    users_purchases: dict[str, list[schemas_sport_competition.PurchaseComplete]],
) -> tuple[list[list[str | int]], list[int]]:
    data_rows: list[list[str | int]] = []
    thick_columns = [len(FIXED_COLUMNS) - 1]
    school_dict = {school.school_id: school.school for school in schools}
    for participant in participants:
        participant_purchases = users_purchases.get(participant.user.user.id, [])
        school = school_dict.get(
            participant.user.user.school_id,
        )
        if not school:
            hyperion_error_logger.error(
                f"Missing school data for user ID {participant.user.user.id} "
                "while exporting sport participants.",
            )
            raise MissingDataError("Required school data is missing.")  # noqa: TRY003
        row: list[str | int] = [
            participant.user.user.name,
            participant.user.user.firstname,
            participant.user.user.email,
            school.name,
            ", ".join(get_user_types(participant.user)),
            "Non validé"
            if not participant.user.validated
            else "Validé et payé"
            if all(purchase.validated for purchase in participant_purchases)
            else "Validé non payé",
            participant.license or "Certificat médical"
            if participant.certificate_file_id
            else "Aucune",
            "OUI" if participant.is_license_valid else "NON",
            participant.team.name,
        ]
        data_rows.append(row)

    return data_rows, thick_columns


def write_fixed_headers(
    worksheet: xlsxwriter.Workbook.worksheet_class,
    formats: dict,
):
    for col, title in enumerate(FIXED_COLUMNS):
        worksheet.write(1, col, title, formats["header"]["base"])


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
        start_row=2,
    )
    autosize_columns(worksheet, columns_max_length)
    worksheet.freeze_panes(5, 4)


def construct_sport_users_excel(
    schools: list[schemas_sport_competition.SchoolExtension],
    participants: list[schemas_sport_competition.ParticipantComplete],
    users_purchases: dict[str, list[schemas_sport_competition.PurchaseComplete]],
    export_io: BytesIO,
):
    schools_dict = {school.school_id: school for school in schools}
    participants.sort(
        key=lambda u: (
            schools_dict[u.user.user.school_id].school.name.lower(),
            u.user.user.name.lower(),
            u.user.user.firstname.lower(),
        ),
    )
    data_rows, thick_columns = build_data_rows(
        schools,
        participants,
        users_purchases,
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
