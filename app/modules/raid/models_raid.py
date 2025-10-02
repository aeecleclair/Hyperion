"""Models file for module_raid"""

from datetime import date, datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules.raid.raid_type import (
    Difficulty,
    DocumentType,
    DocumentValidation,
    MeetingPlace,
    Size,
)
from app.types.sqlalchemy import Base


class Document(Base):
    __tablename__ = "raid_document"
    id: Mapped[str] = mapped_column(
        primary_key=True,
        index=True,
    )
    name: Mapped[str]
    uploaded_at: Mapped[date]
    type: Mapped[DocumentType]
    validation: Mapped[DocumentValidation] = mapped_column(
        default=DocumentValidation.pending,
    )


class SecurityFile(Base):
    __tablename__ = "raid_security_file"
    id: Mapped[str] = mapped_column(
        primary_key=True,
        index=True,
    )
    allergy: Mapped[str | None]
    asthma: Mapped[bool]
    intensive_care_unit: Mapped[bool | None]
    intensive_care_unit_when: Mapped[str | None]
    ongoing_treatment: Mapped[str | None]
    sicknesses: Mapped[str | None]
    hospitalization: Mapped[str | None]
    surgical_operation: Mapped[str | None]
    trauma: Mapped[str | None]
    family: Mapped[str | None]
    participant: Mapped["RaidParticipant"] = relationship(
        back_populates="security_file",
        init=False,
    )
    emergency_person_firstname: Mapped[str | None]
    emergency_person_name: Mapped[str | None]
    emergency_person_phone: Mapped[str | None]
    file_id: Mapped[str | None]

    @property
    def validation(self) -> DocumentValidation:
        validated_fields = 0
        if self.emergency_person_firstname:
            validated_fields += 1
        if self.emergency_person_name:
            validated_fields += 1
        if self.emergency_person_phone:
            validated_fields += 1
        if validated_fields == 0:
            return DocumentValidation.refused
        if validated_fields == 3:
            return DocumentValidation.accepted
        return DocumentValidation.temporary


class RaidParticipant(Base):
    __tablename__ = "raid_participant"
    id: Mapped[str] = mapped_column(
        primary_key=True,
        index=True,
    )
    name: Mapped[str]
    firstname: Mapped[str]
    birthday: Mapped[date]
    phone: Mapped[str]
    email: Mapped[str]
    address: Mapped[str | None] = mapped_column(default=None)
    bike_size: Mapped[Size | None] = mapped_column(default=None)
    t_shirt_size: Mapped[Size | None] = mapped_column(default=None)
    situation: Mapped[str | None] = mapped_column(default=None)
    other_school: Mapped[str | None] = mapped_column(default=None)
    company: Mapped[str | None] = mapped_column(default=None)
    diet: Mapped[str | None] = mapped_column(default=None)
    id_card_id: Mapped[str | None] = mapped_column(
        ForeignKey("raid_document.id"),
        default=None,
    )
    id_card: Mapped[Document | None] = relationship(
        "app.modules.raid.models_raid.Document",
        foreign_keys=[id_card_id],
        init=False,
    )
    medical_certificate_id: Mapped[str | None] = mapped_column(
        ForeignKey("raid_document.id"),
        default=None,
    )
    medical_certificate: Mapped[Document | None] = relationship(
        "app.modules.raid.models_raid.Document",
        foreign_keys=[medical_certificate_id],
        init=False,
    )
    security_file_id: Mapped[str | None] = mapped_column(
        ForeignKey("raid_security_file.id"),
        default=None,
    )
    security_file: Mapped[SecurityFile | None] = relationship(
        back_populates="participant",
        init=False,
    )
    student_card_id: Mapped[str | None] = mapped_column(
        ForeignKey("raid_document.id"),
        default=None,
    )
    student_card: Mapped[Document | None] = relationship(
        "app.modules.raid.models_raid.Document",
        foreign_keys=[student_card_id],
        init=False,
    )
    raid_rules_id: Mapped[str | None] = mapped_column(
        ForeignKey("raid_document.id"),
        default=None,
    )
    raid_rules: Mapped[Document | None] = relationship(
        "app.modules.raid.models_raid.Document",
        foreign_keys=[raid_rules_id],
        init=False,
    )
    parent_authorization_id: Mapped[str | None] = mapped_column(
        ForeignKey("raid_document.id"),
        default=None,
    )
    parent_authorization: Mapped[Document | None] = relationship(
        "app.modules.raid.models_raid.Document",
        foreign_keys=[parent_authorization_id],
        init=False,
    )
    attestation_on_honour: Mapped[bool] = mapped_column(
        default=False,
    )
    payment: Mapped[bool] = mapped_column(default=False)
    t_shirt_payment: Mapped[bool] = mapped_column(
        default=False,
    )
    is_minor: Mapped[bool] = mapped_column(default=False)

    @property
    def number_of_document(self) -> int:
        number_total = 3
        if self.situation and self.situation.split(" : ")[0] in [
            "centrale",
            "otherschool",
        ]:
            number_total += 1
        if self.is_minor:
            number_total += 1
        return number_total

    @property
    def number_of_validated_document(self) -> int:
        number_validated = 0
        if (
            self.situation
            and self.situation.split(" : ")[0] in ["centrale", "otherschool"]
            and self.student_card
            and self.student_card.validation == DocumentValidation.accepted
        ):
            number_validated += 1
        if self.id_card and self.id_card.validation == DocumentValidation.accepted:
            number_validated += 1
        if (
            self.medical_certificate
            and self.medical_certificate.validation == DocumentValidation.accepted
        ):
            number_validated += 1
        if (
            self.raid_rules
            and self.raid_rules.validation == DocumentValidation.accepted
        ):
            number_validated += 1
        if (
            self.is_minor
            and self.parent_authorization
            and self.parent_authorization.validation == DocumentValidation.accepted
        ):
            number_validated += 1
        return number_validated

    @property
    def validation_progress(self) -> float:
        number_total = 10
        conditions = [
            self.address,
            self.bike_size,
            self.t_shirt_size,
            self.situation,
            self.attestation_on_honour,
        ]
        number_validated: float = sum(
            [condition is not None for condition in conditions],
        )
        if self.situation and self.situation.split(" : ")[0] in [
            "centrale",
            "otherschool",
        ]:
            number_total += 1
            if (
                self.student_card
                and self.student_card.validation == DocumentValidation.accepted
            ):
                number_validated += 1
        if self.is_minor:
            number_total += 1
            if self.parent_authorization:
                if self.parent_authorization.validation == DocumentValidation.accepted:
                    number_validated += 1
                elif (
                    self.parent_authorization.validation == DocumentValidation.temporary
                ):
                    number_validated += 0.5
        if self.id_card and self.id_card.validation == DocumentValidation.accepted:
            number_validated += 1
        if self.medical_certificate:
            if self.medical_certificate.validation == DocumentValidation.accepted:
                number_validated += 1
            elif self.medical_certificate.validation == DocumentValidation.temporary:
                number_validated += 0.5
        if self.security_file and self.security_file:
            if self.security_file.validation == DocumentValidation.accepted:
                number_validated += 1
            elif self.security_file.validation == DocumentValidation.temporary:
                number_validated += 0.5
        if (
            self.raid_rules
            and self.raid_rules.validation == DocumentValidation.accepted
        ):
            number_validated += 1
        return (number_validated / number_total) * 100


