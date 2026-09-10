from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.core.groups import schemas_groups
from app.core.users import schemas_users


class VerificationContextCreation(BaseModel):
    name: str
    group_id: str


class VerificationContext(VerificationContextCreation):
    id: UUID
    archived: bool


class VerificationContextComplete(VerificationContext):
    group: schemas_groups.CoreGroupSimple


class VerificationContextEdit(BaseModel):
    archived: bool | None = None


class IdentityToken(BaseModel):
    id: UUID
    token: str
    user_id: str
    expire_on: datetime


class IdentityTokenResponse(IdentityToken):
    firstname: str
    name: str
    nickname: str | None


class IdentityTokenResponseComplete(IdentityTokenResponse):
    already_scanned: bool


class VerificationScan(BaseModel):
    id: UUID
    user_id: str
    verification_context_id: UUID
    datetime: datetime
    scanner_user_id: str


class VerificationScanComplete(VerificationScan):
    user: schemas_users.CoreUserSimple
