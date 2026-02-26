from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schools import cruds_schools
from app.core.schools.models_schools import CoreSchool
from app.core.utils.config import Settings
from app.types.factory import Factory


class CoreSchoolsFactory(Factory):
    depends_on = []

    school_id: UUID = uuid4()

    @classmethod
    async def run(cls, db: AsyncSession, settings: Settings) -> None:
        await cruds_schools.create_school(
            CoreSchool(
                id=cls.school_id,
                name="ENS",
                email_regex=r"^[a-zA-Z0-9_.+-]+@ens\.fr$",
            ),
            db,
        )

    @classmethod
    async def should_run(cls, db: AsyncSession):
        return len(await cruds_schools.get_schools(db)) == 2
