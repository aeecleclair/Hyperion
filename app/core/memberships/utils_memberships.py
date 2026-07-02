from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.documents import cruds_documents, schemas_documents
from app.core.documents.exceptions_documents import (
    ElementTemplateNotFoundError,
)
from app.core.documents.types_documenso import DocumentStatus
from app.core.documents.utils_documents import (
    _configure_documenso_api_wrapper,
    delete_document,
    document_model_to_schema,
    template_model_to_schema,
    use_template_for_user,
)
from app.core.memberships import (
    cruds_memberships,
    models_memberships,
    schemas_memberships,
)
from app.core.users.schemas_users import CoreUser
from app.core.users.utils_users import user_model_to_schema
from app.core.utils.config import Settings

MODULE_ROOT = "memberships"


def membership_model_to_schema(
    model: models_memberships.CoreAssociationMembership,
) -> schemas_memberships.MembershipSimple:
    """Convert a CoreAssociationMembership model to a MembershipSimple schema."""
    return schemas_memberships.MembershipSimple(
        id=model.id,
        name=model.name,
        manager_group_id=model.manager_group_id,
        template_id=model.template_id,
    )


def membership_complete_model_to_schema(
    model: models_memberships.CoreAssociationMembership,
) -> schemas_memberships.MembershipComplete:
    """Convert a CoreAssociationMembership model to a MembershipComplete schema."""
    return schemas_memberships.MembershipComplete(
        id=model.id,
        name=model.name,
        manager_group_id=model.manager_group_id,
        template_id=model.template_id,
        template=template_model_to_schema(model.template) if model.template else None,
    )


def user_membership_complete_model_to_schema(
    model: models_memberships.CoreAssociationUserMembership,
) -> schemas_memberships.UserMembershipComplete:
    """Convert a CoreAssociationUserMembership model to a UserMembershipComplete schema."""
    return schemas_memberships.UserMembershipComplete(
        id=model.id,
        user_id=model.user_id,
        association_membership_id=model.association_membership_id,
        start_date=model.start_date,
        end_date=model.end_date,
        document_id=model.document_id,
        document_status=model.document_status,
        valid=model.valid,
        user=user_model_to_schema(model.user),
        document=document_model_to_schema(model.document) if model.document else None,
    )


def user_membership_with_association_model_to_schema(
    model: models_memberships.CoreAssociationUserMembership,
) -> schemas_memberships.UserMembershipWithAssociation:
    """Convert a CoreAssociationUserMembership model to a UserMembershipComplete schema."""
    return schemas_memberships.UserMembershipWithAssociation(
        id=model.id,
        user_id=model.user_id,
        association_membership_id=model.association_membership_id,
        start_date=model.start_date,
        end_date=model.end_date,
        document_id=model.document_id,
        document_status=model.document_status,
        valid=model.valid,
        user=user_model_to_schema(model.user),
        document=document_model_to_schema(model.document) if model.document else None,
        association_membership=membership_model_to_schema(model.association_membership),
    )


async def validate_user_new_membership(
    user_membership: schemas_memberships.UserMembershipSimple,
    db: AsyncSession,
) -> schemas_memberships.UserMembershipSimple:
    """
    Validate the given membership data.

    :param membership: The membership data to validate.
    :return: The validated membership data.
    """
    if user_membership.start_date > user_membership.end_date:
        raise HTTPException(
            status_code=400,
            detail="The start date must be before the end date.",
        )
    memberships = list(
        await cruds_memberships.get_user_memberships_by_user_id_and_association_membership_id(
            db,
            user_membership.user_id,
            user_membership.association_membership_id,
        ),
    )
    for membership in memberships:
        if user_membership.id != membership.id:
            if (
                user_membership.start_date
                < membership.end_date
                < user_membership.end_date
                or user_membership.start_date
                < membership.start_date
                < user_membership.end_date
                or membership.start_date
                < user_membership.end_date
                < membership.end_date
                or membership.start_date
                < user_membership.start_date
                < membership.end_date
            ):
                raise HTTPException(
                    status_code=400,
                    detail="The new membership period overlaps with an existing one.",
                )

    return user_membership


