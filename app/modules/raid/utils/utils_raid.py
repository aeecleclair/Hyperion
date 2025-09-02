import logging
import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime
from pathlib import Path

import aiofiles
import fitz
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.google_api.google_api import DriveGoogleAPI
from app.core.payment import schemas_payment
from app.core.utils.config import Settings
from app.modules.raid import coredata_raid, cruds_raid, models_raid, schemas_raid
from app.modules.raid.raid_type import Difficulty
from app.modules.raid.schemas_raid import (
    ParticipantBase,
    ParticipantUpdate,
)
from app.modules.raid.utils.drive.drive_file_manager import DriveFileManager
from app.modules.raid.utils.pdf.conversion_utils import (
    date_to_string,
    get_difficulty_label,
    get_document_validation_label,
    get_meeting_place_label,
    nullable_number_to_string,
)
from app.utils.tools import (
    concat_pdf,
    delete_file_from_data,
    generate_pdf_from_template,
    get_core_data,
    get_file_path_from_data,
    save_bytes_as_data,
)

hyperion_error_logger = logging.getLogger("hyperion.error")


class RaidPayementError(ValueError):
    def __init__(self, checkout_id):
        super().__init__(f"RAID participant checkout {checkout_id} not found.")


def will_participant_be_minor_on(
    participant: ParticipantUpdate | models_raid.Participant | ParticipantBase,
    raid_start_date: date | None,
) -> bool:
    """
    Determine if the participant will be minor at the RAID dates. If the date is not known, we will use January the first of next year.
    """

    # If we don't know the participant birthday we may consider they may be minor
    if participant.birthday is None:
        return True

    if raid_start_date is None:
        raid_start_date = date(
            year=datetime.now(UTC).year + 1,
            month=1,
            day=1,
        )

    return (
        date(
            participant.birthday.year + 18,
            participant.birthday.month,
            participant.birthday.day,
        )
        > raid_start_date
    )


async def validate_payment(
    checkout_payment: schemas_payment.CheckoutPayment,
    db: AsyncSession,
) -> None:
    paid_amount = checkout_payment.paid_amount
    checkout_id = checkout_payment.checkout_id
    hyperion_error_logger.info(f"RAID: Callback Checkout id {checkout_id}")

    participant_checkout = await cruds_raid.get_participant_checkout_by_checkout_id(
        str(checkout_id),
        db,
    )
    if not participant_checkout:
        raise RaidPayementError(checkout_id)
    participant_id = participant_checkout.participant_id
    prices = await get_core_data(coredata_raid.RaidPrice, db)
    if prices.student_price and (
        paid_amount in (prices.student_price, prices.external_price or 0)
    ):
        await cruds_raid.confirm_payment(participant_id, db)
    elif prices.t_shirt_price and paid_amount == prices.t_shirt_price:
        await cruds_raid.confirm_t_shirt_payment(participant_id, db)
    elif (
        prices.student_price
        and prices.t_shirt_price
        and paid_amount
        in (
            prices.student_price + prices.t_shirt_price,
            (prices.external_price or 0) + prices.t_shirt_price,
        )
    ):
        await cruds_raid.confirm_payment(participant_id, db)
        await cruds_raid.confirm_t_shirt_payment(participant_id, db)
    else:
        hyperion_error_logger.error("Invalid payment amount")
    # team = await cruds_raid.get_team_by_participant_id(participant_id, db)
    # await post_update_actions(team, db, drive_file_manager)


