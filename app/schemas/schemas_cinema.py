from datetime import datetime

from pydantic import BaseModel


class CineSessionTime(BaseModel):
    start: datetime
    duration: int


class CineSessionBase(CineSessionTime):
    name: str
    overview: str | None = None
    genre: str | None = None
    tagline: str | None = None


class CineSessionComplete(CineSessionBase):
    id: str

    class Config:
        orm_mode = True


class CineSessionUpdate(BaseModel):
    name: str | None = None
    start: datetime | None = None
    duration: int | None = None
    overview: str | None = None
    genre: str | None = None
    tagline: str | None = None
