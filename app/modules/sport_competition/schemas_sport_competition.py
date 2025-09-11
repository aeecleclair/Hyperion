from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, NonNegativeInt, PositiveInt, model_validator

from app.core.schools import schemas_schools
from app.core.users import schemas_users
from app.modules.sport_competition.types_sport_competition import (
    CompetitionGroupType,
    InvalidUserType,
    SportCategory,
)


class CompetitionEditionBase(BaseModel):
    name: str
    year: int
    start_date: datetime
    end_date: datetime
    active: bool = True
    inscription_enabled: bool = False


class CompetitionEdition(CompetitionEditionBase):
    id: UUID


class CompetitionEditionEdit(BaseModel):
    name: str | None = None
    year: PositiveInt | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None


class SchoolExtensionBase(BaseModel):
    school_id: UUID
    from_lyon: bool
    active: bool = True
    inscription_enabled: bool = False


class SchoolExtension(SchoolExtensionBase):
    school: schemas_schools.CoreSchool
    general_quota: "SchoolGeneralQuota | None" = None


class SchoolExtensionEdit(BaseModel):
    from_lyon: bool | None = None
    active: bool | None = None
    inscription_enabled: bool | None = None


class SchoolGeneralQuotaBase(BaseModel):
    athlete_quota: NonNegativeInt | None = None
    cameraman_quota: NonNegativeInt | None = None
    pompom_quota: NonNegativeInt | None = None
    fanfare_quota: NonNegativeInt | None = None
    non_athlete_quota: NonNegativeInt | None = None


class SchoolGeneralQuota(SchoolGeneralQuotaBase):
    school_id: UUID
    edition_id: UUID


class UserGroupMembership(BaseModel):
    user_id: str
    group: CompetitionGroupType
    edition_id: UUID


class CompetitionUserBase(BaseModel):
    sport_category: SportCategory | None = None
    is_pompom: bool = False
    is_fanfare: bool = False
    is_cameraman: bool = False
    is_athlete: bool = False
    is_volunteer: bool = False

    @model_validator(mode="after")
    def validate_sport_category(self) -> "CompetitionUserBase":
        if (
            sum(
                [
                    self.is_pompom,
                    self.is_fanfare,
                    self.is_cameraman,
                ],
            )
            > 1
        ):
            raise InvalidUserType("too_many")

        if not any(
            [
                self.is_pompom,
                self.is_fanfare,
                self.is_cameraman,
                self.is_athlete,
                self.is_volunteer,
            ],
        ):
            raise InvalidUserType("none")
        return self


class CompetitionUserSimple(CompetitionUserBase):
    user_id: str
    edition_id: UUID
    created_at: datetime
    validated: bool = False


class CompetitionUser(CompetitionUserSimple):
    """
    A user with additional fields for competition purposes.
    This is used to represent a user in the context of a competition.
    """

    user: schemas_users.CoreUser


class CompetitionUserEdit(BaseModel):
    sport_category: SportCategory | None = None
    validated: bool | None = None
    is_pompom: bool | None = None
    is_fanfare: bool | None = None
    is_cameraman: bool | None = None
    is_athlete: bool | None = None
    is_volunteer: bool | None = None


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


class ParticipantEdit(BaseModel):
    license: str | None = None
    team_id: UUID | None = None
    sport_id: UUID | None = None
    user_id: str | None = None
    substitute: bool | None = None
    validated: bool | None = None


class ParticipantComplete(Participant):
    user: CompetitionUser


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
    created_at: datetime


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
    location_id: UUID | None = None
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
    location_id: UUID | None = None
    score_team1: int | None = None
    score_team2: int | None = None
    winner_id: UUID | None = None


class SportPodiumBase(BaseModel):
    first_place_points: NonNegativeInt
    second_place_points: NonNegativeInt
    third_place_points: NonNegativeInt


class SportPodium(SportPodiumBase):
    sport_id: UUID
    edition_id: UUID
    team1_id: UUID | None = None
    team2_id: UUID | None = None
    team3_id: UUID | None = None
    user1_id: str | None = None
    user2_id: str | None = None
    user3_id: str | None = None


class SportPodiumComplete(SportPodium):
    team1: Team | None = None
    team2: Team | None = None
    team3: Team | None = None
    user1: schemas_users.CoreUser | None = None
    user2: schemas_users.CoreUser | None = None
    user3: schemas_users.CoreUser | None = None


class SportPodiumEdit(BaseModel):
    first_place_points: NonNegativeInt | None = None
    second_place_points: NonNegativeInt | None = None
    third_place_points: NonNegativeInt | None = None
    team1_id: UUID | None = None
    team2_id: UUID | None = None
    team3_id: UUID | None = None
    user1_id: str | None = None
    user2_id: str | None = None
    user3_id: str | None = None


# Importing here to avoid circular imports
from app.core.groups.schemas_groups import CoreGroupSimple  # noqa: E402, F401

CompetitionUser.model_rebuild()
