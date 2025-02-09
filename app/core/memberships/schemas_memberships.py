from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core import schemas_core


class MembershipBase(BaseModel):
    name: str
    group_id: str


class MembershipSimple(MembershipBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


class MembershipDateFilter(BaseModel):
    minimal_date: date | None = None


class UserMembershipBase(BaseModel):
    association_membership_id: UUID
    start_date: date
    end_date: date


class UserMembershipSimple(UserMembershipBase):
    id: UUID
    user_id: str

    model_config = ConfigDict(from_attributes=True)


class UserMembershipComplete(UserMembershipSimple):
    user: schemas_core.CoreUserSimple

    model_config = ConfigDict(from_attributes=True)


class UserMembershipEdit(BaseModel):
    start_date: date | None = None
    end_date: date | None = None


class MembershipUserMappingEmail(BaseModel):
    user_email: str
    start_date: date
    end_date: date
