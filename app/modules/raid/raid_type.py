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
    centrale = "centrale"  # student from Centrale Lyon
    otherSchool = "otherSchool"  # student from another school
    corporatePartner = "corporatePartner"  # enterprise team
    other = "other"  # anything else


class DocumentValidation(StrEnum):
    pending = "pending"
    accepted = "accepted"
    refused = "refused"
    temporary = "temporary"


class RaidRegistrationStatus(StrEnum):
    draft = "draft"
    submitted = "submitted"
    validated = "validated"
    cancelled = "cancelled"
