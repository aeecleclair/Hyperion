from pydantic import BaseModel

from app.core import schemas_core
from app.modules.sport_competition.types_sport_competition import Gender


class CompetitionEditionBase(BaseModel):
    name: str
    year: int
    start_date: str
    end_date: str
    activated: bool = True


class CompetitionEdition(CompetitionEditionBase):
    id: str


class SchoolExtension(BaseModel):
    id: str
    from_lyon: bool
    activated: bool = True

    school: schemas_core.CoreSchool
    general_quota: "SchoolGeneralQuota"


class SchoolExtensionEdit(BaseModel):
    id: str
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


class GroupBase(BaseModel):
    name: str
    description: str | None


class Group(GroupBase):
    id: str


class GroupComplete(Group):
    members: list[GroupMembership]


class GroupEdit(BaseModel):
    id: str
    name: str | None
    description: str | None


class SportBase(BaseModel):
    name: str
    team_size: int
    substitute_max: int | None
    gender: Gender | None
    activated: bool = True


class Sport(SportBase):
    id: str


class SportEdit(BaseModel):
    id: str
    name: str | None
    team_size: int | None
    substitute_max: int | None
    gender: Gender | None
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


class QuotaComplete(Quota):
    school: schemas_core.CoreSchool
    sport: Sport


class QuotaEdit(BaseModel):
    participant_quota: int | None
    team_quota: int | None


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
    id: str
    name: str | None
    captain_id: str | None


class TeamComplete(Team):
    school: schemas_core.CoreSchool
    sport: Sport
    captain: schemas_core.CoreUser
    users: list[schemas_core.CoreUser]


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


class ParticipantComplete(Participant):
    user: schemas_core.CoreUser
    sport: Sport
    team: Team | None
