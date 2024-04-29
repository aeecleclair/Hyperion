"""Models file for module_raid"""

from datetime import date

from sqlalchemy import Boolean, Date, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

from app.utils.types.raid_type import Difficulty, DocumentType, Size


class Document(Base):
    __tablename__ = "raid_document"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    uploaded_at: Mapped[date] = mapped_column(Date, nullable=False)
    validated: Mapped[bool] = mapped_column(Boolean, nullable=False)
    type: Mapped[DocumentType] = mapped_column(Enum(DocumentType), nullable=False)


class SecurityFile(Base):
    __tablename__ = "raid_security_file"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, index=True, nullable=False
    )
    allergy: Mapped[str] = mapped_column(String, nullable=True)
    asthma: Mapped[bool] = mapped_column(Boolean, nullable=False)
    intensive_care_unit: Mapped[bool] = mapped_column(Boolean, nullable=True)
    intensive_care_unit_when: Mapped[str] = mapped_column(String, nullable=True)
    ongoing_treatment: Mapped[str] = mapped_column(String, nullable=True)
    sicknesses: Mapped[str] = mapped_column(String, nullable=True)
    hospitalization: Mapped[str] = mapped_column(String, nullable=True)
    surgical_operation: Mapped[str] = mapped_column(String, nullable=True)
    trauma: Mapped[str] = mapped_column(String, nullable=True)
    family: Mapped[str] = mapped_column(String, nullable=True)
    participant: Mapped["Participant"] = relationship(back_populates="security_file")


class Participant(Base):
    __tablename__ = "raid_participant"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    firstname: Mapped[str] = mapped_column(String, nullable=False)
    birthday: Mapped[date] = mapped_column(Date, nullable=False)
    address: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    bike_size: Mapped[Size] = mapped_column(Enum(Size), nullable=False)
    t_shirt_size: Mapped[Size] = mapped_column(Enum(Size), nullable=False)
    situation: Mapped[str] = mapped_column(String, nullable=False)
    other_school: Mapped[str] = mapped_column(String, nullable=True)
    company: Mapped[str] = mapped_column(String, nullable=True)
    diet: Mapped[str] = mapped_column(String, nullable=True)
    id_card_id: Mapped[str] = mapped_column(
        ForeignKey("raid_document.id"), nullable=False
    )
    id_card: Mapped[Document] = relationship("Document", foreign_keys=[id_card_id])
    medical_certificate_id: Mapped[str] = mapped_column(
        ForeignKey("raid_document.id"), nullable=False
    )
    medical_certificate: Mapped[Document] = relationship(
        "Document", foreign_keys=[medical_certificate_id]
    )
    security_file_id: Mapped[str | None] = mapped_column(
        ForeignKey("raid_security_file.id"), nullable=True
    )
    security_file: Mapped[SecurityFile] = relationship(back_populates="participant")
    student_card_id: Mapped[str | None] = mapped_column(
        ForeignKey("raid_document.id"), nullable=True
    )
    student_card: Mapped[Document] = relationship(
        "Document", foreign_keys=[student_card_id]
    )
    raid_rules_id: Mapped[str] = mapped_column(
        ForeignKey("raid_document.id"), nullable=False
    )
    raid_rules: Mapped[Document] = relationship(
        "Document", foreign_keys=[raid_rules_id]
    )
    attestation_on_honour: Mapped[bool] = mapped_column(Boolean, nullable=False)
    validation_progress: Mapped[float] = mapped_column(Float, nullable=False)


class Team(Base):
    __tablename__ = "raid_team"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    difficulty: Mapped[Difficulty] = mapped_column(Enum(Difficulty), nullable=False)
    captain_id: Mapped[str] = mapped_column(
        ForeignKey("raid_participant.id"), nullable=False
    )
    captain: Mapped[Participant] = relationship(
        "Participant", foreign_keys=[captain_id]
    )
    second_id: Mapped[str] = mapped_column(
        ForeignKey("raid_participant.id"), nullable=False
    )
    second: Mapped[Participant] = relationship("Participant", foreign_keys=[second_id])
    validationProgress: Mapped[float] = mapped_column(Float, nullable=False)
