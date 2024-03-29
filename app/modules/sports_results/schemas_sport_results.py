from datetime import date

from app.database import Base


class Captain(Base):
    user_id: str
    sport: Sport


class Sport(Base):
    id: str
    name: str
    capitains: list[Captain]


class Result(Base):
    id: str
    sport_id: str
    score1: int
    score2: int
    rank: int
    match_date: date
