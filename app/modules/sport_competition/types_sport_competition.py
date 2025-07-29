from enum import Enum
from typing import Literal


class InvalidUserType(Exception):
    def __init__(self, complement: Literal["too_many", "none"], *args: object) -> None:
        super().__init__(*args)
        self.complement: Literal["too_many", "none"] = complement

    def __str__(self) -> str:
        if self.complement == "too_many":
            return "Invalid user type: too many types selected"
        return "Invalid user type: no type selected"


class SportCategory(Enum):
    masculine = "masculine"
    feminine = "feminine"


class CompetitionGroupType(Enum):
    sport_manager = "sport_manager"
    schools_bds = "schools_bds"


class ProductPublicType(Enum):
    pompom = "pompom"
    fanfare = "fanfare"
    cameraman = "cameraman"
    athlete = "athlete"
    volunteer = "volunteer"


class ProductSchoolType(Enum):
    centrale = "centrale"
    from_lyon = "from_lyon"
    others = "others"
