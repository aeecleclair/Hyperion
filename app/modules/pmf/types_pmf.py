from enum import Enum


class OfferType(str, Enum):  # for the T-shirt and the bike
    TFE = "TFE"
    APP = "APP"
    EXE = "EXE"
    CDI = "CDI"
    CDD = "CDD"


class LocationType(str, Enum):
    On_site = "On_site"
    Hybrid = "Hybrid"
    Remote = "Remote"
