"""Common schemas file for endpoint /users et /groups because it would cause circular import"""

from enum import Enum
from typing import Sequence

from pydantic import BaseModel, ConfigDict, Field

from app.core.groups.groups_type import AccountType


class CoreInformation(BaseModel):
    """Information about Hyperion"""

    ready: bool
    version: str
    minimal_titan_version_code: int


class ModuleVisibility(BaseModel):
    root: str
    allowed_group_ids: Sequence[str]
    allowed_account_types: Sequence[AccountType | str]
    model_config = ConfigDict(from_attributes=True)


class ModuleVisibilityCreate(BaseModel):
    root: str
    allowed_group_id: str | None = None
    allowed_account_type: AccountType | None = None
    model_config = ConfigDict(from_attributes=True)


class ActivationFormField(Enum):
    NICKNAME = "nickname"
    BIRTHDATE = "birthdate"
    PHONE = "phone"
    PROMOTION = "promotion"
    FLOOR = "floor"


class MainActivationForm(BaseModel):
    fields: list[ActivationFormField] = Field(
        description="List of fields that are to be asked in the main activation form",
    )
    floor_choices: list[str] = Field(
        description="List of choices for the floor field if it is asked",
        default_factory=list,
    )
    promotion_offset: int | None = None


class CoreVariables(BaseModel):
    """Variables used by Hyperion"""

    name: str
    entity_name: str
    email_placeholder: str
    main_activation_form: MainActivationForm
    student_email_regex: str
    staff_email_regex: str | None = None
    former_student_email_regex: str | None = None
    primary_color: str = Field(
        description="Returned as an HSL triplet (ex: `24.6 95% 53.1%`)",
    )
    play_store_url: str | None = None
    app_store_url: str | None = None
