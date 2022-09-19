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

    class Config:
        orm_mode = True
