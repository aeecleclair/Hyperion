from pydantic import BaseModel


class SectionBase(BaseModel):
    """Base schema for a section of AEECL."""

    name: str
    logo_path: str
    description: str

    class Config:
        orm_mode = True


class ListBase(BaseModel):
    """Base schema for a list."""

    name: str
    description: str
    logo_path: str
    type: str  # Add an enum
    section: str

    class Config:
        orm_mode = True


class ListComplete(ListBase):
    id: str


class VoteBase(BaseModel):
    """Base schema for a vote."""

    list_id: str

    class Config:
        orm_mode = True


class VoteStatus(BaseModel):
    status: bool
