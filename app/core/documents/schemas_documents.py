from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.core.documents.types_documenso import DocumentStatus
from app.core.groups.schemas_groups import CoreGroup
from app.core.users.schemas_users import CoreUser


class TeamBase(BaseModel):
    team_id: int
    group_id: str
    name: str
    api_key: str


class Team(TeamBase):
    id: UUID


class TeamComplete(Team):
    templates: list["Template"]
    group: CoreGroup


class TeamUpdate(BaseModel):
    group_id: str | None = None
    name: str | None = None
    api_key: str | None = None


class TemplateBase(BaseModel):
    documenso_id: int
    name: str
    team_id: UUID


class Template(TemplateBase):
    id: UUID
    deleted: bool
    document_directory_id: str | None = None
    created_at: datetime
    updated_at: datetime


class TemplateComplete(Template):
    documents: list["Document"]
    team: Team


class TemplateUpdate(BaseModel):
    document_directory_id: str | None = None


class TemplateDocumensoUpdate(BaseModel):
    name: str | None = None
    deleted: bool | None = None


class TemplateUse(BaseModel):
    recipients: list[str]


class TemplateUseResponse(BaseModel):
    errors: dict[str, str]
    documents: list["Document"]


class DocumentBase(BaseModel):
    template_id: UUID
    name: str
    module: str
    user_id: str


class Document(DocumentBase):
    id: UUID
    documenso_id: int
    status: DocumentStatus
    created_at: datetime
    updated_at: datetime


class DocumentWithToken(Document):
    signing_token: str


class DocumentComplete(Document):
    user: CoreUser
