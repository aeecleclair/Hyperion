from enum import StrEnum


class NewsStatus(StrEnum):
    WAITING_APPROVAL = "waiting_approval"
    REJECTED = "rejected"
    PUBLISHED = "published"