async def write_teams_csv(
    teams: Sequence[models_raid.Team],
    db: AsyncSession,
    drive_file_manager: DriveFileManager,
    settings: Settings,
) -> None:
    file_name = "Équipes - " + datetime.now(UTC).strftime("%Y-%m-%d_%H_%M_%S") + ".csv"
    file_path = "data/raid/" + file_name
    data: list[list[str]] = [["Team name", "Captain", "Second", "Difficulty", "Number"]]
    data.extend(
        [
            [
                team.name.replace(",", " "),
                f"{team.captain.firstname} {team.captain.name}".replace(",", " "),
                f"{team.second.firstname} {team.second.name}".replace(",", " ")
                if team.second
                else "",
                str(team.difficulty or ""),
                str(team.number or ""),
            ]
            for team in teams
        ],
    )
    async with aiofiles.open(
        file_path,
        mode="w",
        newline="",
        encoding="utf-8",
    ) as file:
        for line in data:
            await file.write(",".join(line) + "\n")

    await drive_file_manager.upload_raid_file(
        file_path,
        file_name,
        db,
        settings=settings,
    )
    Path(file_path).unlink()


async def set_team_number(team: models_raid.Team, db: AsyncSession) -> None:
    if team.difficulty is None:
        return
    number_of_team = await cruds_raid.get_number_of_team_by_difficulty(
        team.difficulty,
        db,
    )
    difficulty_separator = {
        Difficulty.discovery: 0,
        Difficulty.sports: 100,
        Difficulty.expert: 200,
    }
    new_team_number = (
        difficulty_separator[team.difficulty] + 1
        if number_of_team == 0
        else number_of_team + 1
    )
    updated_team: schemas_raid.TeamUpdate = schemas_raid.TeamUpdate(
        number=new_team_number,
    )
    await cruds_raid.update_team(team.id, updated_team, db)


async def save_team_info(
    team: models_raid.Team,
    information: coredata_raid.RaidInformation,
    db: AsyncSession,
    drive_file_manager: DriveFileManager,
    settings: Settings,
):
    try:
        physical_file_uuid = await prepare_complete_team_file(
            team=team,
            information=information,
        )

        file_path = str(
            get_file_path_from_data(
                directory="raid/team",
                filename=physical_file_uuid,
            ),
        )

        file_name = (
            str(team.number) + "_" if team.number else ""
        ) + f"{team.name}_{team.captain.name}_{team.captain.firstname}.pdf"

        if team.file_id:
            try:
                async with DriveGoogleAPI(db, settings) as google_api:
                    file_id = google_api.replace_file(file_path, team.file_id)
            except Exception:
                hyperion_error_logger.exception(
                    "RAID: could not replace file",
                )
                file_id = await drive_file_manager.upload_team_file(
                    file_path,
                    file_name,
                    db,
                    settings=settings,
                )
        else:
            file_id = await drive_file_manager.upload_team_file(
                file_path,
                file_name,
                db,
                settings=settings,
            )
        await cruds_raid.update_team_file_id(team.id, file_id, db)
    except Exception:
        hyperion_error_logger.exception("Error while creating pdf")
        return


async def post_update_actions(
    team: models_raid.Team,
    db: AsyncSession,
    drive_file_manager: DriveFileManager,
    settings: Settings,
    should_generate_all_teams_csv: bool = True,
) -> None:
    try:
        if team.validation_progress == 100 and (
            team.number is None or team.number == -1
        ):
            await set_team_number(team, db)

            # Usually we want to update the csv file each team a team is updated
            # but when we batch update teams we only want to update the csv file once, at the end
            if should_generate_all_teams_csv:
                all_teams = await cruds_raid.get_all_validated_teams(db)
                await write_teams_csv(
                    all_teams,
                    db,
                    drive_file_manager,
                    settings=settings,
                )
        information = await get_core_data(coredata_raid.RaidInformation, db)
        await save_team_info(
            team,
            information,
            db,
            drive_file_manager,
            settings=settings,
        )
    except Exception:
        hyperion_error_logger.exception(f"Error while creating pdf for team {team.id}")
        return


