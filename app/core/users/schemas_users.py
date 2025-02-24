from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.groups.groups_type import AccountType
from app.core.schools.schemas_schools import CoreSchool
from app.types.floors_type import FloorsType
from app.utils import validators
from app.utils.examples import examples_core


class CoreUserBase(BaseModel):
    """Base schema for user's model"""

    name: str
    firstname: str
    nickname: str | None = None

    _normalize_name = field_validator("name")(validators.trailing_spaces_remover)
    _normalize_firstname = field_validator("firstname")(
        validators.trailing_spaces_remover,
    )
    _normalize_nickname = field_validator("nickname")(
        validators.trailing_spaces_remover,
    )


class CoreUserSimple(CoreUserBase):
    """Simplified schema for user's model, used when getting all users"""

    id: str
    account_type: AccountType
    school_id: UUID

    model_config = ConfigDict(from_attributes=True)


class CoreUser(CoreUserSimple):
    """Schema for user's model similar to core_user table in database"""

    email: str
    birthday: date | None = None
    promo: int | None = None
    floor: FloorsType | None = None
    phone: str | None = None
    created_on: datetime | None = None
    groups: "list[CoreGroupSimple]" = []
    school: CoreSchool | None = None


class CoreUserUpdate(BaseModel):
    """Schema for user update"""

    nickname: str | None = None
    birthday: date | None = None
    phone: str | None = None
    floor: FloorsType | None = None

    _normalize_nickname = field_validator("nickname")(
        validators.trailing_spaces_remover,
    )
    _format_phone = field_validator("phone")(
        validators.phone_formatter,
    )
    model_config = ConfigDict(json_schema_extra=examples_core.example_CoreUserUpdate)


class CoreUserFusionRequest(BaseModel):
    """Schema for user fusion"""

    user_kept_email: str
    user_deleted_email: str


class CoreUserUpdateAdmin(BaseModel):
    email: str | None = None
    school_id: UUID | None = None
    account_type: AccountType | None = None
    name: str | None = None
    firstname: str | None = None
    promo: int | None = None
    nickname: str | None = None
    birthday: date | None = None
    phone: str | None = None
    floor: FloorsType | None = None

    _normalize_name = field_validator("name")(validators.trailing_spaces_remover)
    _normalize_firstname = field_validator("firstname")(
        validators.trailing_spaces_remover,
    )
    _normalize_nickname = field_validator("nickname")(
        validators.trailing_spaces_remover,
    )
    _format_phone = field_validator("phone")(
        validators.phone_formatter,
    )
    model_config = ConfigDict(json_schema_extra=examples_core.example_CoreUserUpdate)


class CoreUserCreateRequest(BaseModel):
    """
    The schema is used to send an account creation request.
    """

    email: str
    accept_external: bool | None = Field(
        None,
        deprecated=True,
        description="Allow Hyperion to create an external user. Without this, Hyperion will only allow non external students to be created. The email address will be used to determine if the user should be external or not. An external user may not have an ECL email address, he won't be able to access most features.",
    )

    # Email normalization, this will modify the email variable
    # https://pydantic-docs.helpmanual.io/usage/validators/#reuse-validators
    _normalize_email = field_validator("email")(validators.email_normalizer)
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra=examples_core.example_CoreUserCreateRequest,
    )


class CoreBatchUserCreateRequest(BaseModel):
    """
    The schema is used for batch account creation requests.
    """

    email: str

    # Email normalization, this will modify the email variable
    # https://pydantic-docs.helpmanual.io/usage/validators/#reuse-validators
    _normalize_email = field_validator("email")(validators.email_normalizer)
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra=examples_core.example_CoreBatchUserCreateRequest,
    )


class CoreUserActivateRequest(CoreUserBase):
    activation_token: str
    password: str
    birthday: date | None = None
    phone: str | None = None
    floor: FloorsType | None = None
    promo: int | None = Field(
        default=None,
        description="Promotion of the student, an integer like 2021",
    )

    # Password validator
    # https://pydantic-docs.helpmanual.io/usage/validators/#reuse-validators
    _normalize_password = field_validator("password")(validators.password_validator)
    _format_phone = field_validator("phone")(
        validators.phone_formatter,
    )
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra=examples_core.example_CoreUserActivateRequest,
    )


class CoreUserRecoverRequest(BaseModel):
    email: str
    user_id: str
    reset_token: str
    created_on: datetime
    expire_on: datetime

    _normalize_email = field_validator("email")(validators.email_normalizer)
    model_config = ConfigDict(from_attributes=True)


class ChangePasswordRequest(BaseModel):
    email: str
    old_password: str
    new_password: str

    # Password validator
    # https://pydantic-docs.helpmanual.io/usage/validators/#reuse-validators
    _normalize_password = field_validator("new_password")(validators.password_validator)


class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str

    # Password validator
    # https://pydantic-docs.helpmanual.io/usage/validators/#reuse-validators
    _normalize_password = field_validator("new_password")(validators.password_validator)


class MailMigrationRequest(BaseModel):
    new_email: str


# Importing here to avoid circular imports
from app.core.groups.schemas_groups import CoreGroupSimple  # noqa: E402, TCH001

CoreUserSimple.model_rebuild()
