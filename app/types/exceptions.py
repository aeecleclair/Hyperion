from typing import Any

from fastapi import HTTPException


class CoreDataNotFoundError(Exception):
    pass


class GoogleAPIInvalidCredentialsError(Exception):
    pass


class GoogleAPIMissingConfigInDotenvError(Exception):
    def __init__(self):
        super().__init__("Google API is not configured in dotenv")


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
    def __init__(self):
        super().__init__("HelloAsso API credentials are not set")


class FileNameIsNotAnUUIDError(Exception):
    def __init__(self):
        super().__init__("The filename is not a valid UUID")


class RedisConnectionError(Exception):
    def __init__(self):
        super().__init__("Connection to Redis failed")


class MatrixRequestError(Exception):
    def __init__(self):
        super().__init__("Error while requesting the matrix server")


class MatrixSendMessageError(Exception):
    def __init__(self, room_id: str):
        super().__init__(
            f"Could not send message to Matrix server, check the room_id ({room_id}) in settings.",
        )


class MissingTZInfoInDatetimeError(TypeError):
    def __init__(self):
        super().__init__("tzinfo info is required for datetime objects")


class DotenvMissingVariableError(Exception):
    def __init__(self, variable_name: str):
        super().__init__(f"{variable_name} should be configured in the dotenv")


class DotenvInvalidVariableError(Exception):
    pass


class DotenvInvalidAuthClientNameInError(Exception):
    def __init__(self, auth_client_name: str):
        super().__init__(
            f"client name {auth_client_name} of AUTH_CLIENTS list from the dotenv is not a valid auth client. It should be an instance from app.utils.auth.providers",
        )


class InvalidRSAKeyInDotenvError(TypeError):
    def __init__(self, actual_key_type: str):
        super().__init__(
            f"RSA_PRIVATE_PEM_STRING in dotenv is not an RSA key but a {actual_key_type}",
        )


class UserWithEmailAlreadyExistError(Exception):
    def __init__(self, email: str):
        super().__init__(
            f"An account with the email {email} already exist",
        )


class SchedulerNotStartedError(Exception):
    def __init__(self):
        super().__init__("Scheduler not started")


class MissingHelloAssoSlugError(Exception):
    def __init__(self, slug_type: str):
        super().__init__(
            f"HelloAsso slug {slug_type} is missing in dotenv",
        )


class MissingHelloAssoCheckoutIdError(Exception):
    def __init__(self):
        super().__init__(
            "HelloAsso checkout id is missing in response",
        )


class InvalidS3BucketNameError(Exception):
    def __init__(self, bucket_name: str):
        super().__init__(f"Invalid S3 bucket name: {bucket_name}")


class InvalidS3AccessError(Exception):
    def __init__(self):
        super().__init__("Invalid S3 configuration")


class InvalidS3FileNameError(Exception):
    def __init__(self, filename: str):
        super().__init__(
            f"Invalid S3 file name: {filename} - it should not contain '/'",
        )
