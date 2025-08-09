#########################################################################################
#########################################################################################
#### /!\ Warning /!\ /!\ Warning /!\ /!\ Warning /!\ /!\ Warning /!\ /!\ Warning /!\ ####
####                                                                                 ####
####     Following functions are used to format MyECLPay actions for S3 storage.     ####
####                   Modifying them will break the verification                    ####
####                   of MyECLPay's integrity via S3 validation.                    ####
####                                                                                 ####
####       Please do not modify them without understanding the consequences.         ####
####                                                                                 ####
#### /!\ Warning /!\ /!\ Warning /!\ /!\ Warning /!\ /!\ Warning /!\ /!\ Warning /!\ ####
#########################################################################################
#########################################################################################


from uuid import UUID

from app.core.mypayment import models_mypayment, schemas_mypayment
from app.core.mypayment.types_mypayment import ActionType


def format_transfer_log(
    transfer: schemas_mypayment.Transfer | models_mypayment.Transfer,
):
    return f"{ActionType.TRANSFER.name} {transfer.id} {transfer.type.name} {transfer.total} {transfer.wallet_id}"


def format_transaction_log(
    transaction: schemas_mypayment.TransactionBase,
):
    return f"{ActionType.TRANSACTION.name} {transaction.id} {transaction.debited_wallet_id} {transaction.credited_wallet_id} {transaction.total}"


def format_refund_log(
    refund: schemas_mypayment.RefundBase,
):
    return (
        f"{ActionType.REFUND.name} {refund.id} {refund.transaction_id} {refund.total}"
    )


def format_cancel_log(
    transaction_id: UUID,
):
    return f"{ActionType.CANCEL.name} {transaction_id}"
