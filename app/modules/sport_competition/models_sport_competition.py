from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, ForeignKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.schools.models_schools import CoreSchool
from app.core.users.models_users import CoreUser
from app.modules.sport_competition.types_sport_competition import (
    CompetitionGroupType,
    ProductPublicType,
    ProductSchoolType,
    SportCategory,
)
from app.types.sqlalchemy import Base, PrimaryKey


class CompetitionEdition(Base):
    __tablename__ = "competition_edition"

    id: Mapped[PrimaryKey]
    year: Mapped[int]
    name: Mapped[str]
    start_date: Mapped[datetime]
    end_date: Mapped[datetime]
    active: Mapped[bool]
    inscription_enabled: Mapped[bool]


class CompetitionGroupMembership(Base):
    __tablename__ = "competition_group_membership"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
        primary_key=True,
    )
    group: Mapped[CompetitionGroupType] = mapped_column(
        primary_key=True,
    )
    edition_id: Mapped[UUID] = mapped_column(
        ForeignKey("competition_edition.id"),
        primary_key=True,
    )


class CompetitionUser(Base):
    __tablename__ = "competition_user"

    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), primary_key=True)
    edition_id: Mapped[UUID] = mapped_column(
        ForeignKey("competition_edition.id"),
        primary_key=True,
    )
    sport_category: Mapped[SportCategory]
    validated: Mapped[bool]
    created_at: Mapped[datetime]
    is_pompom: Mapped[bool] = mapped_column(default=False)
    is_fanfare: Mapped[bool] = mapped_column(default=False)
    is_cameraman: Mapped[bool] = mapped_column(default=False)
    is_athlete: Mapped[bool] = mapped_column(default=False)
    is_volunteer: Mapped[bool] = mapped_column(default=False)

    user: Mapped[CoreUser] = relationship(
        "CoreUser",
        lazy="joined",
        init=False,
    )


class Sport(Base):
    __tablename__ = "competition_sport"

    id: Mapped[PrimaryKey]
    active: Mapped[bool]
    name: Mapped[str]
    team_size: Mapped[int]
    substitute_max: Mapped[int | None]
    sport_category: Mapped[SportCategory | None]


class SchoolExtension(Base):
    __tablename__ = "competition_school_extension"

    school_id: Mapped[PrimaryKey] = mapped_column(
        ForeignKey("core_school.id"),
    )
    ffsu_id: Mapped[str | None]
    from_lyon: Mapped[bool]
    active: Mapped[bool]
    inscription_enabled: Mapped[bool]

    school: Mapped[CoreSchool] = relationship(
        "CoreSchool",
        lazy="joined",
        init=False,
    )
    general_quota: Mapped["SchoolGeneralQuota | None"] = relationship(
        "SchoolGeneralQuota",
        lazy="selectin",
        init=False,
    )
    product_quotas: Mapped[list["SchoolProductQuota"]] = relationship(
        "SchoolProductQuota",
        lazy="selectin",
        default_factory=list,
        init=False,
    )


class SchoolGeneralQuota(Base):
    __tablename__ = "competition_school_general_quota"

    school_id: Mapped[UUID] = mapped_column(
        ForeignKey("competition_school_extension.school_id"),
        primary_key=True,
    )
    edition_id: Mapped[UUID] = mapped_column(
        ForeignKey("competition_edition.id"),
        primary_key=True,
    )
    athlete_quota: Mapped[int | None]
    cameraman_quota: Mapped[int | None]
    pompom_quota: Mapped[int | None]
    fanfare_quota: Mapped[int | None]
    athlete_cameraman_quota: Mapped[int | None]
    athlete_pompom_quota: Mapped[int | None]
    athlete_fanfare_quota: Mapped[int | None]
    non_athlete_cameraman_quota: Mapped[int | None]
    non_athlete_pompom_quota: Mapped[int | None]
    non_athlete_fanfare_quota: Mapped[int | None]


