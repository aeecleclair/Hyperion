from datetime import date, datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    computed_field,
    field_validator,
    model_validator,
)

from app.core.users.schemas_users import CoreUser
from app.modules.raid.raid_type import (
    Difficulty,
    DocumentType,
    DocumentValidation,
    MeetingPlace,
    RaidRegistrationStatus,
    Situation,
    Size,
)
from app.modules.raid.utils.validation_checker import (
    compute_participant_progress,
    count_accepted_documents,
    count_total_required_documents,
)


class DocumentBase(BaseModel):
    type: DocumentType
    name: str
    id: str


class DocumentCreation(BaseModel):
    id: str


class DocumentUpdate(BaseModel):
    type: DocumentType | None = None
    name: str | None = None


class Document(DocumentBase):
    uploaded_at: date
    validation: DocumentValidation

    model_config = ConfigDict(from_attributes=True)


class SecurityFileBase(BaseModel):
    allergy: str | None = None
    asthma: bool
    intensive_care_unit: bool | None = None
    intensive_care_unit_when: str | None = None
    ongoing_treatment: str | None = None
    sicknesses: str | None = None
    hospitalization: str | None = None
    surgical_operation: str | None = None
    trauma: str | None = None
    family: str | None = None
    emergency_person_firstname: str | None = None
    emergency_person_name: str | None = None
    emergency_person_phone: str | None = None
    file_id: str | None = None


class SecurityFile(SecurityFileBase):
    validation: DocumentValidation
    id: str

    model_config = ConfigDict(from_attributes=True)


class RaidParticipantBase(BaseModel):
    """Shape used when the user first self-enrols.

    Identity fields (name, firstname, email, birthday, phone) are not here:
    they live on CoreUser and are read via the `user` relationship on the
    read schemas below.
    """


class RaidParticipantCreate(BaseModel):
    """Flat column-level payload used by the create CRUD."""

    user_id: str
    edition_id: UUID
    status: RaidRegistrationStatus
    address: str | None = None
    bike_size: Size | None = None
    t_shirt_size: Size | None = None
    situation: Situation | None = None
    other_school: str | None = None
    company: str | None = None
    diet: str | None = None
    id_card_id: str | None = None
    medical_certificate_id: str | None = None
    security_file_id: str | None = None
    student_card_id: str | None = None
    raid_rules_id: str | None = None
    parent_authorization_id: str | None = None
    attestation_on_honour: bool = False
    payment: bool = False
    t_shirt_payment: bool = False
    is_minor: bool = False


class RaidParticipantPreview(RaidParticipantBase):
    user_id: str
    edition_id: UUID
    status: RaidRegistrationStatus
    bike_size: Size | None = None
    t_shirt_size: Size | None = None
    situation: Situation | None = None
    payment: bool
    t_shirt_payment: bool
    user: CoreUser

    model_config = ConfigDict(from_attributes=True)


class RaidParticipant(RaidParticipantPreview):
    address: str | None = None
    other_school: str | None = None
    company: str | None = None
    diet: str | None = None
    id_card_id: str | None = None
    id_card: Document | None = None
    medical_certificate_id: str | None = None
    medical_certificate: Document | None = None
    security_file_id: str | None = None
    security_file: SecurityFile | None = None
    student_card_id: str | None = None
    student_card: Document | None = None
    raid_rules_id: str | None = None
    raid_rules: Document | None = None
    parent_authorization_id: str | None = None
    parent_authorization: Document | None = None
    attestation_on_honour: bool
    is_minor: bool

    @computed_field
    @property
    def validation_progress(self) -> float:
        return compute_participant_progress(self)

    @computed_field
    @property
    def number_of_document(self) -> int:
        return count_total_required_documents(self)

    @computed_field
    @property
    def number_of_validated_document(self) -> int:
        return count_accepted_documents(self)


class RaidParticipantUpdate(BaseModel):
    address: str | None = None
    bike_size: Size | None = None
    t_shirt_size: Size | None = None
    # Accept legacy string values (e.g. "otherschool", "otherschool : MyPrepa");
    # `_coerce_legacy_situation` normalizes them to a `Situation`.
    situation: Situation | str | None = None
    other_school: str | None = None
    company: str | None = None
    diet: str | None = None
    attestation_on_honour: bool | None = None
    id_card_id: str | None = None
    medical_certificate_id: str | None = None
    security_file_id: str | None = None
    student_card_id: str | None = None
    raid_rules_id: str | None = None
    parent_authorization_id: str | None = None

    @field_validator("situation", mode="before")
    @classmethod
    def _coerce_legacy_situation(cls, value):
        """Accept the legacy lowercase `otherschool` during the grace period."""
        if isinstance(value, str):
            if value.startswith("otherschool"):
                return Situation.otherSchool
            if value == "otherSchool":
                return Situation.otherSchool
            if value == "centrale":
                return Situation.centrale
            if value == "corporatePartner":
                return Situation.corporatePartner
            if value == "other":
                return Situation.other
        return value

    @model_validator(mode="after")
    def _check_situation_consistency(self):
        if self.situation == Situation.otherSchool and self.other_school is None:
            msg = "situation=otherSchool requires other_school to be set"
            raise ValueError(msg)
        if self.situation == Situation.centrale and self.other_school:
            self.other_school = None
        return self


