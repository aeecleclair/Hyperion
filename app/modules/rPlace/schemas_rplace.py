from typing import Literal

from datetime import datetime
from pydantic import BaseModel

from app.core.core_endpoints.schemas_core import CoreUserSimple
from app.types.websocket import WSMessageModel


class Pixel(BaseModel):
    x: int
    y: int
    color: str

class PixelComplete(BaseModel):
    user: CoreUserSimple
    date: datetime

class NewPixelWSMessageModel(WSMessageModel):
    command: Literal["NEW_PIXEL"] = "NEW_PIXEL"
    data: Pixel

class UserInfo(BaseModel):
    date: datetime