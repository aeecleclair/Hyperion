from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.documents.types_documenso import DocumentStatus
from app.core.groups.models_groups import CoreGroup
from app.core.users.models_users import CoreUser
from app.types.sqlalchemy import Base, PrimaryKey


class DocumentTeam(Base):
    __tablename__ = "document_team"

    id: Mapped[PrimaryKey]
    team_id: Mapped[int] = mapped_column(unique=True)
    group_id: Mapped[str] = mapped_column(ForeignKey("core_group.id"), unique=True)
    name: Mapped[str] = mapped_column(unique=True)
    api_key: Mapped[str]

    templates: Mapped[list["DocumentTemplate"]] = relationship(
        "DocumentTemplate",
        lazy="selectin",
        init=False,
        back_populates="team",
    )
    group: Mapped[CoreGroup] = relationship(
        "CoreGroup",
        lazy="joined",
        init=False,
    )


class DocumentTemplate(Base):
    __tablename__ = "document_template"

    id: Mapped[PrimaryKey]
    documenso_id: Mapped[int]
    name: Mapped[str]
    team_id: Mapped[UUID] = mapped_column(ForeignKey("document_team.id"))
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    deleted: Mapped[bool] = mapped_column(default=False)
    document_directory_id: Mapped[str | None] = mapped_column(default=None)

    documents: Mapped[list["DocumentDocument"]] = relationship(
        "DocumentDocument",
        lazy="selectin",
        init=False,
    )
    team: Mapped[DocumentTeam] = relationship(
        "DocumentTeam",
        lazy="joined",
        init=False,
        back_populates="templates",
    )


class DocumentDocument(Base):
    __tablename__ = "document_document"

    id: Mapped[PrimaryKey]
    documenso_id: Mapped[int] = mapped_column(unique=True)
    name: Mapped[str]
    template_id: Mapped[UUID] = mapped_column(ForeignKey("document_template.id"))
    module: Mapped[str]
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"))
    signing_token: Mapped[str]
    status: Mapped[DocumentStatus]
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    user: Mapped[CoreUser] = relationship(
        "CoreUser",
        lazy="joined",
        init=False,
    )
