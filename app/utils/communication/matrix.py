from typing import Any

import httpx

from app.types.exceptions import MatrixRequestError, MatrixSendMessageError


class Matrix:
    """
    A Matrix client.
    `MATRIX_USER_NAME` and `MATRIX_USER_PASSWORD` need to be configured in settings.
    A custom Matrix server can be used with `MATRIX_SERVER_BASE_URL`, default is https://matrix.org/
    """

    def __init__(
        self,
        token: str,
        server_base_url: str | None = None,
    ):
        self.server = server_base_url or "https://matrix.org/"
        # A trailing slash is required
        if self.server[-1] != "/":
            self.server += "/"

        self.access_token = token

    async def post(
        self,
        url: str,
        json: dict[str, Any],
        headers: dict[str, Any] | None,
    ) -> Any:
        """
        The function adds an access token to the request authorization header and issue a post operation.
        The authorization header will only be added if one is not already provided

        https://spec.matrix.org/v1.3/client-server-api/#using-access-tokens
        """
        if headers is None:
            # If no headers are provided, create a new dict
            headers = {}

        if "Authorization" not in headers:
            headers["Authorization"] = "Bearer " + self.access_token

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, json=json, headers=headers, timeout=10
                )
            response.raise_for_status()
        except httpx.RequestError as err:
            raise MatrixRequestError() from err

        return response.json()

    async def send_message(self, room_id: str, formatted_body: str) -> None:
        """
        Send a message to the room `room_id`.
        `formatted_body` can contain html formatted text
        """
        url = (
            self.server + "_matrix/client/r0/rooms/" + room_id + "/send/m.room.message"
        )

        # https://github.com/matrix-org/matrix-spec-proposals/issues/917
        # formatted_body = '<b>test</b> test <font color ="red">red test</font> https://docs.google.com/document/d/1QPncBmMkKOo6_B2jyBuy5FFSZJrRsq7WU5wgRSzOMho/edit#heading=h.arjuwv7itr4h <table style="width:100%"><tr><th>Firstname</th><th>Lastname</th><th>Age</th></tr><tr><td>Jill</td><td>Smith</td><td>50</td></tr><tr><td>Eve</td><td>Jackson</td><td>94</td></tr></table> https://www.w3schools.com/html/html_tables.asp'

        data = {
            "body": "hello matrix",
            "format": "org.matrix.custom.html",
            "formatted_body": formatted_body,
            "msgtype": "m.text",
        }

        try:
            await self.post(url, json=data, headers=None)
        except MatrixRequestError as error:
            raise MatrixSendMessageError(room_id=room_id) from error
