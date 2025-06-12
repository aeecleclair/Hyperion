from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.schools.models_schools import CoreSchool
from app.core.users.models_users import CoreUser
from app.modules.sport_competition.types_sport_competition import SportCategory
from app.types.sqlalchemy import Base, PrimaryKey


class CompetitionEdition(Base):
    __tablename__ = "competition_edition"

    id: Mapped[PrimaryKey]
    year: Mapped[int]
    name: Mapped[str]
    start_date: Mapped[datetime]
    end_date: Mapped[datetime]
    activated: Mapped[bool]


class CompetitionGroup(Base):
    __tablename__ = "competition_group"

    id: Mapped[PrimaryKey]
    name: Mapped[str] = mapped_column(unique=True)

    members: Mapped[list["CompetitionUser"]] = relationship(
        "CompetitionUser",
        secondary="competition_edition_group_membership",
        back_populates="competition_groups",
        primaryjoin="EditionGroupMembership.group_id == CompetitionGroup.id",
        secondaryjoin="CompetitionUser.user_id == EditionGroupMembership.user_id",
        default_factory=list,
    )


class EditionGroupMembership(Base):
    __tablename__ = "competition_edition_group_membership"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("competition_user.user_id"),
        primary_key=True,
    )
    group_id: Mapped[UUID] = mapped_column(
        ForeignKey("competition_group.id"),
        primary_key=True,
    )
    edition_id: Mapped[UUID] = mapped_column(
        ForeignKey("competition_edition.id"),
        primary_key=True,
    )


class CompetitionUser(Base):
    __tablename__ = "competition_user"

    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), primary_key=True)
    sport_category: Mapped[SportCategory | None]

    user: Mapped[CoreUser] = relationship(
        "CoreUser",
        lazy="joined",
        init=False,
    )
    competition_groups: Mapped[list[CompetitionGroup]] = relationship(
        "CompetitionGroup",
        secondary="competition_edition_group_membership",
        primaryjoin="EditionGroupMembership.user_id == CompetitionUser.user_id",
        back_populates="members",
        lazy="selectin",
        default_factory=list,
    )


class Sport(Base):
    __tablename__ = "competition_sport"

    id: Mapped[PrimaryKey]
    activated: Mapped[bool]
    name: Mapped[str]
    team_size: Mapped[int]
    substitute_max: Mapped[int | None]
    sport_category: Mapped[SportCategory | None]


class SchoolExtension(Base):
    __tablename__ = "competition_school_extension"

    school_id: Mapped[PrimaryKey] = mapped_column(
        ForeignKey("core_school.id"),
    )
    from_lyon: Mapped[bool]
    activated: Mapped[bool]

    school: Mapped[CoreSchool] = relationship(
        "CoreSchool",
        lazy="selectin",
        init=False,
    )
    general_quota: Mapped["SchoolGeneralQuota"] = relationship(
        "SchoolGeneralQuota",
        lazy="selectin",
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
    non_athlete_quota: Mapped[int | None]


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


class Team(Base):
    __tablename__ = "competition_team"

    id: Mapped[PrimaryKey]
    sport_id: Mapped[UUID] = mapped_column(ForeignKey("competition_sport.id"))
    school_id: Mapped[UUID] = mapped_column(
        ForeignKey("competition_school_extension.school_id"),
    )
    edition_id: Mapped[UUID] = mapped_column(
        ForeignKey("competition_edition.id"),
    )
    name: Mapped[str]
    captain_id: Mapped[str] = mapped_column(ForeignKey("competition_user.user_id"))

    participants: Mapped[list["Participant"]] = relationship(
        "Participant",
        lazy="selectin",
        viewonly=True,
        init=False,
    )


class Participant(Base):
    __tablename__ = "competition_participant"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("competition_user.user_id"),
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
    # We duplicate school_id data to avoid horrible select queries
    school_id: Mapped[UUID] = mapped_column(
        ForeignKey("competition_school_extension.school_id"),
    )
    team_id: Mapped[UUID | None] = mapped_column(ForeignKey("competition_team.id"))
    substitute: Mapped[bool]
    license: Mapped[str | None]
    validated: Mapped[bool]

    user: Mapped[CoreUser] = relationship(
        "CompetitionUser",
        lazy="joined",
        init=False,
    )


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
    location: Mapped[str | None]
    score_team1: Mapped[int | None]
    score_team2: Mapped[int | None]
    winner_id: Mapped[UUID | None] = mapped_column(ForeignKey("competition_team.id"))

    team1: Mapped[Team] = relationship(
        "Team",
        foreign_keys=[team1_id],
        lazy="selectin",
        init=False,
    )
    team2: Mapped[Team] = relationship(
        "Team",
        foreign_keys=[team2_id],
        lazy="selectin",
        init=False,
    )
