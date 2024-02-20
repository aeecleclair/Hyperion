from enum import Enum


class RoleTags(Enum):
    president = "Prez\'"
    treso = "Trez\'"
    sg = "SG"
    resp_co = "Respo Comm\'"
    resp_part = "Respo Partenariats"

    def __str__(self):
        return self.value


class Kinds(Enum):
    club = "Club"
    section = "Section"
    association = "Association"
    association_independante = "Association indépendante"

    def __str__(self):
        return self.value


if __name__ == "__main__":
    print("--> ", list(Kinds.__members__.items())[0][0])
    print("--> ", list(Kinds.__members__.items())[:][0])
    ol = [el[0] for el in list(Kinds.__members__.items())]
    print("--> ", ol)
