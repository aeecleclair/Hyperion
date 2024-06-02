from typing import Any

from fastapi import HTTPException


class CoreDataNotFoundException(Exception):
    pass


class ContentHTTPException(HTTPException):
    """
    A custom HTTPException allowing to return custom content.

    Instead of returning `{detail: <content>}`, this exception can return a json serialized `<content>`.

    You need to define a custom exception handler to use it:
    ```python
    @app.exception_handler(ContentHTTPException)
    async def auth_exception_handler(
        request: Request,
        exc: ContentHTTPException,
    ):
        return JSONResponse(
            status_code=exc.status_code,
            content=jsonable_encoder(exc.content),
            headers=exc.headers,
        )
    ```
    """

    def __init__(
        self,
        status_code: int,
        content: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=content, headers=headers)
        self.content = content


class AuthHTTPException(ContentHTTPException):
    """
    A custom HTTPException used for OIDC or OAuth error responses
    """

    def __init__(
        self,
        status_code: int,
        error: str,
        error_description: str,
    ) -> None:
        content = {
            "error": error,
            "error_description": error_description,
        }

        super().__init__(status_code=status_code, content=content)
class PaymentToolCredentialsNotSetException(Exception):
    pass
