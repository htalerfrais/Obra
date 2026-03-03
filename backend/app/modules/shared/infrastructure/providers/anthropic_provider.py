import os
import httpx
from typing import Optional
import logging

from app.models.llm_models import LLMRequest, LLMResponse
from .base_provider import LLMProviderInterface

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProviderInterface):
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(api_key, base_url)
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.base_url = base_url or "https://api.anthropic.com/v1"

    def get_default_model(self) -> str:
        return "claude-3-sonnet-20240229"

    def validate_request(self, request: LLMRequest) -> bool:
        return request.provider == "anthropic"

    async def generate_text(self, request: LLMRequest) -> LLMResponse:
        if not self.api_key:
            raise ValueError("Anthropic API key is required")
        model = request.model or self.get_default_model()
        payload = {
            "model": model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": [{"role": "user", "content": request.prompt}],
        }
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/messages", json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
            data = response.json()
        return LLMResponse(
            generated_text=data["content"][0]["text"],
            provider="anthropic",
            model=model,
            usage=data.get("usage"),
            metadata={"response_id": data.get("id")},
        )
