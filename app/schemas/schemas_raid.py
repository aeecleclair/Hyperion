from datetime import date

from pydantic import BaseModel

from app.utils.types.raid_type import Difficulty, DocumentType, Size

class Document(BaseModel):
    id: str
    name: str
    uploaded_at: date
    validated: bool
    type: DocumentType

    class Config:
        orm_mode = True

class SecurityFile(BaseModel):
    id: str
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

    class Config:
        orm_mode = True

class Participant(BaseModel):
    id: str
    name: str
    firstname: str
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
    validation_progress: float

    class Config:
        orm_mode = True

class Team(BaseModel):
    id: str
    name: str
    number: int
    difficulty: Difficulty
    captain: Participant
    second: Participant
    validation_progress: float

    class Config:
        orm_mode = True