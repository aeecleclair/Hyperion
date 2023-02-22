from __future__ import annotations

from datetime import datetime
from uuid import uuid4

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

    members: list[ThreadMember] = relationship(
        "ThreadMember", lazy="joined", back_populates="thread"
    )
    # TODO : Put something there
    # messages: list[ThreadMessage] = ...


class ThreadMember(Base):
    __tablename__ = "thread_member"

    id: str = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    core_user_id: str = Column(String, ForeignKey("core_user.id"), index=True)
    thread_id: str = Column(String, ForeignKey("thread.id"), index=True)
    permissions: int = Column(Integer)

    user: models_core.CoreUser = relationship("CoreUser", lazy="joined")
    thread: Thread = relationship("Thread", lazy="joined")
    messages: list[ThreadMessage] = relationship(
        "ThreadMessage", lazy="joined", back_populates="thread_member"
    )

    @hybrid_method
    def has_permission(self, permission: int) -> bool:
        return self.permissions & (permission | ThreadPermission.ADMINISTRATOR) != 0


class ThreadMessage(Base):
    __tablename__ = "thread_message"

    id: str = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    thread_id: str = Column(String, ForeignKey("thread.id"), index=True)
    thread_member_id: str = Column(String, ForeignKey("thread_member.id"), index=True)
    content: str = Column(String)
    image: str = Column(String)
    timestamp: datetime = Column(DateTime(timezone=True), default=func.now())

    thread_member: ThreadMember = relationship("ThreadMember", lazy="joined")
