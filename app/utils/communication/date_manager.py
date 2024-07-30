from datetime import date, datetime, timedelta


def get_date_day(date_object: date | datetime):
    days = [
        "Lundi",
        "Mardi",
        "Mercredi",
        "Jeudi",
        "Vendredi",
        "Samedi",
        "Dimanche",
    ]
    return days[date_object.weekday()]


def get_date_month(date_object: date | datetime):
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
    return months[date_object.month]


def get_previous_sunday(date_object: datetime):
    return (date_object - timedelta(days=(date_object.weekday() + 1))).replace(
        hour=11,
        minute=0,
        second=0,
    )
