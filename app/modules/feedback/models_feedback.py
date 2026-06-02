from datetime import datetime

from sqlalchemy.orm import Mapped

from app.types.sqlalchemy import Base, PrimaryKey


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[PrimaryKey]
    creation: Mapped[datetime]
    user_id: Mapped[str]
    user_name: Mapped[str]
    content: Mapped[str]
    is_addressed: Mapped[bool]
