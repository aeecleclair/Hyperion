import logging
from types import TracebackType

from fastapi import HTTPException, Request
from google.auth.transport import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import Resource, build
from googleapiclient.http import MediaFileUpload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.google_api import cruds_google_api
from app.core.google_api.coredata_google_api import (
    GoogleAPICredentials,
)
from app.core.google_api.models_google_api import OAuthFlowState
from app.core.utils.config import Settings
from app.types.exceptions import (
    CoreDataNotFoundError,
    GoogleAPIInvalidCredentialsError,
    GoogleAPIMissingConfigInDotenvError,
)
from app.utils.tools import get_core_data, set_core_data

hyperion_error_logger = logging.getLogger("hyperion.error")

GoogleId = str


class GoogleAPI:
    SCOPES = [
        "https://www.googleapis.com/auth/script.projects",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/documents",
        "https://www.googleapis.com/auth/drive.readonly",
    ]

    def is_google_api_configured(self, settings: Settings) -> bool:
        return (
            settings.GOOGLE_API_CLIENT_ID is not None
            and settings.GOOGLE_API_CLIENT_SECRET is not None
        )

    def _get_flow(self, settings: Settings) -> Flow:
        if not self.is_google_api_configured(settings):
            raise GoogleAPIMissingConfigInDotenvError

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
            redirect_uri=settings.CLIENT_URL + "google-api/oauth2callback",
        )

        return flow

    async def _start_authentication(
        self,
        db: AsyncSession,
        settings: Settings,
    ) -> None:
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
        oauth_flow_state = OAuthFlowState(state=state)
        await cruds_google_api.create_oauth_flow_state(
            oauth_flow_state=oauth_flow_state,
            db=db,
        )

        hyperion_error_logger.error(
            f"Google API authentication. Visit {authorization_url} to authorize Hyperion",
        )

    async def authentication_callback(
        self,
        db: AsyncSession,
        settings: Settings,
        request: Request,
    ):
        data = request.query_params

        provided_state = data.get("state", None)
        if provided_state is None:
            hyperion_error_logger.error(
                "Missing state in Google API authentication callback",
            )
            raise HTTPException(400, "Missing state in Google API authentication")

        # There may be multiple states in the database, if the authentication process was instanced more than once
        oauth_flow_state = await cruds_google_api.get_oauth_flow_state_by_state(
            state=provided_state,
            db=db,
        )

        if oauth_flow_state is None:
            hyperion_error_logger.error(
                f"Invalid state in Google API authentication, got {provided_state}. This may also happen if a previous auth was successful, purging existing and waiting states",
            )
            raise HTTPException(400, "Mismatched state in Google API authentication")

        flow = self._get_flow(settings=settings)

        flow.fetch_token(**data)

        creds = flow.credentials

        credentials_core_data = GoogleAPICredentials.model_validate_json(
            creds.to_json(),
        )
        await set_core_data(core_data=credentials_core_data, db=db)

        await cruds_google_api.delete_all_states(db=db)

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

        except CoreDataNotFoundError:
            # There are no credentials in the database.
            # This means that Hyperion was never launched with a Google API configuration.
            # We need to start the authentication flow.
            await self._start_authentication(db=db, settings=settings)
            raise GoogleAPIInvalidCredentialsError(  # noqa: TRY003
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
                raise GoogleAPIInvalidCredentialsError(  # noqa: TRY003
                    "Credentials are not valid. A new authentication flow was started",
                ) from None

        return creds


class DriveGoogleAPI:
    """
    DriveGoogleAPI async context manager.

    Example usage:
    ```python
    async with DriveGoogleAPI(db, settings) as google_api:
        google_api.create_folder("folder_name", "parent_folder_id")
    ```
    """

    def __init__(self, db: AsyncSession, settings: Settings):
        self._db = db
        self._settings = settings

    async def __aenter__(self) -> "DriveGoogleAPI":
        google_api = GoogleAPI()
        creds = await google_api.get_credentials(self._db, self._settings)
        self._drive: Resource = build("drive", "v3", credentials=creds)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        # https://github.com/googleapis/google-api-python-client/blob/main/docs/start.md#build-the-service-object
        self._drive.close()

        # We return False to let the exception propagate if there is one.
        return False

    def create_folder(self, folder_name: str, parent_folder_id: GoogleId) -> GoogleId:
        """
        Create a folder in Google Drive, and return its id.
        """

        file_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_folder_id],
        }
        response = self._drive.files().create(body=file_metadata).execute()
        folder_id: GoogleId = response.get("id")
        return folder_id

    async def upload_file(
        self,
        file_path: str,
        file_name: str,
        parent_folder_id: GoogleId,
        mimetype: str = "application/pdf",
    ) -> GoogleId:
        """
        Upload a file to Google Drive, and return its id.
        """
        file_metadata = {
            "name": file_name,
            "mimeType": mimetype,
            "parents": [parent_folder_id],
        }
        media = MediaFileUpload(
            file_path,
            mimetype=mimetype,
        )
        response = (
            self._drive.files().create(body=file_metadata, media_body=media).execute()
        )
        uploaded_file_id: GoogleId = response.get("id")
        return uploaded_file_id

    def replace_file(
        self,
        file_path: str,
        file_id: GoogleId,
    ) -> GoogleId:
        file_metadata = {
            "mimeType": "application/pdf",
        }
        media = MediaFileUpload(
            file_path,
            mimetype="application/pdf",
        )
        response = (
            self._drive.files()
            .update(fileId=file_id, body=file_metadata, media_body=media)
            .execute()
        )
        result: GoogleId = response.get("id")
        return result

    def delete_file(self, file_id: GoogleId) -> None:
        self._drive.files().delete(fileId=file_id).execute()