async def get_user_active_membership_to_association_membership(
    association_membership_id: UUID,
    user_id: str,
    db: AsyncSession,
) -> schemas_memberships.UserMembershipSimple | None:
    """
    Check if the user has an active membership to the association membership.
    :param membership_id: The ID of the membership to check.
    :param user_id: The ID of the user to check.
    :param db: The database session.
    :return: The active membership if found.
    """
    memberships = await cruds_memberships.get_user_memberships_by_user_id_and_association_membership_id(
        db,
        user_id,
        association_membership_id,
    )
    for membership in memberships:
        if membership.start_date <= datetime.now(UTC).date() <= membership.end_date:
            return membership

    return None


async def membership_document_callback(
    document_id: UUID,
    document_status: DocumentStatus,
    db: AsyncSession,
):
    """
    Handle the callback from the document service for a membership document.
    :param document_id: The ID of the document that was updated.
    :param document_status: The new status of the document.
    :param db: The database session.
    """
    user_membership = await cruds_memberships.get_user_membership_by_document_id(
        db,
        document_id,
    )
    if user_membership is None:
        raise HTTPException(
            status_code=404,
            detail="User membership not found for the given document ID.",
        )

    await cruds_memberships.update_user_membership(
        db,
        user_membership.id,
        schemas_memberships.UserMembershipEdit(document_status=document_status),
    )


async def add_membership_to_user(
    user: CoreUser,
    association_membership: schemas_memberships.MembershipSimple,
    user_membership: schemas_memberships.UserMembershipSimple,
    db: AsyncSession,
    settings: Settings,
):
    """
    Add a membership to a user.
    :param user: The user to add the membership to.
    :param association_membership: The association membership to add.
    :param user_membership: The user membership to add.
    :param db: The database session.
    """
    await validate_user_new_membership(user_membership, db)

    if association_membership.template_id is not None:
        template = await cruds_documents.get_template_by_id(
            db,
            association_membership.template_id,
        )
        if template is None:
            raise ElementTemplateNotFoundError(association_membership.template_id)

        documenso = _configure_documenso_api_wrapper(
            team=template.team,
            settings=settings,
        )

        document = await use_template_for_user(
            user=user,
            template=template,
            module=MODULE_ROOT,
            db=db,
            documenso=documenso,
        )
        user_membership.document_id = document.id
        user_membership.document_status = document.status
        user_membership.valid = (
            user_membership.document_status == DocumentStatus.COMPLETED
        )

    await cruds_memberships.create_user_membership(
        db=db,
        user_membership=user_membership,
    )

    return schemas_memberships.UserMembershipComplete(
        id=user_membership.id,
        user_id=user_membership.user_id,
        association_membership_id=user_membership.association_membership_id,
        start_date=user_membership.start_date,
        end_date=user_membership.end_date,
        document_id=user_membership.document_id,
        document_status=user_membership.document_status,
        valid=user_membership.valid,
        user=user,
    )


async def renew_membership_documents(
    association_membership: schemas_memberships.MembershipComplete,
    team: schemas_documents.Team,
    user_membership: schemas_memberships.UserMembershipComplete,
    db: AsyncSession,
    settings: Settings,
) -> None:
    """
    Renew the documents for a user's membership to an association membership.
    :param association_membership: The association membership to renew.
    :param user: The user to renew the membership for.
    :param db: The database session.
    :param settings: The application settings.
    """

    if association_membership.template is None:
        return

    documenso = _configure_documenso_api_wrapper(
        team=team,
        settings=settings,
    )

    document = await use_template_for_user(
        user=user_membership.user,
        template=association_membership.template,
        module=MODULE_ROOT,
        db=db,
        documenso=documenso,
    )

    await cruds_memberships.update_user_membership_document(
        db=db,
        user_membership_id=user_membership.id,
        document_id=document.id,
        document_status=document.status,
    )


async def remove_membership_from_user(
    user_membership: schemas_memberships.UserMembershipComplete,
    settings: Settings,
    db: AsyncSession,
):
    """
    Remove a membership from a user.
    :param user_membership: The user membership to remove.
    :param db: The database session.
    """
    await cruds_memberships.delete_user_membership(
        db=db,
        user_membership_id=user_membership.id,
    )

    if user_membership.document_id is not None:
        document = await cruds_documents.get_document_by_id(
            db,
            user_membership.document_id,
        )
        if document is None:
            return
        template = await cruds_documents.get_template_by_id(
            db,
            document.template_id,
        )
        if template is None:
            return
        documenso = _configure_documenso_api_wrapper(
            team=template.team,
            settings=settings,
        )
        await delete_document(
            document=document,
            documenso=documenso,
            db=db,
        )
