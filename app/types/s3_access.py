import logging
from datetime import UTC, datetime, timedelta
from io import BytesIO

import boto3
import botocore
import botocore.exceptions

from app.types.exceptions import (
    InvalidS3AccessError,
    InvalidS3BucketNameError,
    InvalidS3FileNameError,
)


class S3Access:
    """Class to manage S3 access with object locking."""

    def __init__(
        self,
        failure_logger: str,
        folder: str,
        s3_bucket_name: str | None = None,
        s3_access_key_id: str | None = None,
        s3_secret_access_key: str | None = None,
        retention: int = -1,
    ) -> None:
        """ """
        self.folder = folder
        self.retention = retention
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

    def write_secure_log(self, message: str, filename: str):
        """Write in an immuable S3 bucket"""
        # If there is a "/" in the filename the s3 while consider it as a folder
        if "/" in filename:
            raise InvalidS3FileNameError(filename)
        filename = f"{self.folder}{filename}"

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
                    + timedelta(days=self.retention),
                }
                if self.retention > 0
                else {},
            )
        except botocore.exceptions.ClientError as e:
            self.failure_logger.warning(f"Filename: {filename}, Message: {message}")
            self.failure_logger.info(f"Filename: {filename}, Error: {e}")

    def get_log_with_name(self, name: str) -> str:
        """Get logs corresponding to a given filename"""
        # If there is a "/" in the filename the s3 while consider it as a folder
        if "/" in name:
            raise InvalidS3FileNameError(name)
        name = f"{self.folder}{name}"
        file_object = BytesIO()
        if self.s3 is None:
            self.failure_logger.warning(f"GET Filename: {name}")
            return name
        self.s3.download_fileobj(self.bucket_name, name, file_object)
        return file_object.getvalue().decode("utf-8")

    def list_object(self, prefix: str):
        """List s3 objects with a given prefix"""
        # If there is a "/" in the filename the s3 while consider it as a folder
        if "/" in prefix:
            raise InvalidS3FileNameError(prefix)
        prefix = f"{self.folder}{prefix}"
        if self.s3 is None:
            self.failure_logger.warning(f"LIST Prefix: {prefix}")
            return {"Contents": []}
        objects = self.s3.list_objects_v2(Prefix=prefix, Bucket=self.bucket_name)

        return objects

    def get_log_content_for_prefix(self, prefix: str) -> list[str]:
        """List all logs with a given prefix"""
        objects = self.list_object(prefix)
        if "Contents" not in objects or not objects["Contents"]:
            return []
        file_names = [obj["Key"].split("/")[-1] for obj in objects["Contents"]]
        return [self.get_log_with_name(x) for x in file_names]
