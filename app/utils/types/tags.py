"""File defining the tags for the automatic FastAPI documentation (found on http://domainname/docs)"""

from enum import Enum


class Tags(str, Enum):
    users = "Users"
    groups = "Groups"
