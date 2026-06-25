from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.core.documents.types_documenso import DocumentStatus

# ---------------------------------------------------------------------------
# DocumentTeam
# ---------------------------------------------------------------------------


class TeamBase(BaseModel):
    group_id: str
    name: str
    api_key: str
    documenso_url: str


class Team(TeamBase):
    id: UUID
    team_id: UUID


class TeamUpdate(BaseModel):
    group_id: str | None = None
    name: str | None = None
    api_key: str | None = None
    documenso_url: str | None = None


# ---------------------------------------------------------------------------
# DocumentTemplate
# ---------------------------------------------------------------------------


class TemplateBase(BaseModel):
    documenso_id: str
    name: str
    team_id: UUID


class Template(TemplateBase):
    id: UUID
    deleted: bool
    document_directory_id: str | None = None
    created_at: datetime
    updated_at: datetime


class TemplateUpdate(BaseModel):
    document_directory_id: str | None = None


# ---------------------------------------------------------------------------
# DocumentDocument
# ---------------------------------------------------------------------------


class DocumentBase(BaseModel):
    template_id: UUID
    name: str
    module: str
    user_id: str


class Document(DocumentBase):
    id: UUID
    status: DocumentStatus
    created_at: datetime
    updated_at: datetime


class DocumentComplete(Document):
    signing_token: str
