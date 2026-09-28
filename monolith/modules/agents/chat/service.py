import uuid
from collections.abc import AsyncIterator

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver

from monolith.modules.agents.base import BaseAgent
from monolith.modules.agents.chat.agent import ChatAgent
from monolith.modules.agents.chat.tools import make_rag_tool
from monolith.modules.memory.base import Turn
from monolith.modules.memory.service import MemoryService
from monolith.modules.rag.service import RAGService
from monolith.shared.config import Settings
from monolith.shared.config import settings as default_settings
from monolith.shared.llm import build_chat_model
from monolith.shared.prompts import render_prompt
from monolith.shared.streaming import SourcesChunk


class ChatService:
    def __init__(self, agent: BaseAgent, memory: MemoryService | None = None) -> None:
        self._agent = agent
        self._memory = memory

    @classmethod
    def with_defaults(
        cls,
        rag: RAGService,
        checkpointer: BaseCheckpointSaver | None = None,
        memory: MemoryService | None = None,
        settings: Settings | None = None,
    ) -> "ChatService":
        settings = settings or default_settings

        # único lugar do módulo que conhece as classes concretas
        llm = build_chat_model(settings)
        tools = [make_rag_tool(rag)]
        agent = ChatAgent(
            llm=llm,
            tools=tools,
            checkpointer=checkpointer or InMemorySaver(),
            system_prompt=(
                render_prompt("persona", project_name=settings.PROJECT_NAME)
                + "\n\n"
                + render_prompt(
                    "agent_tool_policy",
                    knowledge_base=settings.KNOWLEDGE_BASE_DESCRIPTION,
                )
            ),
        )
        return cls(agent, memory)

    async def astream(
        self,
        message: str,
        thread_id: str,
        collection_id: int | None = None,
        user_id: uuid.UUID | None = None,
    ) -> AsyncIterator[str | SourcesChunk]:
        # Sem motor ou sem usuário não há de quem lembrar: segue o fluxo antigo.
        if self._memory is None or user_id is None:
            async for chunk in self._agent.astream(message, thread_id, collection_id):
                yield chunk
            return

        # Hook, não tool: busca SEMPRE antes e grava SEMPRE depois do turno. Assim
        # todo motor recebe exatamente as mesmas entradas e a única variável da
        # comparação é o motor.
        recalled = await self._memory.recall(message, user_id)

        answer: list[str] = []
        sources: list[dict] = []
        async for chunk in self._agent.astream(
            message, thread_id, collection_id, memories=[m.content for m in recalled]
        ):
            if isinstance(chunk, SourcesChunk):
                sources.extend(chunk.sources)
            else:
                answer.append(chunk)
            yield chunk

        # Gravado antes do [DONE], de propósito: o cliente só recebe o fim do
        # stream quando a memória já existe, então o turno seguinte de um cenário
        # de teste sempre a enxerga. Custa latência; aqui determinismo vale mais.
        await self._memory.record(
            Turn(
                user_id=user_id,
                thread_id=uuid.UUID(thread_id),
                collection_id=collection_id,
                user_message=message,
                assistant_message="".join(answer),
                sources=sources,
                recalled=recalled,
            )
        )
