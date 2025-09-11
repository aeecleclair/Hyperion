from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, NonNegativeInt, PositiveInt

from app.core.schools import schemas_schools
from app.core.users import schemas_users
from app.modules.sport_competition.types_sport_competition import SportCategory


class CompetitionEditionBase(BaseModel):
    name: str
    year: int
    start_date: datetime
    end_date: datetime
    active: bool = True


class CompetitionEdition(CompetitionEditionBase):
    id: UUID


class CompetitionEditionEdit(BaseModel):
    name: str | None = None
    year: PositiveInt | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    active: bool | None = None


class SchoolExtensionBase(BaseModel):
    school_id: UUID
    from_lyon: bool
    active: bool = True


class SchoolExtension(SchoolExtensionBase):
    school: schemas_schools.CoreSchool
    general_quota: "SchoolGeneralQuota"


class SchoolExtensionEdit(BaseModel):
    from_lyon: bool | None = None
    active: bool | None = None


class SchoolGeneralQuota(BaseModel):
    school_id: UUID
    edition_id: str
    athlete_quota: NonNegativeInt | None = None
    cameraman_quota: NonNegativeInt | None = None
    pompom_quota: NonNegativeInt | None = None
    fanfare_quota: NonNegativeInt | None = None
    non_athlete_quota: NonNegativeInt | None = None


class UserGroupMembership(BaseModel):
    user_id: str
    group_id: UUID
    edition_id: UUID


class GroupBase(BaseModel):
    name: str


class Group(GroupBase):
    id: UUID


class GroupComplete(Group):
    members: list[schemas_users.CoreUser]


class GroupEdit(BaseModel):
    name: str | None


class CompetitionUser(schemas_users.CoreUser):
    """
    A user with additional fields for competition purposes.
    This is used to represent a user in the context of a competition.
    """

    competition_category: SportCategory | None = None
    competition_groups: list[Group] = []


class SportBase(BaseModel):
    name: str
    team_size: PositiveInt
    substitute_max: NonNegativeInt | None = None
    sport_category: SportCategory | None = None
    active: bool = True


class Sport(SportBase):
    id: UUID


class SportEdit(BaseModel):
    name: str | None = None
    team_size: PositiveInt | None = None
    substitute_max: NonNegativeInt | None = None
    sport_category: SportCategory | None = None
    active: bool | None = None


class QuotaInfo(BaseModel):
    participant_quota: NonNegativeInt
    team_quota: NonNegativeInt


class Quota(BaseModel):
    school_id: UUID
    sport_id: UUID
    edition_id: UUID
    participant_quota: NonNegativeInt | None = None
    team_quota: NonNegativeInt | None = None


class QuotaEdit(BaseModel):
    participant_quota: NonNegativeInt | None = None
    team_quota: NonNegativeInt | None = None


class ParticipantInfo(BaseModel):
    license: str | None = None
    substitute: bool = False
    team_id: UUID | None = None


class Participant(BaseModel):
    user_id: str
    sport_id: UUID
    edition_id: UUID
    school_id: UUID
    license: str
    substitute: bool = False
    team_id: UUID | None = None
    validated: bool = False


class ParticipantEdit(BaseModel):
    license: str | None = None
    team_id: UUID | None = None
    sport_id: UUID | None = None
    user_id: str | None = None
    substitute: bool | None = None
    validated: bool | None = None


class ParticipantComplete(Participant):
    user: schemas_users.CoreUser


class TeamBase(BaseModel):
    name: str
    edition_id: UUID
    school_id: UUID
    sport_id: UUID
    captain_id: UUID


class TeamInfo(BaseModel):
    name: str
    school_id: UUID
    sport_id: UUID
    captain_id: UUID


class Team(TeamBase):
    id: UUID


class TeamEdit(BaseModel):
    name: str | None = None
    captain_id: str | None = None


class TeamComplete(Team):
    participants: list[ParticipantComplete]


class MatchBase(BaseModel):
    edition_id: UUID
    name: str
    sport_id: UUID
    team1_id: UUID
    team2_id: UUID
    date: datetime | None = None
    location: str | None = None
    score_team1: int | None = None
    score_team2: int | None = None
    winner_id: UUID | None = None


class Match(MatchBase):
    id: UUID
    team1: Team
    team2: Team


class MatchEdit(BaseModel):
    name: str | None = None
    sport_id: UUID | None = None
    team1_id: UUID | None = None
    team2_id: UUID | None = None
    date: datetime | None = None
    location: str | None = None
    score_team1: int | None = None
    score_team2: int | None = None
    winner_id: UUID | None = None


# Importing here to avoid circular imports
from app.core.groups.schemas_groups import CoreGroupSimple  # noqa: E402, TC001

CompetitionUser.model_rebuild()
