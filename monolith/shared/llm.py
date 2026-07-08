from langchain.chat_models import BaseChatModel, init_chat_model

from monolith.shared.config import Settings


def build_chat_model(settings: Settings) -> BaseChatModel:
    """Constrói o chat model a partir das settings (mesma lógica usada pelo RAG).

    Ollama self-hosted não exige auth; se LLM_API_KEY existir, manda como Bearer
    (permite apontar o chat pra um provider cloud sem mudar o código).
    """
    key = settings.LLM_API_KEY.get_secret_value() if settings.LLM_API_KEY else None
    client_kwargs = {"headers": {"Authorization": f"Bearer {key}"}} if key else {}
    return init_chat_model(
        model=settings.LLM_MODEL,
        model_provider=settings.LLM_MODEL_PROVIDER,
        base_url=settings.LLM_BASE_URL,
        client_kwargs=client_kwargs,
    )
