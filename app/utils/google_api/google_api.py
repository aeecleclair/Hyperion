import logging

from fastapi import HTTPException, Request
from google.auth.transport import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.types.exceptions import (
    CoreDataNotFoundException,
    GoogleAPIInvalidCredentialsError,
    GoogleAPIMissingConfigInDotenvError,
)
from app.utils.google_api.coredata_google_api import (
    GoogleAPICredentials,
    GoogleAPIOAuthFlow,
)
from app.utils.tools import get_core_data, set_core_data

hyperion_error_logger = logging.getLogger("hyperion.error")


class GoogleAPI:
    SCOPES = [
        "https://www.googleapis.com/auth/script.projects",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/documents",
        "https://www.googleapis.com/auth/drive.readonly",
    ]

    def _get_flow(self, settings: Settings) -> Flow:
        if (
            settings.GOOGLE_API_CLIENT_ID is None
            or settings.GOOGLE_API_CLIENT_SECRET is None
        ):
            raise GoogleAPIMissingConfigInDotenvError(
                "Google API is not configured in dotenv",
            )

        client_config = {
            "web": {
                "client_id": settings.GOOGLE_API_CLIENT_ID,
                # "project_id": "",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": settings.GOOGLE_API_CLIENT_SECRET,
                # "redirect_uris": [""],
            },
        }
        flow = Flow.from_client_config(
            client_config,
            GoogleAPI.SCOPES,
            redirect_uri=settings.DOCKER_URL + "google-api/oauth2callback",
        )

        return flow

    async def _start_authentication(
        self,
        db: AsyncSession,
        settings: Settings,
    ) -> Credentials:
        """
        Start an authentication oauth 2 flow with the Google API.
        This method should only be called if tokens are not available in the database.

        You should use `get_credentials` to get the credentials, which will call this method if needed.
        """
        # See https://developers.google.com/identity/protocols/oauth2/web-server?hl=fr#python

        flow = self._get_flow(settings=settings)

        authorization_url, state = flow.authorization_url(
            # Recommended, enable offline access so that you can refresh an access token without
            # re-prompting the user for permission. Recommended for web server apps.
            access_type="offline",
            # Optional, enable incremental authorization. Recommended as a best practice.
            include_granted_scopes="true",
            # Optional, if your application knows which user is trying to authenticate, it can use this
            # parameter to provide a hint to the Google Authentication Server.
            login_hint="hyperion@",
            # Optional, set prompt to 'consent' will prompt the user for consent
            prompt="consent",
        )

        # We store the state in the database to be able to check it later in the callback endpoint.
        core_data = GoogleAPIOAuthFlow(state=state)
        await set_core_data(core_data=core_data, db=db)

        hyperion_error_logger.error(
            f"Google API authentication. Visit {authorization_url} to authorize Hyperion",
        )

    async def authentication_callback(
        self,
        db: AsyncSession,
        settings: Settings,
        request: Request,
    ):
        core_data: GoogleAPIOAuthFlow = await get_core_data(
            GoogleAPIOAuthFlow,
            db=db,
        )

        data = request.query_params

        if data.get("state", None) != core_data.state:
            hyperion_error_logger.error(
                f"Mismatched state in Google API authentication, got {data.get('state', None)} but expected {core_data.state}",
            )
            raise HTTPException(400, "Mismatched state in Google API authentication")

        flow = self._get_flow(settings=settings)

        flow.fetch_token(**data)

        creds = flow.credentials

        core_data = GoogleAPICredentials.model_validate_json(creds.to_json())
        await set_core_data(core_data=core_data, db=db)

    async def get_credentials(
        self,
        db: AsyncSession,
        settings: Settings,
    ) -> Credentials:
        """
        Return the credentials for the Google API.
        The method will check if valid credentials are available in the database. If they are expired, they will be renewed using the refresh token.

        If not, an oauth flow will be started using `_start_authentication()` to get new credentials and an error will be raised.

        Obtained or renewed credentials will be saved in the database for future use.
        """

        creds: Credentials | None = None

        try:
            # We store the credentials in the database to be able to use them in the future.
            core_data: GoogleAPICredentials = await get_core_data(
                GoogleAPICredentials,
                db=db,
            )

            creds = Credentials(
                token=core_data.token,
                refresh_token=core_data.refresh_token,
                token_uri=core_data.token_uri,
                client_id=core_data.client_id,
                client_secret=core_data.client_secret,
                scopes=core_data.scopes,
                # Even if Google API return a timezone aware expiry datetime
                # it requires a naive datetime object to be able to check if the token is expired.
                expiry=core_data.expiry.replace(tzinfo=None),
            )

        except CoreDataNotFoundException:
            # There are no credentials in the database.
            # This means that Hyperion was never launched with a Google API configuration.
            # We need to start the authentication flow.
            await self._start_authentication(db=db, settings=settings)
            raise GoogleAPIInvalidCredentialsError(
                "Missing credentials in database. A new authentication flow was started",
            ) from None

        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(requests.Request())

                # Save the credentials for the next run
                core_data = GoogleAPICredentials.model_validate_json(creds.to_json())
                await set_core_data(core_data=core_data, db=db)
            else:
                await self._start_authentication(db=db, settings=settings)
                raise GoogleAPIInvalidCredentialsError(
                    "Credentials are not valid. A new authentication flow was started",
                ) from None

        return creds
