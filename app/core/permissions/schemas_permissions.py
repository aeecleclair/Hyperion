from pydantic import BaseModel


class CorePermission(BaseModel):
    permission_name: str
    group_id: str
