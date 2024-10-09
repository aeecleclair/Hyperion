from datetime import date

from pydantic import BaseModel

class Pixel(BaseModel):
    x: int
    y: int
    color: str