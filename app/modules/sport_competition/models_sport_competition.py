from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.models_core import CoreSchool, CoreUser
from app.modules.sport_competition.types_sport_competition import Gender
from app.types.sqlalchemy import Base


class CompetitionGroup(Base):
    __tablename__ = "competition_group"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    description: Mapped[str | None]

    members: Mapped[list[CoreUser]] = relationship(
        "CoreUser",
        secondary="competition_annual_group_membership",
        lazy="selectin",
        viewonly=True,
        init=False,
    )


class AnnualGroupMembership(Base):
    __tablename__ = "competition_annual_group_membership"

    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), primary_key=True)
    group_id: Mapped[str] = mapped_column(
        ForeignKey("competition_group.id"),
        primary_key=True,
    )
    edition_id: Mapped[str] = mapped_column(
        ForeignKey("competition_edition.id"),
        primary_key=True,
    )


class SchoolExtension(Base):
    __tablename__ = "competition_school_extension"

    id: Mapped[str] = mapped_column(ForeignKey("core_school.id"), primary_key=True)
    from_lyon: Mapped[bool]
    activated: Mapped[bool]

    school: Mapped[CoreSchool] = relationship(
        "CoreSchool",
        lazy="joined",
        init=False,
    )
    general_quota: Mapped["SchoolGeneralQuota"] = relationship(
        "SchoolGeneralQuota",
        lazy="joined",
        init=False,
    )


class SchoolGeneralQuota(Base):
    __tablename__ = "competition_school_general_quota"

    school_id: Mapped[str] = mapped_column(
        ForeignKey("core_school.id"),
        primary_key=True,
    )
    edition_id: Mapped[str] = mapped_column(
        ForeignKey("competition_edition.id"),
        primary_key=True,
    )
    athlete_quota: Mapped[int | None]
    cameraman_quota: Mapped[int | None]
    pompom_quota: Mapped[int | None]
    fanfare_quota: Mapped[int | None]
    non_athlete_quota: Mapped[int | None]


class CompetitionEdition(Base):
    __tablename__ = "competition_edition"

    id: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int]
    name: Mapped[str]
    start_date: Mapped[str]
    end_date: Mapped[str]
    activated: Mapped[bool]


class Sport(Base):
    __tablename__ = "competition_sport"

    id: Mapped[str] = mapped_column(primary_key=True)
    activated: Mapped[bool]
    name: Mapped[str]
    team_size: Mapped[int]
    substitute_max: Mapped[int | None]
    gender: Mapped[Gender | None]


class Team(Base):
    __tablename__ = "competition_team"

    id: Mapped[str] = mapped_column(primary_key=True)
    sport_id: Mapped[str] = mapped_column(ForeignKey("competition_sport.id"))
    school_id: Mapped[str] = mapped_column(ForeignKey("core_school.id"))
    edition_id: Mapped[str] = mapped_column(
        ForeignKey("competition_edition.id"),
        primary_key=True,
    )
    name: Mapped[str]
    captain_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"))

    users: Mapped[list[CoreUser]] = relationship(
        "User",
        secondary="participants",
        lazy="selectin",
        viewonly=True,
        init=False,
    )
    sport: Mapped[Sport] = relationship(
        "Sport",
        lazy="joined",
        init=False,
    )
    school: Mapped[SchoolExtension] = relationship(
        "SchoolExtension",
        lazy="joined",
        init=False,
    )
    captain: Mapped[CoreUser] = relationship(
        "User",
        lazy="joined",
        init=False,
    )
    edition: Mapped[CompetitionEdition] = relationship(
        "CompetitionEdition",
        lazy="joined",
    )


class Participant(Base):
    __tablename__ = "competition_participant"

    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), primary_key=True)
    sport_id: Mapped[str] = mapped_column(
        ForeignKey("competition_sport.id"),
        primary_key=True,
    )
    edition_id: Mapped[str] = mapped_column(
        ForeignKey("competition_edition.id"),
        primary_key=True,
    )
    team_id: Mapped[str | None] = mapped_column(ForeignKey("competition_team.id"))
    captain: Mapped[bool]
    substitute: Mapped[bool]
    license: Mapped[str]

    user: Mapped[CoreUser] = relationship(
        "User",
        lazy="joined",
        init=False,
    )
    sport: Mapped[Sport] = relationship(
        "Sport",
        lazy="joined",
        init=False,
    )
    team: Mapped[Team] = relationship(
        "Team",
        lazy="joined",
        init=False,
    )
    edition: Mapped[CompetitionEdition] = relationship(
        "CompetitionEdition",
        lazy="joined",
    )


class SchoolSportQuota(Base):
    __tablename__ = "competition_sport_quota"

    sport_id: Mapped[str] = mapped_column(
        ForeignKey("competition_sport.id"),
        primary_key=True,
    )
    school_id: Mapped[str] = mapped_column(
        ForeignKey("core_school.id"),
        primary_key=True,
    )
    edition_id: Mapped[str] = mapped_column(
        ForeignKey("competition_edition.id"),
        primary_key=True,
    )
    participant_quota: Mapped[int]
    team_quota: Mapped[int]

    sport: Mapped[Sport] = relationship(
        "Sport",
        lazy="joined",
        init=False,
    )
    school: Mapped[SchoolExtension] = relationship(
        "SchoolExtension",
        lazy="joined",
        init=False,
    )
    edition: Mapped[CompetitionEdition] = relationship(
        "CompetitionEdition",
        lazy="joined",
        init=False,
    )
