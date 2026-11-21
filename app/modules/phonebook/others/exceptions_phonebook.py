from fastapi import HTTPException


class BadRequestException(HTTPException):
    def __init__(self, detail: str) -> None:
        super().__init__(status_code=400, detail=detail)


class ForbiddenException(HTTPException):
    def __init__(self, detail: str) -> None:
        super().__init__(status_code=403, detail=detail)


class NotFoundException(HTTPException):
    def __init__(self, detail: str) -> None:
        super().__init__(status_code=404, detail=detail)
