from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.core.schools import schemas_schools
from app.core.users import schemas_users
from app.modules.sport_competition.types_sport_competition import SportCategory


class CompetitionEditionBase(BaseModel):
    name: str
    year: int
    start_date: datetime
    end_date: datetime
    activated: bool = True


class CompetitionEdition(CompetitionEditionBase):
    id: UUID


class SchoolExtension(BaseModel):
    school_id: UUID
    from_lyon: bool
    activated: bool = True

    school: schemas_schools.CoreSchool
    general_quota: "SchoolGeneralQuota"


class SchoolExtensionEdit(BaseModel):
    from_lyon: bool | None
    activated: bool | None


class SchoolGeneralQuota(BaseModel):
    school_id: UUID
    edition: str
    athlete_quota: int | None
    cameraman_quota: int | None
    pompom_quota: int | None
    fanfare_quota: int | None
    non_athlete_quota: int | None


class GroupMembership(BaseModel):
    user: schemas_users.CoreUser
    edition_id: UUID


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


class SportBase(BaseModel):
    name: str
    team_size: int
    substitute_max: int | None
    sport_category: SportCategory | None
    activated: bool = True


class Sport(SportBase):
    id: UUID


class SportEdit(BaseModel):
    name: str | None
    team_size: int | None
    substitute_max: int | None
    sport_category: SportCategory | None
    activated: bool | None


class QuotaInfo(BaseModel):
    participant_quota: int
    team_quota: int


class Quota(BaseModel):
    school_id: UUID
    sport_id: UUID
    edition_id: UUID
    participant_quota: int
    team_quota: int


class QuotaEdit(BaseModel):
    participant_quota: int | None
    team_quota: int | None


class ParticipantInfo(BaseModel):
    license: str
    substitute: bool = False
    team_id: UUID | None


class Participant(BaseModel):
    user_id: str
    sport_id: UUID
    edition_id: UUID
    license: str
    substitute: bool = False
    team_id: UUID | None


class ParticipantEdit(BaseModel):
    license: str | None
    team_id: UUID | None
    sport_id: UUID | None
    user_id: str | None
    substitute: bool | None
    validated: bool | None


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
    school_id: UUID | None
    sport_id: UUID | None
    captain_id: UUID | None


class Team(TeamBase):
    id: UUID


class TeamEdit(BaseModel):
    name: str | None
    captain_id: str | None


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
    name: str | None
    sport_id: UUID | None
    team1_id: UUID | None
    team2_id: UUID | None
    date: datetime | None
    location: str | None
    score_team1: int | None
    score_team2: int | None
    winner_id: UUID | None
