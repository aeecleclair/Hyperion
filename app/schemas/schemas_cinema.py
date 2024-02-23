from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.utils import validators


class CineSessionTime(BaseModel):
    start: datetime
    duration: int

    _normalize_start = field_validator("start")(validators.time_zone_converter)


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

    _normalize_start = field_validator("start")(validators.time_zone_converter)
