import random
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.users.factory_users import CoreUsersFactory
from app.modules.seed_library import coredata_seed_library, cruds_seed_library
from app.modules.seed_library.schemas_seed_library import PlantComplete, SpeciesComplete
from app.modules.seed_library.types_seed_library import (
    PlantState,
    PropagationMethod,
    SpeciesType,
)
from app.types.factory import Factory
from app.utils import tools


class SeedLibraryFactory(Factory):
    def __init__(self):
        super().__init__(
            depends_on=[CoreUsersFactory],
        )
        self.species: list[SpeciesComplete] = []

    async def create_species(
        self,
        db: AsyncSession,
    ):
        species_names = [
            "Tomato",
            "Potato",
            "Lavender",
            "Rose",
            "Thyme",
        ]
        prefixes = [
            "TOM",
            "POT",
            "LAV",
            "ROS",
            "THY",
        ]
        species_types = [
            SpeciesType.vegetables,
            SpeciesType.vegetables,
            SpeciesType.ornamental,
            SpeciesType.ornamental,
            SpeciesType.aromatic,
        ]
        start_seasons = [
            date(2023, 1, 1),
            date(2023, 7, 1),
            date(2023, 5, 1),
            date(2023, 3, 1),
            date(2023, 11, 1),
        ]
        end_seasons = [
            date(2023, 6, 1),
            date(2023, 8, 1),
            date(2023, 8, 1),
            date(2023, 7, 1),
            date(2023, 2, 1),
        ]
        time_maturations = [
            30,
            60,
            90,
            120,
            150,
        ]
        for (
            name,
            prefix,
            species_type,
            start_season,
            end_season,
            time_maturation,
            i,
        ) in zip(
            species_names,
            prefixes,
            species_types,
            start_seasons,
            end_seasons,
            time_maturations,
            range(len(species_names)),
            strict=True,
        ):
            species = SpeciesComplete(
                id=uuid4(),
                prefix=prefix,
                name=name,
                species_type=species_type,
                card="example.org",
                nb_seeds_recommended=5,
                start_season=start_season,
                end_season=end_season,
                difficulty=i,
                time_maturation=time_maturation,
            )
            await cruds_seed_library.create_species(
                db=db,
                species=species,
            )
            self.species.append(species)

    async def create_plants(
        self,
        db: AsyncSession,
    ):
        states = list(PlantState)
        for species in self.species:
            for i in range(3):
                await cruds_seed_library.create_plant(
                    db=db,
                    plant=PlantComplete(
                        id=uuid4(),
                        reference=f"{species.prefix}-{i}",
                        state=states[i],
                        species_id=species.id,
                        propagation_method=random.choice(
                            list(PropagationMethod),
                        ),
                        borrower_id=CoreUsersFactory.demo_users_id[0]
                        if i != 0
                        else None,
                        borrowing_date=datetime.now(tz=UTC).date() - timedelta(days=30),
                        planting_date=datetime.now(tz=UTC).date()
                        - timedelta(days=random.randint(1, 30)),
                    ),
                )

    async def run(self, db: AsyncSession):
        await self.create_species(db=db)
        await self.create_plants(db=db)
        await tools.set_core_data(
            db=db,
            core_data=coredata_seed_library.SeedLibraryInformation(
                facebook_url="https://www.facebook.com",
                forum_url="https://l.myecl.fr/s/test",
                description=Faker().text(200),
                contact="demo1@myecl.fr",
            ),
        )

    async def should_run(self, db: AsyncSession):
        return len(await cruds_seed_library.get_all_species(db)) == 0
