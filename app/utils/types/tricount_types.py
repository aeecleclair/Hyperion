from enum import Enum


class TransactionType(str, Enum):
    expense = "expense"
    reimbursement = "reimbursement"
