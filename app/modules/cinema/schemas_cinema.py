from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
    model_config = ConfigDict(from_attributes=True)


class CineSessionUpdate(BaseModel):
    name: str | None = None
    start: datetime | None = None
    duration: int | None = None
    overview: str | None = None
    genre: str | None = None
    tagline: str | None = None


class TheMovieDB(BaseModel):
    genres: list[dict[str, int | str]] | None = None
    overview: str | None = None
    poster_path: str | None = None
    title: str | None = None
    runtime: int | None = None
    tagline: str | None = None
