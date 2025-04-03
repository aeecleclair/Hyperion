import uuid
from datetime import date

from app.core.users.factory_users import CoreUsersFactory
from app.modules.loan import cruds_loan, models_loan
from app.types.factory import Factory


class LoanFactory(Factory):
    def __init__(self):
        super().__init__(
            name="loan",
            depends_on=[CoreUsersFactory],
        )

    async def create_loan(self, db):
        loaner_id_1 = str(uuid.uuid4())
        group_manager_id_1 = str(uuid.uuid4())
        await cruds_loan.create_loaner(
            db=db,
            loaner=models_loan.Loaner(
                id=loaner_id_1,
                name="Eclair",
                group_manager_id=group_manager_id_1,
            ),
        )

        loaner_id_2 = str(uuid.uuid4())
        group_manager_id_2 = str(uuid.uuid4())
        await cruds_loan.create_loaner(
            db=db,
            loaner=models_loan.Loaner(
                id=loaner_id_2,
                name="Bazar",
                group_manager_id=group_manager_id_2,
            ),
        )
        item_id_1 = str(uuid.uuid4())
        item_1 = await cruds_loan.create_item(
            db=db,
            item=models_loan.Item(
                id=item_id_1,
                name="Cable HDMI",
                loaner_id=loaner_id_1,
                suggested_caution=0,
                total_quantity=50,
                suggested_lending_duration=360000,
            ),
        )

        item_id_2 = str(uuid.uuid4())
        item_2 = await cruds_loan.create_item(
            db=db,
            item=models_loan.Item(
                id=item_id_2,
                name="PC n°1",
                loaner_id=loaner_id_1,
                suggested_caution=1000,
                total_quantity=100,
                suggested_lending_duration=180000,
            ),
        )

        item_id_3 = str(uuid.uuid4())
        item_3 = await cruds_loan.create_item(
            db=db,
            item=models_loan.Item(
                id=item_id_3,
                name="Loup-Garou",
                loaner_id=loaner_id_2,
                suggested_caution=10,
                total_quantity=2,
                suggested_lending_duration=72000,
            ),
        )

        loan_id_1 = str(uuid.uuid4())
        await cruds_loan.create_loan(
            db=db,
            loan=models_loan.Loan(
                id=loan_id_1,
                borrower_id=CoreUsersFactory.demo_users_id[0],
                loaner_id=loaner_id_1,
                start=date(2025, 2, 22),
                end=date(2025, 2, 25),
                notes=None,
                caution=None,
                returned=False,
                returned_date=None,
                items=[item_1, item_2],
            ),
        )

        loan_id_2 = str(uuid.uuid4())
        await cruds_loan.create_loan(
            db=db,
            loan=models_loan.Loan(
                id=loan_id_2,
                borrower_id=CoreUsersFactory.demo_users_id[1],
                loaner_id=loaner_id_2,
                start=date(2025, 2, 22),
                end=date(2025, 2, 25),
                notes=None,
                caution="10",
                returned=True,
                returned_date=date(2025, 2, 24),
                items=[item_3],
            ),
        )

    async def run(self, db):
        await self.create_loan(db)

    async def should_run(self, db):
        campaigns = await cruds_loan.get_loaners(db=db)
        return len(campaigns) == 0


factory = LoanFactory()
