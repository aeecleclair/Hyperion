from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.google_api import models_google_api


async def create_oauth_flow_state(
    oauth_flow_state: models_google_api.OAuthFlowState,
    db: AsyncSession,
) -> None:
    db.add(oauth_flow_state)
    await db.flush()


async def get_oauth_flow_state_by_state(
    state: str,
    db: AsyncSession,
) -> models_google_api.OAuthFlowState | None:
    result = await db.execute(
        select(models_google_api.OAuthFlowState).where(
            models_google_api.OAuthFlowState.state == state,
        ),
    )
    return result.scalars().first()


async def delete_all_states(
    db: AsyncSession,
) -> None:
    await db.execute(delete(models_google_api.OAuthFlowState))
