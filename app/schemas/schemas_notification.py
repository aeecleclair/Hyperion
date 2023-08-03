from datetime import date

from pydantic import BaseModel, Field


class Message(BaseModel):
    # A context represents a topic (ex: a loan),
    # there can only by one notification per context (ex: the loan should be returned, the loan is overdue or has been returned)
    context: str = Field(
        description="A context represents a topic. There can only by one notification per context."
    )
    # `firebase_device_token` is only contained in the database but is not returned by the API

    is_visible: bool = Field(
        description="A message can be visible or not, if it is not visible, it should only trigger an action"
    )

    title: str | None
    content: str | None

    # TODO
    action_module: str = Field(
        description="An action id is used by Titan to know what to do when receiving the notification"
    )
    action_table: str
    expire_on: date

    class Config:
        orm_mode = True


class FirebaseDevice(BaseModel):
    user_id: str = Field(description="The Hyperion user id")
    firebase_device_token: str = Field("Firebase device token")

    class Config:
        orm_mode = True
