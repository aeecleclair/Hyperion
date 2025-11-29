from datetime import date

from app.modules.raid.raid_type import Difficulty, DocumentType, DocumentValidation


def nullable_number_to_string(number: float | None) -> str:
    if number is None:
        return "Non défini"
    return str(number)


def date_to_string(date: date) -> str:
    return date.strftime("%d/%m/%Y")


def get_difficulty_label(difficulty: Difficulty | None) -> str:
    if difficulty == Difficulty.discovery:
        return "Découverte"
    if difficulty == Difficulty.sports:
        return "Sportif"
    if difficulty == Difficulty.expert:
        return "Expert"
    return "Non défini"


def get_meeting_place_label(meeting_place: str | None) -> str:
    labels = {
        "centrale": "Centrale Lyon",
        "bellecour": "Bellecour",
        "anyway": "Peu importe",
    }
    if meeting_place in labels:
        return labels[meeting_place]
    return "Non défini"


def get_size_label(size: str | None) -> str:
    if size is None:
        return "Non défini"
    return size


def get_situation_label(situation: str | None) -> str:
    labels = {
        "centrale": "Centrale Lyon",
        "otherSchool": "Autre école",
        "corporatePartner": "Partenaire entreprise",
        "other": "Autre",
    }
    if situation in labels:
        return labels[situation]
    return "Non défini"


def get_document_label(document_type: DocumentType) -> str:
    if document_type == DocumentType.idCard:
        return "Carte d'identité"
    if document_type == DocumentType.medicalCertificate:
        return "Certificat médical"
    if document_type == DocumentType.studentCard:
        return "Carte étudiante"
    return "Règlement du raid"


def get_document_validation_label(validation_label: DocumentValidation) -> str:
    if validation_label == DocumentValidation.accepted:
        return "Validé"
    if validation_label == DocumentValidation.pending:
        return "En attente"
    if validation_label == DocumentValidation.refused:
        return "Refusé"
    return "Validation temporaire"
