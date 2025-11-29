from uuid import UUID

from pydantic import BaseModel, Field


class Message(BaseModel):
    title: str | None = None
    content: str | None = None

    action_module: str


class FirebaseDevice(BaseModel):
    user_id: str = Field(description="The Hyperion user id")
    firebase_device_token: str = Field("Firebase device token")


class TopicBase(BaseModel):
    id: UUID
    name: str

    module_root: str
    topic_identifier: str | None


class Topic(TopicBase):
    restrict_to_group_id: str | None = None
    restrict_to_members: bool = True


class TopicUser(TopicBase):
    is_user_subscribed: bool


class GroupNotificationRequest(BaseModel):
    group_id: str
    title: str
    content: str
