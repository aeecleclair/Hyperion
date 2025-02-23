from uuid import UUID

from pydantic import BaseModel, field_validator

from app.utils import validators


class CoreSchoolBase(BaseModel):
    """Schema for school's model"""

    name: str
    email_regex: str

    _normalize_name = field_validator("name")(validators.trailing_spaces_remover)


class CoreSchool(CoreSchoolBase):
    id: UUID


class CoreSchoolUpdate(BaseModel):
    """Schema for school update"""

    name: str | None = None
    email_regex: str | None = None

    _normalize_name = field_validator("name")(validators.trailing_spaces_remover)