class SchoolSportQuota(Base):
    __tablename__ = "competition_sport_quota"

    sport_id: Mapped[UUID] = mapped_column(
        ForeignKey("competition_sport.id"),
        primary_key=True,
    )
    school_id: Mapped[UUID] = mapped_column(
        ForeignKey("competition_school_extension.school_id"),
        primary_key=True,
    )
    edition_id: Mapped[UUID] = mapped_column(
        ForeignKey("competition_edition.id"),
        primary_key=True,
    )
    participant_quota: Mapped[int | None]
    team_quota: Mapped[int | None]


class SchoolProductQuota(Base):
    __tablename__ = "competition_school_product_quota"

    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("competition_product.id"),
        primary_key=True,
    )
    school_id: Mapped[UUID] = mapped_column(
        ForeignKey("competition_school_extension.school_id"),
        primary_key=True,
    )
    edition_id: Mapped[UUID] = mapped_column(
        ForeignKey("competition_edition.id"),
        primary_key=True,
    )
    quota: Mapped[int | None]


class CompetitionTeam(Base):
    __tablename__ = "competition_team"

    id: Mapped[PrimaryKey]
    sport_id: Mapped[UUID] = mapped_column(ForeignKey("competition_sport.id"))
    school_id: Mapped[UUID] = mapped_column(
        ForeignKey("competition_school_extension.school_id"),
    )
    edition_id: Mapped[UUID] = mapped_column(ForeignKey("competition_edition.id"))
    name: Mapped[str]
    captain_id: Mapped[str]
    created_at: Mapped[datetime]

    participants: Mapped[list["CompetitionParticipant"]] = relationship(
        "CompetitionParticipant",
        lazy="selectin",
        viewonly=True,
        init=False,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["captain_id", "edition_id"],
            ["competition_user.user_id", "competition_user.edition_id"],
            name="fk_competition_team_captain",
        ),
    )


class CompetitionParticipant(Base):
    __tablename__ = "competition_participant"

    user_id: Mapped[str] = mapped_column(
        primary_key=True,
    )
    sport_id: Mapped[UUID] = mapped_column(
        ForeignKey("competition_sport.id"),
        primary_key=True,
    )
    edition_id: Mapped[UUID] = mapped_column(
        ForeignKey("competition_edition.id"),
        primary_key=True,
    )
    school_id: Mapped[UUID] = mapped_column(
        ForeignKey("competition_school_extension.school_id"),
    )
    team_id: Mapped[UUID] = mapped_column(ForeignKey("competition_team.id"))
    substitute: Mapped[bool]
    license: Mapped[str | None]
    is_licence_valid: Mapped[bool]

    user: Mapped[CompetitionUser] = relationship(
        "CompetitionUser",
        lazy="joined",
        init=False,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "edition_id"],
            ["competition_user.user_id", "competition_user.edition_id"],
            name="fk_competition_participant_user",
        ),
    )


class MatchLocation(Base):
    __tablename__ = "competition_location"

    id: Mapped[PrimaryKey]
    edition_id: Mapped[UUID] = mapped_column(
        ForeignKey("competition_edition.id"),
    )
    name: Mapped[str]
    address: Mapped[str | None]
    latitude: Mapped[float | None]
    longitude: Mapped[float | None]
    description: Mapped[str | None]


class Match(Base):
    __tablename__ = "competition_match"

    id: Mapped[PrimaryKey]
    sport_id: Mapped[UUID] = mapped_column(ForeignKey("competition_sport.id"))
    edition_id: Mapped[UUID] = mapped_column(
        ForeignKey("competition_edition.id"),
    )
    name: Mapped[str]
    team1_id: Mapped[UUID] = mapped_column(ForeignKey("competition_team.id"))
    team2_id: Mapped[UUID] = mapped_column(ForeignKey("competition_team.id"))
    date: Mapped[datetime | None]
    location_id: Mapped[UUID] = mapped_column(ForeignKey("competition_location.id"))
    score_team1: Mapped[int | None]
    score_team2: Mapped[int | None]
    winner_id: Mapped[UUID | None] = mapped_column(ForeignKey("competition_team.id"))

    team1: Mapped[CompetitionTeam] = relationship(
        "CompetitionTeam",
        foreign_keys=[team1_id],
        lazy="selectin",
        init=False,
    )
    team2: Mapped[CompetitionTeam] = relationship(
        "CompetitionTeam",
        foreign_keys=[team2_id],
        lazy="selectin",
        init=False,
    )
    location: Mapped[MatchLocation] = relationship(
        "MatchLocation",
        lazy="selectin",
        init=False,
    )


