import logging
from datetime import UTC, datetime
from logging import StreamHandler

from typing_extensions import override

from app.types.s3_access import S3Access

hyperion_error_logger = logging.getLogger("hyperion.error")


class S3LogHandler(StreamHandler):
    def __init__(
        self,
        failure_logger: str,
        folder: str,
        s3_bucket_name: str | None = None,
        s3_access_key_id: str | None = None,
        s3_secret_access_key: str | None = None,
        retention: int = -1,
    ):
        self.s3_access = S3Access(
            failure_logger,
            folder,
            s3_bucket_name,
            s3_access_key_id,
            s3_secret_access_key,
            retention,
        )
        StreamHandler.__init__(self)

    @override
    def emit(self, record):
        msg = self.format(record)
        now = datetime.now(UTC)
        self.s3_access.write_secure_log(msg, now.strftime("%Y-%m-%dT%H:%M:%S.%fZ"))
