import uuid
from datetime import UTC, datetime, time, timedelta
from pathlib import Path

from fastapi import Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core
from app.core.groups.groups_type import GroupType
from app.core.module import Module
from app.core.notification.notification_types import CustomTopic, Topic
from app.core.notification.schemas_notification import Message
from app.dependencies import (
    get_db,
    get_notification_tool,
    get_request_id,
    is_user_a_member,
    is_user_a_member_of,
)
from app.modules.ph import cruds_ph, models_ph, schemas_ph
from app.types.content_type import ContentType
from app.utils.communication.notifications import NotificationTool
from app.utils.tools import (
    delete_file_from_data,
    get_file_from_data,
    save_file_as_data,
    save_pdf_first_page_as_image,
)

module = Module(
    root="ph",
    tag="ph",
    default_allowed_groups_ids=[GroupType.student],
)


@module.router.get(
    "/ph/{paper_id}/pdf",
    response_class=FileResponse,
    status_code=200,
)
async def get_paper_pdf(
    paper_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    paper = await cruds_ph.get_paper_by_id(db=db, paper_id=paper_id)
    if paper is None:
        raise HTTPException(
            status_code=404,
            detail="The paper does not exist.",
        )

    return get_file_from_data(
        default_asset="assets/pdf/default_ph.pdf",
        directory="ph/pdf",
        filename=str(paper_id),
    )


@module.router.get(
    "/ph/",
    response_model=list[schemas_ph.PaperComplete],
    status_code=200,
)
async def get_papers(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Return all editions until now, sorted from the latest to the oldest
    """
    result = await cruds_ph.get_papers(
        db=db,
        end_date=datetime.now(tz=UTC).date(),
    )  # Return papers from the latest to the oldest until now
    return result


@module.router.get(
    "/ph/admin",
    response_model=list[schemas_ph.PaperComplete],
    status_code=200,
)
async def get_papers_admin(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.ph)),
):
    """
    Return all editions, sorted from the latest to the oldest
    """
    result = await cruds_ph.get_papers(
        db=db,
    )  # Return all papers from the latest to the oldest
    return result


@module.router.post(
    "/ph/",
    response_model=schemas_ph.PaperComplete,
    status_code=201,
)
async def create_paper(
    paper: schemas_ph.PaperBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.ph)),
    notification_tool: NotificationTool = Depends(get_notification_tool),
):
    """Create a new paper."""

    paper_complete = schemas_ph.PaperComplete(
        id=str(uuid.uuid4()),
        **paper.model_dump(),
    )
    try:
        paper_db = models_ph.Paper(
            id=paper_complete.id,
            name=paper_complete.name,
            release_date=paper_complete.release_date,
        )

        now = datetime.now(UTC)

        # We only want to send a notification if the paper was released less than a month ago.
        if paper_db.release_date >= now.date() - timedelta(days=30):
            message = Message(
                context=f"ph-{paper_db.id}",
                is_visible=True,
                title=f"📗 PH - {paper_db.name}",
                content="Un nouveau journal est disponible! 🎉",
                delivery_datetime=datetime.combine(
                    paper_db.release_date,
                    time(hour=8, tzinfo=UTC),
                ),
                # The notification will expire in 10 days
                expire_on=now + timedelta(days=10),
            )
            await notification_tool.send_notification_to_topic(
                custom_topic=CustomTopic(topic=Topic.ph),
                message=message,
            )
        return await cruds_ph.create_paper(paper=paper_db, db=db)

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@module.router.post(
    "/ph/{paper_id}/pdf",
    status_code=201,
)
async def create_paper_pdf_and_cover(
    paper_id: str,
    pdf: UploadFile = File(...),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.ph)),
    request_id: str = Depends(get_request_id),
    db: AsyncSession = Depends(get_db),
):
    paper = await cruds_ph.get_paper_by_id(db=db, paper_id=paper_id)
    if paper is None:
        raise HTTPException(
            status_code=404,
            detail="The paper does not exist.",
        )

    await save_file_as_data(
        upload_file=pdf,
        directory="ph/pdf",
        filename=str(paper_id),
        request_id=request_id,
        max_file_size=10 * 1024 * 1024,  # 10 MB
        accepted_content_types=ContentType.pdf,
    )

    await save_pdf_first_page_as_image(
        input_pdf_directory="ph/pdf",
        output_image_directory="ph/cover",
        filename=str(paper_id),
        default_pdf_path="assets/pdf/default_ph.pdf",
        request_id=request_id,
        jpg_quality=95,
    )


@module.router.get(
    "/ph/{paper_id}/cover",
    status_code=200,
)
async def get_cover(
    paper_id: str,
    user: models_core.CoreUser = Depends(is_user_a_member),
    db: AsyncSession = Depends(get_db),
):
    paper = await cruds_ph.get_paper_by_id(db=db, paper_id=paper_id)
    if paper is None:
        raise HTTPException(
            status_code=404,
            detail="The paper does not exist.",
        )

    return get_file_from_data(
        default_asset="assets/images/default_cover.jpg",
        directory="ph/cover",
        filename=str(paper_id),
    )


@module.router.patch(
    "/ph/{paper_id}",
    status_code=204,
)
async def update_paper(
    paper_id: str,
    paper_update: schemas_ph.PaperUpdate,
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.ph)),
    db: AsyncSession = Depends(get_db),
):
    paper = await cruds_ph.get_paper_by_id(paper_id=paper_id, db=db)
    if not paper:
        raise HTTPException(
            status_code=404,
            detail="Invalid paper_id",
        )

    await cruds_ph.update_paper(
        paper_id=paper_id,
        paper_update=paper_update,
        db=db,
    )


@module.router.delete(
    "/ph/{paper_id}",
    status_code=204,
)
async def delete_paper(
    paper_id: str,
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.ph)),
    db: AsyncSession = Depends(get_db),
):
    paper = await cruds_ph.get_paper_by_id(paper_id=paper_id, db=db)
    if not paper:
        raise HTTPException(
            status_code=404,
            detail="Invalid paper_id",
        )

    delete_file_from_data(
        directory="ph/pdf",
        filename=str(paper_id),
    )

    delete_file_from_data(
        directory="ph/cover",
        filename=str(paper_id),
    )

    await cruds_ph.delete_paper(
        paper_id=paper_id,
        db=db,
    )
