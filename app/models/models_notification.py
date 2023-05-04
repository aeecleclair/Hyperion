from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String

from app.database import Base


class Message(Base):
    __tablename__ = "notification_message"

    # A context represents a topic (ex: a loan),
    # there can only by one notification per context (ex: the loan should be returned, the loan is overdue or has been returned)
    context: str = Column(String, index=True, primary_key=True)
    # If there can be one notification per context, there can be multiple messages per notification: one by token_firebase
    # A token_firebase is related to a device from an user (its phone, its computer, etc.)
    token_firebase: str = Column(String, index=True, primary_key=True)

    # A message can be visible or not, if it is not visible, it should only trigger an action
    is_visible: bool = Column(Boolean, default=True)

    title: str = Column(String)
    content: str = Column(String)

    # TODO
    # An action id is used by Titan to know what to do when receiving the notification
    action_id: str = Column(String)
    expire_on: datetime = Column(DateTime(timezone=True), nullable=False)


