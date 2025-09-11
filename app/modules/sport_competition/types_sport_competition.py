from datetime import UTC, datetime
from enum import Enum
from uuid import UUID


class InconsistentData(Exception):
    def __init__(self, complement: str | None, *args: object) -> None:
        super().__init__(*args)
        self.complement = complement

    def __str__(self) -> str:
        if self.complement:
            return f"Inconsistent data: {self.complement}"
        return "Inconsistent data"


class MultipleEditions(Exception):
    def __str__(self) -> str:
        return "Multiple activated editions"


class UnauthorizedAction(Exception):
    def __str__(self) -> str:
        return "Unauthorized action"


class SportCategory(str, Enum):
    masculine = "masculine"
    feminine = "feminine"


class CompetitionGroupType(UUID, Enum):
    fanfaron = UUID("c69ed623-1cf5-4769-acc7-ddbc6490fb07")
    pompom = UUID("22af0472-0a15-4f05-a670-fa02eda5e33f")
    cameraman = UUID("9cb535c7-ca19-4dbc-8b04-8b34017b5cff")
    non_athlete = UUID("84a9972c-56b0-4024-86ec-a284058e1cb1")
    sport_manager = UUID("a3f48a0b-ada1-4fe0-b987-f4170d8896c4")
    schools_bds = UUID("96f8ffb8-c585-4ca5-8360-dc3881f9f1e2")
    competition_admin = UUID("41b8735a-1702-4a9e-8486-a453572f6b5c")


class DefaultCoreData(str, Enum):
    challenge_year = datetime.now(tz=UTC).year
