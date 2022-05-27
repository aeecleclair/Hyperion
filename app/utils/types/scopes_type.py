from enum import Enum


class ScopeType(str, Enum):
    """
    Various scope that can be included in JWT token
    """

    # API allows the user to access every endpoint from the api (but not the auth endpoints)
    API = "API"
    # auth only allows the user to access the auth endpoints
    auth = "auth"
    # userinfos only allows the user to access the userinfos auth endpoint
    userinfos = "userinfos"
