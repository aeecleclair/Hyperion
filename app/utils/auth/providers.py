import re
from typing import Any, Set

import unidecode

from app.models import models_core
from app.utils.tools import get_display_name, is_user_member_of_an_allowed_group
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

    # redirect_uri should alway match the one provided by the client
    redirect_uri: str
    # Set of scopes the auth client is authorized to grant when issuing an access token.
    # See app.utils.types.scopes_type.ScopeType for possible values
    # WARNING: to be able to use openid connect, `ScopeType.openid` should always be allowed
    allowed_scopes: Set[ScopeType] = {ScopeType.openid}
    # Restrict the authentication to this client to specific Hyperion groups.
    # When set to `None`, users from any group can use the auth client
    allowed_groups: list[GroupType] | None = None
    # Sometimes, when the client is wrongly configured, it may return an incorrect return_uri. This may also be useful for debugging clients.
    # `override_redirect_uri` allows bypassing all redirect_uri verifications and overriding the returned redirect_uri.
    # This setting will override the previous `BaseAuthClient.redirect_uri``
    # WARNING: This property is not part of OAuth or Openid connect specifications and should be used with caution.
    override_redirect_uri: str | None = None

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
        # There can indeed be more than one client using the class, the client will need to have its own client id and secret.

        self.client_id: str = client_id
        # If no secret is provided, the client is expected to use PKCE
        self.secret: str | None = secret

    def filter_scopes(self, requested_scopes: Set[str]) -> Set[ScopeType]:
        return self.allowed_scopes.intersection(requested_scopes)


class AppAuthClient(BaseAuthClient):
    """
    An auth client for Hyperion mobile application
    """

    # redirect_uri should alway match the one provided by the client
    redirect_uri: str
    # Set of scopes the auth client is authorized to grant when issuing an access token.
    # See app.utils.types.scopes_type.ScopeType for possible values
    # WARNING: to be able to use openid connect, `ScopeType.openid` should always be allowed
    allowed_scopes: Set[ScopeType] = {ScopeType.API}
    # Restrict the authentication to this client to specific Hyperion groups.
    # When set to `None`, users from any group can use the auth client
    allowed_groups: list[GroupType] | None = None


class PostmanAuthClient(BaseAuthClient):
    """
    An auth client for Postman
    """

    # redirect_uri should alway match the one provided by the client
    redirect_uri: str = "http://postman/"
    # Set of scopes the auth client is authorized to grant when issuing an access token.
    # See app.utils.types.scopes_type.ScopeType for possible values
    # WARNING: to be able to use openid connect, `ScopeType.openid` should always be allowed
    allowed_scopes: Set[ScopeType] = {ScopeType.API}


class NextcloudAuthClient(BaseAuthClient):
    # redirect_uri should alway match the one provided by the client
    redirect_uri: str = "https://ecloud.myecl.fr/apps/oidc_login/oidc"
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
            "name": get_display_name(
                firstname=user.firstname, name=user.name, nickname=user.nickname
            ),
            # TODO: should we use group ids instead of names? It would be less human readable but would guarantee uniqueness. Question: are group names unique?
            "groups": [
                group.name for group in user.groups
            ],  # We may want to filter which groups are provided as they won't always all be useful
            "email": user.email,
            "picture": f"https://hyperion.myecl.fr/users/{user.id}/profile-picture",
            "is_admin": is_user_member_of_an_allowed_group(user, [GroupType.admin]),
        }


class PiwigoAuthClient(BaseAuthClient):
    # redirect_uri should alway match the one provided by the client
    redirect_uri: str = "https://piwigo.myecl.fr/plugins/OpenIdConnect/auth.php"
    # Set of scopes the auth client is authorized to grant when issuing an access token.
    # See app.utils.types.scopes_type.ScopeType for possible values
    # WARNING: to be able to use openid connect, `ScopeType.openid` should always be allowed
    allowed_scopes: Set[ScopeType] = {ScopeType.openid}
    # Restrict the authentication to this client to specific Hyperion groups.
    # When set to `None`, users from any group can use the auth client
    allowed_groups: list[GroupType] | None = None
    # Sometimes, when the client is wrongly configured, it may return an incorrect return_uri. This may also be useful for debugging clients.
    # `override_redirect_uri` allows to bypass all redirect_uri verifications and override the returned redirect_uri.
    # This setting will override the previous `BaseAuthClient.redirect_uri``
    # WARNING: This property is not part of OAuth or Openid connect specifications and should be used with caution.
    override_redirect_uri: str | None = None

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

        # For Piwigo, providing the username is sufficient. The name of the claim (here `"name"`) needs to be set in Piwigo oidc plugin configuration page.
        # A modified Piwigo oidc plugin allows managing groups from the oidc provider
        return {
            "sub": user.id,
            "name": get_display_name(
                firstname=user.firstname, name=user.name, nickname=user.nickname
            ),
            "groups": [group.name for group in user.groups],
            "email": user.email,
        }


