from typing import List, Optional, Tuple

from app.models.tool_models import ToolCall, ToolDefinition, ToolResult
from app.modules.shared.ports import ToolExecutionPort
from app.tools.registry import ToolRegistry


class ToolGateway(ToolExecutionPort):
    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry

    def get_definitions(self, names: Optional[List[str]] = None) -> List[ToolDefinition]:
        return self.tool_registry.get_definitions(names)

    async def execute(self, tool_call: ToolCall, user_id: int) -> Tuple[ToolResult, List[dict]]:
        return await self.tool_registry.execute(tool_call, user_id)
