from enum import Enum


class RoleTags(Enum):
    president = "Prez'"
    treso = "Trez'"
    sg = "SG"
    resp_co = "Respo Com'"
    resp_part = "Respo Partenariats"


class Kinds(Enum):
    comity = "Comité"
    section_ae = "Section AE"
    club_ae = "Club AE"
    section_use = "Section USE"
    club_use = "Club USE"
    association_independant = "Asso indé"
