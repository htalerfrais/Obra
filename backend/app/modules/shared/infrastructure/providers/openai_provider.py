import json
import logging
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings
from app.models.llm_models import LLMRequest, LLMResponse
from app.models.tool_models import ConversationMessage, ToolAugmentedRequest, ToolAugmentedResponse, ToolCall, ToolDefinition
from .base_provider import LLMProviderInterface

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProviderInterface):
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(api_key, base_url)
        self.api_key = api_key or settings.openai_api_key
        self.base_url = base_url or settings.openai_base_url

    def get_default_model(self) -> str:
        return "gpt-4.1-mini"

    def validate_request(self, request: LLMRequest) -> bool:
        return request.provider == "openai"

    async def generate_text(self, request: LLMRequest) -> LLMResponse:
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        model = request.model or self.get_default_model()
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": request.prompt}],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=settings.api_timeout,
            )
            response.raise_for_status()
            data = response.json()
        return LLMResponse(
            generated_text=data["choices"][0]["message"]["content"],
            provider="openai",
            model=model,
            usage=data.get("usage"),
            metadata={"response_id": data.get("id")},
        )

    async def generate_with_tools(self, request: ToolAugmentedRequest) -> ToolAugmentedResponse:
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        model = request.model or self.get_default_model()
        payload: Dict[str, Any] = {
            "model": model,
            "messages": self._build_openai_messages(request.messages),
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "tools": self._build_openai_tools(request.tools),
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=settings.api_timeout,
            )
            response.raise_for_status()
            data = response.json()
        return self._parse_openai_tool_response(data, model, data.get("usage"))

    def _build_openai_tools(self, tools: List[ToolDefinition]) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {"name": tool.name, "description": tool.description, "parameters": tool.parameters},
            }
            for tool in tools
        ]

    def _build_openai_messages(self, messages: List[ConversationMessage]) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        for msg in messages:
            if msg.role in ("system", "user"):
                result.append({"role": msg.role, "content": msg.content or ""})
            elif msg.role == "assistant":
                entry: Dict[str, Any] = {"role": "assistant"}
                if msg.content:
                    entry["content"] = msg.content
                if msg.tool_calls:
                    entry["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                        }
                        for tc in msg.tool_calls
                    ]
                result.append(entry)
            elif msg.role == "tool":
                result.append({"role": "tool", "tool_call_id": msg.tool_call_id or "", "content": msg.content or ""})
        return result

    def _parse_openai_tool_response(self, data: dict, model: str, usage: Any) -> ToolAugmentedResponse:
        message = data["choices"][0]["message"]
        tool_calls: List[ToolCall] = []
        for tc in message.get("tool_calls") or []:
            func = tc.get("function", {})
            try:
                args = json.loads(func.get("arguments", "{}"))
            except Exception:
                args = {}
            tool_calls.append(ToolCall(id=tc.get("id", ""), name=func.get("name", ""), arguments=args))
        return ToolAugmentedResponse(
            text=message.get("content"),
            tool_calls=tool_calls,
            provider="openai",
            model=model,
            usage=usage,
        )
