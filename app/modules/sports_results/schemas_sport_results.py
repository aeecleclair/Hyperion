from datetime import date

from pydantic import BaseModel


class Captain(BaseModel):
    user_id: str
    sport: "Sport"


class Sport(BaseModel):
    id: str
    name: str
    capitains: list[Captain]


class ResultBase(BaseModel):
    sport_id: str
    score1: int
    score2: int
    rank: int
    location: str
    match_date: date


class ResultUpdate(BaseModel):
    sport_id: str | None = None
    score1: int | None = None
    score2: int | None = None
    rank: int | None = None
    match_date: date | None = None


class ResultComplete(ResultBase):
    id: str
