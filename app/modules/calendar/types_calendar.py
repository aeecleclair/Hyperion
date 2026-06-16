from enum import StrEnum


class CalendarEventType(StrEnum):
    eventAE = "Event AE"
    eventUSE = "Event USE"
    independentAssociation = "Asso indé"
    happyHour = "HH"
    direction = "Strass"
    nightParty = "Rewass"
    other = "Autre"

    def __str__(self) -> str:
        return f"{self.name}<{self.value}"


class Decision(StrEnum):
    approved = "approved"
    declined = "declined"
    pending = "pending"

    def __str__(self) -> str:
        return f"{self.name}<{self.value}>"
