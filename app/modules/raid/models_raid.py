"""Models file for module_raid"""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import ForeignKey, ForeignKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.users.models_users import CoreUser
from app.modules.raid.raid_type import (
    Difficulty,
    DocumentType,
    DocumentValidation,
    MeetingPlace,
    RaidRegistrationStatus,
    Situation,
    Size,
)
from app.types.sqlalchemy import Base, PrimaryKey


class RaidEdition(Base):
    __tablename__ = "raid_edition"

    id: Mapped[PrimaryKey]
    year: Mapped[int]
    name: Mapped[str]
    start_date: Mapped[date | None]
    end_date: Mapped[date | None]
    registering_end_date: Mapped[date | None]
    active: Mapped[bool]
    inscription_enabled: Mapped[bool]


class Document(Base):
    __tablename__ = "raid_document"
    id: Mapped[str] = mapped_column(
        primary_key=True,
        index=True,
    )
    edition_id: Mapped[UUID] = mapped_column(ForeignKey("raid_edition.id"))
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
    edition_id: Mapped[UUID] = mapped_column(ForeignKey("raid_edition.id"))
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
    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
        primary_key=True,
        index=True,
    )
    edition_id: Mapped[UUID] = mapped_column(
        ForeignKey("raid_edition.id"),
        primary_key=True,
    )
    status: Mapped[RaidRegistrationStatus] = mapped_column(
        default=RaidRegistrationStatus.draft,
    )
    address: Mapped[str | None] = mapped_column(default=None)
    bike_size: Mapped[Size | None] = mapped_column(default=None)
    t_shirt_size: Mapped[Size | None] = mapped_column(default=None)
    situation: Mapped[Situation | None] = mapped_column(default=None)
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
    attestation_on_honour: Mapped[bool] = mapped_column(default=False)
    payment: Mapped[bool] = mapped_column(default=False)
    t_shirt_payment: Mapped[bool] = mapped_column(default=False)
    is_minor: Mapped[bool] = mapped_column(default=False)

    user: Mapped[CoreUser] = relationship(
        "CoreUser",
        lazy="joined",
        init=False,
    )


class RaidTeam(Base):
    __tablename__ = "raid_team"
    id: Mapped[str] = mapped_column(
        primary_key=True,
        index=True,
    )
    edition_id: Mapped[UUID] = mapped_column(ForeignKey("raid_edition.id"))
    name: Mapped[str]
    difficulty: Mapped[Difficulty | None]
    captain_id: Mapped[str]
    second_id: Mapped[str | None] = mapped_column(default=None)
    number: Mapped[int | None] = mapped_column(default=None)
    captain: Mapped[RaidParticipant] = relationship(
        "RaidParticipant",
        foreign_keys="[RaidTeam.captain_id, RaidTeam.edition_id]",
        init=False,
        overlaps="second",
    )
    second: Mapped[RaidParticipant | None] = relationship(
        "RaidParticipant",
        foreign_keys="[RaidTeam.second_id, RaidTeam.edition_id]",
        init=False,
        overlaps="captain",
    )
    meeting_place: Mapped[MeetingPlace | None] = mapped_column(default=None)
    file_id: Mapped[str | None] = mapped_column(default=None)

    __table_args__ = (
        ForeignKeyConstraint(
            ["captain_id", "edition_id"],
            ["raid_participant.user_id", "raid_participant.edition_id"],
            name="fk_raid_team_captain",
        ),
        ForeignKeyConstraint(
            ["second_id", "edition_id"],
            ["raid_participant.user_id", "raid_participant.edition_id"],
            name="fk_raid_team_second",
        ),
    )


class InviteToken(Base):
    __tablename__ = "raid_invite"
    id: Mapped[str] = mapped_column(
        primary_key=True,
        index=True,
    )
    edition_id: Mapped[UUID] = mapped_column(ForeignKey("raid_edition.id"))
    team_id: Mapped[str] = mapped_column(ForeignKey("raid_team.id"))
    token: Mapped[str]


class RaidParticipantCheckout(Base):
    __tablename__ = "raid_participant_checkout"
    id: Mapped[str] = mapped_column(
        primary_key=True,
        index=True,
    )
    participant_user_id: Mapped[str]
    edition_id: Mapped[UUID]
    checkout_id: Mapped[str] = mapped_column(ForeignKey("checkout_checkout.id"))

    __table_args__ = (
        ForeignKeyConstraint(
            ["participant_user_id", "edition_id"],
            ["raid_participant.user_id", "raid_participant.edition_id"],
            name="fk_raid_participant_checkout_participant",
        ),
    )


class RaidVolunteer(Base):
    __tablename__ = "raid_volunteer"
    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
        primary_key=True,
    )
    edition_id: Mapped[UUID] = mapped_column(
        ForeignKey("raid_edition.id"),
        primary_key=True,
    )
    created_at: Mapped[datetime]
    validated: Mapped[bool]
    cancelled: Mapped[bool]
    diet: Mapped[str | None] = mapped_column(default=None)
    allergy: Mapped[str | None] = mapped_column(default=None)
    t_shirt_size: Mapped[Size | None] = mapped_column(default=None)
    emergency_person_name: Mapped[str | None] = mapped_column(default=None)
    emergency_person_phone: Mapped[str | None] = mapped_column(default=None)
    has_car: Mapped[bool] = mapped_column(default=False)
    car_seats: Mapped[int | None] = mapped_column(default=None)
    is_special_driver: Mapped[bool] = mapped_column(default=False)
    is_utility_vehicle_driver: Mapped[bool] = mapped_column(default=False)
    is_parcours_helper: Mapped[bool] = mapped_column(default=False)

    user: Mapped[CoreUser] = relationship(
        "CoreUser",
        lazy="joined",
        init=False,
    )
