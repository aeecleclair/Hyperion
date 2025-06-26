import re
from typing import Any

import unidecode

from app.core.groups.groups_type import (
    AccountType,
    GroupType,
    get_account_types_except_externals,
    get_ecl_account_types,
    get_schools_account_types,
)
from app.core.users import models_users
from app.types.floors_type import FloorsType
from app.types.scopes_type import ScopeType
from app.utils.tools import is_user_member_of_any_group


class BaseAuthClient:
    """
    When registering an OAuth or Openid connect client in config, a corresponding auth_client must be provided.
    The auth_client class is responsible for configuring the redirect_uri, granting scopes, returning adapted userinfo...

    To register a new client, you should create a new class inheriting from `BaseAuthClient` and override some of its parameters and methods
    """

    ########################################################
    # Auth client configuration: override these parameters #
    ########################################################

    # Set of scopes the auth client is authorized to grant when issuing an access token.
    # See app.types.scopes_type.ScopeType for possible values
    # If the client always send a specific scope (ex: `name`), you may add it to the allowed scopes as a string (ex: `"name"`)
    # These "string" scopes won't have any effect for Hyperion but won't raise a warning when asked by the client
    # WARNING: to be able to use openid connect, `ScopeType.openid` should always be allowed
    allowed_scopes: set[ScopeType | str] = {ScopeType.openid}
    # Restrict the authentication to this client to specific Hyperion groups.
    # When set to `None`, users from any group can use the auth client
    allowed_groups: list[GroupType] | None = None
    # Restrict the authentication to this client to specific Hyperion account types.
    # When set to `None`, users from any account type can use the auth client
    allowed_account_types: list[AccountType] | None = (
        get_account_types_except_externals()
    )
    # redirect_uri should alway match the one provided by the client
    redirect_uri: list[str]
    # Sometimes, when the client is wrongly configured, it may return an incorrect return_uri. This may also be useful for debugging clients.
    # `override_redirect_uri` allows bypassing all redirect_uri verifications and overriding the returned redirect_uri.
    # This setting will override the previous `BaseAuthClient.redirect_uri``
    # WARNING: This property is not part of OAuth or Openid connect specifications and should be used with caution.
    override_redirect_uri: str | None = None

    # Some rare oidc providers (like NextAuth.js) does not support getting userinfo from userinfo endpoints
    # but instead require to include the user information in the id_token
    # By setting this parameter to True, the userinfo will be added to the id_token.
    return_userinfo_in_id_token: bool = False

    # Some clients may require to enable token introspection to validate access tokens.
    # We don't want to enable token introspection for all clients as it may be a security risk, allowing attackers to do token fishing.
    allow_token_introspection: bool = False

    # OIDC specification forbids using PKCE when using a client secret.
    # However, some clients may try to use PKCE anyway. This parameter allows to bypass this check.
    # NOTE: you should only set this to True if you are sure the client is correctly configured and secure.
    allow_pkce_with_client_secret: bool = False

    def get_userinfo(self, user: models_users.CoreUser) -> dict[str, Any]:
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

    def __init__(
        self,
        client_id: str,
        secret: str | None,
        redirect_uri: list[str],
    ) -> None:
        # The following parameters are not class variables but instance variables.
        # There can indeed be more than one client using the class, the client will need to have its own client id and secret.

        self.client_id: str = client_id
        # If no secret is provided, the client is expected to use PKCE
        self.secret: str | None = secret
        # redirect_uri should alway match the one provided by the client
        self.redirect_uri: list[str] = redirect_uri

    def filter_scopes(self, requested_scopes: set[str]) -> set[ScopeType | str]:
        return self.allowed_scopes.intersection(requested_scopes)


class AppAuthClient(BaseAuthClient):
    """
    An auth client for Hyperion mobile application
    """

    # Set of scopes the auth client is authorized to grant when issuing an access token.
    # See app.types.scopes_type.ScopeType for possible values
    # WARNING: to be able to use openid connect, `ScopeType.openid` should always be allowed
    allowed_scopes: set[ScopeType | str] = {ScopeType.API}

    allowed_account_types: list[AccountType] | None = (
        None  # No restriction on account types
    )


class APIToolAuthClient(BaseAuthClient):
    """
    An auth client for API development tools
    """

    allowed_scopes: set[ScopeType | str] = {ScopeType.API}
    allow_pkce_with_client_secret: bool = True


