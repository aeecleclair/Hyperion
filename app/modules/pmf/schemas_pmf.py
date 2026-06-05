from datetime import date
from uuid import UUID

from pydantic import BaseModel

from app.core.users import schemas_users
from app.modules.pmf.types_pmf import LocationType, OfferType

class ProfileBase(BaseModel):
    user_id: str

class ProfileComplete(ProfileBase):
    cv_list: list[CvComplete]

class CvBase(BaseModel):
    name: str
    user_id: str

class CvSimple(CvBase):
    id: UUID
    created_on: date

class CvUpdate(BaseModel):
    name: str | None = None

class CvComplete(CvSimple):
    allowed_users: list[str]

class ApplicationBase(BaseModel):
    applicant_id: str
    alumni_id: str
    cv_id: UUID
    offer_id: UUID

class ApplicationComplete(ApplicationBase):
    created_on: date

class TagBase(BaseModel):
    tag: str

class TagComplete(TagBase):
    id: UUID
    created_on: date


class OfferBase(BaseModel):
    author_id: str

    company_name: str
    title: str
    description: str
    offer_type: OfferType
    location: str
    location_type: LocationType
    start_date: date
    duration: int  # days


class OfferSimple(OfferBase):
    id: UUID
    hidden: bool


class OfferUpdate(BaseModel):
    author_id: str | None = None
    company_name: str | None = None
    title: str | None = None
    description: str | None = None
    offer_type: OfferType | None = None
    location: str | None = None
    location_type: LocationType | None = None
    start_date: date | None = None
    duration: int | None = None  # months
    hidden: bool | None = None
    tags: list[TagBase] | None = None


class OfferComplete(OfferSimple):
    author: schemas_users.CoreUserSimple
    created_on: date
    tags: list[TagComplete]
