from enum import Enum

from fastapi import APIRouter


class RouterList(Enum):
    module_visibility = APIRouter()
