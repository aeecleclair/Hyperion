# TODO: How do we store the secret properly ?


from app.models import models_core


class BaseAuthClient:
    secret: str = ""
    redirect_uri: str = "azerty"

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


class NextcloudAuthClient(BaseAuthClient):
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
