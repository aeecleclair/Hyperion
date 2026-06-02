from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.feedback import models_feedback, schemas_feedback


async def get_feedbacks(db: AsyncSession) -> list[schemas_feedback.Feedback] | None:
    result = await db.execute(select(models_feedback.Feedback))
    return [
        schemas_feedback.Feedback(
            content=r.content,
            id=r.id,
            user_id=r.user_id,
            user_name=r.user_name,
            creation=r.creation,
            is_addressed=r.is_addressed,
        )
        for r in result.scalars().all()
    ]


async def add_feedback(
    db: AsyncSession,
    feedback: schemas_feedback.Feedback,
) -> schemas_feedback.Feedback:
    feedback_db = models_feedback.Feedback(
        id=feedback.id,
        content=feedback.content,
        user_id=feedback.user_id,
        user_name=feedback.user_name,
        creation=feedback.creation,
        is_addressed=feedback.is_addressed,
    )
    db.add(feedback_db)
    await db.flush()
    print("dbbbbbb")


async def delete_feedback(db: AsyncSession, feedback_id: UUID):
    await db.execute(
        delete(models_feedback.Feedback).where(
            models_feedback.Feedback.id == feedback_id,
        ),
    )
