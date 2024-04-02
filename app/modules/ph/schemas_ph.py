from datetime import date

from pydantic import BaseModel


class PaperBase(BaseModel):
    """Base schema for paper's model"""

    name: str
    release_date: date


class PaperComplete(PaperBase):
    id: str


class PaperUpdate(BaseModel):
    name: str
    release_date: date
