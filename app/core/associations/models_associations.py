from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.types.sqlalchemy import Base, PrimaryKey


class CoreAssociation(Base):
    __tablename__ = "associations_associations"

    id: Mapped[PrimaryKey]
    name: Mapped[str] = mapped_column(unique=True)
    group_id: Mapped[str] = mapped_column(ForeignKey("core_group.id"))
