import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.google_api.google_api import DriveGoogleAPI
from app.core.utils.config import Settings
from app.modules.raid import coredata_raid
from app.utils.tools import get_core_data, set_core_data

hyperion_error_logger = logging.getLogger("hyperion.error")


class DriveFileManager:
    def __init__(self):
        self.REGISTERING_FOLDER_NAME = "Équipes"
        self.SECURITY_FOLDER_NAME = "Fiches sécurité"
        self.drive_folders: coredata_raid.RaidDriveFolders | None = None

    async def init_folders(self, db: AsyncSession, settings: Settings) -> None:
        if self.drive_folders:
            hyperion_error_logger.info(
                "Raid Registering: drive folders already initialized",
            )
        else:
            hyperion_error_logger.info(
                "Raid Registering: creating drive folders",
            )
            self.drive_folders = await get_core_data(coredata_raid.RaidDriveFolders, db)
            if not self.drive_folders.parent_folder_id:
                hyperion_error_logger.error("No parent folder id found in database")
                return
            async with DriveGoogleAPI(db, settings) as google_api:
                if not self.drive_folders.registering_folder_id:
                    self.drive_folders.registering_folder_id = google_api.create_folder(
                        self.REGISTERING_FOLDER_NAME,
                        self.drive_folders.parent_folder_id,
                    )
                if not self.drive_folders.security_folder_id:
                    self.drive_folders.security_folder_id = google_api.create_folder(
                        self.SECURITY_FOLDER_NAME,
                        self.drive_folders.parent_folder_id,
                    )
            await set_core_data(
                self.drive_folders,
                db,
            )

    async def upload_team_file(
        self,
        file_path: str,
        file_name: str,
        db: AsyncSession,
        settings: Settings,
    ) -> str:
        await self.init_folders(db, settings)
        if not self.drive_folders or not self.drive_folders.registering_folder_id:
            hyperion_error_logger.error("No registering folder id found in database")
            return ""
        async with DriveGoogleAPI(db, settings) as google_api:
            return await google_api.upload_file(
                file_path,
                file_name,
                self.drive_folders.registering_folder_id,
            )

    async def upload_participant_file(
        self,
        file_path: str,
        file_name: str,
        db: AsyncSession,
        settings: Settings,
    ) -> str:
        await self.init_folders(db, settings)
        if not self.drive_folders or not self.drive_folders.security_folder_id:
            hyperion_error_logger.error("No security folder id found in database")
            return ""
        async with DriveGoogleAPI(db, settings) as google_api:
            return await google_api.upload_file(
                file_path,
                file_name,
                self.drive_folders.security_folder_id,
            )

    async def upload_raid_file(
        self,
        file_path: str,
        file_name: str,
        db: AsyncSession,
        settings: Settings,
    ) -> str:
        await self.init_folders(db, settings)
        if not self.drive_folders or not self.drive_folders.parent_folder_id:
            hyperion_error_logger.error("No parent folder id found in database")
            return ""
        async with DriveGoogleAPI(db, settings) as google_api:
            return await google_api.upload_file(
                file_path,
                file_name,
                self.drive_folders.parent_folder_id,
                mimetype="text/csv",
            )