async def generate_security_file_pdf(
    participant: models_raid.Participant,
    information: coredata_raid.RaidInformation,
    team_number: int | None = None,
):
    """
    Generate a security file PDF for a participant.
    The file will be saved in the `raid/security_file` directory with the participant's ID as the filename.
    """
    context = {
        **participant.__dict__,
        "president": information.president.__dict__ if information.president else None,
        "rescue": information.rescue.__dict__ if information.rescue else None,
        "security_responsible": information.security_responsible.__dict__
        if information.security_responsible
        else None,
        "volunteer_responsible": information.volunteer_responsible.__dict__
        if information.volunteer_responsible
        else None,
        "team_number": team_number,
    }

    await generate_pdf_from_template(
        template_name="raid_security_file.html",
        directory="raid/security_file",
        filename=participant.id,
        context=context,
    )

    return participant.id


async def generate_recap_file_pdf(
    team: models_raid.Team,
):
    context = {
        "team_name": team.name,
        "parcours": get_difficulty_label(team.difficulty),
        "lieu_rdv": get_meeting_place_label(team.meeting_place),
        "numero": nullable_number_to_string(team.number),
        "inscription": str(int(team.validation_progress)) + " %",
        "capitaine": team.captain.__dict__,
        "participant": team.second.__dict__ if team.second else None,
    }

    file_id = team.id

    await generate_pdf_from_template(
        template_name="raid_inscription_recap.html",
        directory="raid/recap",
        filename=file_id,
        context=context,
    )
    return file_id


def scale_rect_to_fit(container, content_width, content_height):
    """Return a rect that fits content inside container preserving aspect ratio."""
    container_width = container.width
    container_height = container.height

    scale = min(container_width / content_width, container_height / content_height)
    new_width = content_width * scale
    new_height = content_height * scale

    x0 = container.x0 + (container_width - new_width) / 2
    y0 = container.y0 + (container_height - new_height) / 2
    x1 = x0 + new_width
    y1 = y0 + new_height

    return fitz.Rect(x0, y0, x1, y1)


async def prepare_complete_team_file(
    team: models_raid.Team,
    information: coredata_raid.RaidInformation,
):
    recap_file_id = await generate_recap_file_pdf(
        team=team,
    )

    output_pdf: fitz.Document = fitz.open()

    concat_pdf(
        source_directory="raid/recap",
        source_filename=recap_file_id,
        output_pdf=output_pdf,
    )

    security_file_id = await generate_security_file_pdf(
        participant=team.captain,
        information=information,
        team_number=team.number,
    )
    concat_pdf(
        source_directory="raid/security_file",
        source_filename=security_file_id,
        output_pdf=output_pdf,
    )

    if team.second:
        security_file_id = await generate_security_file_pdf(
            participant=team.second,
            information=information,
            team_number=team.number,
        )
        concat_pdf(
            source_directory="raid/security_file",
            source_filename=security_file_id,
            output_pdf=output_pdf,
        )

    for participant in [team.captain, team.second] if team.second else [team.captain]:
        for document in [
            participant.id_card,
            participant.medical_certificate,
            participant.student_card,
            participant.raid_rules,
            participant.parent_authorization,
        ]:
            if document:
                path = get_file_path_from_data("raid", document.id)

                page = output_pdf.new_page(width=595, height=842)  # A4 size in points
                title_font_size = 16
                subtitle_font_size = 12
                margin = 50
                page.insert_text(
                    (margin, margin),
                    participant.firstname + " " + participant.name,
                    fontsize=title_font_size,
                    fontname="helv",
                    fill=(0, 0, 0),
                )
                page.insert_text(
                    (margin, margin + 25),
                    f"Date de téléversement {date_to_string(document.uploaded_at)} | Validation : {get_document_validation_label(document.validation)}",
                    fontsize=subtitle_font_size,
                    fontname="helv",
                    fill=(0.2, 0.2, 0.2),
                )

                if path.suffix.lower() in [".pdf"]:
                    src_doc = fitz.open(path)
                    src_page = src_doc.load_page(0)
                    pix = src_page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))

                else:  # assume image
                    pix = fitz.Pixmap(path)

                # Define the area for the image
                image_rect = fitz.Rect(margin, 120, 595 - margin, 742 - margin)

                # Scale to fit
                img_rect = scale_rect_to_fit(image_rect, pix.width, pix.height)
                page.insert_image(img_rect, pixmap=pix)

                if path.suffix.lower() in [".pdf"]:
                    if len(src_doc) > 1:
                        output_pdf.insert_pdf(
                            src_doc,
                            from_page=1,
                            to_page=len(src_doc),
                        )

    for i, page in enumerate(output_pdf, start=1):
        footer_text = (
            f"RAID Raid Centrale Lyon - équipe {team.number} {team.name} - Page {i}"
        )
        page_width = page.rect.width
        font_size = 10
        margin = 40

        # Calculate x position to center the footer
        text_width = fitz.get_text_length(
            footer_text,
            fontname="helv",
            fontsize=font_size,
        )
        x_pos = (page_width - text_width) / 2

        # Add footer text near the bottom of the page
        page.insert_text(
            (x_pos, page.rect.height - margin),
            footer_text,
            fontsize=font_size,
            fontname="helv",
            fill=(0.5, 0.5, 0.5),
        )

    file_id = uuid.uuid4()
    await save_bytes_as_data(
        file_bytes=output_pdf.write(),
        directory="raid/team",
        filename=file_id,
        extension="pdf",
    )

    output_pdf.close()

    return file_id


