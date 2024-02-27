from pydantic import BaseModel, ConfigDict

from app.schemas import schemas_core


class RoleTagsReturn(BaseModel):
    tags: list[str]

    model_config = ConfigDict(from_attributes=True)


class RoleTagsBase(BaseModel):
    role_tag: str
    membership_id: str

    model_config = ConfigDict(from_attributes=True)


class AssociationBase(BaseModel):
    name: str
    kind: str
    description: str | None = None


class AssociationComplete(AssociationBase):
    id: str
    mandate_year: int

    model_config = ConfigDict(from_attributes=True)


class AssociationEdit(BaseModel):
    name: str | None
    kind: str | None
    description: str | None
    mandate_year: int | None


class AssociationEditComplete(AssociationEdit):
    id: str

    model_config = ConfigDict(from_attributes=True)


class MembershipBase(BaseModel):
    user_id: str
    association_id: str
    mandate_year: int
    role_name: str
    role_tags: str | None  # "roletag1;roletag2;..."

    model_config = ConfigDict(from_attributes=True)


class MembershipComplete(MembershipBase):
    id: str

    model_config = ConfigDict(from_attributes=True)


class MembershipEdit(BaseModel):
    role_name: str | None
    role_tags: str | None


class MemberBase(schemas_core.CoreUserSimple):
    id: str
    email: str
    phone: str | None = None
    nickname: str
    firstname: str
    name: str
    promo: int | None = None

    model_config = ConfigDict(from_attributes=True)


class MemberComplete(MemberBase):
    memberships: list[MembershipComplete]

    model_config = ConfigDict(from_attributes=True)


class KindsReturn(BaseModel):
    kinds: list[str]
