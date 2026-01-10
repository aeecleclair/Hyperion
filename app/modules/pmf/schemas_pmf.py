from datetime import date
from uuid import UUID

from pydantic import BaseModel

from app.core.users import schemas_users
from app.modules.pmf.types_pmf import LocationType, OfferType


class TagBase(BaseModel):
    tag: str


class TagComplete(TagBase):
    id: UUID
    created_at: date


class OfferBase(BaseModel):
    author_id: str

    company_name: str
    title: str
    description: str
    offer_type: OfferType
    location: str
    location_type: LocationType

    start_date: date
    end_date: date
    duration: int  # days


class OfferSimple(OfferBase):
    id: UUID


class OfferUpdate(BaseModel):
    author_id: str | None = None
    company_name: str | None = None
    title: str | None = None
    description: str | None = None
    offer_type: OfferType | None = None
    location: str | None = None
    location_type: LocationType | None = None
    start_date: date | None = None
    end_date: date | None = None
    duration: int | None = None  # days

    tags: list[TagBase] | None = None


class OfferComplete(OfferSimple):
    author: schemas_users.CoreUserSimple
    tags: list[TagComplete]