class RaidTeam(Base):
    __tablename__ = "raid_team"
    id: Mapped[str] = mapped_column(
        primary_key=True,
        index=True,
    )
    name: Mapped[str]
    difficulty: Mapped[Difficulty | None]
    captain_id: Mapped[str] = mapped_column(
        ForeignKey("raid_participant.id"),
    )
    second_id: Mapped[str | None] = mapped_column(
        ForeignKey("raid_participant.id"),
        default=None,
    )
    number: Mapped[int | None] = mapped_column(default=None)
    captain: Mapped[RaidParticipant] = relationship(
        "RaidParticipant",
        foreign_keys=[captain_id],
        init=False,
    )
    second: Mapped[RaidParticipant] = relationship(
        "RaidParticipant",
        foreign_keys=[second_id],
        init=False,
    )
    meeting_place: Mapped[MeetingPlace | None] = mapped_column(default=None)
    file_id: Mapped[str | None] = mapped_column(default=None)

    @property
    def validation_progress(self) -> float:
        number_validated = 0
        number_total = 2
        if self.difficulty:
            number_validated += 1
        if self.meeting_place:
            number_validated += 1
        return (number_validated / number_total) * 10 + (
            self.captain.validation_progress
            + (self.second.validation_progress if self.second else 0)
        ) * 0.45


class InviteToken(Base):
    __tablename__ = "raid_invite"
    id: Mapped[str] = mapped_column(
        primary_key=True,
        index=True,
    )
    team_id: Mapped[str] = mapped_column(ForeignKey("raid_team.id"))
    token: Mapped[str]


class RaidParticipantCheckout(Base):
    __tablename__ = "raid_participant_checkout"
    id: Mapped[str] = mapped_column(
        primary_key=True,
        index=True,
    )
    participant_id: Mapped[str] = mapped_column(
        ForeignKey("raid_participant.id"),
    )
    checkout_id: Mapped[str] = mapped_column(ForeignKey("payment_checkout.id"))


#################################### MODELS FOR CHRONO RAID ####################################


class Temps(Base):
    __tablename__ = "chrono_raid_temps"
    id: Mapped[str] = mapped_column(
        primary_key=True,
        index=True,
    )
    dossard: Mapped[int]
    date: Mapped[datetime]
    parcours: Mapped[str]
    ravito: Mapped[str]
    status: Mapped[bool]
    last_modification_date: Mapped[datetime]


class Remark(Base):
    __tablename__ = "chrono_raid_remaks"
    id: Mapped[str] = mapped_column(
        primary_key=True,
        index=True,
    )
    date: Mapped[datetime]
    ravito: Mapped[str]
    text: Mapped[str]
