from collections.abc import AsyncIterator

from langchain.chat_models import BaseChatModel
from langchain_core.messages import AIMessageChunk
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.prebuilt import create_react_agent

from modules.agents.base import BaseAgent


class GraphAgent(BaseAgent):
    """Agente ReAct sobre LangGraph. Compila o grafo uma vez; cada conversa é
    isolada pelo thread_id no checkpointer."""

    def __init__(
        self,
        llm: BaseChatModel,
        tools: list[BaseTool],
        checkpointer: BaseCheckpointSaver,
        system_prompt: str,
    ) -> None:
        self._graph = create_react_agent(
            llm,
            tools,
            prompt=system_prompt,
            checkpointer=checkpointer,
        )

    async def astream(
        self,
        message: str,
        thread_id: str,
        collection_id: int | None = None,
    ) -> AsyncIterator[str]:
        config = {"configurable": {"thread_id": thread_id}}
        if collection_id is not None:
            config["configurable"]["collection_id"] = collection_id

        # stream_mode="messages" emite (chunk, metadata) por token; filtramos só
        # os tokens de texto do LLM (ToolMessages e tool_calls vazios ficam de fora).
        async for chunk, _ in self._graph.astream(
            {"messages": [{"role": "user", "content": message}]},
            config,
            stream_mode="messages",
        ):
            if isinstance(chunk, AIMessageChunk) and chunk.content:
                yield chunk.content
