
from app.modules.feedback import (schemas_feedback, models_feedback)
from sqlalchemy import and_, delete, func, not_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID


async def get_feedbacks(db: AsyncSession) -> list[schemas_feedback.Feedback] | None:
    result = await db.execute(select(models_feedback.Feedback)).scalars().all()
    return [schemas_feedback.Feedback(id=r.id, creation=r.creation, content=r.content, user_id=r.user_id) for r in result]

    
async def add_feedbacks(db: AsyncSession, feedback: schemas_feedback.Feedback) -> None:
    db.add(models_feedback.Feedback(**feedback.model_dump()))

async def delete_feedback(db: AsyncSession, feedback_id: UUID):
    db.execute(delete(models_feedback.Feedback).where(models_feedback.Feedback.id == feedback_id))
