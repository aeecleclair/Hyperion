from enum import StrEnum


class DocumentType(StrEnum):
    idCard = "idCard"  # the id card of the participant
    medicalCertificate = (
        "medicalCertificate"  # the medical certificate of the participant
    )
    studentCard = "studentCard"  # the student card of the participant
    raidRules = "raidRules"  # the rules of the raid
    parentAuthorization = "parentAuthorization"  # the parent authorization


class Size(StrEnum):  # for the T-shirt and the bike
    XS = "XS"
    S = "S"
    M = "M"
    L = "L"
    XL = "XL"
    None_ = "None"


class MeetingPlace(StrEnum):  # place of meeting for the raid
    centrale = "centrale"
    bellecour = "bellecour"
    anyway = "anyway"


class Difficulty(StrEnum):  # the difficulty of the raid
    discovery = "discovery"
    sports = "sports"
    expert = "expert"


class Situation(StrEnum):  # the situation of the participant
    centrale = "centrale"
    otherSchool = "otherSchool"
    corporatePartner = "corporatePartner"
    other = "other"


class DocumentValidation(StrEnum):
    pending = "pending"
    accepted = "accepted"
    refused = "refused"
    temporary = "temporary"
