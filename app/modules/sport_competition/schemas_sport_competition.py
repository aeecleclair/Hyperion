from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, NonNegativeInt, PositiveInt, model_validator

from app.core.schools import schemas_schools
from app.core.users import schemas_users
from app.modules.sport_competition.types_sport_competition import (
    CompetitionGroupType,
    InvalidUserType,
    ProductPublicType,
    ProductSchoolType,
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
    ffsu_id: str | None = None
    active: bool = True
    inscription_enabled: bool = False


class SchoolExtension(SchoolExtensionBase):
    school: schemas_schools.CoreSchool


class SchoolExtensionEdit(BaseModel):
    from_lyon: bool | None = None
    ffsu_id: str | None = None
    active: bool | None = None
    inscription_enabled: bool | None = None


class SchoolGeneralQuotaBase(BaseModel):
    athlete_quota: NonNegativeInt | None = None
    cameraman_quota: NonNegativeInt | None = None
    pompom_quota: NonNegativeInt | None = None
    fanfare_quota: NonNegativeInt | None = None
    athlete_cameraman_quota: NonNegativeInt | None = None
    athlete_pompom_quota: NonNegativeInt | None = None
    athlete_fanfare_quota: NonNegativeInt | None = None
    non_athlete_cameraman_quota: NonNegativeInt | None = None
    non_athlete_pompom_quota: NonNegativeInt | None = None
    non_athlete_fanfare_quota: NonNegativeInt | None = None


class SchoolGeneralQuota(SchoolGeneralQuotaBase):
    school_id: UUID
    edition_id: UUID


class UserGroupMembership(BaseModel):
    user_id: str
    group: CompetitionGroupType
    edition_id: UUID


class UserGroupMembershipComplete(UserGroupMembership):
    user: schemas_users.CoreUser


class CompetitionUserBase(BaseModel):
    sport_category: SportCategory
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


class SportQuotaInfo(BaseModel):
    participant_quota: NonNegativeInt | None = None
    team_quota: NonNegativeInt | None = None


class SchoolSportQuota(SportQuotaInfo):
    school_id: UUID
    sport_id: UUID
    edition_id: UUID


class SchoolSportQuotaEdit(BaseModel):
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
    license: str | None = None
    certificate_file_id: UUID | None = None
    is_license_valid: bool
    substitute: bool = False
    team_id: UUID


class ParticipantEdit(BaseModel):
    license: str | None = None
    team_id: UUID | None = None
    sport_id: UUID | None = None
    user_id: str | None = None
    substitute: bool | None = None


class ParticipantComplete(Participant):
    user: CompetitionUser
    team: "Team"


class TeamBase(BaseModel):
    name: str
    edition_id: UUID
    school_id: UUID
    sport_id: UUID
    captain_id: str


class TeamInfo(BaseModel):
    name: str
    school_id: UUID
    sport_id: UUID
    captain_id: str


class Team(TeamBase):
    id: UUID
    created_at: datetime


class TeamEdit(BaseModel):
    name: str | None = None
    captain_id: str | None = None


class TeamComplete(Team):
    participants: list[ParticipantComplete]


class LocationBase(BaseModel):
    name: str
    description: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class Location(LocationBase):
    id: UUID
    edition_id: UUID


class LocationComplete(Location):
    matches: list["MatchComplete"] = []


class LocationEdit(BaseModel):
    name: str | None = None
    description: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class MatchBase(BaseModel):
    name: str
    team1_id: UUID
    team2_id: UUID
    location_id: UUID
    date: datetime
    score_team1: int | None = None
    score_team2: int | None = None
    winner_id: UUID | None = None


class Match(MatchBase):
    id: UUID
    sport_id: UUID
    edition_id: UUID


class MatchComplete(Match):
    team1: Team
    team2: Team
    location: Location


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


class TeamSportResultBase(BaseModel):
    school_id: UUID
    sport_id: UUID
    team_id: UUID
    points: NonNegativeInt


class TeamSportResult(TeamSportResultBase):
    edition_id: UUID
    rank: PositiveInt


class TeamSportResultComplete(TeamSportResult):
    team: Team


class SportPodiumRankings(BaseModel):
    rankings: list[TeamSportResultBase]


class SchoolResult(BaseModel):
    school_id: UUID
    total_points: NonNegativeInt


class ProductVariantBase(BaseModel):
    product_id: UUID
    name: str
    description: str | None = None
    price: int
    enabled: bool = True
    unique: bool
    school_type: ProductSchoolType
    public_type: ProductPublicType | None = None


class ProductVariant(ProductVariantBase):
    edition_id: UUID
    id: UUID


class ProductVariantEdit(BaseModel):
    name: str | None = None
    description: str | None = None
    price: int | None = None
    enabled: bool | None = None
    unique: bool | None = None
    school_type: ProductSchoolType | None = None
    public_type: ProductPublicType | None = None


class ProductBase(BaseModel):
    name: str
    required: bool = False
    description: str | None = None


class Product(ProductBase):
    id: UUID
    edition_id: UUID


class ProductComplete(Product):
    variants: list[ProductVariant] = []


class ProductVariantComplete(ProductVariant):
    product: Product


class ProductEdit(BaseModel):
    name: str | None = None
    required: bool | None = None
    description: str | None = None


class SchoolProductQuotaBase(BaseModel):
    product_id: UUID
    quota: NonNegativeInt


class SchoolProductQuota(SchoolProductQuotaBase):
    school_id: UUID
    edition_id: UUID


class SchoolProductQuotaEdit(BaseModel):
    quota: NonNegativeInt


class PurchaseBase(BaseModel):
    product_variant_id: UUID
    quantity: int


class Purchase(PurchaseBase):
    user_id: str
    edition_id: UUID
    validated: bool
    purchased_on: datetime


class PurchaseComplete(Purchase):
    product_variant: ProductVariant


class PurchaseEdit(BaseModel):
    quantity: int | None = None


class PaymentBase(BaseModel):
    total: NonNegativeInt


class PaymentComplete(PaymentBase):
    id: UUID
    user_id: str
    edition_id: UUID


class PaymentUrl(BaseModel):
    url: str


class Checkout(BaseModel):
    id: UUID
    user_id: str
    edition_id: UUID
    checkout_id: UUID


class VolunteerShiftBase(BaseModel):
    name: str
    description: str | None = None
    value: PositiveInt
    start_time: datetime
    end_time: datetime
    location: str | None = None
    max_volunteers: PositiveInt


class VolunteerShift(VolunteerShiftBase):
    id: UUID
    edition_id: UUID


class VolunteerShiftComplete(VolunteerShift):
    registrations: list["VolunteerRegistrationWithUser"] = []


class VolunteerShiftEdit(BaseModel):
    name: str | None = None
    description: str | None = None
    value: PositiveInt | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    location: str | None = None
    max_volunteers: PositiveInt | None = None


class VolunteerRegistration(BaseModel):
    user_id: str
    edition_id: UUID
    shift_id: UUID
    registered_at: datetime
    validated: bool


class VolunteerRegistrationWithUser(VolunteerRegistration):
    user: CompetitionUser


class VolunteerRegistrationComplete(VolunteerRegistration):
    shift: VolunteerShift
