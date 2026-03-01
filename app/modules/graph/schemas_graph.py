from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.users.schemas_users import CoreUserSimple

class Acquaintance(BaseModel):
    user_id: UUID

class Link(BaseModel):
    user1_id: UUID
    user2_id: UUID
    groupement_id: UUID