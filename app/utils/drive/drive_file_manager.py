import google.oauth2.credentials
import googleapiclient.http
from googleapiclient.discovery import build

from app.utils.drive.config import DriveSettings


class DriveFileManager:
    def __init__(self):
        config = DriveSettings(_env_file=".google.env")

        oauth_credentials = google.oauth2.credentials.Credentials(
            token="",
            refresh_token=config.REFRESH_TOKEN,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=config.CLIENT_ID,
            client_secret=config.CLIENT_SECRET,
            scopes=["https://www.googleapis.com/auth/drive"],
        )

        self.drive_service = build(
            "drive", "v3", credentials=oauth_credentials, developerKey=config.API_KEY
        )
        self.working_folder_name = "Dossiers d'inscription"
        self.working_folder_id = "1j1h_ly9ZxRMnhXiegs0DzKbavNwwxDu9"

    def upload_file(self, file_path: str, file_name: str) -> str:
        file_metadata = {
            "name": file_name,
            "mimeType": "application/pdf",
            "parents": [self.working_folder_id],
        }
        media = googleapiclient.http.MediaFileUpload(
            file_path, mimetype="application/pdf"
        )
        response = (
            self.drive_service.files()
            .create(body=file_metadata, media_body=media)
            .execute()
        )
        return response.get("id")

    def replace_file(self, file_path: str, file_id: str) -> str:
        file_metadata = {
            "mimeType": "application/pdf",
        }
        media = googleapiclient.http.MediaFileUpload(
            file_path, mimetype="application/pdf"
        )
        if not file_id:
            return self.upload_file(file_path, file_id)
        response = (
            self.drive_service.files()
            .update(fileId=file_id, body=file_metadata, media_body=media)
            .execute()
        )
        return response.get("id")

    def delete_file(self, file_id: str) -> bool:
        self.drive_service.files().delete(fileId=file_id).execute()
        return True
