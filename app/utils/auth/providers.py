# TODO: How do we store the secret properly ?


from typing import Set

from app.models import models_core
from app.utils.types.scopes_type import ScopeType


class BaseAuthClient:
    """
    When registering an OAuth or Openid connect client in config, a corresponding auth_client must be provided.
    The auth_client class is responsible for configuring the redirect_uri, granting scopes, returning adapted userinfo...

    To register a new client, you should create a new class inheriting from `BaseAuthClient` and override its parameters
    """

    ########################################################
    # Auth client configuration: override these parameters #
    ########################################################

    # If no secret are provided, the client is expected to use PKCE
    secret: str | None = None
    # If no redirect_uri are hardcoded, the client will need to provide one in its request
    redirect_uri: str | None = None
    # Set of scopes the auth client is authorized to grant when issuing an access token.
    # See app.utils.types.scopes_type.ScopeType for possible values
    allowed_scopes: Set[ScopeType] = set()

    def get_userinfo(self, user: models_core.CoreUser):

        # For Nextcloud, partial claims
        # See https://github.com/pulsejet/nextcloud-oidc-login#config right values

        # For Piwigo, a name is sufficient. We need to put the claim name in th econfig file
        return {
            "sub": user.id,
            "name": user.firstname,
        }

        # info = BaseAuthClient.base_user_info(user=user)
        # return info

    ########################################################
    #                   Utilities methods                  #
    #    The following methods should not be overridden    #
    ########################################################

    @classmethod
    def base_user_info(cls, user: models_core.CoreUser):
        return {
            "sub": user.id,
            "name": user.firstname,
            "given_name": user.nickname,
            "family_name": user.name,
            "preferred_username": user.nickname,
            "ownCloudGroups": ["pixels"],
            "email": user.email,
            "picture": "",
            "piwigo_groups": ["pixelbbb", "pixels"],
        }

    @classmethod
    def filter_scopes(cls, requested_scopes: Set[str]) -> Set[ScopeType]:
        return cls.allowed_scopes.intersection(requested_scopes)


class ExampleClient(BaseAuthClient):
    secret = "secret"
    redirect_uri = "http://127.0.0.1:8000/docs"


class NextcloudAuthClient(BaseAuthClient):
    # For Nextcloud:
    # Required iss : the issuer value form .well-known (corresponding code : https://github.com/pulsejet/nextcloud-oidc-login/blob/0c072ecaa02579384bb5e10fbb9d219bbd96cfb8/3rdparty/jumbojett/openid-connect-php/src/OpenIDConnectClient.php#L1255)
    # Required claims : https://github.com/pulsejet/nextcloud-oidc-login/blob/0c072ecaa02579384bb5e10fbb9d219bbd96cfb8/3rdparty/jumbojett/openid-connect-php/src/OpenIDConnectClient.php#L1016

    def get_userinfo(self, user: models_core.CoreUser):
        # For Nextcloud, various claims can be provided.
        # See https://github.com/pulsejet/nextcloud-oidc-login#config for claim names

        return {
            "sub": user.id,
            "name": user.firstname,
            "given_name": user.nickname,
            "family_name": user.name,
            "preferred_username": user.nickname,
            "ownCloudGroups": user.groups,  # ["pixels"], # We may want to filter which groups are provided as they won't not always all be useful
            "email": user.email,
            "picture": "",  # TODO: add a PFP
        }


class PiwigoAuthClient(BaseAuthClient):
    def get_userinfo(self, user: models_core.CoreUser):
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
