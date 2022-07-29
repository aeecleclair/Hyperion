from typing import Any, Dict

import requests

from app.core.settings import settings


class Matrix:
    """
    A Matrix client.
    `MATRIX_USER_NAME` and `MATRIX_USER_PASSWORD` need to be configured in settings.
    A custom Matrix server can be used with `MATRIX_SERVER_BASE_URL`, default is https://matrix.org/
    """

    def __init__(self):
        if not (settings.MATRIX_USER_NAME and settings.MATRIX_USER_PASSWORD):
            raise ValueError(
                "Matrix username and password are not configured in settings"
            )

        self.server = settings.MATRIX_SERVER_BASE_URL or "https://matrix.org/"
        self.access_token = self.login_for_access_token(
            settings.MATRIX_USER_NAME, settings.MATRIX_USER_PASSWORD
        )

    def login_for_access_token(self, username: str, password: str) -> str:
        """
        https://spec.matrix.org/v1.3/client-server-api/#post_matrixclientv3login
        """
        response = requests.post(
            self.server + "_matrix/client/v3/login",
            json={
                "device_id": "hyperion",
                "identifier": {"type": "m.id.user", "user": username},
                "initial_device_display_name": "Hyperion",
                "password": password,
                "type": "m.login.password",
            },
        )
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            raise ValueError(
                "Could not login to Matrix server. "
                "Check your username and password in settings."
            )
        json_response = response.json()

        if "access_token" not in json_response:
            raise KeyError(
                "Matrix server login response does not contain an access_token"
            )

        return json_response["access_token"]

    def post(self, url, json, headers={}) -> Dict[str, Any]:
        """
        The function add an access token to the request authorization header and issue a post operation.
        The authorization header will only be added if one is not already provided

        https://spec.matrix.org/v1.3/client-server-api/#using-access-tokens
        """

        if "Authorization" not in headers:
            headers["Authorization"] = "Bearer " + self.access_token

        response = requests.post(url, json=json, headers=headers)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            raise ValueError(
                "Could not send message to Matrix server. "
                "Check the room_id in settings."
            )

        return response.json()

    def send_message(self, room_id: str, formatted_body: str) -> None:
        """
        Send a message to the room `room_id`.
        `formatted_body` can contain html formated text
        """
        url = (
            "https://matrix.org/_matrix/client/r0/rooms/"
            + room_id
            + "/send/m.room.message"
        )

        # https://github.com/matrix-org/matrix-spec-proposals/issues/917
        # formatted_body = '<b>test</b> test <font color ="red">red test</font> https://docs.google.com/document/d/1QPncBmMkKOo6_B2jyBuy5FFSZJrRsq7WU5wgRSzOMho/edit#heading=h.arjuwv7itr4h <table style="width:100%"><tr><th>Firstname</th><th>Lastname</th><th>Age</th></tr><tr><td>Jill</td><td>Smith</td><td>50</td></tr><tr><td>Eve</td><td>Jackson</td><td>94</td></tr></table> https://www.w3schools.com/html/html_tables.asp'

        data = {
            "body": "hello matrix",
            "format": "org.matrix.custom.html",
            "formatted_body": formatted_body,
            "msgtype": "m.text",
        }

        self.post(url, json=data)
