import logging
import re
from datetime import UTC, datetime, timedelta
from io import BytesIO
from typing import Any

import boto3
import botocore
import botocore.exceptions

from app.types.exceptions import (
    InvalidS3AccessError,
    InvalidS3BucketNameError,
    InvalidS3FileNameError,
    InvalidS3FolderError,
)

AUTHORIZED_FILE_STRING = r"^[\w](?:[\w_:\.-]*[\w])?$"
AUTHORIZED_FOLDER_STRING = r"^[\w](?:[\w/_:\.-]*[\w])?$"


class S3Access:
    """Class to manage S3 access with configurable object locking."""

    def __init__(
        self,
        failure_logger: str,
        folder: str,
        s3_bucket_name: str | None = None,
        s3_access_key_id: str | None = None,
        s3_secret_access_key: str | None = None,
    ) -> None:
        if folder != "" and not re.match(AUTHORIZED_FOLDER_STRING, folder):
            raise InvalidS3FolderError(folder)
        self.folder = folder
        self.failure_logger = logging.getLogger(failure_logger)
        if (
            s3_access_key_id is None
            or s3_secret_access_key is None
            or s3_bucket_name is None
        ):
            self.failure_logger.critical(
                "S3_ACCESS_KEY_ID or S3_SECRET_ACCESS_KEY or S3_MYECLPAY_LOGS_BUCKET_NAME is not set. Working with fallback logger only.",
            )
            self.s3 = None
            return
        self.bucket_name = s3_bucket_name
        self.s3 = boto3.client(
            "s3",
            aws_access_key_id=s3_access_key_id,
            aws_secret_access_key=s3_secret_access_key,
        )
        try:
            response = self.s3.list_buckets()
        except botocore.exceptions.ClientError as e:
            raise InvalidS3AccessError() from e
        except botocore.exceptions.EndpointConnectionError:
            self.failure_logger.critical(
                "S3 is not accessible, defaulting to fallback logger",
            )
            self.s3 = None
            return
        if not any(
            bucket["Name"] == self.bucket_name for bucket in response["Buckets"]
        ):
            raise InvalidS3BucketNameError(self.bucket_name)

    def write_file(
        self,
        message: str,
        filename: str,
        subfolder: str | None = None,
        retention: int = 0,
    ):
        """Write in an S3 bucket with object locking if needed.
        The filename must not contain a "/" because S3 will consider it as a folder.

        Args:
            message (str): Message to write
            filename (str): Filename to write
            subfolder (str): Subfolder to write in, it must not start nor end with a special caracter (optional)

        Raises:
            InvalidS3FileNameError: If the prefix is not a valid filename
            InvalidS3SubfolderError: If the subfolder is not a valid subfolder

        Returns:
            None
        """
        # If there is a "/" in the filename the s3 while consider it as a folder
        if not re.match(AUTHORIZED_FILE_STRING, filename):
            raise InvalidS3FileNameError(filename)
        if subfolder is not None and not re.match(AUTHORIZED_FOLDER_STRING, subfolder):
            raise InvalidS3FolderError(subfolder)

        if subfolder is not None:
            filename = subfolder + "/" + filename
        if self.folder != "":
            filename = self.folder + "/" + filename

        file_object = BytesIO(message.encode("utf-8"))

        if self.s3 is None:
            self.failure_logger.warning(
                f"POST Filename: {filename}, Message: {message}",
            )
            return
        try:
            self.s3.upload_fileobj(
                file_object,
                self.bucket_name,
                filename,
                # "COMPLIANCE" mode forbids anyone to delete or modify the created object, including its owner
                ExtraArgs={
                    "ObjectLockMode": "COMPLIANCE",
                    "ObjectLockRetainUntilDate": datetime.now(UTC)
                    + timedelta(days=retention),
                }
                if retention > 0
                else {},
            )
        except botocore.exceptions.ClientError as e:
            self.failure_logger.warning(f"Filename: {filename}, Message: {message}")
            self.failure_logger.info(f"Filename: {filename}, Error: {e}")

    def get_file_with_name(
        self,
        filename: str,
        subfolder: str | None = None,
    ) -> str:
        """Get a file from S3 with a given name and subfolder.
        The filename must not contain a "/" because S3 will consider it as a folder.

        Args:
            name (str): Filename to get
            subfolder (str): Subfolder to get in, it must not start nor end with a special caracter (optional)
        Raises:
            InvalidS3FileNameError: If the prefix is not a valid filename
            InvalidS3SubfolderError: If the subfolder is not a valid subfolder
        Returns:
            str: File content
        """

        # If there is a "/" in the filename the s3 while consider it as a folder
        if not re.match(AUTHORIZED_FILE_STRING, filename):
            raise InvalidS3FileNameError(filename)
        if subfolder is not None and not re.match(AUTHORIZED_FOLDER_STRING, subfolder):
            raise InvalidS3FolderError(subfolder)

        if subfolder is not None:
            filename = subfolder + "/" + filename
        if self.folder != "":
            filename = self.folder + "/" + filename

        file_object = BytesIO()
        if self.s3 is None:
            self.failure_logger.warning(f"GET Filename: {filename}")
            return filename
        self.s3.download_fileobj(self.bucket_name, filename, file_object)
        return file_object.getvalue().decode("utf-8")

    def list_object(
        self,
        prefix: str,
        subfolder: str = "",
    ) -> Any:
        """List s3 objects with a given prefix
        The prefix must not contain a "/" because S3 will consider it as a folder.

        Args:
            prefix (str): Prefix to list
            subfolder (str): Subfolder to list in, it must not start nor end with a special caracter (optional)
        Raises:
            InvalidS3FileNameError: If the prefix is not a valid filename
            InvalidS3SubfolderError: If the subfolder is not a valid subfolder
        Returns:
            Any: List of objects
        """

        # If there is a "/" in the filename the s3 while consider it as a folder
        if not re.match(AUTHORIZED_FILE_STRING, prefix):
            raise InvalidS3FileNameError(prefix)
        if subfolder != "" and not re.match(AUTHORIZED_FOLDER_STRING, subfolder):
            raise InvalidS3FolderError(subfolder)

        prefix = (
            f"{self.folder}/{subfolder}/{prefix}"
            if self.folder != ""
            else f"{subfolder}/{prefix}"
        )

        if self.s3 is None:
            self.failure_logger.warning(f"LIST Prefix: {prefix}")
            return {"Contents": []}
        return self.s3.list_objects_v2(Prefix=prefix, Bucket=self.bucket_name)

    def get_files_content_for_prefix(
        self,
        prefix: str,
        subfolder: str = "",
    ) -> list[str]:
        """List all logs with a given prefix
        The prefix must not contain a "/" because S3 will consider it as a folder.

        Args:
            prefix (str): Prefix to list
            subfolder (str): Subfolder to list in, it must not start nor end with a special caracter (optional)
        Raises:
            InvalidS3FileNameError: If the prefix is not a valid filename
            InvalidS3SubfolderError: If the subfolder is not a valid subfolder
        Returns:
            list[str]: List of objects
        """
        objects = self.list_object(prefix, subfolder)
        if "Contents" not in objects or not objects["Contents"]:
            return []
        file_names = [obj["Key"].split("/")[-1] for obj in objects["Contents"]]
        return [self.get_file_with_name(x, subfolder) for x in file_names]
