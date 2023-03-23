import uuid

from app.dependencies import get_settings
from app.main import app
from app.models import models_core, models_raffle
from app.utils.types.groups_type import GroupType
from app.utils.types.raffle_types import RaffleStatusType
from tests.commons import TestingSessionLocal, create_user_with_groups

raffle_user: models_core.CoreUser | None = None
student_user: models_core.CoreUser | None = None
raffle: models_raffle.Raffle | None = None
typeticket: models_raffle.TypeTicket | None = None
lot: models_raffle.Lots | None = None
ticket: models_raffle.Tickets | None = None
cash: models_raffle.Cash | None = None


settings = app.dependency_overrides.get(get_settings, get_settings)()


@app.on_event("startup")  # create the data needed in the tests
async def startuptest():
    global raffle_user, student_user, raffle, typeticket, ticket, lot, cash

    async with TestingSessionLocal() as db:
        raffle_user = await create_user_with_groups([GroupType.admin], db=db)
        student_user = await create_user_with_groups([GroupType.student], db=db)

        raffle = models_raffle.Raffle(
            id=str(uuid.uuid4()),
            name="The best raffle",
            status=RaffleStatusType.creation,
            group_id="123",
        )
        db.add(raffle)
        typeticket = models_raffle.TypeTicket(
            id=str(uuid.uuid4()), price=1.0, nb_ticket=1, raffle_id=raffle.id
        )
        db.add(typeticket)

        ticket = models_raffle.Tickets(
            id=str(uuid.uuid4()),
            nb_tickets=3,
            raffle_id=raffle.id,
            group_id=raffle.group_id,
            type_id=typeticket.id,
            user_id=student_user.id,
            unit_price=typeticket.price,
        )
        db.add(ticket)

        lot = models_raffle.Lots(
            id=str(uuid.uuid4()),
            raffle_id=raffle.id,
            description="Description of the lot",
            name="Name of the lot",
            quantity=3,
        )
        db.add(lot)

        cash = models_raffle.Cash(
            user_id=student_user.id, user=student_user, balance=66
        )
        db.add(cash)

        await db.commit()
