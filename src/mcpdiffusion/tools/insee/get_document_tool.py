"""Tool: get_insee_document."""

from fastmcp.dependencies import Depends

from ...dependencies.insee import get_insee_document_service
from ...models.insee import (
    DocumentContentOutput,
    DocumentUrls,
    IncludeTableOfContents,
    TruncateContent,
)
from ...services.insee.document_service import InseeDocumentService


async def get_insee_document(
    document_urls: DocumentUrls,
    include_table_of_contents: IncludeTableOfContents = True,
    truncate_content: TruncateContent = True,
    insee_document_service: InseeDocumentService = Depends(get_insee_document_service),
) -> DocumentContentOutput:
    """Fetch and parse INSEE publications from known URLs and return their full text in markdown.

    Every per-URL entry carries the same keys whether it succeeded or failed, so results can be
    iterated without type-sniffing.

    WHEN TO USE
    - You have a concrete URL of the form `/fr/statistiques/<id>` or `/fr/statistiques/<id>?sommaire=<sid>`,
      returned by `search_insee_documents`, `search_insee_conjoncture` or `search_insee_chiffrecle`.

    WHEN NOT TO USE
    - You are still looking for the right publication. Use `search_insee_documents` first.
    - You need a quick, up-to-date indicator. Use `get_insee_homepage`.
    """
    results = await insee_document_service.fetch_documents(
        document_urls=document_urls,
        include_table_of_contents=include_table_of_contents,
        truncate_content=truncate_content,
    )
    return DocumentContentOutput(
        results=results,
        count=len(results),
    )
