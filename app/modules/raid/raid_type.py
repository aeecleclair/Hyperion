from enum import Enum


class DocumentType(str, Enum):
    id_card = "idCard"  # the id card of the participant
    medical_certificate = (
        "medicalCertificate"  # the medical certificate of the participant
    )
    student_card = "studentCard"  # the student card of the participant
    raid_rules = "raidRules"  # the rules of the raid
    parent_authorization = "parentAuthorization"  # the parent authorization


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
    other_school = "otherSchool"
    corporate_partner = "corporatePartner"
    other = "other"


class DocumentValidation(str, Enum):
    pending = "pending"
    accepted = "accepted"
    refused = "refused"
    temporary = "temporary"
