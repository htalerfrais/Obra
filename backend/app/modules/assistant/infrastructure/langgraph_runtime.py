import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from app.config import settings
from app.models.chat_models import SourceItem
from app.models.tool_models import ConversationMessage, ToolAugmentedRequest, ToolAugmentedResponse
from app.modules.shared.ports import LLMChatPort, ToolExecutionPort


class ChatGraphState(TypedDict):
    messages: List[ConversationMessage]
    tools: List[Any]
    user_id: Optional[int]
    response: Optional[ToolAugmentedResponse]
    all_sources: List[SourceItem]
    iteration: int
    done: bool
    provider: str


class LangGraphChatRuntime:
    def __init__(self, llm_port: LLMChatPort, tool_port: ToolExecutionPort):
        self.llm_port = llm_port
        self.tool_port = tool_port
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(ChatGraphState)
        graph.add_node("llm_step", self._llm_step)
        graph.add_node("tool_step", self._tool_step)
        graph.set_entry_point("llm_step")
        graph.add_conditional_edges(
            "llm_step",
            self._route_after_llm,
            {
                "tool_step": "tool_step",
                "end": END,
            },
        )
        graph.add_edge("tool_step", "llm_step")
        return graph.compile()

    async def run(self, messages: List[ConversationMessage], user_id: Optional[int], provider: str) -> Dict[str, Any]:
        tools = self.tool_port.get_definitions() if user_id else []
        state: ChatGraphState = {
            "messages": messages,
            "tools": tools,
            "user_id": user_id,
            "response": None,
            "all_sources": [],
            "iteration": 0,
            "done": False,
            "provider": provider,
        }
        final_state = await self.graph.ainvoke(state)
        response: Optional[ToolAugmentedResponse] = final_state.get("response")
        return {
            "text": (response.text if response else "") or "",
            "provider": response.provider if response else settings.default_provider,
            "model": response.model if response else settings.default_model,
            "sources": final_state.get("all_sources", []),
            "iterations": final_state.get("iteration", 0),
        }

    async def _llm_step(self, state: ChatGraphState) -> ChatGraphState:
        response = await self.llm_port.generate_with_tools(
            ToolAugmentedRequest(
                messages=state["messages"],
                tools=state["tools"],
                provider=state["provider"],
                max_tokens=settings.chat_max_tokens,
                temperature=settings.chat_temperature,
            )
        )
        state["response"] = response
        state["iteration"] += 1
        if not response.tool_calls or state["iteration"] >= settings.chat_max_tool_iterations:
            state["done"] = True
        return state

    def _route_after_llm(self, state: ChatGraphState) -> str:
        if state["done"]:
            return "end"
        return "tool_step"

    async def _tool_step(self, state: ChatGraphState) -> ChatGraphState:
        response = state.get("response")
        if not response or not response.tool_calls:
            state["done"] = True
            return state

        state["messages"].append(
            ConversationMessage(role="assistant", content=response.text, tool_calls=response.tool_calls)
        )

        tasks = [self.tool_port.execute(tc, state["user_id"]) for tc in response.tool_calls]
        results = await asyncio.gather(*tasks)

        for tool_result, source_dicts in results:
            state["messages"].append(
                ConversationMessage(role="tool", content=tool_result.content, tool_call_id=tool_result.call_id)
            )
            for source in source_dicts:
                state["all_sources"].append(
                    SourceItem(
                        url=source.get("url", ""),
                        title=source.get("title", "Untitled"),
                        visit_time=source.get("visit_time", datetime.now()),
                        url_hostname=source.get("url_hostname"),
                    )
                )

        return state
