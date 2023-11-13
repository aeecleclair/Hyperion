from fastapi import APIRouter

from app.core.groups.groups_type import GroupType
from app.core.module import Module

router = APIRouter()
module = Module(
    root="centralisation",
    default_allowed_groups_ids=[GroupType.student, GroupType.staff],
)
