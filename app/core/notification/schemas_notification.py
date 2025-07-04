from pydantic import BaseModel, Field


class Message(BaseModel):
    title: str | None = None
    content: str | None = None

    action_module: str


class FirebaseDevice(BaseModel):
    user_id: str = Field(description="The Hyperion user id")
    firebase_device_token: str = Field("Firebase device token")


class GroupNotificationRequest(BaseModel):
    group_id: str
    title: str
    content: str
