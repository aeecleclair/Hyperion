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
    intensiveCareUnit: bool | None = None
    intensiveCareUnitWhen: str | None = None
    ongoingTreatment: str | None = None
    sicknesses: str | None = None
    hospitalization: str | None = None
    surgicalOperation: str | None = None
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
    bikeSize: Size
    tShirtSize: Size
    situation: str
    otherSchool: str | None = None
    company: str | None = None
    diet: str | None = None
    idCard: Document
    medicalCertificate: Document
    securityFile: SecurityFile
    studentCard: Document | None = None
    raidRules: Document
    certificateOfHonour: bool
    validationProgress: float

    class Config:
        orm_mode = True

class Team(BaseModel):
    id: str
    name: str
    number: int
    difficulty: Difficulty
    captain: Participant
    second: Participant
    validationProgress: float

    class Config:
        orm_mode = True