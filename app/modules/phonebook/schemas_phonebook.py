from typing import Sequence
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.users.schemas_users import CoreUserSimple


class RoleTagsReturn(BaseModel):
    tags: Sequence[str]

    model_config = ConfigDict(from_attributes=True)


class RoleTagsBase(BaseModel):
    role_tag: str
    membership_id: str

    model_config = ConfigDict(from_attributes=True)


class AssociationBase(BaseModel):
    name: str
    groupement_id: UUID
    mandate_year: int
    description: str | None = None
    associated_groups: list[str] = []  # Should be a list of ids
    deactivated: bool = False  # Deactivated associations won't be displayed in the phonebook unless looking at previous years and cannot be used for new memberships


class AssociationComplete(AssociationBase):
    id: str

    model_config = ConfigDict(from_attributes=True)


class AssociationEdit(BaseModel):
    name: str | None = None
    groupement_id: UUID | None = None
    description: str | None = None
    mandate_year: int | None = None


class AssociationGroupsEdit(BaseModel):
    associated_groups: list[str] = []  # Should be a list of ids


class MembershipBase(BaseModel):
    user_id: str
    association_id: str
    mandate_year: int
    role_name: str
    role_tags: str = ""  # "roletag1;roletag2;..."
    member_order: int

    model_config = ConfigDict(from_attributes=True)


class MembershipComplete(MembershipBase):
    id: str

    model_config = ConfigDict(from_attributes=True)


class MembershipEdit(BaseModel):
    role_name: str | None = None
    role_tags: str | None = None
    member_order: int | None = None


class MemberBase(CoreUserSimple):
    email: str
    phone: str | None = None
    promo: int | None = None

    model_config = ConfigDict(from_attributes=True)


class MemberComplete(MemberBase):
    memberships: Sequence[MembershipComplete]

    model_config = ConfigDict(from_attributes=True)


class AssociationGroupementBase(BaseModel):
    name: str
    manager_group_id: str

    model_config = ConfigDict(from_attributes=True)


class AssociationGroupement(AssociationGroupementBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)
