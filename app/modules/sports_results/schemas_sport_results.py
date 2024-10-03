from datetime import date

from pydantic import BaseModel


class CaptainBase(BaseModel):
    user_id: str
    sports: list["SportComplete"]


class CaptainUpdate(BaseModel):
    user_id: str | None = None
    sports: "list[SportComplete] | None" = None


class CaptainComplete(CaptainBase):
    id: str


class SportBase(BaseModel):
    name: str
    captains: list[CaptainComplete]


class SportUpdate(BaseModel):
    name: str | None = None
    captains: list[CaptainComplete] | None = None


class SportComplete(SportBase):
    id: str


class ResultBase(BaseModel):
    sport_id: str
    score1: int | None
    score2: int | None
    rank: int | None
    location: str
    match_date: date


class ResultUpdate(BaseModel):
    sport_id: str | None = None
    score1: int | None = None
    score2: int | None = None
    rank: int | None = None
    location: str | None = None
    match_date: date | None = None


class ResultComplete(ResultBase):
    id: str