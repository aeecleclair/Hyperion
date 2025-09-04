from datetime import datetime

from pydantic import BaseModel

from app.core import schemas_core
from app.core.models_core import CoreUser
from app.modules.sport_competition.types_sport_competition import SportCategory


class CompetitionEditionBase(BaseModel):
    name: str
    year: int
    start_date: datetime
    end_date: datetime
    activated: bool = True


class CompetitionEdition(CompetitionEditionBase):
    id: str


class SchoolExtension(BaseModel):
    school_id: str
    from_lyon: bool
    activated: bool = True

    school: schemas_core.CoreSchool
    general_quota: "SchoolGeneralQuota"


class SchoolExtensionEdit(BaseModel):
    from_lyon: bool | None
    activated: bool | None


class SchoolGeneralQuota(BaseModel):
    school_id: str
    edition: str
    athlete_quota: int | None
    cameraman_quota: int | None
    pompom_quota: int | None
    fanfare_quota: int | None
    non_athlete_quota: int | None


class GroupMembership(BaseModel):
    user: schemas_core.CoreUser
    edition_id: str


class UserGroupMembership(BaseModel):
    user_id: str
    group_id: str
    edition_id: str


class GroupBase(BaseModel):
    name: str


class Group(GroupBase):
    id: str


class GroupComplete(Group):
    members: list[CoreUser]


class GroupEdit(BaseModel):
    name: str | None


class SportBase(BaseModel):
    name: str
    team_size: int
    substitute_max: int | None
    sport_category: SportCategory | None
    activated: bool = True


class Sport(SportBase):
    id: str


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
    school_id: str
    sport_id: str
    edition_id: str
    participant_quota: int
    team_quota: int


class QuotaEdit(BaseModel):
    participant_quota: int | None
    team_quota: int | None


class ParticipantInfo(BaseModel):
    license: str
    substitute: bool = False
    team_id: str | None


class Participant(BaseModel):
    user_id: str
    sport_id: str
    edition_id: str
    license: str
    substitute: bool = False
    team_id: str | None


class ParticipantEdit(BaseModel):
    license: str | None
    team_id: str | None
    sport_id: str | None
    user_id: str | None
    substitute: bool | None
    validated: bool | None


class ParticipantComplete(Participant):
    user: schemas_core.CoreUser


class TeamBase(BaseModel):
    name: str
    edition_id: str
    school_id: str
    sport_id: str
    captain_id: str


class TeamInfo(BaseModel):
    name: str
    school_id: str | None
    sport_id: str | None
    captain_id: str | None


class Team(TeamBase):
    id: str


class TeamEdit(BaseModel):
    name: str | None
    captain_id: str | None


class TeamComplete(Team):
    participants: list[ParticipantComplete]


class MatchBase(BaseModel):
    edition_id: str
    name: str
    sport_id: str
    team1_id: str
    team2_id: str
    date: datetime | None = None
    location: str | None = None
    score_team1: int | None = None
    score_team2: int | None = None
    winner_id: str | None = None


class Match(MatchBase):
    id: str
    team1: Team
    team2: Team


class MatchEdit(BaseModel):
    name: str | None
    sport_id: str | None
    team1_id: str | None
    team2_id: str | None
    date: datetime | None
    location: str | None
    score_team1: int | None
    score_team2: int | None
    winner_id: str | None
