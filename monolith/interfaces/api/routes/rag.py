import uuid
from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse

from monolith.interfaces.api.dependencies import (
    get_collection,
    get_object_store,
    get_rag_service,
)
from monolith.interfaces.api.schemas.rag import (
    DocumentReference,
    IngestRequest,
    IngestResponse,
    QueryRequest,
    RetrievedChunk,
    SearchResponse,
    UploadResponse,
)
from monolith.modules.rag import crud
from monolith.modules.rag.models import Collection
from monolith.modules.rag.service import RAGService
from monolith.shared.storage import ObjectStore
from monolith.shared.streaming import sse_stream_with_sources

router = APIRouter(prefix="/rag/collections/{collection_id}", tags=["RAG"])
documents_router = APIRouter(prefix="/rag/documents", tags=["RAG"])


RAGServiceDeps = Annotated[RAGService, Depends(get_rag_service)]
CollectionDeps = Annotated[Collection, Depends(get_collection)]
ObjectStoreDeps = Annotated[ObjectStore, Depends(get_object_store)]

# A ingestão é aberta: sem teto, um PDF grande vira memória do worker e uma
# conta de embeddings.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@router.post(
    "/ingest", status_code=status.HTTP_201_CREATED, response_model=IngestResponse
)
async def ingest(
    service: RAGServiceDeps, collection: CollectionDeps, request: IngestRequest
):
    await service.ingest(request.to_source(), collection.id)
    return IngestResponse(message="Documento processado com sucesso.")


@router.post("/search", status_code=status.HTTP_200_OK, response_model=SearchResponse)
async def search(
    service: RAGServiceDeps, collection: CollectionDeps, request: QueryRequest
):
    r = await service.search(request.query, collection.id, request.top_k)
    return SearchResponse(
        results=[
            RetrievedChunk(
                content=doc.document.page_content,
                score=doc.score,
            )
            for doc in r
        ]
    )


@router.post("/ask", status_code=status.HTTP_200_OK)
async def ask(
    service: RAGServiceDeps, collection: CollectionDeps, request: QueryRequest
):
    result = await service.astream_ask(request.query, collection.id, request.top_k)
    stream = sse_stream_with_sources([asdict(s) for s in result.sources], result.stream)
    return StreamingResponse(stream, media_type="text/event-stream")


@router.post(
    "/documents",
    status_code=status.HTTP_201_CREATED,
    response_model=UploadResponse,
)
async def upload_document(
    service: RAGServiceDeps,
    collection: CollectionDeps,
    file: Annotated[UploadFile, File(description="PDF a ser ingerido")],
):
    if file.content_type != "application/pdf":
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Apenas PDF é aceito; recebido {file.content_type!r}.",
        )

    # Starlette preenche o size a partir do multipart: checar antes de ler evita
    # trazer o arquivo inteiro para a memória só para descobrir que é grande.
    if file.size is not None and file.size > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            f"Arquivo excede o limite de {MAX_UPLOAD_BYTES // 1024**2} MB.",
        )

    document_id = await service.ingest_upload(
        filename=file.filename or "documento.pdf",
        data=await file.read(),
        content_type=file.content_type,
        collection_id=collection.id,
    )
    return UploadResponse(
        document_id=document_id, message="Documento processado com sucesso."
    )


@documents_router.get(
    "/{document_id}/reference",
    status_code=status.HTTP_200_OK,
    response_model=DocumentReference,
)
async def get_reference(document_id: uuid.UUID, store: ObjectStoreDeps):
    document = await crud.get_document_by_external_id(document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento não encontrado.")

    try:
        url = store.presigned_url(document.source)
    except ValueError as exc:
        # Documento ingerido de URL: existe no índice, mas não há binário nosso.
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Documento não tem binário guardado no object store.",
        ) from exc

    return DocumentReference(url=url, expires_in=store.url_ttl)
