from datetime import date, datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.types.sqlalchemy import Base


class FirebaseDevice(Base):
    __tablename__ = "notification_firebase_devices"

    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"))
    firebase_device_token: Mapped[str] = mapped_column(
        index=True,
        primary_key=True,
    )
    register_date: Mapped[date]


class NotificationTopic(Base):
    __tablename__ = "notification_topic"

    id: Mapped[str] = mapped_column(
        primary_key=True,
    )
    name: Mapped[str] = mapped_column(primary_key=True)


class TopicMembership(Base):
    __tablename__ = "notification_topic_membership"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
        primary_key=True,
    )
    topic_id: Mapped[str] = mapped_column(
        primary_key=True,
    )
