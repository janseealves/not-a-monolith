from langchain_core.tools import BaseTool, tool
from langgraph.config import get_config

from monolith.rag.service import RAGService


def make_rag_tool(rag: RAGService) -> BaseTool:
    """Embrulha o RAGService numa tool que o LLM decide (ou não) chamar.

    Dependência módulo→módulo pela interface pública (RAGService), nunca pelos
    internos. O collection_id não é argumento do LLM: vem do config da conversa
    via get_config(), evitando que o modelo alucine ids.
    """

    @tool
    async def search_knowledge_base(query: str) -> str:
        """Busca informações na base de conhecimento (documentos ingeridos).

        Use quando a pergunta exigir fatos específicos que possam estar nos
        documentos. Retorna trechos relevantes com suas fontes.
        """
        collection_id = get_config()["configurable"].get("collection_id")
        if collection_id is None:
            return "Nenhuma collection foi selecionada para esta conversa."

        docs = await rag.search(query, collection_id, top_k=5)
        if not docs:
            return "Nenhum documento relevante encontrado na base."

        return "\n\n".join(
            f"[{i + 1}] {d.document.page_content} "
            f"(fonte: {d.document.metadata.get('source', 'desconhecida')})"
            for i, d in enumerate(docs)
        )

    return search_knowledge_base
