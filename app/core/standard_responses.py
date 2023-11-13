from pydantic import BaseModel


class Result(BaseModel):
    success: bool = True


class BatchResult(BaseModel):
    """
    Return a dictionary of {key: error message} indicating which element of failed.
    """

    failed: dict[str, str]
