from enum import Enum


class MemeStatus(str, Enum):
    neutral = "neutral"
    reported = "reported"
    banned = "banned"
    allowed = "allowed"
