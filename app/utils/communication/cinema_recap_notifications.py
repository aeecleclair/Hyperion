from datetime import timedelta

from app.core.notification.schemas_notification import Message
from app.modules.cinema import cruds_cinema


async def cinema_recap_notification(result, db):
    session_date = result.start
    sunday = (session_date - timedelta(days=(session_date.weekday() + 1))).replace(
        hour=11,
        minute=0,
        second=0,
    )
    next_week_sessions = await cruds_cinema.get_sessions_in_time_frame(
        start_after=sunday,
        start_before=sunday + timedelta(days=7),
        db=db,
    )
    message_content = ""
    days = [
        "Lundi",
        "Mardi",
        "Mercredi",
        "Jeudi",
        "Vendredi",
        "Samedi",
        "Dimanche",
    ]
    months = [
        "janvier",
        "février",
        "mars",
        "avril",
        "mai",
        "juin",
        "juillet",
        "août",
        "septembre",
        "octobre",
        "novembre",
        "décembre",
    ]
    for next_session in next_week_sessions:
        message_content += f"{days[next_session.start.weekday()]} {next_session.start.day} {months[next_session.start.month]} - {next_session.name}\n"
    message = Message(
        # We use sunday date as context to avoid sending the recap twice
        context=f"cinema-recap-{sunday}",
        is_visible=True,
        title="🎬 Cinéma - Programme de la semaine",
        content=message_content,
        delivery_datetime=sunday,
        # The notification will expire the next sunday
        expire_on=sunday + timedelta(days=7),
    )
    return message
