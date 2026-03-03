from abc import ABC, abstractmethod
from typing import Optional

from app.models.llm_models import LLMRequest, LLMResponse
from app.models.tool_models import ToolAugmentedRequest, ToolAugmentedResponse


class LLMProviderInterface(ABC):
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url

    @abstractmethod
    async def generate_text(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError

    @abstractmethod
    def get_default_model(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def validate_request(self, request: LLMRequest) -> bool:
        raise NotImplementedError

    async def generate_with_tools(self, request: ToolAugmentedRequest) -> ToolAugmentedResponse:
        raise NotImplementedError(f"{self.__class__.__name__} does not support function calling")
