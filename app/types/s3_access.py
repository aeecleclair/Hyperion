from datetime import UTC, datetime, timedelta
from io import BytesIO
from logging import Logger

import boto3
import botocore
import botocore.exceptions

from app.core.utils.config import Settings
from app.types.exceptions import (
    InvalidS3AccessError,
    InvalidS3BucketNameError,
    InvalidS3FileNameError,
)


class S3Access:
    """Class to manage S3 access with object locking."""

    def __init__(
        self,
        settings: Settings,
        folder: str = "logs/",
        retention: int = -1,
        failure_logger: Logger | None = None,
    ) -> None:
        self.bucket_name = settings.S3_BUCKET_NAME or "default-bucket-name"
        self.folder = folder
        self.retention = retention
        self.failure_logger = failure_logger
        if settings.S3_ACCESS_KEY_ID is None or settings.S3_SECRET_ACCESS_KEY is None:
            if self.failure_logger:
                self.failure_logger.critical(
                    "S3_ACCESS_KEY_ID or S3_SECRET_ACCESS_KEY is not set. Working with logger only.",
                )
            self.s3 = None
            return
        self.s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.S3_ACCESS_KEY_ID or "default",
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY or "default",
        )
        try:
            response = self.s3.list_buckets()
        except botocore.exceptions.ClientError as e:
            raise InvalidS3AccessError(str(e)) from e
        if not any(
            bucket["Name"] == self.bucket_name for bucket in response["Buckets"]
        ):
            raise InvalidS3BucketNameError(self.bucket_name)

    def write_secure_log(self, message: str, filename: str):
        """Écrit un log dans un objet S3 immuable"""
        if filename.find("/") != -1:
            raise InvalidS3FileNameError(filename)
        filename = f"{self.folder}{filename}"

        file_object = BytesIO(message.encode("utf-8"))

        if self.s3 is None:
            if self.failure_logger:
                self.failure_logger.warning(
                    f"POST Filename: {filename}, Message: {message}",
                )
            return
        try:
            self.s3.upload_fileobj(
                file_object,
                self.bucket_name,
                filename,
                ExtraArgs={
                    "ObjectLockMode": "COMPLIANCE",
                    "ObjectLockRetainUntilDate": datetime.now(UTC)
                    + timedelta(days=self.retention),
                }
                if self.retention > 0
                else {},
            )
        except botocore.exceptions.ClientError as e:
            if self.failure_logger:
                self.failure_logger.warning(f"Filename: {filename}, Message: {message}")
                self.failure_logger.info(f"Filename: {filename}, Error: {e}")

    def get_log_with_name(self, name: str) -> str:
        """Récupère les logs avec un nom donné"""
        if name.find("/") != -1:
            raise InvalidS3FileNameError(name)
        name = f"{self.folder}{name}"
        file_object = BytesIO()
        if self.s3 is None:
            if self.failure_logger:
                self.failure_logger.warning(f"GET Filename: {name}")
            return name
        self.s3.download_fileobj(self.bucket_name, name, file_object)
        return file_object.getvalue().decode("utf-8")

    def list_object(self, prefix: str):
        """Liste les objets S3 avec un préfixe donné"""
        if prefix.find("/") != -1:
            raise InvalidS3FileNameError(prefix)
        prefix = f"{self.folder}{prefix}"
        if self.s3 is None:
            if self.failure_logger:
                self.failure_logger.warning(f"LIST Prefix: {prefix}")
            return {"Contents": []}
        objects = self.s3.list_objects_v2(Prefix=prefix, Bucket=self.bucket_name)

        return objects

    def get_log_content_for_prefix(self, prefix: str) -> list[str]:
        """Liste les fichiers de logs dans le bucket S3"""
        objects = self.list_object(prefix)
        if "Contents" not in objects or not objects["Contents"]:
            return []
        file_names = [obj["Key"].split("/")[-1] for obj in objects["Contents"]]
        return [self.get_log_with_name(x) for x in file_names]
