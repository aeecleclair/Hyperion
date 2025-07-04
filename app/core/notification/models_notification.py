from datetime import date
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.types.sqlalchemy import Base, PrimaryKey


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

    id: Mapped[PrimaryKey]

    name: Mapped[str]

    # `module_root` and `topic_identifier` should allow a module to find its topic
    # topic_identifier will usually contains the id of one object. For example the id of an announcer
    module_root: Mapped[str]
    topic_identifier: Mapped[str | None]

    # If `restrict_to_group_id` is set, only users from the group can subscribe to the topic
    # If `restrict_to_members` is set, external users can not subscribe to the topic
    restrict_to_group_id: Mapped[str | None] = mapped_column(
        ForeignKey("core_group.id"),
    )
    restrict_to_members: Mapped[bool]


class TopicMembership(Base):
    __tablename__ = "notification_topic_membership"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
        primary_key=True,
    )
    topic_id: Mapped[UUID] = mapped_column(
        ForeignKey("notification_topic.id"),
        primary_key=True,
    )