class HedgeDocAuthClient(BaseAuthClient):
    # redirect_uri should alway match the one provided by the client
    redirect_uri: str = "https://hedgedoc.eclair.ec-lyon.fr/auth/oauth2/callback"
    # Set of scopes the auth client is authorized to grant when issuing an access token.
    # See app.utils.types.scopes_type.ScopeType for possible values
    allowed_scopes: Set[ScopeType] = {ScopeType.profile}

    @classmethod
    def get_userinfo(cls, user: models_core.CoreUser):
        return {
            "sub": user.id,
            "name": user.firstname,
            "email": user.email,
        }


class WikijsAuthClient(BaseAuthClient):
    # https://github.com/requarks/wiki/blob/main/server/modules/authentication/oidc/definition.yml

    # redirect_uri should alway match the one provided by the client
    redirect_uri: str = (
        "https://wiki.myecl.fr/login/ebf58183-230b-4d2d-aa12-77bef30512b7/callback"
    )
    # Set of scopes the auth client is authorized to grant when issuing an access token.
    # See app.utils.types.scopes_type.ScopeType for possible values
    allowed_scopes: Set[ScopeType] = {ScopeType.openid, ScopeType.profile}

    @classmethod
    def get_userinfo(cls, user: models_core.CoreUser):
        return {
            "sub": user.id,
            "name": get_display_name(
                firstname=user.firstname, name=user.name, nickname=user.nickname
            ),
            "email": user.email,
            "groups": [group.name for group in user.groups],
        }


class SynapseAuthClient(BaseAuthClient):
    # redirect_uri should alway match the one provided by the client
    redirect_uri: str = "https://matrix.eclair.ec-lyon.fr/_synapse/client/oidc/callback"
    # Set of scopes the auth client is authorized to grant when issuing an access token.
    # See app.utils.types.scopes_type.ScopeType for possible values
    allowed_scopes: Set[ScopeType] = {ScopeType.openid, ScopeType.profile}

    @classmethod
    def get_userinfo(cls, user: models_core.CoreUser):
        # Accepted characters are [a-z] [0-9] `.` and `-`. Spaces are replaced by `-` and accents are removed.
        username = (
            unidecode.unidecode(f"{user.firstname.strip()}.{user.name.strip()}")
            .lower()
            .replace(" ", "-")
        )
        username = re.sub(r"[^a-z0-9.-\\]", "", username)

        return {
            "sub": user.id,
            "picture": f"https://hyperion.myecl.fr/users/{user.id}/profile-picture",
            # Matrix does not support special characters in username
            "username": username,
            "displayname": get_display_name(
                firstname=user.firstname, name=user.name, nickname=user.nickname
            ),
            "email": user.email,
        }


class MinecraftAuthClient(BaseAuthClient):
    # redirect_uri should alway match the one provided by the client
    redirect_uri: str = "http://minecraft.myecl.fr:25566"
    # Set of scopes the auth client is authorized to grant when issuing an access token.
    # See app.utils.types.scopes_type.ScopeType for possible values
    allowed_scopes: Set[ScopeType] = {ScopeType.profile}

    @classmethod
    def get_userinfo(cls, user: models_core.CoreUser):
        return {
            "id": user.id,
            "nickname": user.nickname,
            "promo": user.promo,
            "floor": user.floor,
        }


class ChallengerAuthClient(BaseAuthClient):
    # redirect_uri should alway match the one provided by the client
    redirect_uri: str = "https://challenger.challenge-centrale-lyon.fr/login"
    # Set of scopes the auth client is authorized to grant when issuing an access token.
    # See app.utils.types.scopes_type.ScopeType for possible values
    allowed_scopes: Set[ScopeType] = {ScopeType.openid, ScopeType.profile}

    @classmethod
    def get_userinfo(cls, user: models_core.CoreUser):
        return {
            "sub": user.id,
            "name": user.name,
            "firstname": user.firstname,
            "email": user.email,
        }


class OpenProjectAuthClient(BaseAuthClient):
    # redirect_uri should alway match the one provided by the client
    redirect_uri: str = "https://project.myecl.fr:443/auth/myecl/callback"
    # Set of scopes the auth client is authorized to grant when issuing an access token.
    # See app.utils.types.scopes_type.ScopeType for possible values
    allowed_scopes: Set[ScopeType] = {ScopeType.openid, ScopeType.profile}

    @classmethod
    def get_userinfo(cls, user: models_core.CoreUser):
        return {
            "sub": user.id,
            "name": get_display_name(
                firstname=user.firstname, name=user.name, nickname=user.nickname
            ),
            "given_name": user.firstname,
            "family_name": user.name,
            "picture": f"https://hyperion.myecl.fr/users/{user.id}/profile-picture",
            "email": user.email,
            "email_verified": True,
        }
