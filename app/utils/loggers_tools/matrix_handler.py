from logging import StreamHandler

from app.utils.communication.matrix import Matrix


class MatrixHandler(StreamHandler):
    """
    A logging handler which send log records to a Matrix server.

    `room_id`: str, the Matrix room identifier the messages needs to be send to.
    `enabled`: bool, default True, if the handler should be enabled

    NOTE: the Matrix user configured in the dotenv should have access to the room.
    Has this handler needs a Matrix configuration to be set, it is possible to disable it.
    """

    def __init__(
        self,
        room_id: str,
        user_name: str,
        user_password: str,
        server_base_url: str | None,
        enabled: bool = True,
    ) -> None:
        StreamHandler.__init__(self)

        self.room_id = room_id
        self.enabled = enabled
        try:
            self.matrix = Matrix(
                user_name=user_name,
                user_password=user_password,
                server_base_url=server_base_url,
            )
        except ValueError as err:
            print(err)
            print("MatrixHandler: Matrix configuration not set, disabling the handler")
            self.enabled = False

    def emit(self, record):
        if self.enabled:
            msg = self.format(record)

            try:
                self.matrix.send_message(self.room_id, msg)
            except ValueError as err:
                print(err)
                print(
                    "MatrixHandler: Unable to send message to Matrix server, disabling the handler"
                )
                self.enabled = False
