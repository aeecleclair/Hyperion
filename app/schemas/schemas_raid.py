from datetime import date

from pydantic import BaseModel

from app.utils.types.raid_type import Difficulty, DocumentType, Size


class DocumentBase(BaseModel):
    name: str
    type: DocumentType


class Document(DocumentBase):
    id: str
    uploaded_at: date
    validated: bool

    class Config:
        orm_mode = True


class SecurityFileBase(BaseModel):
    name: str
    firstname: str
    birthday: date
    address: str
    phone: str
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


class SecurityFileUpdate(SecurityFileBase):
    name: str | None = None
    firstname: str | None = None
    birthday: date | None = None
    address: str | None = None
    phone: str | None = None
    allergy: str | None = None
    asthma: bool | None = None
    intensive_care_unit: bool | None = None
    intensive_care_unit_when: str | None = None
    ongoing_treatment: str | None = None
    sicknesses: str | None = None
    hospitalization: str | None = None
    surgical_operation: str | None = None
    trauma: str | None = None
    family: str | None = None


class SecurityFile(SecurityFileBase):
    id: str

    class Config:
        orm_mode = True


class ParticipantBase(BaseModel):
    name: str
    firstname: str
    validation_progress: float


class Participant(ParticipantBase):
    id: str
    birthday: date
    address: str
    phone: str
    email: str
    bike_size: Size
    t_shirt_size: Size
    situation: str
    other_school: str | None = None
    company: str | None = None
    diet: str | None = None
    id_card: Document
    medical_certificate: Document
    security_file: SecurityFile
    student_card: Document | None = None
    raid_rules: Document
    attestation_on_honour: bool
    payment: bool

    class Config:
        orm_mode = True


class ParticipantUpdate(ParticipantBase):
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
    id_card: Document | None = None
    medical_certificate: Document | None = None
    security_file: SecurityFile | None = None
    student_card: Document | None = None
    raid_rules: Document | None = None
    attestation_on_honour: bool | None = None


class TeamBase(BaseModel):
    name: str


class TeamPreview(TeamBase):
    id: str
    number: int
    captain: ParticipantBase
    second: ParticipantBase
    difficulty: Difficulty | None
    validation_progress: float

    class Config:
        orm_mode = True


class Team(TeamBase):
    id: str
    number: int
    captain: Participant
    second: Participant
    difficulty: Difficulty | None
    validation_progress: float

    class Config:
        orm_mode = True


class TeamUpdate(TeamBase):
    name: str | None = None
    number: int | None = None
    difficulty: Difficulty | None = None
