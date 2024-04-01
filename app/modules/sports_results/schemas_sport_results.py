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
    match_date: date


class ResultComplete(ResultBase):
    id: str
