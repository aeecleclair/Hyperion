from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.graph import schemas_graph
from app.core.groups import models_groups
from app.core.users import models_users

from app.modules.graph import Acquaintances

async def get_acquaintances(
        db: AsyncSession,
        user_id: UUID,
        depth: int = 2,
) -> Sequence[schemas_graph.Acquaintance]:
    result = await db.execute(
        select(models_groups.CoreMembership)
        .join(models_groups.CoreGroup)
        .join(models_groups.CoreMembership, models_groups.CoreMembership.group_id == models_groups.CoreGroup.id)
        .join(models_users.CoreUser, models_users.CoreUser.id == models_groups.CoreMembership.user_id)
        .where(models_groups.CoreMembership.user_id == user_id))