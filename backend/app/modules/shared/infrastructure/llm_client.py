from typing import Dict
import logging

from app.models.llm_models import LLMRequest, LLMResponse
from app.models.tool_models import ToolAugmentedRequest, ToolAugmentedResponse
from app.monitoring import track_llm_call
from app.modules.shared.infrastructure.providers.anthropic_provider import AnthropicProvider
from app.modules.shared.infrastructure.providers.google_provider import GoogleProvider
from app.modules.shared.infrastructure.providers.ollama_provider import OllamaProvider
from app.modules.shared.infrastructure.providers.openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self):
        self.providers: Dict[str, object] = {}
        self._initialize_providers()

    def _initialize_providers(self):
        for provider_name, provider_class in (
            ("openai", OpenAIProvider),
            ("anthropic", AnthropicProvider),
            ("ollama", OllamaProvider),
            ("google", GoogleProvider),
        ):
            try:
                self.providers[provider_name] = provider_class()
            except Exception as exc:
                logger.warning("Failed to initialize %s provider: %s", provider_name, str(exc))

    @track_llm_call
    async def generate_text(self, request: LLMRequest) -> LLMResponse:
        if request.provider not in self.providers:
            raise ValueError(f"Provider {request.provider} not available. Available providers: {list(self.providers.keys())}")
        return await self.providers[request.provider].generate_text(request)

    @track_llm_call
    async def generate_with_tools(self, request: ToolAugmentedRequest) -> ToolAugmentedResponse:
        if request.provider not in self.providers:
            raise ValueError(f"Provider {request.provider} not available. Available providers: {list(self.providers.keys())}")
        return await self.providers[request.provider].generate_with_tools(request)
