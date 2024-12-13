from enum import Enum


class MemeStatus(str, Enum):
    neutral = "neutral"
    reported = "reported"
    banned = "banned"
    allowed = "allowed"


class MemeSort(str, Enum):
    best = "best"
    worst = "worst"
    trending = "trending"
    newest = "newest"
    oldest = "oldest"
