from datetime import date

from pydantic import BaseModel


class Journal(BaseModel):
    """Base schema for journal's model"""

    id: str
    name: str
    release_date: date