class NextcloudAuthClient(BaseAuthClient):
    allowed_account_types: list[AccountType] | None = get_ecl_account_types()

    # For Nextcloud:
    # Required iss : the issuer value form .well-known (corresponding code : https://github.com/pulsejet/nextcloud-oidc-login/blob/0c072ecaa02579384bb5e10fbb9d219bbd96cfb8/3rdparty/jumbojett/openid-connect-php/src/OpenIDConnectClient.php#L1255)
    # Required claims : https://github.com/pulsejet/nextcloud-oidc-login/blob/0c072ecaa02579384bb5e10fbb9d219bbd96cfb8/3rdparty/jumbojett/openid-connect-php/src/OpenIDConnectClient.php#L1016

    @classmethod
    def get_userinfo(cls, user: models_users.CoreUser):
        # For Nextcloud, various claims can be provided.
        # See https://github.com/pulsejet/nextcloud-oidc-login#config for claim names

        return {
            "sub": user.id,
            "name": user.full_name,
            # TODO: should we use group ids instead of names? It would be less human readable but would guarantee uniqueness. Question: are group names unique?
            # We may want to filter which groups are provided as they won't always all be useful
            "groups": [group.name for group in user.groups] + [user.account_type.value],
            "email": user.email,
            "picture": f"https://hyperion.myecl.fr/users/{user.id}/profile-picture",
            "is_admin": is_user_member_of_any_group(user, [GroupType.admin]),
        }


class PiwigoAuthClient(BaseAuthClient):
    # Restrict the authentication to this client to specific Hyperion groups.
    # When set to `None`, users from any group can use the auth client
    allowed_account_types: list[AccountType] | None = get_ecl_account_types()

    def get_userinfo(self, user: models_users.CoreUser) -> dict[str, Any]:
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
            "name": user.full_name,
            "groups": [group.name for group in user.groups] + [user.account_type.value],
            "email": user.email,
        }


class HedgeDocAuthClient(BaseAuthClient):
    # Set of scopes the auth client is authorized to grant when issuing an access token.
    # See app.types.scopes_type.ScopeType for possible values
    allowed_scopes: set[ScopeType | str] = {ScopeType.profile}

    allowed_account_types: list[AccountType] | None = get_ecl_account_types()

    @classmethod
    def get_userinfo(cls, user: models_users.CoreUser):
        return {
            "sub": user.id,
            "name": user.firstname,
            "email": user.email,
        }


class WikijsAuthClient(BaseAuthClient):
    # https://github.com/requarks/wiki/blob/main/server/modules/authentication/oidc/definition.yml

    # Set of scopes the auth client is authorized to grant when issuing an access token.
    # See app.types.scopes_type.ScopeType for possible values
    allowed_scopes: set[ScopeType | str] = {ScopeType.openid, ScopeType.profile}

    allowed_account_types: list[AccountType] | None = get_schools_account_types()

    @classmethod
    def get_userinfo(cls, user: models_users.CoreUser):
        return {
            "sub": user.id,
            "name": user.full_name,
            "email": user.email,
            "groups": [group.name for group in user.groups] + [user.account_type.value],
        }


class SynapseAuthClient(BaseAuthClient):
    # Set of scopes the auth client is authorized to grant when issuing an access token.
    # See app.types.scopes_type.ScopeType for possible values
    allowed_scopes: set[ScopeType | str] = {ScopeType.openid, ScopeType.profile}

    allowed_account_types: list[AccountType] | None = get_ecl_account_types()

    # https://github.com/matrix-org/matrix-authentication-service/issues/2088
    return_userinfo_in_id_token: bool = True

    allow_token_introspection: bool = True

    @classmethod
    def get_userinfo(cls, user: models_users.CoreUser):
        # Accepted characters are [a-z] [0-9] `.` and `-`. Spaces are replaced by `-` and accents are removed.
        username = (
            unidecode.unidecode(f"{user.firstname.strip()}.{user.name.strip()}")
            .lower()
            .replace(" ", "-")
        )
        username = re.sub(r"[^a-z0-9.-\\]", "", username)

        return {
            "sub": user.id,
            # "picture": f"https://hyperion.myecl.fr/users/{user.id}/profile-picture",
            # Matrix does not support special characters in username
            "username": username,
            "displayname": user.full_name,
            "email": user.email,
        }


class MinecraftAuthClient(BaseAuthClient):
    # Set of scopes the auth client is authorized to grant when issuing an access token.
    # See app.types.scopes_type.ScopeType for possible values
    allowed_scopes: set[ScopeType | str] = {ScopeType.profile}

    allowed_account_types: list[AccountType] | None = get_ecl_account_types()

    @classmethod
    def get_userinfo(cls, user: models_users.CoreUser):
        return {
            "id": user.id,
            "nickname": user.nickname,
            "promo": user.promo,
            "floor": user.floor or FloorsType.Autre,
        }


