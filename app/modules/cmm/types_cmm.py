from enum import Enum

from app.modules.cmm.models_cmm import Vote


class MemeStatus(str, Enum):
    neutral = "neutral"
    banned = "banned"


class MemeSort(str, Enum):
    best = "best"
    worst = "worst"
    trending = "trending"
    newest = "newest"
    oldest = "oldest"


class VoteValue(str, Enum):
    down = "down"
    up = "up"
    neutral = "neutral"


def compute_vote_value(vote: Vote | None) -> VoteValue:
    if vote is None:
        my_vote_value = VoteValue.neutral
    elif vote.positive:
        my_vote_value = VoteValue.up
    else:
        my_vote_value = VoteValue.down

    return my_vote_value