class SportPodium(Base):
    __tablename__ = "competition_sport_podium"

    sport_id: Mapped[UUID] = mapped_column(
        ForeignKey("competition_sport.id"),
        primary_key=True,
    )
    edition_id: Mapped[UUID] = mapped_column(
        ForeignKey("competition_edition.id"),
        primary_key=True,
    )
    school_id: Mapped[UUID] = mapped_column(
        ForeignKey("competition_school_extension.school_id"),
        primary_key=True,
    )
    points: Mapped[int]
    rank: Mapped[int]
    team_id: Mapped[UUID] = mapped_column(ForeignKey("competition_team.id"))

    team: Mapped[CompetitionTeam] = relationship(
        "CompetitionTeam",
        foreign_keys=[team_id],
        lazy="selectin",
        init=False,
    )


class CompetitionProduct(Base):
    __tablename__ = "competition_product"

    id: Mapped[PrimaryKey]
    edition_id: Mapped[UUID] = mapped_column(
        ForeignKey("competition_edition.id"),
    )
    name: Mapped[str]
    description: Mapped[str | None] = mapped_column(default=None)

    variants: Mapped[list["CompetitionProductVariant"]] = relationship(
        "CompetitionProductVariant",
        lazy="selectin",
        default_factory=list,
    )


class CompetitionProductVariant(Base):
    __tablename__ = "competition_product_variant"

    id: Mapped[PrimaryKey]
    edition_id: Mapped[UUID] = mapped_column(
        ForeignKey("competition_edition.id"),
    )
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("competition_product.id"),
    )
    name: Mapped[str]
    price: Mapped[int]
    enabled: Mapped[bool]
    unique: Mapped[bool]
    school_type: Mapped[ProductSchoolType]
    public_type: Mapped[ProductPublicType | None]
    description: Mapped[str | None] = mapped_column(default=None)


class CompetitionPurchase(Base):
    __tablename__ = "competition_purchase"

    user_id: Mapped[str] = mapped_column(
        primary_key=True,
    )
    product_variant_id: Mapped[UUID] = mapped_column(
        ForeignKey("competition_product_variant.id"),
        primary_key=True,
    )
    edition_id: Mapped[UUID] = mapped_column(
        ForeignKey("competition_edition.id"),
    )
    quantity: Mapped[int]
    validated: Mapped[bool]
    purchased_on: Mapped[datetime]

    product_variant: Mapped["CompetitionProductVariant"] = relationship(
        "CompetitionProductVariant",
        init=False,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "edition_id"],
            ["competition_user.user_id", "competition_user.edition_id"],
            name="fk_competition_purchase_user",
        ),
    )


class CompetitionPayment(Base):
    __tablename__ = "competition_payment"

    id: Mapped[PrimaryKey]
    user_id: Mapped[str]
    edition_id: Mapped[UUID] = mapped_column(
        ForeignKey("competition_edition.id"),
    )
    total: Mapped[int]

    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "edition_id"],
            ["competition_user.user_id", "competition_user.edition_id"],
            name="fk_competition_payment_user",
        ),
    )


class Checkout(Base):
    __tablename__ = "competition_checkout"
    id: Mapped[PrimaryKey]
    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
    )
    edition_id: Mapped[UUID] = mapped_column(
        ForeignKey("competition_edition.id"),
    )
    checkout_id: Mapped[UUID] = mapped_column(ForeignKey("payment_checkout.id"))
