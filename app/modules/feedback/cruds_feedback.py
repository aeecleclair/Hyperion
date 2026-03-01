from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.feedback import models_feedback, schemas_feedback


async def get_feedbacks(db: AsyncSession) -> list[schemas_feedback.Feedback] | None:
    result = await db.execute(select(models_feedback.Feedback))
    return [
        schemas_feedback.Feedback(
            id=r.id,
            creation=r.creation,
            content=r.content,
            user_id=r.user_id,
        )
        for r in result.scalars().all()
    ]


async def add_feedback(db: AsyncSession, feedback: schemas_feedback.Feedback) -> None:
    db.add(models_feedback.Feedback(**feedback.model_dump()))


async def delete_feedback(db: AsyncSession, feedback_id: UUID):
    db.execute(
        delete(models_feedback.Feedback).where(
            models_feedback.Feedback.id == feedback_id,
        ),
    )
