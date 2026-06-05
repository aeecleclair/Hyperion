import logging
import zipfile
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

import fitz
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.payment import schemas_payment
from app.modules.raid import coredata_raid, cruds_raid, schemas_raid
from app.modules.raid.raid_type import Difficulty, Situation, Size
from app.modules.raid.utils.pdf.conversion_utils import (
    get_difficulty_label,
    get_meeting_place_label,
    nullable_number_to_string,
)
from app.utils.tools import (
    generate_pdf_from_template,
    get_core_data,
    get_file_path_from_data,
)

hyperion_error_logger = logging.getLogger("hyperion.error")


class RaidPayementError(ValueError):
    def __init__(self, checkout_id):
        super().__init__(f"RAID participant checkout {checkout_id} not found.")


def will_birthday_be_minor_on(
    birthday: date | None,
    raid_start_date: date | None,
) -> bool:
    """
    Determine if a participant will be minor at the RAID dates. If the raid
    date is not known, fall back to January 1st of next year. If the birthday
    is unknown, assume they may be minor.
    """
    if birthday is None:
        return True

    if raid_start_date is None:
        raid_start_date = date(
            year=datetime.now(UTC).year + 1,
            month=1,
            day=1,
        )

    return date(birthday.year + 18, birthday.month, birthday.day) > raid_start_date


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
    participant_user_id = participant_checkout.participant_user_id
    edition_id = participant_checkout.edition_id
    prices = await get_core_data(coredata_raid.RaidPrice, db)
    if (prices.student_price and paid_amount == prices.student_price) or (
        prices.external_price and paid_amount == prices.external_price
    ):
        await cruds_raid.confirm_payment(participant_user_id, edition_id, db)
    elif prices.t_shirt_price and paid_amount == prices.t_shirt_price:
        await cruds_raid.confirm_t_shirt_payment(
            participant_user_id,
            edition_id,
            db,
        )
    elif prices.t_shirt_price and (
        (
            prices.student_price
            and paid_amount == prices.student_price + prices.t_shirt_price
        )
        or (
            prices.external_price
            and paid_amount == prices.external_price + prices.t_shirt_price
        )
    ):
        await cruds_raid.confirm_payment(participant_user_id, edition_id, db)
        await cruds_raid.confirm_t_shirt_payment(
            participant_user_id,
            edition_id,
            db,
        )
    else:
        hyperion_error_logger.error("Invalid payment amount")


async def set_team_number(
    team: schemas_raid.RaidTeam,
    edition_id: UUID,
    db: AsyncSession,
) -> None:
    if team.difficulty is None:
        return
    max_number = await cruds_raid.get_max_team_number_by_difficulty(
        team.difficulty,
        edition_id,
        db,
    )
    difficulty_separator = {
        Difficulty.discovery: 0,
        Difficulty.sports: 100,
        Difficulty.expert: 200,
    }
    new_team_number = (
        difficulty_separator[team.difficulty] + 1 if not max_number else max_number + 1
    )
    updated_team = schemas_raid.RaidTeamUpdate(number=new_team_number)
    await cruds_raid.update_team(team.id, updated_team, db)


def _participant_pdf_context(participant: schemas_raid.RaidParticipant) -> dict:
    """Build a template context with identity fields pulled from CoreUser."""
    ctx = participant.model_dump()
    if participant.user is not None:
        ctx["name"] = participant.user.name
        ctx["firstname"] = participant.user.firstname
        ctx["email"] = participant.user.email
        ctx["phone"] = participant.user.phone
        ctx["birthday"] = participant.user.birthday
    return ctx


async def generate_security_file_pdf(
    participant: schemas_raid.RaidParticipant,
    information: coredata_raid.RaidInformation,
    team_number: int | None = None,
):
    """Generate a security file PDF for a participant."""
    context = {
        **_participant_pdf_context(participant),
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
        filename=participant.user_id,
        context=context,
    )

    return participant.user_id


