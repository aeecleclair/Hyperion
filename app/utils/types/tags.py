"""File defining the tags for the automatic FastAPI documentation (found on http://domainname/docs)"""

from enum import Enum


class Tags(str, Enum):
    users = "Users"
    groups = "Groups"
    core = "Core"
    auth = "Auth"
    loans = "Loans"
    amap = "AMAP"
    bdebooking = "BDEBooking"
    calendar = "Calendar"
    campaign = "Campaign"
    cinema = "Cinema"
    raffle = "Raffle"
    advert = "Advert"
    notifications = "Notifications"
