from enum import Enum


class ScopeType(str, Enum):
    """
    Various scopes that can be included in JWT token
    """

    # API allows the user to access every endpoint from the api (but not auth endpoints)
    API = "API"
    # auth only allows the user to access auth endpoints
    auth = "auth"
    # openid only allows the user to access the userinfos auth endpoint
    openid = "openid"
    # profile allows the user to access the userinfos auth endpoint
    # The profile scope is introduced because some clients may want to access the user's profile without doing oidc
    profile = "profile"

    # Some services may ask to access the user's email
    # This scope is not required as the email can be included with any other scope
    email = "email"
