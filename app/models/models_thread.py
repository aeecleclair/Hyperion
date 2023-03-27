from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Optional

from sqlalchemy import Column, DateTime, String, ForeignKey, Boolean, Integer, func
from sqlalchemy.ext.hybrid import hybrid_method
from sqlalchemy.orm import relationship

from app.database import Base
from app.models import models_core
from app.utils.types.thread_permissions_types import ThreadPermission


class Thread(Base):
    __tablename__ = "thread"

    id: str = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    name: str = Column(String, unique=True, nullable=False)
    is_public: bool = Column(Boolean, nullable=False)
    creation_time: datetime = Column(DateTime(timezone=True), default=func.now())
    image: str | None = Column(String)

    members: list[ThreadMember] = relationship("ThreadMember", back_populates="thread")
    """messages: list[ThreadMessage] = relationship(
        "ThreadMessage", back_populates="thread"
    )"""


class ThreadMember(Base):
    __tablename__ = "thread_member"

    user_id: str = Column(String, ForeignKey("core_user.id"), primary_key=True)
    thread_id: str = Column(String, ForeignKey("thread.id"), primary_key=True)
    permissions: int = Column(Integer)

    user: models_core.CoreUser = relationship("CoreUser", viewonly=True)
    thread: Thread = relationship("Thread", viewonly=True)

    @hybrid_method
    def has_permission(self, permission: int) -> bool:
        return self.permissions & (permission | ThreadPermission.ADMINISTRATOR) != 0


class ThreadMessage(Base):
    __tablename__ = "thread_message"

    id: str = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    thread_id: str = Column(String, ForeignKey("thread.id"), index=True)
    author_id: str = Column(String, ForeignKey("core_user.id"), index=True)
    content: Optional[str] = Column(String)
    image: Optional[str] = Column(String)
    timestamp: datetime = Column(DateTime(timezone=True), default=func.now())

    author: models_core.CoreUser = relationship("CoreUser")
    # thread: Thread = relationship("Thread", back_populates="messages")
