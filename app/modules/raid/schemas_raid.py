from datetime import date

from pydantic import BaseModel

from app.modules.raid.raid_type import (
    Difficulty,
    DocumentType,
    DocumentValidation,
    MeetingPlace,
    Size,
)


class DocumentBase(BaseModel):
    type: DocumentType
    name: str


class DocumentCreation(DocumentBase):
    id: str

    class Config:
        orm_mode = True


class Document(DocumentBase):
    id: str
    uploaded_at: date
    validation: DocumentValidation

    class Config:
        orm_mode = True


class SecurityFileBase(BaseModel):
    allergy: str | None = None
    asthma: bool
    intensive_care_unit: bool | None = None
    intensive_care_unit_when: str | None = None
    ongoing_treatment: str | None = None
    sicknesses: str | None = None
    hospitalization: str | None = None
    surgical_operation: str | None = None
    trauma: str | None = None
    family: str | None = None
    emergency_person_firstname: str | None = None
    emergency_person_name: str | None = None
    emergency_person_phone: str | None = None
    id: str
    file_id: str | None = None


class SecurityFile(SecurityFileBase):
    validation: DocumentValidation

    class Config:
        orm_mode = True


class ParticipantBase(BaseModel):
    name: str
    firstname: str
    birthday: date
    phone: str
    email: str


class ParticipantPreview(ParticipantBase):
    id: str
    bike_size: Size | None
    t_shirt_size: Size | None
    situation: str | None
    validation_progress: float
    payment: bool
    number_of_document: int
    number_of_validated_document: int


class Participant(ParticipantPreview):
    address: str | None
    other_school: str | None = None
    company: str | None = None
    diet: str | None = None
    id_card: Document | None
    medical_certificate: Document | None
    security_file: SecurityFile | None
    student_card: Document | None = None
    raid_rules: Document | None = None
    parent_authorization: Document | None = None
    attestation_on_honour: bool
    is_minor: bool

    class Config:
        orm_mode = True


class ParticipantUpdate(BaseModel):
    name: str | None = None
    firstname: str | None = None
    birthday: date | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    bike_size: Size | None = None
    t_shirt_size: Size | None = None
    situation: str | None = None
    other_school: str | None = None
    company: str | None = None
    diet: str | None = None
    attestation_on_honour: bool | None = None


class TeamBase(BaseModel):
    name: str


class TeamPreview(TeamBase):
    id: str
    number: int | None
    captain: ParticipantPreview
    second: ParticipantPreview | None
    difficulty: Difficulty | None
    meeting_place: MeetingPlace | None
    validation_progress: float

    class Config:
        orm_mode = True


class Team(TeamBase):
    id: str
    number: int | None
    captain: Participant
    second: Participant | None
    difficulty: Difficulty | None
    meeting_place: MeetingPlace | None
    validation_progress: float
    file_id: str | None

    class Config:
        orm_mode = True


class TeamUpdate(BaseModel):
    name: str | None = None
    number: int | None = None
    difficulty: Difficulty | None = None
    meeting_place: MeetingPlace | None = None


class InviteToken(BaseModel):
    team_id: str
    token: str

    class Config:
        orm_mode = True


class RaidInformation(BaseModel):
    raid_start_date: date | None = None
    raid_end_date: date | None = None
    raid_registering_end_date: date | None = None
    payment_link: str | None = None
    contact: str | None = None

    class Config:
        orm_mode = True


class RaidDriveFoldersCreation(BaseModel):
    parent_folder_id: str


class RaidDriveFolders(BaseModel):
    parent_folder_id: str | None = None
    registering_folder_id: str | None = None
    security_folder_id: str | None = None


class RaidPrice(BaseModel):
    student_price: float
    partner_price: float
    t_shirt_price: float

    class Config:
        orm_mode = True
