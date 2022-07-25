from logging import StreamHandler

from app.core.settings import settings
from app.utils.communication.matrix import Matrix


class MatrixHandler(StreamHandler):
    def __init__(self):
        StreamHandler.__init__(self)

        self.matrix = Matrix()

    def emit(self, record):
        msg = self.format(record)
        room_id = settings.MATRIX_LOG_ROOM_ID

        self.matrix.send_message(room_id, msg)
