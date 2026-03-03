import logging
from typing import Optional

import httpx

from app.config import settings
from app.models.llm_models import LLMRequest, LLMResponse
from .base_provider import LLMProviderInterface

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProviderInterface):
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(api_key, base_url)
        self.base_url = base_url or settings.ollama_base_url

    def get_default_model(self) -> str:
        return "llama2"

    def validate_request(self, request: LLMRequest) -> bool:
        return request.provider == "ollama"

    async def generate_text(self, request: LLMRequest) -> LLMResponse:
        model = request.model or self.get_default_model()
        payload = {
            "model": model,
            "prompt": request.prompt,
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=settings.ollama_timeout,
            )
            response.raise_for_status()
            data = response.json()
        generated_text = data.get("response", "")
        return LLMResponse(
            generated_text=generated_text,
            provider="ollama",
            model=model,
            usage={"prompt_tokens": len(request.prompt.split()), "completion_tokens": len(generated_text.split())},
            metadata={"done": data.get("done")},
        )
