from enum import Enum


class MemeStatus(str, Enum):
    neutral = "neutral"
    hidden = "hidden"


class MemeSort(str, Enum):
    best = "best"
    worst = "worst"
    trending = "trending"
    newest = "newest"
    oldest = "oldest"


class PeriodLeaderboard(str, Enum):
    week = "week"
    month = "month"
    year = "year"
    always = "always"


class EntityLeaderboard(str, Enum):
    promo = "promo"
    floor = "floor"
    user = "user"
