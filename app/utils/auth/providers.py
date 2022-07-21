# TODO: How do we store the secret properly ?


from typing import Any, Set

from app.models import models_core
from app.utils.types.groups_type import GroupType
from app.utils.types.scopes_type import ScopeType


class BaseAuthClient:
    """
    When registering an OAuth or Openid connect client in config, a corresponding auth_client must be provided.
    The auth_client class is responsible for configuring the redirect_uri, granting scopes, returning adapted userinfo...

    To register a new client, you should create a new class inheriting from `BaseAuthClient` and override some of its parameters and methods
    """

    ########################################################
    # Auth client configuration: override these parameters #
    ########################################################

    # If no redirect_uri are hardcoded, the client will need to provide one in its request
    redirect_uri: str | None = None
    # Set of scopes the auth client is authorized to grant when issuing an access token.
    # See app.utils.types.scopes_type.ScopeType for possible values
    # WARNING: to be able to use openid connect, `ScopeType.openid` should always be allowed
    allowed_scopes: Set[ScopeType] = {ScopeType.openid}
    # Restrict the authentification to this client to specifics Hyperion groups.
    # When set to `None`, users from any group can use the auth client
    allowed_groups: list[GroupType] | None = None

    def get_userinfo(self, user: models_core.CoreUser) -> dict[str, Any]:
        """
        Return information about the user in a format understandable by the client.
        This method return the result of Openid connect userinfo endpoint.

        See oidc specifications and `app.endpoints.auth.auth_get_userinfo` for more information:
        https://openid.net/specs/openid-connect-core-1_0.html#UserInfo

        See the client documentation and implementation to know claims it needs or can receive
        """
        # Override this method with custom information adapted for the client
        # WARNING: The sub (subject) Claim MUST always be returned in the UserInfo Response.
        return {
            "sub": user.id,
            "name": user.firstname,
        }

    ########################################################
    #                   Utilities methods                  #
    #    The following methods should not be overridden    #
    ########################################################

    def __init__(self, client_id: str, secret: str | None) -> None:
        # The following parameters are not class variables but instance variables.
        # There can indeed be more that one client using the class, the client will need to have its own client id and secret.

        self.client_id: str = client_id
        # If no secret are provided, the client is expected to use PKCE
        self.secret: str | None = secret

    def filter_scopes(self, requested_scopes: Set[str]) -> Set[ScopeType]:
        return self.allowed_scopes.intersection(requested_scopes)


class AppAuthClient:
    """
    An auth client for Hyperion mobile application
    """

    # If no redirect_uri are hardcoded, the client will need to provide one in its request
    redirect_uri: str | None = None
    # Set of scopes the auth client is authorized to grant when issuing an access token.
    # See app.utils.types.scopes_type.ScopeType for possible values
    # WARNING: to be able to use openid connect, `ScopeType.openid` should always be allowed
    allowed_scopes: Set[ScopeType] = set()
    # Restrict the authentification to this client to specifics Hyperion groups.
    # When set to `None`, users from any group can use the auth client
    allowed_groups: list[GroupType] | None = None


class ExampleClient(BaseAuthClient):
    secret = "secret"
    redirect_uri = "http://127.0.0.1:8000/docs"


class NextcloudAuthClient(BaseAuthClient):
    # If no secret are provided, the client is expected to use PKCE
    secret: str | None = "secret"
    # If no redirect_uri are hardcoded, the client will need to provide one in its request
    redirect_uri: str | None = None
    # Set of scopes the auth client is authorized to grant when issuing an access token.
    # See app.utils.types.scopes_type.ScopeType for possible values
    allowed_scopes: Set[ScopeType] = {ScopeType.openid}

    # For Nextcloud:
    # Required iss : the issuer value form .well-known (corresponding code : https://github.com/pulsejet/nextcloud-oidc-login/blob/0c072ecaa02579384bb5e10fbb9d219bbd96cfb8/3rdparty/jumbojett/openid-connect-php/src/OpenIDConnectClient.php#L1255)
    # Required claims : https://github.com/pulsejet/nextcloud-oidc-login/blob/0c072ecaa02579384bb5e10fbb9d219bbd96cfb8/3rdparty/jumbojett/openid-connect-php/src/OpenIDConnectClient.php#L1016

    @classmethod
    def get_userinfo(cls, user: models_core.CoreUser):
        # For Nextcloud, various claims can be provided.
        # See https://github.com/pulsejet/nextcloud-oidc-login#config for claim names

        return {
            "sub": user.id,
            "name": user.firstname,
            "given_name": user.nickname,
            "family_name": user.name,
            "preferred_username": user.nickname,
            # TODO: should we use group ids instead of names? It would be less human readable but would guarantee uniqueness. Question: are group names unique?
            "ownCloudGroups": [
                group.name for group in user.groups
            ],  # ["pixels"], # We may want to filter which groups are provided as they won't not always all be useful
            "email": user.email,
            "picture": "",  # TODO: add a PFP
        }


class PiwigoAuthClient(BaseAuthClient):
    @classmethod
    def get_userinfo(cls, user: models_core.CoreUser):
        # For Piwigo, a name is sufficient.
        # We need to put the claim name in Piwigo oidc plugin config

        # A modified Piwigo oidc plugin allows to manage groups from the oidc provider
        return {
            "sub": user.id,
            "name": user.firstname,
            "piwigo_groups": user.groups,  # ["pixels"], # We may want to filter which groups are provided as they won't not always all be useful
        }


# Where do we put the users that are allowed to access a service
# Maybe a function in these class
