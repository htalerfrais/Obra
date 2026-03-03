import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.config import settings
from app.models.llm_models import LLMRequest, LLMResponse
from app.models.tool_models import ConversationMessage, ToolAugmentedRequest, ToolAugmentedResponse, ToolCall, ToolDefinition
from .base_provider import LLMProviderInterface

logger = logging.getLogger(__name__)


class GoogleProvider(LLMProviderInterface):
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(api_key, base_url)
        self.api_key = api_key or settings.google_api_key
        self.base_url = base_url or settings.google_base_url

    def get_default_model(self) -> str:
        return settings.default_model

    def validate_request(self, request: LLMRequest) -> bool:
        return request.provider == "google"

    async def generate_text(self, request: LLMRequest) -> LLMResponse:
        if not self.api_key:
            raise ValueError("Google API key is required")
        model = request.model or self.get_default_model()
        payload = {
            "contents": [{"parts": [{"text": request.prompt}]}],
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
            },
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/models/{model}:generateContent?key={self.api_key}",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=settings.api_timeout,
            )
            response.raise_for_status()
            data = response.json()
        text = ""
        if data.get("candidates"):
            parts = data["candidates"][0].get("content", {}).get("parts", [])
            if parts and "text" in parts[0]:
                text = parts[0]["text"]
        return LLMResponse(
            generated_text=text,
            provider="google",
            model=model,
            usage=data.get("usageMetadata"),
            metadata={"response_id": data.get("model")},
        )

    async def generate_with_tools(self, request: ToolAugmentedRequest) -> ToolAugmentedResponse:
        if not self.api_key:
            raise ValueError("Google API key is required")
        model = request.model or self.get_default_model()
        system_instruction, contents = self._build_google_contents(request.messages)
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
            },
            "tools": self._build_google_tools(request.tools),
        }
        if system_instruction:
            payload["system_instruction"] = system_instruction
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/models/{model}:generateContent?key={self.api_key}",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=settings.api_timeout,
            )
            response.raise_for_status()
            data = response.json()
        return self._parse_google_tool_response(data, model, data.get("usageMetadata"))

    def _build_google_tools(self, tools: List[ToolDefinition]) -> List[Dict[str, Any]]:
        declarations = [{"name": t.name, "description": t.description, "parameters": t.parameters} for t in tools]
        return [{"functionDeclarations": declarations}] if declarations else []

    def _build_google_contents(self, messages: List[ConversationMessage]) -> Tuple[Optional[dict], List[Dict[str, Any]]]:
        system_instruction = None
        contents: List[Dict[str, Any]] = []
        for msg in messages:
            if msg.role == "system":
                system_instruction = {"parts": [{"text": msg.content or ""}]}
            elif msg.role == "user":
                contents.append({"role": "user", "parts": [{"text": msg.content or ""}]})
            elif msg.role == "assistant":
                parts: List[Dict[str, Any]] = []
                if msg.content:
                    parts.append({"text": msg.content})
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        parts.append({"functionCall": {"name": tc.name, "args": tc.arguments}})
                if parts:
                    contents.append({"role": "model", "parts": parts})
            elif msg.role == "tool":
                fn_name = self._extract_func_name_from_call_id(msg.tool_call_id or "")
                try:
                    parsed = json.loads(msg.content or "{}")
                except Exception:
                    parsed = {"result": msg.content or ""}
                contents.append(
                    {
                        "role": "user",
                        "parts": [{"functionResponse": {"name": fn_name, "response": parsed}}],
                    }
                )
        return system_instruction, contents

    @staticmethod
    def _extract_func_name_from_call_id(call_id: str) -> str:
        parts = call_id.split("_", 2)
        return parts[2] if len(parts) >= 3 else call_id

    def _parse_google_tool_response(self, data: dict, model: str, usage: Any) -> ToolAugmentedResponse:
        tool_calls: List[ToolCall] = []
        text_parts: List[str] = []
        if data.get("candidates"):
            parts = data["candidates"][0].get("content", {}).get("parts", [])
            for idx, part in enumerate(parts):
                if "functionCall" in part:
                    fc = part["functionCall"]
                    tool_calls.append(
                        ToolCall(
                            id=f"call_{idx}_{fc.get('name', 'unknown')}",
                            name=fc.get("name", ""),
                            arguments=fc.get("args", {}),
                        )
                    )
                elif "text" in part:
                    text_parts.append(part["text"])
        return ToolAugmentedResponse(
            text="\n".join(text_parts) if text_parts else None,
            tool_calls=tool_calls,
            provider="google",
            model=model,
            usage=usage,
        )
