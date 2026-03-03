import uuid
from datetime import datetime
from typing import List

from app.config import settings
from app.models.chat_models import ChatRequest, ChatResponse
from app.models.tool_models import ConversationMessage
from app.modules.assistant.infrastructure.langgraph_runtime import LangGraphChatRuntime
from app.modules.identity.application.user_use_case import UserUseCase


class ChatUseCase:
    def __init__(self, runtime: LangGraphChatRuntime, user_service: UserUseCase):
        self.runtime = runtime
        self.user_service = user_service

    def _build_messages(self, request: ChatRequest) -> List[ConversationMessage]:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        system_prompt = (
            "You are a helpful assistant for browsing history analysis. "
            f"Current date and time: {now}. "
            "Never invent browsing history and rely on tools for factual claims."
        )
        messages: List[ConversationMessage] = [ConversationMessage(role="system", content=system_prompt)]
        for msg in (request.history or [])[-settings.chat_history_limit:]:
            messages.append(ConversationMessage(role=msg.role, content=msg.content))
        messages.append(ConversationMessage(role="user", content=request.message))
        return messages

    async def process_message(self, request: ChatRequest) -> ChatResponse:
        conversation_id = request.conversation_id or str(uuid.uuid4())
        user_id = None
        if request.user_token:
            user = await self.user_service.get_user_from_token(request.user_token)
            if user:
                user_id = user["id"]

        result = await self.runtime.run(
            messages=self._build_messages(request),
            user_id=user_id,
            provider=request.provider,
        )
        return ChatResponse(
            response=result["text"],
            conversation_id=conversation_id,
            timestamp=datetime.now(),
            provider=result["provider"],
            model=result["model"],
            sources=result["sources"] or None,
        )
