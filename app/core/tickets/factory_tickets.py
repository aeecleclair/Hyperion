import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.mypayment.factory_mypayment import MyPaymentFactory
from app.core.tickets import cruds_tickets, schemas_tickets, types_tickets
from app.core.utils.config import Settings
from app.types.factory import Factory


class TicketsFactory(Factory):
    depends_on = [MyPaymentFactory]

    @classmethod
    async def run(cls, db: AsyncSession, settings: Settings) -> None:
        for store_ids in MyPaymentFactory.other_stores_id:
            for store_id in store_ids:
                await cruds_tickets.create_event(
                    event_id=uuid.uuid4(),
                    event=schemas_tickets.EventCreate(
                        store_id=store_id,
                        name=f"Test Event for store {store_id}",
                        quota=100,
                        open_datetime=datetime.now(UTC),
                        close_datetime=datetime.now(UTC) + timedelta(days=7),
                        sessions=[
                            schemas_tickets.SessionCreate(
                                name="Session 1",
                                start_datetime=datetime.now(UTC) + timedelta(days=10),
                                quota=10,
                            ),
                            schemas_tickets.SessionCreate(
                                name="Session 2",
                                start_datetime=datetime.now(UTC) + timedelta(days=5),
                                quota=None,
                            ),
                        ],
                        categories=[
                            schemas_tickets.CategoryCreate(
                                name="Category 1",
                                price=100,
                                required_membership=None,
                                quota=10,
                            ),
                            schemas_tickets.CategoryCreate(
                                name="Category 2",
                                price=0,
                                required_membership=None,
                                quota=None,
                            ),
                        ],
                        questions=[
                            schemas_tickets.QuestionCreate(
                                question="Question 1",
                                answer_type=types_tickets.AnswerType.TEXT,
                                required=True,
                                price=10,
                            ),
                            schemas_tickets.QuestionCreate(
                                question="Question 2",
                                answer_type=types_tickets.AnswerType.BOOLEAN,
                                required=False,
                                price=0,
                            ),
                            schemas_tickets.QuestionCreate(
                                question="Question 2",
                                answer_type=types_tickets.AnswerType.NUMBER,
                                required=False,
                                price=0,
                            ),
                        ],
                    ),
                    db=db,
                )

    @classmethod
    async def should_run(cls, db: AsyncSession):
        return len(await cruds_tickets.get_all_events(db)) == 0
