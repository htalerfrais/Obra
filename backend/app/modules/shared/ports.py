from typing import Any, Dict, List, Optional, Protocol, Tuple

from app.models.tool_models import ToolAugmentedRequest, ToolAugmentedResponse, ToolCall, ToolDefinition


class LLMChatPort(Protocol):
    async def generate_with_tools(self, request: ToolAugmentedRequest) -> ToolAugmentedResponse:
        ...


class ToolExecutionPort(Protocol):
    def get_definitions(self, names: Optional[List[str]] = None) -> List[ToolDefinition]:
        ...

    async def execute(self, tool_call: ToolCall, user_id: int) -> Tuple[Any, List[dict]]:
        ...


class EventPublisherPort(Protocol):
    def publish(
        self,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload: Dict[str, Any],
        event_version: int = 1,
        idempotency_key: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        ...
