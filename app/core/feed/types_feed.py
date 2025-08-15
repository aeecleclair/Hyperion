from enum import Enum


class NewsStatus(str, Enum):
    WAITING_APPROVAL = "waiting_approval"
    REJECTED = "rejected"
    PUBLISHED = "published"
