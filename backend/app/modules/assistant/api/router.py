from fastapi import APIRouter, HTTPException

from app.models.chat_models import ChatRequest, ChatResponse


def build_router(container) -> APIRouter:
    router = APIRouter(prefix="", tags=["assistant"])

    @router.post("/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest):
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        try:
            return await container.chat_use_case.process_message(request)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Chat failed: {str(exc)}")

    return router
