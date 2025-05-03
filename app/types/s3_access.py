import datetime
from io import BytesIO

import boto3  # type: ignore[import-untyped]
import botocore
import botocore.exceptions

from app.core.utils.config import Settings
from app.types.exceptions import (
    InvalidS3AccessError,
    InvalidS3BucketNameError,
)


class S3Access:
    """Classe pour gérer l'accès S3 avec verrouillage d'objet."""

    def __init__(self, settings: Settings):
        self.bucket_name = settings.S3_BUCKET_NAME or "default-bucket-name"
        self.folder = "logs/"
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

    def write_secure_log(self, message: str, date: datetime.datetime):
        """Écrit un log dans un objet S3 immuable"""
        filename = f"{self.folder}log_{date.strftime('%Y%m%dT%H%M%S')}.txt"

        file_object = BytesIO(message.encode("utf-8"))

        result = self.s3.upload_fileobj(
            file_object,
            self.bucket_name,
            filename,
            ExtraArgs={
                "ContentType": "text/plain",
            },
        )
        return filename if result is None else result

    def get_log_with_name(self, name: str) -> str:
        """Récupère les logs avec un préfixe donné"""
        file_object = BytesIO()
        self.s3.download_fileobj(self.bucket_name, name, file_object)
        return file_object.getvalue().decode("utf-8")

    def list_object(self, prefix: str):
        """Liste les objets S3 avec un préfixe donné"""
        objects = self.s3.list_objects_v2(Prefix=prefix, Bucket=self.bucket_name)

        return objects

    def list_log_content_for_prefix(self, prefix: str) -> list[str]:
        """Liste les fichiers de logs dans le bucket S3"""
        objects = self.list_object(prefix)
        if "Contents" not in objects or not objects["Contents"]:
            return []
        file_names = [obj["Key"] for obj in objects["Contents"]]
        return [self.get_log_with_name(x) for x in file_names]
