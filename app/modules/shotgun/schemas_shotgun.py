from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.schemas_core import CoreGroupBase


class OrganizerBase(BaseModel):
    group_id: str


class OrganizerComplete(OrganizerBase):
    id: UUID
    group: CoreGroupBase

    model_config = ConfigDict(from_attributes=True)


class SessionBase(BaseModel):
    name: str
    description: str | None = None
    start: datetime
    end: datetime | None = None
    quantity: int
    price: int


class SessionComplete(SessionBase):
    id: UUID
    organizer_id: UUID

    model_config = ConfigDict(from_attributes=True)


class GeneratorBase(BaseModel):
    name: str
    max_use: int
    expiration: datetime


class GeneratorComplete(GeneratorBase):
    id: UUID
    session_id: UUID


class PurchaseComplete(BaseModel):
    id: UUID
    session_id: UUID
    user_id: str
    checkout_id: UUID
    purchased_on: datetime
    paid: bool
