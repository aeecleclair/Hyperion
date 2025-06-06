import string
from datetime import UTC, datetime
from logging import StreamHandler

from typing_extensions import override

from app.types.s3_access import S3Access
from app.utils.tools import get_random_string

alphanum = string.ascii_lowercase + string.digits


class S3LogHandler(StreamHandler):
    def __init__(
        self,
        failure_logger: str,
        folder: str,
        s3_bucket_name: str | None = None,
        s3_access_key_id: str | None = None,
        s3_secret_access_key: str | None = None,
    ):
        super().__init__()
        self.s3_access = S3Access(
            failure_logger,
            folder,
            s3_bucket_name,
            s3_access_key_id,
            s3_secret_access_key,
        )

    @override
    def emit(self, record):
        filename: str | None = getattr(record, "s3_filename", None)
        subfolder: str | None = getattr(record, "s3_subfolder", None)
        retention: int = getattr(record, "s3_retention", 0)

        if filename is None:
            now = datetime.now(UTC)
            filename = now.strftime("%Y-%m-%dT%H:%M:%S.%fZ") + get_random_string(8)

        msg = self.format(record)
        self.s3_access.write_file(msg, filename, subfolder, retention)
