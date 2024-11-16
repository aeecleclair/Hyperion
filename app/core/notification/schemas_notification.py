from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Message(BaseModel):
    title: str | None = None
    content: str | None = None

    action_module: str | None = Field(
        None,
        description="An identifier for the module that should be triggered when the notification is clicked",
    )
    


class FirebaseDevice(BaseModel):
    user_id: str = Field(description="The Hyperion user id")
    firebase_device_token: str = Field("Firebase device token")
