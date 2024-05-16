import logging

import google.oauth2.credentials
import googleapiclient.http
from googleapiclient.discovery import build
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_settings
from app.modules.raid import schemas_raid
from app.utils.tools import get_core_data, set_core_data

hyperion_error_logger = logging.getLogger("hyperion.error")


class DriveFileManager:
    def __init__(self):
        config = get_settings()

        oauth_credentials = google.oauth2.credentials.Credentials(
            token="",
            refresh_token=config.RAID_DRIVE_REFRESH_TOKEN,
            token_uri="https://oauth2.googleapis.com/token",  # noqa: S106
            client_id=config.RAID_DRIVE_CLIENT_ID,
            client_secret=config.RAID_DRIVE_CLIENT_SECRET,
            scopes=["https://www.googleapis.com/auth/drive"],
        )

        self.drive_service = build(
            "drive",
            "v3",
            credentials=oauth_credentials,
            developerKey=config.RAID_DRIVE_API_KEY,
        )

        self.REGISTERING_FOLDER_NAME = "Équipes"
        self.SECURITY_FOLDER_NAME = "Fiches sécurité"
        self.drive_folders = None

    async def init_folders(self, db: AsyncSession):
        if not self.drive_folders:
            self.drive_folders = await get_core_data(schemas_raid.RaidDriveFolders, db)
            if not self.drive_folders.parent_folder_id:
                hyperion_error_logger.error("No parent folder id found in database")
                return
            if not self.drive_folders.registering_folder_id:
                self.drive_folders.registering_folder_id = self.create_folder(
                    self.REGISTERING_FOLDER_NAME,
                    self.drive_folders.parent_folder_id,
                )
            if not self.drive_folders.security_folder_id:
                self.drive_folders.security_folder_id = self.create_folder(
                    self.SECURITY_FOLDER_NAME,
                    self.drive_folders.parent_folder_id,
                )
            await set_core_data(
                self.drive_folders,
                db,
            )

    def create_folder(self, folder_name: str, parent_folder_id: str) -> str:
        file_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_folder_id],
        }
        response = self.drive_service.files().create(body=file_metadata).execute()
        return response.get("id")

    async def upload_file(
        self,
        file_path: str,
        file_name: str,
        parent_folder_id: str,
        mimetype: str = "application/pdf",
    ) -> str:
        file_metadata = {
            "name": file_name,
            "mimeType": mimetype,
            "parents": [parent_folder_id],
        }
        media = googleapiclient.http.MediaFileUpload(
            file_path,
            mimetype=mimetype,
        )
        response = (
            self.drive_service.files()
            .create(body=file_metadata, media_body=media)
            .execute()
        )
        return response.get("id")

    async def upload_team_file(
        self,
        file_path: str,
        file_name: str,
        db: AsyncSession,
    ) -> str:
        await self.init_folders(db)
        return await self.upload_file(
            file_path,
            file_name,
            self.drive_folders.registering_folder_id,
        )

    async def upload_participant_file(
        self,
        file_path: str,
        file_name: str,
        db: AsyncSession,
    ) -> str:
        await self.init_folders(db)
        return await self.upload_file(
            file_path,
            file_name,
            self.drive_folders.security_folder_id,
        )

    async def upload_raid_file(
        self,
        file_path: str,
        file_name: str,
        db: AsyncSession,
    ) -> str:
        await self.init_folders(db)
        return await self.upload_file(
            file_path,
            file_name,
            self.drive_folders.parent_folder_id,
            mimetype="text/csv",
        )

    def replace_file(
        self,
        file_path: str,
        file_id: str,
    ) -> str:
        file_metadata = {
            "mimeType": "application/pdf",
        }
        media = googleapiclient.http.MediaFileUpload(
            file_path,
            mimetype="application/pdf",
        )
        response = (
            self.drive_service.files()
            .update(fileId=file_id, body=file_metadata, media_body=media)
            .execute()
        )
        return response.get("id")

    def delete_file(self, file_id: str) -> bool:
        self.drive_service.files().delete(fileId=file_id).execute()
        return True
