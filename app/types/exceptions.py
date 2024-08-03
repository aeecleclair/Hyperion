class CoreDataNotFoundError(Exception):
    pass


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


class MissingVariableInDotenvError(Exception):
    def __init__(self, variable_name: str):
        super().__init__(f"{variable_name} should be configured in the dotenv")


class InvalidAuthClientNameInDotenvError(Exception):
    def __init__(self, auth_client_name: str):
        super().__init__(
            f"client name {auth_client_name} of AUTH_CLIENTS list from the dotenv is not a valid auth client. It should be an instance from app.utils.auth.providers",
        )


class InvalidRSAKeyInDotenvError(TypeError):
    def __init__(self, actual_key_type: str):
        super().__init__(
            f"RSA_PRIVATE_PEM_STRING in dotenv is not an RSA key but a {actual_key_type}",
        )
