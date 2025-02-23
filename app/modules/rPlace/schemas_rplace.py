from typing import Literal

from pydantic import BaseModel

from app.types.websocket import WSMessageModel


class Pixel(BaseModel):
    x: int
    y: int
    color: str


class NewPixelWSMessageModel(WSMessageModel):
    command: Literal["NEW_PIXEL"] = "NEW_PIXEL"
    data: Pixel
