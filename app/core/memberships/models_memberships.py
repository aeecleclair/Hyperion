from datetime import date
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.documents.models_documents import DocumentDocument, DocumentTemplate
from app.core.documents.types_documenso import DocumentStatus
from app.core.users.models_users import CoreUser
from app.types.sqlalchemy import Base, PrimaryKey


class CoreAssociationMembership(Base):
    __tablename__ = "core_association_membership"

    id: Mapped[PrimaryKey]
    name: Mapped[str] = mapped_column(unique=True)
    manager_group_id: Mapped[str] = mapped_column(ForeignKey("core_group.id"))
    template_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("document_template.id"),
        default=None,
    )

    template: Mapped[DocumentTemplate | None] = relationship(
        "DocumentTemplate",
        lazy="joined",
        init=False,
    )


class CoreAssociationUserMembership(Base):
    __tablename__ = "core_association_user_membership"

    id: Mapped[PrimaryKey]
    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
    )
    association_membership_id: Mapped[UUID] = mapped_column(
        ForeignKey("core_association_membership.id"),
        index=True,
    )
    start_date: Mapped[date]
    end_date: Mapped[date]
    document_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("document_document.id"),
        default=None,
    )
    document_status: Mapped[DocumentStatus | None] = mapped_column(default=None)

    @property
    def valid(self) -> bool:
        """Check if the membership is currently valid based document_status"""
        return (
            self.document_id is None or self.document_status == DocumentStatus.COMPLETED
        )

    user: Mapped[CoreUser] = relationship(
        "CoreUser",
        lazy="joined",
        init=False,
    )
    association_membership: Mapped[CoreAssociationMembership] = relationship(
        "CoreAssociationMembership",
        lazy="joined",
        init=False,
    )
    document: Mapped[DocumentDocument | None] = relationship(
        "DocumentDocument",
        lazy="joined",
        init=False,
    )
