from enum import Enum


class CapsMode(str, Enum):
    SINGLE = "single"
    CD = "cd"
    CAPACKS = "capacks"
    SEMI_CAPACKS = "semi_capacks"
