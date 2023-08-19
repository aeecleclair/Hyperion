from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ModuleVisibility(Base):
    __tablename__ = "module_visibility"

    root: Mapped[str] = mapped_column(String, primary_key=True)
    allowed_group_id: Mapped[str] = mapped_column(String, primary_key=True)
