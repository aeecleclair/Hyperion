import logging
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core
from app.core.config import Settings
from app.core.groups.groups_type import GroupType
from app.core.module import Module
from app.core.notification.notification_types import CustomTopic, Topic
from app.core.notification.schemas_notification import Message
from app.dependencies import (
    get_db,
    get_notification_tool,
    get_settings,
    is_user_a_member,
    is_user_a_member_of,
)
from app.modules.booking import cruds_booking, models_booking, schemas_booking
from app.modules.booking.types_booking import Decision
from app.utils.communication.notifications import NotificationTool
from app.utils.tools import is_group_id_valid, is_user_member_of_an_allowed_group
