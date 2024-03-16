from pydantic import BaseModel, ConfigDict

from app.core import schemas_core
from app.modules.phonebook.phonebook_types import Kinds


class RoleTagsReturn(BaseModel):
    tags: list[str]

    model_config = ConfigDict(from_attributes=True)


class RoleTagsBase(BaseModel):
    role_tag: str
    membership_id: str

    model_config = ConfigDict(from_attributes=True)


class AssociationBase(BaseModel):
    name: str
    kind: Kinds
    mandate_year: int
    description: str | None = None


class AssociationComplete(AssociationBase):
    id: str

    model_config = ConfigDict(from_attributes=True)


class AssociationEdit(BaseModel):
    name: str | None = None
    kind: Kinds | None = None
    description: str | None = None
    mandate_year: int | None = None


class MembershipBase(BaseModel):
    user_id: str
    association_id: str
    mandate_year: int
    role_name: str
    role_tags: str | None = None  # "roletag1;roletag2;..."

    model_config = ConfigDict(from_attributes=True)


class MembershipComplete(MembershipBase):
    id: str

    model_config = ConfigDict(from_attributes=True)


class MembershipEdit(BaseModel):
    role_name: str | None = None
    role_tags: str | None = None


class MemberBase(schemas_core.CoreUserSimple):
    email: str
    phone: str | None = None
    promo: int | None = None

    model_config = ConfigDict(from_attributes=True)


class MemberComplete(MemberBase):
    memberships: list[MembershipComplete]

    model_config = ConfigDict(from_attributes=True)


class KindsReturn(BaseModel):
    kinds: list[Kinds]
