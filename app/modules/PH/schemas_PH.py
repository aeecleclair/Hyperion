from datetime import date

from pydantic import BaseModel


class Journal(BaseModel):
    """Base schema for journal's model"""

    name: str
    id: str
    release_date: date
