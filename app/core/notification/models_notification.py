from datetime import date, datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.types.sqlalchemy import Base


class Message(Base):
    __tablename__ = "notification_message"

    # A context represents a topic (ex: a loan),
    # there can only by one notification per context (ex: the loan should be returned, the loan is overdue or has been returned)
    context: Mapped[str] = mapped_column(index=True, primary_key=True)
    # If there can be one notification per context, there can be multiple messages per notification: one by firebase_device_token
    # A firebase_device_token is related to a device from an user (its phone, its computer, etc.)
    firebase_device_token: Mapped[str] = mapped_column(
        index=True,
        primary_key=True,
    )

    title: Mapped[str | None]
    content: Mapped[str | None]

    # TODO
    # An action id is used by Titan to know what to do when receiving the notification
    action_module: Mapped[str | None]
    action_table: Mapped[str | None]

    # We can plan a notification to be sent later, the frontend should not display it before the planned date
    delivery_datetime: Mapped[datetime | None]
    # Messages should be deleted after a certain time
    expire_on: Mapped[datetime]

    # A message can be visible or not, if it is not visible, it should only trigger an action
    is_visible: Mapped[bool] = mapped_column(default=True)


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
