from app.core.memberships import schemas_memberships
from app.core.mypayment import models_mypayment, schemas_mypayment
from app.core.users import schemas_users


def structure_model_to_schema(
    structure: models_mypayment.Structure,
) -> schemas_mypayment.Structure:
    """
    Convert a structure model to a schema.
    """
    return schemas_mypayment.Structure(
        id=structure.id,
        short_id=structure.short_id,
        name=structure.name,
        association_membership_id=structure.association_membership_id,
        association_membership=schemas_memberships.MembershipSimple(
            id=structure.association_membership.id,
            name=structure.association_membership.name,
            manager_group_id=structure.association_membership.manager_group_id,
        )
        if structure.association_membership
        else None,
        manager_user_id=structure.manager_user_id,
        manager_user=schemas_users.CoreUserSimple(
            id=structure.manager_user.id,
            firstname=structure.manager_user.firstname,
            name=structure.manager_user.name,
            nickname=structure.manager_user.nickname,
            account_type=structure.manager_user.account_type,
            school_id=structure.manager_user.school_id,
        ),
        administrators=[
            schemas_users.CoreUserSimple(
                id=admin.user.id,
                firstname=admin.user.firstname,
                name=admin.user.name,
                nickname=admin.user.nickname,
                account_type=admin.user.account_type,
                school_id=admin.user.school_id,
            )
            for admin in structure.administrators
        ],
        siret=structure.siret,
        siege_address_street=structure.siege_address_street,
        siege_address_city=structure.siege_address_city,
        siege_address_zipcode=structure.siege_address_zipcode,
        siege_address_country=structure.siege_address_country,
        iban=structure.iban,
        bic=structure.bic,
        creation=structure.creation,
    )


def refund_model_to_schema(
    refund: models_mypayment.Refund,
) -> schemas_mypayment.Refund:
    """
    Convert a refund model to a schema.
    """
    return schemas_mypayment.Refund(
        id=refund.id,
        transaction_id=refund.transaction_id,
        credited_wallet_id=refund.credited_wallet_id,
        debited_wallet_id=refund.debited_wallet_id,
        total=refund.total,
        creation=refund.creation,
        seller_user_id=refund.seller_user_id,
        transaction=schemas_mypayment.Transaction(
            id=refund.transaction.id,
            debited_wallet_id=refund.transaction.debited_wallet_id,
            credited_wallet_id=refund.transaction.credited_wallet_id,
            transaction_type=refund.transaction.transaction_type,
            seller_user_id=refund.transaction.seller_user_id,
            total=refund.transaction.total,
            creation=refund.transaction.creation,
            status=refund.transaction.status,
        ),
        debited_wallet=schemas_mypayment.WalletInfo(
            id=refund.debited_wallet.id,
            type=refund.debited_wallet.type,
            owner_name=refund.debited_wallet.store.name
            if refund.debited_wallet.store
            else refund.debited_wallet.user.full_name
            if refund.debited_wallet.user
            else None,
        ),
        credited_wallet=schemas_mypayment.WalletInfo(
            id=refund.credited_wallet.id,
            type=refund.credited_wallet.type,
            owner_name=refund.credited_wallet.store.name
            if refund.credited_wallet.store
            else refund.credited_wallet.user.full_name
            if refund.credited_wallet.user
            else None,
        ),
    )


def invoice_model_to_schema(
    invoice: models_mypayment.Invoice,
) -> schemas_mypayment.Invoice:
    """
    Convert an invoice model to a schema.
    """
    return schemas_mypayment.Invoice(
        id=invoice.id,
        reference=invoice.reference,
        structure_id=invoice.structure_id,
        creation=invoice.creation,
        start_date=invoice.start_date,
        end_date=invoice.end_date,
        total=invoice.total,
        paid=invoice.paid,
        received=invoice.received,
        structure=structure_model_to_schema(invoice.structure),
        details=[
            schemas_mypayment.InvoiceDetail(
                invoice_id=invoice.id,
                store_id=detail.store_id,
                total=detail.total,
                store=schemas_mypayment.StoreSimple(
                    id=detail.store.id,
                    name=detail.store.name,
                    structure_id=detail.store.structure_id,
                    wallet_id=detail.store.wallet_id,
                    creation=detail.store.creation,
                ),
            )
            for detail in invoice.details
        ],
    )
