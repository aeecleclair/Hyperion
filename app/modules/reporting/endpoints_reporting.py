import logging
import uuid
from datetime import UTC, datetime

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from zoneinfo import ZoneInfo

from app.core.groups import cruds_groups
from app.core.groups.groups_type import AccountType
from app.core.notification.schemas_notification import Message
from app.core.permissions.type_permissions import ModulePermissions
from app.core.users import models_users
from app.dependencies import (
    get_db,
    get_notification_tool,
    is_user_allowed_to,
)
from app.modules.reporting import (
    cruds_reporting,
    models_reporting,
    schemas_reporting,
)

#from app.modules.reporting.types_reporting import Decision
from app.types.module import Module
from app.utils.communication.notifications import NotificationTool
from app.utils.tools import is_group_id_valid, is_user_member_of_any_group

class ReportingPermissions(ModulePermissions):
    access_reporting = "access_reporting"
    manage_reporting = "manage_reporting"

module = Module(
    root="reporting",
    tag="Reporting",
    default_allowed_account_types=[AccountType.student, AccountType.staff], factory= None,
    permissions = ReportingPermissions,
)

hyperion_error_logger = logging.getLogger("hyperion.error")

@module.router.get(
    "/reporting/managers",
    response_model=list[schemas_reporting.Manager],
    status_code=200,
)
async def get_managers(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([ReportingPermissions.manage_reporting]),
    ),
):
    """
    Get existing managers.

    **This endpoint is only usable by administrators**
    """

    return await cruds_reporting.get_managers(db=db)