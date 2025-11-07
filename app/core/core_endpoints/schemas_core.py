"""Common schemas file for endpoint /users et /groups because it would cause circular import"""

from pydantic import BaseModel


class CoreInformation(BaseModel):
    """Information about Hyperion"""

    ready: bool
    version: str
    minimal_titan_version_code: int
