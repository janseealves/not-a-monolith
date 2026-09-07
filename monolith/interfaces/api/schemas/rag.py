import uuid
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from monolith.modules.rag.ingestion.base import LocalSource, Source, WebSource


class IngestRequest(BaseModel):
    source: str = Field(..., description="URL ou caminho do documento a ser ingerido")
    source_type: Literal["web", "local"] = Field(
        "web", description="Tipo da fonte: 'web' para URLs, 'local' para arquivos"
    )

    def to_source(self) -> Source:
        if self.source_type == "local":
            return LocalSource(path=Path(self.source))
        return WebSource(url=self.source)


class IngestResponse(BaseModel):
    message: str = Field(..., description="Mensagem de confirmação da ingestão")


class UploadResponse(BaseModel):
    document_id: uuid.UUID = Field(
        ...,
        description="Identificador público do documento; use-o para pedir a referência",
    )
    message: str = Field(..., description="Mensagem de confirmação da ingestão")


class DocumentReference(BaseModel):
    url: str = Field(
        ..., description="URL temporária e assinada para ler o documento original"
    )
    expires_in: int = Field(..., description="Validade da URL, em segundos")


class QueryRequest(BaseModel):
    query: str = Field(..., description="Pergunta a ser respondida")
    top_k: int = Field(
        5, ge=1, le=20, description="Número de chunks relevantes a serem recuperados"
    )


class RetrievedChunk(BaseModel):
    content: str = Field(..., description="Conteúdo do chunk recuperado")
    score: float = Field(..., description="Pontuação de relevância do chunk")


class SearchResponse(BaseModel):
    results: list[RetrievedChunk] = Field(
        ..., description="Lista de chunks relevantes encontrados"
    )
