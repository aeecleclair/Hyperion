from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.groups_type import GroupType
from app.core.permissions import cruds_permissions, schemas_permissions
from app.core.utils.config import Settings
from app.module import permissions_list
from app.types.factory import Factory


class CorePermissionsFactory(Factory):
    depends_on = []

    @classmethod
    async def run(cls, db: AsyncSession, settings: Settings) -> None:
        for permission in permissions_list:
            await cruds_permissions.create_group_permission(
                permission=schemas_permissions.CoreGroupPermission(
                    permission_name=permission,
                    group_id=GroupType.admin.value,
                ),
                db=db,
            )
        await db.commit()

    @classmethod
    async def should_run(cls, db: AsyncSession):
        permissions = await cruds_permissions.get_permissions(
            permissions_list,
            db,
        )
        return len(permissions) == 0
