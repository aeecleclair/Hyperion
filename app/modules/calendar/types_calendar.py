from enum import Enum


class CalendarEventType(str, Enum):
    eventAE = "Event AE"
    eventUSE = "Event USE"
    independentAssociation = "Asso indé"
    happyHour = "HH"
    direction = "Strass"
    nightParty = "Rewass"
    other = "Autre"

    def __str__(self) -> str:
        return f"{self.name}<{self.value}"


class Decision(str, Enum):
    approved = "approved"
    not_sent = "not_sent"
    declined = "declined"
    pending = "pending"

    def __str__(self) -> str:
        return f"{self.name}<{self.value}>"


class QuestionType(str, Enum):
    boolean = "bool"
    open = "open"
    dates = "date"
