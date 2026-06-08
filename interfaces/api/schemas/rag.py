from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    source: str = Field(..., description="URL do documento a ser ingerido")


class IngestResponse(BaseModel):
    message: str = Field(..., description="Mensagem de confirmação da ingestão")


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


class AskResponse(BaseModel):
    answer: str = Field(..., description="Resposta gerada para a pergunta")
