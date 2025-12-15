import csv
from io import StringIO

from app.core.myeclpay import models_myeclpay


def generate_store_history_csv(
    transactions_with_sellers: list[tuple[models_myeclpay.Transaction, str | None]],
    refunds_map: dict,
    store_wallet_id,
) -> str:
    """
    Generate a CSV string containing the store payment history.

    Args:
        transactions_with_sellers: List of tuples (Transaction, seller_full_name)
        refunds_map: Dictionary mapping transaction_id to (Refund, seller_name) tuples
        store_wallet_id: UUID of the store's wallet to determine transaction direction

    Returns:
        CSV string with UTF-8 BOM for Excel compatibility
    """
    csv_io = StringIO()
    # Add UTF-8 BOM for Excel compatibility
    csv_io.write("\ufeff")

    writer = csv.writer(csv_io, delimiter=";", quoting=csv.QUOTE_MINIMAL)

    # Write headers
    writer.writerow(
        [
            "Date/Heure",
            "Type",
            "Autre partie",
            "Montant (€)",
            "Statut",
            "Vendeur",
            "Montant remboursé (€)",
            "Date remboursement",
            "Note magasin",
        ],
    )

    # Write transaction data
    for transaction, seller_full_name in transactions_with_sellers:
        transaction_type = (
            "REÇU" if transaction.credited_wallet_id == store_wallet_id else "DONNÉ"
        )
        other_party_wallet = (
            transaction.debited_wallet
            if transaction.credited_wallet_id == store_wallet_id
            else transaction.credited_wallet
        )
        other_party = "Inconnu"
        if other_party_wallet.user:
            other_party = (
                f"{other_party_wallet.user.firstname} {other_party_wallet.user.name}"
            )
        elif other_party_wallet.store:
            other_party = other_party_wallet.store.name

        # Check if transaction has a refund
        refund_data = refunds_map.get(transaction.id)
        refund_amount = ""
        refund_date = ""
        if refund_data:
            refund, _ = refund_data
            refund_amount = str(refund.total / 100)
            refund_date = refund.creation.strftime("%d/%m/%Y %H:%M:%S")

        writer.writerow(
            [
                transaction.creation.strftime("%d/%m/%Y %H:%M:%S"),
                transaction_type,
                other_party,
                str(transaction.total / 100),
                transaction.status.value,
                seller_full_name or "N/A",
                refund_amount,
                refund_date,
                transaction.store_note or "",
            ],
        )

    csv_content = csv_io.getvalue()
    csv_io.close()

    return csv_content
