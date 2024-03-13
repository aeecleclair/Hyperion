from datetime import date, datetime

from sqlalchemy import Boolean, Date, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.notification.notification_types import Topic
from app.database import Base
from app.utils.types.datetime import TZDateTime


class Message(Base):
    __tablename__ = "notification_message"

    # A context represents a topic (ex: a loan),
    # there can only by one notification per context (ex: the loan should be returned, the loan is overdue or has been returned)
    context: Mapped[str] = mapped_column(String, index=True, primary_key=True)
    # If there can be one notification per context, there can be multiple messages per notification: one by firebase_device_token
    # A firebase_device_token is related to a device from an user (its phone, its computer, etc.)
    firebase_device_token: Mapped[str] = mapped_column(
        String, index=True, primary_key=True
    )

    # A message can be visible or not, if it is not visible, it should only trigger an action
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)

    title: Mapped[str | None] = mapped_column(String)
    content: Mapped[str | None] = mapped_column(String)

    # TODO
    # An action id is used by Titan to know what to do when receiving the notification
    action_module: Mapped[str | None] = mapped_column(String, nullable=True)
    action_table: Mapped[str | None] = mapped_column(String, nullable=True)

    # We can plan a notification to be sent later, the frontend should not display it before the planned date
    delivery_datetime: Mapped[datetime] = mapped_column(TZDateTime, nullable=True)
    # Messages should be deleted after a certain time
    expire_on: Mapped[date] = mapped_column(Date, nullable=False)


class FirebaseDevice(Base):
    __tablename__ = "notification_firebase_devices"

    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), nullable=False)
    firebase_device_token: Mapped[str] = mapped_column(
        String, index=True, nullable=False, primary_key=True
    )
    register_date: Mapped[date] = mapped_column(Date, nullable=False)


class TopicMembership(Base):
    __tablename__ = "notification_topic_membership"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"), nullable=False, primary_key=True
    )
    topic: Mapped[Topic] = mapped_column(
        Enum(Topic), index=True, nullable=False, primary_key=True
    )
    topic_identifier: Mapped[str] = mapped_column(
        String, nullable=False, primary_key=True
    )
