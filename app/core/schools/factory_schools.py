from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schools import cruds_schools
from app.core.schools.models_schools import CoreSchool
from app.types.factory import Factory


class SchoolsFactory(Factory):
    def __init__(self):
        super().__init__(
            name="module",
            depends_on=[],
        )

    async def run(self, db: AsyncSession):
        await cruds_schools.create_school(
            CoreSchool(
                id=uuid4(),
                name="ENS",
                email_regex=r"^[a-zA-Z0-9_.+-]+@ens\.fr$",
            ),
            db,
        )

    async def should_run(self, db: AsyncSession):
        return len(await cruds_schools.get_schools(db)) == 2


factory = SchoolsFactory()