async def save_security_file(
    participant: models_raid.Participant,
    information: coredata_raid.RaidInformation,
    team_number: int | None,
    db: AsyncSession,
    drive_file_manager: DriveFileManager,
    settings: Settings,
) -> None:
    try:
        security_file_id = await generate_security_file_pdf(
            participant,
            information,
            team_number,
        )

        file_path = get_file_path_from_data(
            directory="raid/security_file",
            filename=security_file_id,
        )

        file_name = f"{str(team_number) + '_' if team_number else ''}{participant.firstname}_{participant.name}_fiche_sécurité.pdf"
        if participant.security_file is None:
            hyperion_error_logger.error(
                "RAID: The security file should have been created",
            )
            return

        async with DriveGoogleAPI(db, settings) as google_api:
            if participant.security_file.file_id:
                file_id = google_api.replace_file(
                    str(file_path),
                    participant.security_file.file_id,
                )

            else:
                file_id = await drive_file_manager.upload_participant_file(
                    str(file_path),
                    file_name,
                    db,
                    settings=settings,
                )

        await cruds_raid.update_security_file_id(
            participant.security_file.id,
            file_id,
            db,
        )

        delete_file_from_data(
            directory="raid/security_file",
            filename=participant.id,
        )
    except Exception:
        hyperion_error_logger.exception("Error while creating pdf")
        return


async def get_participant(
    participant_id: str,
    db: AsyncSession,
) -> models_raid.Participant:
    participant = await cruds_raid.get_participant_by_id(participant_id, db)
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found.")
    return participant


async def generate_teams_pdf_util(
    db: AsyncSession,
    drive_file_manager: DriveFileManager,
    settings: Settings,
):
    teams = await cruds_raid.get_all_teams(db)

    hyperion_error_logger.warning(f"RAID: Generating PDF for {len(teams)} teams")

    for index, team in enumerate(teams):
        hyperion_error_logger.info(f"RAID: team {index}/{len(teams)}")

        # We reset the team number to -1 to force the update of the team number
        await cruds_raid.update_team(team.id, schemas_raid.TeamUpdate(number=-1), db)
        await post_update_actions(
            team,
            db,
            drive_file_manager,
            settings=settings,
            should_generate_all_teams_csv=False,
        )

    all_teams = await cruds_raid.get_all_validated_teams(db)
    await write_teams_csv(
        all_teams,
        db,
        drive_file_manager,
        settings=settings,
    )

    hyperion_error_logger.warning(
        f"RAID: Successfully generated PDF for {len(teams)} teams",
    )