async def generate_recap_file_pdf(
    team: schemas_raid.RaidTeam,
):
    from app.modules.raid.utils.validation_checker import compute_team_progress

    context = {
        "team_name": team.name,
        "parcours": get_difficulty_label(team.difficulty),
        "lieu_rdv": get_meeting_place_label(team.meeting_place),
        "numero": nullable_number_to_string(team.number),
        "inscription": str(int(compute_team_progress(team))) + " %",
        "capitaine": _participant_pdf_context(team.captain),
        "participant": _participant_pdf_context(team.second) if team.second else None,
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


async def get_all_security_files_zip(
    db: AsyncSession,
    information: coredata_raid.RaidInformation,
    edition_id: UUID,
) -> str:
    teams = await cruds_raid.get_all_teams(edition_id, db)
    hyperion_error_logger.info(
        f"RAID: Generating ZIP for {len(teams)} security files",
    )

    if len(teams) == 0:
        raise HTTPException(status_code=400, detail="No team found.")

    Path("data/raid/").mkdir(parents=True, exist_ok=True)
    zip_file_path = f"data/raid/Fiches_Sécurité_{datetime.now(UTC).strftime('%Y-%m-%d_%H_%M_%S')}.zip"
    with zipfile.ZipFile(zip_file_path, mode="w") as archive:
        for team in teams:
            for participant in [team.captain] + ([team.second] if team.second else []):
                file_id = await generate_security_file_pdf(
                    participant,
                    information,
                    team.number,
                )
                src_pdf = get_file_path_from_data(
                    directory="raid/security_file",
                    filename=file_id,
                )

                archive.write(
                    str(src_pdf),
                    arcname=f"{team.name}_{participant.user.firstname}_{participant.user.name}.pdf",
                )

    return zip_file_path


async def get_all_team_files_zip(
    db: AsyncSession,
    information: coredata_raid.RaidInformation,
    edition_id: UUID,
) -> str:
    teams = await cruds_raid.get_all_teams(edition_id, db)
    hyperion_error_logger.info(
        f"RAID: Generating ZIP for {len(teams)} team recap files",
    )

    if len(teams) == 0:
        raise HTTPException(status_code=400, detail="No team found.")

    Path("data/raid/").mkdir(parents=True, exist_ok=True)
    zip_file_path = (
        f"data/raid/Teams_{datetime.now(UTC).strftime('%Y-%m-%d_%H_%M_%S')}.zip"
    )
    with zipfile.ZipFile(zip_file_path, mode="w") as archive:
        for team in teams:
            file_id = await generate_recap_file_pdf(team)
            src_pdf = get_file_path_from_data(
                directory="raid/recap",
                filename=file_id,
            )

            archive.write(
                str(src_pdf),
                arcname=f"{team.name}.pdf",
            )

    return zip_file_path


async def get_participant(
    user_id: str,
    edition_id: UUID,
    db: AsyncSession,
) -> schemas_raid.RaidParticipant:
    participant = await cruds_raid.get_participant_by_user_id(user_id, edition_id, db)
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found.")
    return participant


def calculate_raid_payment(
    participant: schemas_raid.RaidParticipant,
    raid_prices: coredata_raid.RaidPrice,
):
    if (
        not raid_prices.student_price
        or not raid_prices.t_shirt_price
        or not raid_prices.external_price
    ):
        raise HTTPException(status_code=404, detail="Prices not set.")

    price = 0
    checkout_name = ""
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found.")

    if not participant.payment:
        if (
            participant.situation in (Situation.centrale, Situation.otherSchool)
            and participant.student_card_id is not None
        ):
            price += raid_prices.student_price
            checkout_name = "Inscription Raid - Tarif étudiant"
        else:
            price += raid_prices.external_price
            checkout_name = "Inscription Raid - Tarif externe"
    if (
        participant.t_shirt_size
        and participant.t_shirt_size != Size.None_
        and not participant.t_shirt_payment
    ):
        price += raid_prices.t_shirt_price
        if not checkout_name:
            checkout_name += " + "
        checkout_name += "T Shirt taille" + participant.t_shirt_size.value
    return price, checkout_name
