from datetime import UTC, datetime
from uuid import uuid4

from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.config import Settings
from app.modules.recommendation import cruds_recommendation
from app.modules.recommendation.models_recommendation import Recommendation
from app.types.factory import Factory

faker = Faker("fr_FR")


class RecommendationFactory(Factory):
    depends_on = []

    @classmethod
    async def run(cls, db: AsyncSession, settings: Settings) -> None:
        titles = [
            faker.sentence(nb_words=3),
            faker.sentence(nb_words=3),
            faker.sentence(nb_words=3),
            faker.sentence(nb_words=3),
        ]
        codes = [
            "ASDFQSPMKM",
            None,
            "A/*SDF-QSP-MKM",
            "ASDFQSPMKMPOG8489656556UIVJKL%PS",
        ]
        summaries = [
            faker.sentence(nb_words=10),
            faker.sentence(nb_words=10),
            faker.sentence(nb_words=10),
            faker.sentence(nb_words=10),
        ]
        descriptions = [
            faker.paragraph(nb_sentences=5),
            faker.paragraph(nb_sentences=5),
            faker.paragraph(nb_sentences=5),
            faker.paragraph(nb_sentences=5),
        ]
        for i in range(4):
            await cruds_recommendation.create_recommendation(
                recommendation=Recommendation(
                    id=uuid4(),
                    creation=datetime.now(tz=UTC),
                    title=titles[i],
                    code=codes[i],
                    summary=summaries[i],
                    description=descriptions[i],
                ),
                db=db,
            )

    @classmethod
    async def should_run(cls, db: AsyncSession):
        return len(await cruds_recommendation.get_recommendations(db=db)) == 0
