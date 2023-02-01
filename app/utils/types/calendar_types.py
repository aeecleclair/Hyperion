from enum import Enum


class CalendarEventType(str, Enum):
    eventAE = "Event AE"
    eventUSE = "Event USE"
    happyHour = "HH"
    direction = "Strass"
    nightParty = "Soirée"
    other = "Autre"

    def __str__(self):
        return f"{self.name}<{self.value}"


class Decision(str, Enum):
    approved = "approved"
    declined = "declined"
    pending = "pending"

    def __str__(self):
        return f"{self.name}<{self.value}>"
