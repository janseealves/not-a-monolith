from dataclasses import asdict

from langchain_core.tools import BaseTool, tool
from langgraph.config import get_config

from monolith.modules.rag.service import RAGService, build_sources


def make_rag_tool(rag: RAGService) -> BaseTool:
    """Embrulha o RAGService numa tool que o LLM decide (ou não) chamar.

    Dependência módulo→módulo pela interface pública (RAGService), nunca pelos
    internos. O collection_id não é argumento do LLM: vem do config da conversa
    via get_config(), evitando que o modelo alucine ids.
    """

    @tool(response_format="content_and_artifact")
    async def search_knowledge_base(query: str) -> tuple[str, list[dict]]:
        """Busca informações na base de conhecimento (documentos ingeridos).

        Use quando a pergunta exigir fatos específicos que possam estar nos
        documentos. Retorna trechos relevantes com suas fontes.
        """
        collection_id = get_config()["configurable"].get("collection_id")
        if collection_id is None:
            return "Nenhuma collection foi selecionada para esta conversa.", []

        docs = await rag.search(query, collection_id, top_k=5)
        if not docs:
            return "Nenhum documento relevante encontrado na base.", []

        # Título, não o source: o source de um PDF é uma URI s3:// com um uuid,
        # e o modelo repetia isso na resposta ao ser instruído a citar a fonte.
        content = "\n\n".join(
            f"[{i + 1}] {d.document.page_content} "
            f"(fonte: {d.document.metadata.get('title') or 'desconhecida'})"
            for i, d in enumerate(docs)
        )
        # artifact: dado estruturado que não vai pro contexto do LLM, só pro app.
        return content, [asdict(s) for s in build_sources(docs)]

    return search_knowledge_base
