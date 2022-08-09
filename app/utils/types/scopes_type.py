from enum import Enum


class ScopeType(str, Enum):
    """
    Various scope that can be included in JWT token
    """

    # API allows the user to access every endpoint from the api (but not auth endpoints)
    API = "API"
    # auth only allows the user to access auth endpoints
    auth = "auth"
    # openid only allows the user to access the userinfos auth endpoint
    openid = "openid"
