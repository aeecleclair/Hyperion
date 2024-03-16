import logging
from logging import StreamHandler

from app.utils.communication.matrix import Matrix

hyperion_error_logger = logging.getLogger("hyperion.error")


class MatrixHandler(StreamHandler):
    """
    A logging handler which sends log records to a Matrix server.

    `room_id`: str, the Matrix room identifier the messages need to be sent to.
    `enabled`: bool, default True, if the handler should be enabled

    NOTE: the Matrix user configured in the dotenv should have access to the room.
    Has this handler needs a Matrix configuration to be set, it is possible to disable it.
    """

    def __init__(
        self,
        room_id: str,
        token: str,
        server_base_url: str | None,
        level: str = "INFO",
        enabled: bool = True,
    ) -> None:
        StreamHandler.__init__(self)
        self.setLevel(level)

        self.room_id = room_id
        self.enabled = enabled
        if self.enabled:
            self.matrix = Matrix(
                token=token,
                server_base_url=server_base_url,
            )
        else:
            # We use warning level so that the message is not sent to matrix again
            hyperion_error_logger.warning(
                "MatrixHandler isn't configured in the .env file, disabling the handler",
            )

    def emit(self, record):
        if self.enabled:
            msg = self.format(record)

            try:
                self.matrix.send_message(self.room_id, msg)
            except ValueError as err:
                # We use warning level so that the message is not sent to matrix again
                hyperion_error_logger.warning(
                    f"MatrixHandler: Unable to send message to Matrix server: {err}",
                )
