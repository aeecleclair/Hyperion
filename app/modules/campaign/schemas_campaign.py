from pydantic import BaseModel, ConfigDict

from app.core.core_endpoints import schemas_core
from app.modules.campaign.types_campaign import ListType, StatusType


class SectionBase(BaseModel):
    """Base schema for a section."""

    name: str
    description: str


class SectionComplete(SectionBase):
    id: str
    model_config = ConfigDict(from_attributes=True)


class ListMemberBase(BaseModel):
    user_id: str
    role: str
    model_config = ConfigDict(from_attributes=True)


class ListMemberComplete(ListMemberBase):
    user: schemas_core.CoreUserSimple
    model_config = ConfigDict(from_attributes=True)


class ListBase(BaseModel):
    """Base schema for a list."""

    name: str
    description: str
    type: ListType
    section_id: str
    members: list[ListMemberBase]
    program: str | None = None


class ListComplete(ListBase):
    id: str
    model_config = ConfigDict(from_attributes=True)


class SectionReturn(BaseModel):
    name: str
    description: str
    id: str
    lists: list[ListComplete]
    model_config = ConfigDict(from_attributes=True)


class ListReturn(BaseModel):
    id: str
    name: str
    description: str
    type: ListType
    section: SectionComplete
    members: list[ListMemberComplete]
    program: str | None = None
    model_config = ConfigDict(from_attributes=True)


class ListEdit(BaseModel):
    name: str | None = None
    description: str | None = None
    type: ListType | None = None
    members: list[ListMemberBase] | None = None
    program: str | None = None


class VoterGroup(BaseModel):
    """Base schema for voters (groups allowed to vote)."""

    group_id: str
    model_config = ConfigDict(from_attributes=True)


class VoteBase(BaseModel):
    """Base schema for a vote."""

    list_id: str
    model_config = ConfigDict(from_attributes=True)


class VoteStatus(BaseModel):
    status: StatusType
    model_config = ConfigDict(from_attributes=True)


class Result(BaseModel):
    list_id: str
    count: int
    model_config = ConfigDict(from_attributes=True)


class VoteStats(BaseModel):
    section_id: str
    count: int