class ChallengerAuthClient(BaseAuthClient):
    # Set of scopes the auth client is authorized to grant when issuing an access token.
    # See app.types.scopes_type.ScopeType for possible values
    allowed_scopes: set[ScopeType | str] = {ScopeType.openid, ScopeType.profile}

    @classmethod
    def get_userinfo(cls, user: models_users.CoreUser):
        return {
            "sub": user.id,
            "name": user.name,
            "firstname": user.firstname,
            "email": user.email,
        }


class OpenProjectAuthClient(BaseAuthClient):
    # Set of scopes the auth client is authorized to grant when issuing an access token.
    # See app.types.scopes_type.ScopeType for possible values
    allowed_scopes: set[ScopeType | str] = {ScopeType.openid, ScopeType.profile}

    allowed_account_types: list[AccountType] | None = None

    @classmethod
    def get_userinfo(cls, user: models_users.CoreUser):
        return {
            "sub": user.id,
            "name": user.full_name,
            "given_name": user.firstname,
            "family_name": user.name,
            "picture": f"https://hyperion.myecl.fr/users/{user.id}/profile-picture",
            "email": user.email,
            "email_verified": True,
        }


class RalllyAuthClient(BaseAuthClient):
    allowed_scopes: set[ScopeType | str] = {
        ScopeType.openid,
        ScopeType.profile,
        "email",
    }

    return_userinfo_in_id_token: bool = True

    @classmethod
    def get_userinfo(cls, user: models_users.CoreUser):
        return {
            "sub": user.id,
            "name": user.full_name,
            "email": user.email,
        }


class DocumensoAuthClient(BaseAuthClient):
    allowed_scopes: set[ScopeType | str] = {ScopeType.openid}

    allow_pkce_with_client_secret: bool = True

    allowed_groups: list[GroupType] | None = [
        GroupType.admin,
        GroupType.BDE,
        GroupType.eclair,
    ]

    return_userinfo_in_id_token: bool = True

    @classmethod
    def get_userinfo(cls, user: models_users.CoreUser):
        return {
            "sub": user.id,
            "name": user.full_name,
            "email": user.email,
        }


class RAIDRegisteringAuthClient(BaseAuthClient):
    """
    An auth client for The Raid registering website
    """

    # Set of scopes the auth client is authorized to grant when issuing an access token.
    # See app.utils.types.scopes_type.ScopeType for possible values
    # WARNING: to be able to use openid connect, `ScopeType.openid` should always be allowed
    allowed_scopes: set[ScopeType | str] = {ScopeType.API}

    allowed_account_types: list[AccountType] | None = (
        None  # No restriction on account types
    )


class SiarnaqAuthClient(BaseAuthClient):
    allowed_scopes: set[ScopeType | str] = {ScopeType.API}

    allowed_account_types: list[AccountType] | None = (
        None  # No restriction on account types
    )


class OverleafAuthClient(BaseAuthClient):
    allowed_account_types: list[AccountType] | None = get_ecl_account_types()

    @classmethod
    def get_userinfo(cls, user: models_users.CoreUser):
        return {
            "sub": user.id,
            "firstname": user.firstname,
            "lastname": user.name,
            "email": user.email,
            "is_admin": is_user_member_of_any_group(user, [GroupType.admin]),
        }


class PlankaAuthClient(BaseAuthClient):
    """
    An auth client for Planka, a Trello alternative for kanban boards

    Docs for OIDC integration:
    https://docs.planka.cloud/docs/Configuration/OIDC/
    """

    # required in practice, as Planka uses PKCE as well as the client secret
    allow_pkce_with_client_secret: bool = True
    allowed_scopes: set[ScopeType | str] = {
        ScopeType.openid,
        ScopeType.profile,
    }

    @classmethod
    def get_userinfo(cls, user: models_users.CoreUser):
        return {
            "sub": user.id,
            "name": user.full_name,
            "groups": [group.name for group in user.groups] + [user.account_type.value],
            "email": user.email,
        }


class SlashAuthClient(BaseAuthClient):
    # When set to `None`, users from any group can use the auth client
    allowed_account_types: list[AccountType] | None = get_ecl_account_types()

    def get_userinfo(self, user: models_users.CoreUser) -> dict[str, Any]:
        """
        See oidc specifications and `app.endpoints.auth.auth_get_userinfo` for more information:
        https://openid.net/specs/openid-connect-core-1_0.html#UserInfo

        """
        # Override this method with custom information adapted for the client
        # WARNING: The sub (subject) Claim MUST always be returned in the UserInfo Response.
        return {
            "sub": user.id,
            "name": user.full_name,
            "email": user.email,
        }
