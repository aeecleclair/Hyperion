"""Models file for module_raid"""

from datetime import date

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.modules.raid.raid_type import Difficulty, DocumentType, MeetingPlace, Size


class Document(Base):
    __tablename__ = "raid_document"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    uploaded_at: Mapped[date] = mapped_column(Date, nullable=False)
    validated: Mapped[bool] = mapped_column(Boolean, nullable=False)
    type: Mapped[DocumentType] = mapped_column(Enum(DocumentType), nullable=False)

    # user: Mapped["Participant"] = relationship("Participant")


class SecurityFile(Base):
    __tablename__ = "raid_security_file"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, index=True, nullable=False
    )
    allergy: Mapped[str | None] = mapped_column(String, nullable=True)
    asthma: Mapped[bool] = mapped_column(Boolean, nullable=False)
    intensive_care_unit: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    intensive_care_unit_when: Mapped[str | None] = mapped_column(String, nullable=True)
    ongoing_treatment: Mapped[str | None] = mapped_column(String, nullable=True)
    sicknesses: Mapped[str | None] = mapped_column(String, nullable=True)
    hospitalization: Mapped[str | None] = mapped_column(String, nullable=True)
    surgical_operation: Mapped[str | None] = mapped_column(String, nullable=True)
    trauma: Mapped[str | None] = mapped_column(String, nullable=True)
    family: Mapped[str | None] = mapped_column(String, nullable=True)
    participant: Mapped["Participant"] = relationship(back_populates="security_file")


class Participant(Base):
    __tablename__ = "raid_participant"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    firstname: Mapped[str] = mapped_column(String, nullable=False)
    birthday: Mapped[date] = mapped_column(Date, nullable=False)
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    phone: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    bike_size: Mapped[Size | None] = mapped_column(
        Enum(Size), nullable=True, default=None
    )
    t_shirt_size: Mapped[Size | None] = mapped_column(
        Enum(Size), nullable=True, default=None
    )
    situation: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    other_school: Mapped[str | None] = mapped_column(
        String, nullable=True, default=None
    )
    company: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    diet: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    id_card_id: Mapped[str | None] = mapped_column(
        ForeignKey("raid_document.id"), nullable=True, default=None
    )
    id_card: Mapped[Document] = relationship("Document", foreign_keys=[id_card_id])
    medical_certificate_id: Mapped[str | None] = mapped_column(
        ForeignKey("raid_document.id"), nullable=True, default=None
    )
    medical_certificate: Mapped[Document] = relationship(
        "Document", foreign_keys=[medical_certificate_id]
    )
    security_file_id: Mapped[str | None] = mapped_column(
        ForeignKey("raid_security_file.id"), nullable=True, default=None
    )
    security_file: Mapped[SecurityFile] = relationship(back_populates="participant")
    student_card_id: Mapped[str | None] = mapped_column(
        ForeignKey("raid_document.id"), nullable=True, default=None
    )
    student_card: Mapped[Document] = relationship(
        "Document", foreign_keys=[student_card_id]
    )
    raid_rules_id: Mapped[str | None] = mapped_column(
        ForeignKey("raid_document.id"), nullable=True, default=None
    )
    raid_rules: Mapped[Document] = relationship(
        "Document", foreign_keys=[raid_rules_id]
    )
    attestation_on_honour: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    payment: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Team(Base):
    __tablename__ = "raid_team"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    difficulty: Mapped[Difficulty] = mapped_column(Enum(Difficulty), nullable=True)
    captain_id: Mapped[str] = mapped_column(
        ForeignKey("raid_participant.id"), nullable=False
    )
    captain: Mapped[Participant] = relationship(
        "Participant", foreign_keys=[captain_id]
    )
    second_id: Mapped[str | None] = mapped_column(
        ForeignKey("raid_participant.id"), nullable=True
    )
    second: Mapped[Participant] = relationship("Participant", foreign_keys=[second_id])
    meeting_place: Mapped[MeetingPlace | None] = mapped_column(
        Enum(MeetingPlace), nullable=True
    )


class InviteToken(Base):
    __tablename__ = "raid_invite"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, index=True, nullable=False
    )
    team_id: Mapped[str] = mapped_column(ForeignKey("raid_team.id"), nullable=False)
    token: Mapped[str] = mapped_column(String, nullable=False)
