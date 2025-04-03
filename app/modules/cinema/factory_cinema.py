import random
import uuid
from datetime import UTC, datetime

from app.modules.cinema import cruds_cinema, schemas_cinema
from app.types.factory import Factory


class CinemaFactory(Factory):
    def __init__(self):
        super().__init__(
            name="cinema",
            depends_on=[],
        )

    async def create_films(self, db):
        films = {
            "The Matrix": {
                "overview": "Le premier film de la trilogie",
                "genre": "Action",
                "tagline": "Test tagline",
            },
            "The Matrix Reloaded": {
                "overview": "Le deuxième film de la trilogie",
                "genre": "Action",
                "tagline": "Test tagline",
            },
            "The Matrix Revolutions": {
                "overview": "Le troisième film de la trilogie",
                "genre": "Action",
                "tagline": "Test tagline",
            },
            "The Matrix Resurrections": {
                "overview": "Le film de trop",
                "genre": "Action",
                "tagline": "Test tagline",
            },
            "Captain America Civil War": {
                "overview": "Film marvel plutôt pas mal",
                "genre": "Superheros",
                "tagline": "Test tagline",
            },
        }

        for key, value in films.items():
            await cruds_cinema.create_session(
                session=schemas_cinema.CineSessionComplete(
                    start=datetime.now(UTC),
                    duration=random.randint(90, 180),
                    name=key,
                    overview=value["overview"],
                    genre=value["genre"],
                    tagline=value["tagline"],
                    id=str(uuid.uuid4()),
                ),
                db=db,
            )

    async def run(self, db):
        await self.create_films(db)

    async def should_run(self, db):
        films = await cruds_cinema.get_sessions(db=db)
        return len(films) == 0


factory = CinemaFactory()
