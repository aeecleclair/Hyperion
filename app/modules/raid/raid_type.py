from enum import Enum


class DocumentType(str, Enum):
    idCard = "idCard"  # the id card of the participant
    medicalCertificate = (
        "medicalCertificate"  # the medical certificate of the participant
    )
    studentCard = "studentCard"  # the student card of the participant
    raidRules = "raidRules"  # the rules of the raid


class Size(str, Enum):  # for the T-shirt and the bike
    XS = "XS"
    S = "S"
    M = "M"
    L = "L"
    XL = "XL"


class MeetingPlace(str, Enum):  # place of meeting for the raid
    centrale = "centrale"
    bellecour = "bellecour"
    anyway = "anyway"


class Difficulty(str, Enum):  # the difficulty of the raid
    discovery = "discovery"
    sports = "sports"
    expert = "expert"


class Situation(str, Enum):  # the situation of the participant
    centrale = "centrale"
    otherSchool = "otherSchool"
    corporatePartner = "corporatePartner"
    other = "other"
