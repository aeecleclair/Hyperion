import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.utils import validators


# <-- Contacts for PE5 SafetyCards -->
class ContactBase(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    location: str | None = None


class Contact(ContactBase):
    id: uuid.UUID
    creation: datetime

    model_config = ConfigDict(from_attributes=True)


class ContactEdit(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None

    _normalize_email = field_validator("email")(validators.email_normalizer)
    _format_phone = field_validator("phone")(validators.phone_formatter)


# <-- End of Contacts for PE5 SafetyCards -->
