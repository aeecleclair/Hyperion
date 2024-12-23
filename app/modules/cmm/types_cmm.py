from enum import Enum


class MemeStatus(str, Enum):
    neutral = "neutral"
    banned = "banned"


class MemeSort(str, Enum):
    best = "best"
    worst = "worst"
    trending = "trending"
    newest = "newest"
    oldest = "oldest"


class VoteValue(Enum):
    down = False
    up = True
    neutral = None
