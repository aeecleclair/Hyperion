
from datetime import date

from app.modules.raid.raid_type import Difficulty, DocumentType


def nullable_number_to_string(number: float | int | None) -> str:
    if number is None:
        return "Non défini"
    return str(number)


def date_to_string(date: date) -> str:
    return date.strftime("%d/%m/%Y")


def get_difficulty_label(difficulty: Difficulty | None) -> str:
    if difficulty == Difficulty.discovery:
        return "Découverte"
    elif difficulty == Difficulty.sports:
        return "Sportif"
    elif difficulty == Difficulty.expert:
        return "Expert"
    return "Non défini"


def get_meeting_place_label(meeting_place: str | None) -> str:
    if meeting_place == "centrale":
        return "Centrale Lyon"
    elif meeting_place == "bellecour":
        return "Bellecour"
    elif meeting_place == "anyway":
        return "Peu importe"
    return "Non défini"


def get_size_label(size: str | None) -> str:
    if size == "XS":
        return "XS"
    elif size == "S":
        return "S"
    elif size == "M":
        return "M"
    elif size == "L":
        return "L"
    elif size == "XL":
        return "XL"
    return "Non défini"


def get_situation_label(situation: str | None) -> str:
    if situation == "centrale":
        return "Centrale Lyon"
    elif situation == "otherSchool":
        return "Autre école"
    elif situation == "corporatePartner":
        return "Partenaire entreprise"
    elif situation == "other":
        return "Autre"
    return "Non défini"


def get_document_label(document_type: DocumentType) -> str:
    if document_type == DocumentType.idCard:
        return "Carte d'identité"
    elif document_type == DocumentType.medicalCertificate:
        return "Certificat médical"
    elif document_type == DocumentType.studentCard:
        return "Carte étudiante"
    return "Règlement du raid"
