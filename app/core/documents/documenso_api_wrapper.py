from uuid import UUID

from documenso_sdk import (
    Documenso,
    DocumentDownloadResponse,
    DocumentFindData,
    DocumentUpdateData,
    FolderFindFoldersData,
    FolderFindFoldersQueryParamType,
    FolderFindFoldersResponse,
    TemplateCreateDocumentFromTemplateRecipientRequest,
    TemplateCreateDocumentFromTemplateResponse,
    TemplateFindTemplatesData,
)
from pydantic import BaseModel


class DocumensoConfiguration(BaseModel):
    api_key: str
    documenso_url: str


class DocumensoAPIWrapper:
    def __init__(
        self,
        configuration: DocumensoConfiguration,
    ):
        self.client = Documenso(
            api_key=configuration.api_key,
            server_url=configuration.documenso_url,
        )

    async def find_folders(
        self,
        parent_id: str | None = None,
        folder_type: FolderFindFoldersQueryParamType = FolderFindFoldersQueryParamType.DOCUMENT,
    ) -> list[FolderFindFoldersData]:
        current_page = 1
        max_pages = 1
        all_folders: list[FolderFindFoldersData] = []
        while current_page <= max_pages:
            response: FolderFindFoldersResponse = await self.client.folders.find_async(
                parent_id=parent_id,
                type_=folder_type,
                page=current_page,
                per_page=100,
            )
            all_folders.extend(response.data)
            max_pages = int(response.total_pages)
            current_page += 1
        return all_folders

    async def find_folder_from_path(
        self,
        path: str,
        folder_type: FolderFindFoldersQueryParamType = FolderFindFoldersQueryParamType.DOCUMENT,
    ) -> FolderFindFoldersData | None:
        path_parts = path.strip("/").split("/")
        parent_id = None
        for part in path_parts:
            folders = await self.find_folders(
                parent_id=parent_id,
                folder_type=folder_type,
            )
            matching_folder = next((f for f in folders if f.name == part), None)
            if not matching_folder:
                return None
            parent_id = matching_folder.id
        return matching_folder

    async def get_folder_documents(self, folder_id: str) -> list[DocumentFindData]:
        current_page = 1
        max_pages = 1
        all_documents: list[DocumentFindData] = []
        while current_page <= max_pages:
            response = await self.client.documents.find_async(
                folder_id=folder_id,
                page=current_page,
                per_page=100,
            )
            all_documents.extend(response.data)
            max_pages = int(response.total_pages)
            current_page += 1
        return all_documents

    async def get_folder_templates(
        self,
        folder_id: str | None = None,
    ) -> list[TemplateFindTemplatesData]:
        current_page = 1
        max_pages = 1
        all_templates: list[TemplateFindTemplatesData] = []
        while current_page <= max_pages:
            response = await self.client.templates.find_async(
                folder_id=folder_id,
                page=current_page,
                per_page=100,
            )
            all_templates.extend(response.data)
            max_pages = int(response.total_pages)
            current_page += 1
        return all_templates

    async def use_template(
        self,
        template_id: float,
        external_id: UUID,
        recipients: list[TemplateCreateDocumentFromTemplateRecipientRequest],
        destination_folder_id: str,
    ) -> TemplateCreateDocumentFromTemplateResponse:
        return await self.client.templates.use_async(
            template_id=template_id,
            recipients=recipients,
            folder_id=destination_folder_id,
            distribute_document=True,
            external_id=str(external_id),
        )

    async def download_document(self, document_id: float) -> DocumentDownloadResponse:
        return await self.client.documents.download_async(document_id=document_id)

    async def move_document(
        self,
        document_id: float,
        destination_folder_id: str,
    ) -> bool:
        await self.client.documents.update_async(
            document_id=document_id,
            data=DocumentUpdateData(folder_id=destination_folder_id),
        )
        return True

    async def delete_document(self, document_id: float) -> bool:
        await self.client.documents.delete_async(document_id=document_id)
        return True
