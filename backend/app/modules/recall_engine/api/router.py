from fastapi import APIRouter, HTTPException, Query

from app.models.recall_models import TopicTrackingResponse, RecomputeRecallRequest


def build_router(container) -> APIRouter:
    router = APIRouter(prefix="/tracking", tags=["recall_engine"])

    @router.get("/topics", response_model=TopicTrackingResponse)
    async def list_tracked_topics(
        user_token: str = Query(..., description="Google OAuth token"),
        due_only: bool = Query(False, description="Return only topics due for review"),
    ):
        user = await container.user_service.get_user_from_token(user_token)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        topics = container.recall_service.list_topics(user["id"], due_only=due_only)
        return TopicTrackingResponse(topics=topics)

    @router.post("/recompute")
    async def recompute_tracking(request: RecomputeRecallRequest, user_token: str = Query(...)):
        user = await container.user_service.get_user_from_token(user_token)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        updated = container.recall_service.recompute(user["id"], request.topic_id)
        return {"updated": updated}

    return router