class RaidTeamBase(BaseModel):
    name: str


class RaidTeamPreview(RaidTeamBase):
    id: str
    edition_id: UUID
    number: int | None = None
    captain_id: str
    captain: RaidParticipantPreview
    second_id: str | None = None
    second: RaidParticipantPreview | None = None
    difficulty: Difficulty | None = None
    meeting_place: MeetingPlace | None = None

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def validation_progress(self) -> float:
        captain_progress = (
            self.captain.validation_progress
            if isinstance(self.captain, RaidParticipant)
            else 0
        )
        second_progress = (
            self.second.validation_progress
            if isinstance(self.second, RaidParticipant)
            else 0
        )
        filled = int(self.difficulty is not None) + int(self.meeting_place is not None)
        return (filled / 2) * 10 + (captain_progress + second_progress) * 0.45


class RaidTeam(RaidTeamBase):
    id: str
    edition_id: UUID
    number: int | None = None
    captain_id: str
    captain: RaidParticipant
    second_id: str | None = None
    second: RaidParticipant | None = None
    difficulty: Difficulty | None = None
    meeting_place: MeetingPlace | None = None
    file_id: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def validation_progress(self) -> float:
        captain_progress = self.captain.validation_progress
        second_progress = self.second.validation_progress if self.second else 0
        filled = int(self.difficulty is not None) + int(self.meeting_place is not None)
        return (filled / 2) * 10 + (captain_progress + second_progress) * 0.45


class RaidTeamCreate(BaseModel):
    """Flat column-level payload used by the create CRUD."""

    id: str
    edition_id: UUID
    name: str
    captain_id: str
    second_id: str | None = None
    difficulty: Difficulty | None = None
    meeting_place: MeetingPlace | None = None
    number: int | None = None
    file_id: str | None = None


class RaidTeamUpdate(BaseModel):
    name: str | None = None
    number: int | None = None
    difficulty: Difficulty | None = None
    meeting_place: MeetingPlace | None = None


class InviteToken(BaseModel):
    id: str
    edition_id: UUID
    team_id: str
    token: str

    model_config = ConfigDict(from_attributes=True)


class EmergencyContact(BaseModel):
    firstname: str | None = None
    name: str | None = None
    phone: str | None = None


class RaidDriveFoldersCreation(BaseModel):
    parent_folder_id: str


class PaymentUrl(BaseModel):
    url: str


class RaidParticipantCheckout(BaseModel):
    participant_user_id: str
    edition_id: UUID
    checkout_id: str

    model_config = ConfigDict(from_attributes=True)


class RaidEditionBase(BaseModel):
    name: str
    year: int
    start_date: date | None = None
    end_date: date | None = None
    registering_end_date: date | None = None
    active: bool = False
    inscription_enabled: bool = False


class RaidEdition(RaidEditionBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


class RaidEditionEdit(BaseModel):
    name: str | None = None
    year: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    registering_end_date: date | None = None
    active: bool | None = None
    inscription_enabled: bool | None = None


class RaidVolunteerBase(BaseModel):
    """Shared volunteer fields.

    The car_seats/has_car consistency check is enforced only on the
    write-side schemas (RaidVolunteerCreate, RaidVolunteerEdit). Reads
    pass whatever is stored through unchanged so the admin validation
    endpoint can surface inconsistent rows for manual fix-up.
    """

    t_shirt_size: Size | None = None
    diet: str | None = None
    allergy: str | None = None
    emergency_person_name: str | None = None
    emergency_person_phone: str | None = None
    has_car: bool = False
    car_seats: int | None = None
    is_special_driver: bool = False
    is_utility_vehicle_driver: bool = False
    is_parcours_helper: bool = False


def _validate_car_seats(self):
    if self.has_car and (self.car_seats is None or self.car_seats <= 0):
        msg = "has_car=True requires car_seats > 0"
        raise ValueError(msg)
    if not self.has_car:
        self.car_seats = None
    return self


class RaidVolunteerCreate(RaidVolunteerBase):
    """Flat column-level payload used by the create CRUD (no CoreUser)."""

    user_id: str
    edition_id: UUID
    created_at: datetime
    validated: bool = False
    cancelled: bool = False

    _check_car_seats_consistency = model_validator(mode="after")(_validate_car_seats)


class RaidVolunteer(RaidVolunteerBase):
    user_id: str
    edition_id: UUID
    created_at: datetime
    validated: bool
    cancelled: bool
    user: CoreUser

    model_config = ConfigDict(from_attributes=True)


class RaidVolunteerEdit(BaseModel):
    t_shirt_size: Size | None = None
    diet: str | None = None
    allergy: str | None = None
    emergency_person_name: str | None = None
    emergency_person_phone: str | None = None
    has_car: bool | None = None
    car_seats: int | None = None
    is_special_driver: bool | None = None
    is_utility_vehicle_driver: bool | None = None
    is_parcours_helper: bool | None = None

    @model_validator(mode="after")
    def _check_car_seats_consistency(self):
        if self.has_car is True and (self.car_seats is None or self.car_seats <= 0):
            msg = "has_car=True requires car_seats > 0"
            raise ValueError(msg)
        if self.has_car is False:
            self.car_seats = None
        return self
