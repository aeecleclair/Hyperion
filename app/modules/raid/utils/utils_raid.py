from datetime import date

from app.modules.raid.schemas_raid import ParticipantUpdate


def will_participant_be_minor_on(
    participant: ParticipantUpdate,
    raid_start_date: date | None,
) -> bool:
    """
    Determine if the participant will be minor at the RAID dates. If the date is not known, we will use January the first of next year.
    """

    return (
        date(
            participant.birthday.year + 18,
            participant.birthday.month,
            participant.birthday.day,
        )
        > raid_start_date
    )
