from enum import Enum


class ScopeType(str, Enum):
    """
    Various scopes that can be included in JWT token
    """

    # API allows the user to access every endpoint from the api (but not auth endpoints)
    API = "API"
    # auth only allows the user to access auth endpoints
    auth = "auth"

    # The `openid` and `profile` scopes only allow the user to access the userinfo and token endpoints.
    # Quotes below are excerpts from the OIDC specifications : https://openid.net/specs/openid-connect-core-1_0.html
    # For OIDC (authentication), which extends OAuth2, `openid` is mandatory (hence the access to these endpoints),
    # and other scopes only define what claims are available (this scope should not be used alone).
    # However for OAuth2 (authorization), most clients implement an extension and may also want to access these endpoints,
    # but only send the `profile` scope, thus `profile` also enables these endpoint.
    # > [...] If no openid scope value is present, the request may still be a valid OAuth 2.0 request but is not an OpenID Connect request.
    # That is why both scopes lead to the same behavior in this implementation.

    # It is mandatory for a client supporting OIDC to present the `openid` scope:
    # > Verify that a scope parameter is present and contains the openid scope value [...].
    openid = "openid"

    # > This scope value requests access to the End-User's default profile Claims, which are:
    # > name, family_name, given_name, middle_name, nickname, preferred_username, profile, picture, website, gender, birthdate, zoneinfo, locale, and updated_at.
    profile = "profile"

    # Some services may ask to access the user's email.
    # This scope is not required as the email can be included with any other scope.
    # > This scope value requests access to the email and email_verified Claims.
    email = "email"
