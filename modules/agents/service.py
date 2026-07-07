from collections.abc import AsyncIterator

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver

from modules.agents.base import BaseAgent
from modules.agents.graph.agent import GraphAgent
from modules.agents.graph.tools import make_rag_tool
from modules.rag.service import RAGService
from shared.config import Settings
from shared.config import settings as default_settings
from shared.llm import build_chat_model


class AgentService:
    def __init__(self, agent: BaseAgent) -> None:
        self._agent = agent

    @classmethod
    def with_defaults(
        cls,
        rag: RAGService,
        checkpointer: BaseCheckpointSaver | None = None,
        settings: Settings | None = None,
    ) -> "AgentService":
        settings = settings or default_settings

        # único lugar do módulo que conhece as classes concretas
        llm = build_chat_model(settings)
        tools = [make_rag_tool(rag)]
        agent = GraphAgent(
            llm=llm,
            tools=tools,
            checkpointer=checkpointer or InMemorySaver(),
            system_prompt=settings.AGENT_SYSTEM_PROMPT,
        )
        return cls(agent)

    def astream(
        self,
        message: str,
        thread_id: str,
        collection_id: int | None = None,
    ) -> AsyncIterator[str]:
        return self._agent.astream(message, thread_id, collection_id)
