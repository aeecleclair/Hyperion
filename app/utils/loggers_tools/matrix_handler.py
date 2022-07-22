from logging import StreamHandler

from app.utils.communication.matrix import Matrix


class MatrixHandler(StreamHandler):
    def __init__(self):
        StreamHandler.__init__(self)

        self.matrix = Matrix()

    def emit(self, record):
        msg = self.format(record)
        self.matrix.send_message(room_id, msg)
