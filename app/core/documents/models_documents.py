from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.documents.types_documenso import DocumentStatus
from app.types.sqlalchemy import Base, PrimaryKey


class DocumentTeam(Base):
    __tablename__ = "document_team"

    id: Mapped[PrimaryKey]
    team_id: Mapped[UUID] = mapped_column(unique=True)
    group_id: Mapped[str] = mapped_column(ForeignKey("core_group.id"))
    name: Mapped[str] = mapped_column(unique=True)
    api_key: Mapped[str]
    documenso_url: Mapped[str]


class DocumentTemplate(Base):
    __tablename__ = "document_template"

    id: Mapped[PrimaryKey]
    documenso_id: Mapped[str]
    name: Mapped[str]
    team_id: Mapped[UUID] = mapped_column(ForeignKey("document_team.id"))
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    deleted: Mapped[bool] = mapped_column(default=False)
    document_directory_id: Mapped[str | None] = mapped_column(default=None)


class DocumentDocument(Base):
    __tablename__ = "document_document"

    id: Mapped[PrimaryKey]
    name: Mapped[str]
    template_id: Mapped[UUID] = mapped_column(ForeignKey("document_template.id"))
    module: Mapped[str]
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"))
    signing_token: Mapped[str]
    status: Mapped[DocumentStatus]
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
