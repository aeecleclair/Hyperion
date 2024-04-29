"""Models file for module_raid"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

from app.utils.types.raid_type import Difficulty, DocumentType, Size

class Document(Base):
    id: Mapped[str] = mapped_column(
        String, primary_key=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    validated: Mapped[bool] = mapped_column(Boolean, nullable=False)
    type: Mapped[DocumentType] = mapped_column(Enum(DocumentType), nullable=False)


class SecurityFile(Base):
    id: Mapped[str] = mapped_column(
        String, primary_key=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    firstname: Mapped[str] = mapped_column(String, nullable=False)
    birthday: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    address: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str] = mapped_column(String, nullable=False)
    allergy: Mapped[str] = mapped_column(String, nullable=True)
    asthma: Mapped[bool] = mapped_column(Boolean, nullable=False)
    intensiveCareUnit: Mapped[bool] = mapped_column(Boolean, nullable=True)
    intensiveCareUnitWhen: Mapped[str] = mapped_column(String, nullable=True)
    ongoingTreatment: Mapped[str] = mapped_column(String, nullable=True)
    sicknesses: Mapped[str] = mapped_column(String, nullable=True)
    hospitalization: Mapped[str] = mapped_column(String, nullable=True)
    surgicalOperation: Mapped[str] = mapped_column(String, nullable=True)
    trauma: Mapped[str] = mapped_column(String, nullable=True)
    family: Mapped[str] = mapped_column(String, nullable=True)


class Participant(Base):
    id: Mapped[str] = mapped_column(
        String, primary_key=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    firstname: Mapped[str] = mapped_column(String, nullable=False)
    birthday: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    address: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    bikeSize: Mapped[Size] = mapped_column(Enum(Size), nullable=False)
    tShirtSize: Mapped[Size] = mapped_column(Enum(Size), nullable=False)
    situation: Mapped[str] = mapped_column(String, nullable=False)
    otherSchool: Mapped[str] = mapped_column(String, nullable=True)
    company: Mapped[str] = mapped_column(String, nullable=True)
    diet: Mapped[str] = mapped_column(String, nullable=True)
    idCard: Mapped[Document] = relationship("Document")
    medicalCertificate: Mapped[Document] = relationship("Document")
    securityFile: Mapped[SecurityFile] = relationship("SecurityFile")
    studentCard: Mapped[Document] = relationship("Document")
    raidRules: Mapped[Document] = relationship("Document")
    certificateOfHonour: Mapped[bool] = mapped_column(Boolean, nullable=False)
    validationProgress: Mapped[float] = mapped_column(Float, nullable=False)


class Team(Base):
    __tablename__ = "team"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    difficulty: Mapped[Difficulty] = mapped_column(Enum(Difficulty), nullable=False)
    captain: Mapped[Participant] = relationship("Participant")
    second: Mapped[Participant] = relationship("Participant")
    validationProgress: Mapped[float] = mapped_column(Float, nullable=False)
