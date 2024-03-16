from datetime import date

from pydantic import BaseModel


class Paper(BaseModel):
    """Base schema for paper's model"""

    id: str
    name: str
    release_date: date
