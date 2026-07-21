from collections.abc import AsyncIterator

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver

from monolith.modules.agents.base import BaseAgent
from monolith.modules.agents.graph.agent import GraphAgent
from monolith.modules.agents.graph.tools import make_rag_tool
from monolith.modules.rag.service import RAGService
from monolith.shared.config import Settings
from monolith.shared.config import settings as default_settings
from monolith.shared.llm import build_chat_model
from monolith.shared.prompts import render_prompt


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
            system_prompt=(
                render_prompt("persona", project_name=settings.PROJECT_NAME)
                + "\n\n"
                + render_prompt("agent_tool_policy")
            ),
        )
        return cls(agent)

    def astream(
        self,
        message: str,
        thread_id: str,
        collection_id: int | None = None,
    ) -> AsyncIterator[str]:
        return self._agent.astream(message, thread_id, collection_id)
