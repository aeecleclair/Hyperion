from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.core.schemas_core import CoreUserSimple
from app.types.floors_type import FloorsType


class UserTicket(CoreUserSimple):
    promo: int | None = None
    floor: FloorsType | None = None
    created_on: datetime | None = None


class Ticket(BaseModel):
    id: UUID
    user: UserTicket
    scan_left: int
    tags: str
    expiration: datetime
    name: str


class TicketScan(BaseModel):
    tag: Annotated[
        str,
        StringConstraints(to_lower=True, strip_whitespace=True, pattern=r"[^,]+"),
    ]


class TicketSecret(BaseModel):
    qr_code_secret: UUID


class GenerateTicketBase(BaseModel):
    name: str
    max_use: int
    expiration: datetime
    scanner_group_id: str


class GenerateTicketComplete(GenerateTicketBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


class GenerateTicketEdit(BaseModel):
    max_use: int | None = None
    expiration: datetime | None = None
