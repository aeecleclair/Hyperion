import requests

from app.core.settings import settings


class Matrix:
    server = "https://matrix.org/"
    def send_message(self, room_id, formatted_body):
        """
        Send a message to the room `room_id`.
        `formatted_body` can contain html formated text
        """
        url = (
            "https://matrix.org/_matrix/client/r0/rooms/"
            + room_id
            + "/send/m.room.message"
        )
        headers = {"Authorization": " ".join(["Bearer", settings.MATRIX_ACCESS_TOKEN])}

        # https://github.com/matrix-org/matrix-spec-proposals/issues/917
        # formatted_body = '<b>test</b> test <font color ="red">red test</font> https://docs.google.com/document/d/1QPncBmMkKOo6_B2jyBuy5FFSZJrRsq7WU5wgRSzOMho/edit#heading=h.arjuwv7itr4h <table style="width:100%"><tr><th>Firstname</th><th>Lastname</th><th>Age</th></tr><tr><td>Jill</td><td>Smith</td><td>50</td></tr><tr><td>Eve</td><td>Jackson</td><td>94</td></tr></table> https://www.w3schools.com/html/html_tables.asp'

        data = {
            "body": "hello matrix",
            "format": "org.matrix.custom.html",
            "formatted_body": formatted_body,
            "msgtype": "m.text",
        }

        r = requests.post(url, json=data, headers=headers)
        r.raise_for_status()
