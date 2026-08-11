from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.documents import schemas_documents
from app.core.documents.types_documenso import DocumentStatus
from app.core.users import schemas_users


class MembershipBase(BaseModel):
    name: str
    manager_group_id: str
    template_id: UUID | None = None


class MembershipSimple(MembershipBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


class MembershipComplete(MembershipSimple):
    template: schemas_documents.Template | None = None

    model_config = ConfigDict(from_attributes=True)


class MembershipEdit(BaseModel):
    name: str | None = None
    manager_group_id: str | None = None
    template_id: UUID | None = None


class MembershipDateFilter(BaseModel):
    minimal_date: date | None = None


class MembershipRenewalCriterion(BaseModel):
    active_date: date


class MembershipRenewalErrors(BaseModel):
    errors: dict[str, str]


class UserMembershipBase(BaseModel):
    association_membership_id: UUID
    start_date: date
    end_date: date


class UserMembershipSimple(UserMembershipBase):
    id: UUID
    user_id: str
    document_id: UUID | None = None
    document_status: DocumentStatus | None = None
    valid: bool

    model_config = ConfigDict(from_attributes=True)


class UserMembershipComplete(UserMembershipSimple):
    user: schemas_users.CoreUser
    document: schemas_documents.Document | None = None

    model_config = ConfigDict(from_attributes=True)


class UserMembershipWithAssociation(UserMembershipComplete):
    association_membership: MembershipSimple

    model_config = ConfigDict(from_attributes=True)


class UserMembershipEdit(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    document_status: DocumentStatus | None = None


class MembershipUserMappingEmail(BaseModel):
    user_email: str
    start_date: date
    end_date: date
