import logging
from collections.abc import Sequence
from datetime import UTC, date, datetime
from pathlib import Path

import aiofiles
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
from app.modules.raid.utils.pdf.pdf_writer import HTMLPDFWriter, PDFWriter
from app.utils.tools import get_core_data

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
    if prices.student_price and paid_amount == prices.student_price:
        await cruds_raid.confirm_payment(participant_id, db)
    elif prices.t_shirt_price and paid_amount == prices.t_shirt_price:
        await cruds_raid.confirm_t_shirt_payment(participant_id, db)
    elif (
        prices.student_price
        and prices.t_shirt_price
        and paid_amount == prices.student_price + prices.t_shirt_price
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
    db: AsyncSession,
    drive_file_manager: DriveFileManager,
    settings: Settings,
) -> None:
    try:
        pdf_writer = PDFWriter()
        file_path = pdf_writer.write_team(team)
        file_name = file_path.split("/")[-1]
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
        pdf_writer.clear_pdf()
    except Exception:
        hyperion_error_logger.exception("Error while creating pdf")
        return


async def post_update_actions(
    team: models_raid.Team | None,
    db: AsyncSession,
    drive_file_manager: DriveFileManager,
    settings: Settings,
) -> None:
    try:
        if team:
            if team.validation_progress == 100 and (
                team.number is None or team.number == -1
            ):
                await set_team_number(team, db)
                all_teams = await cruds_raid.get_all_validated_teams(db)
                if all_teams:
                    await write_teams_csv(
                        all_teams,
                        db,
                        drive_file_manager,
                        settings=settings,
                    )
            await save_team_info(
                team,
                db,
                drive_file_manager,
                settings=settings,
            )
    except Exception:
        hyperion_error_logger.exception("Error while creating pdf")
        return


async def save_security_file(
    participant: models_raid.Participant,
    information: coredata_raid.RaidInformation,
    team_number: int | None,
    db: AsyncSession,
    drive_file_manager: DriveFileManager,
    settings: Settings,
) -> None:
    try:
        pdf_writer = HTMLPDFWriter()
        file_path = pdf_writer.write_participant_security_file(
            participant,
            information,
            team_number,
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
                    file_path,
                    participant.security_file.file_id,
                )

            else:
                file_id = await drive_file_manager.upload_participant_file(
                    file_path,
                    file_name,
                    db,
                    settings=settings,
                )

        await cruds_raid.update_security_file_id(
            participant.security_file.id,
            file_id,
            db,
        )

        Path(file_path).unlink()
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
