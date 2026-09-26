from fastapi import APIRouter, HTTPException, Query

from app.models.quiz_models import (
    GenerateQuizRequest,
    GenerateQuizResponse,
    SubmitQuizRequest,
    SubmitQuizResponse,
)
from app.modules.learning_content.domain.models import QuizGenerationError, QuizNotFoundError


def build_router(container) -> APIRouter:
    router = APIRouter(prefix="/quiz", tags=["learning_content"])

    @router.post("/generate", response_model=GenerateQuizResponse)
    async def generate_quiz(request: GenerateQuizRequest, user_token: str = Query(...)):
        user = await container.user_service.get_user_from_token(user_token)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        try:
            return await container.learning_content_service.generate_quiz(
                user_id=user["id"],
                topic_id=request.topic_id,
                topic_name=request.topic_name,
                question_count=request.question_count,
            )
        except QuizNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except QuizGenerationError as exc:
            raise HTTPException(status_code=502, detail=str(exc))

    @router.post("/{quiz_set_id}/submit", response_model=SubmitQuizResponse)
    async def submit_quiz(quiz_set_id: int, request: SubmitQuizRequest, user_token: str = Query(...)):
        user = await container.user_service.get_user_from_token(user_token)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        try:
            return container.learning_content_service.submit_quiz(
                user_id=user["id"],
                quiz_set_id=quiz_set_id,
                payload=request,
            )
        except QuizNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    return router
