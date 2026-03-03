from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.models.session_models import HistorySession, SessionClusteringResponse


def build_router(container) -> APIRouter:
    router = APIRouter(prefix="", tags=["session_intelligence"])

    @router.post("/cluster-session", response_model=SessionClusteringResponse)
    async def cluster_session(session: HistorySession, force: bool = False):
        if not session.items:
            raise HTTPException(status_code=400, detail="Session has no items to cluster")
        if not session.user_token:
            raise HTTPException(status_code=401, detail="Missing user_token")

        user_dict = await container.user_service.get_user_from_token(session.user_token)
        if not user_dict:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        user_id = user_dict["id"]
        if not force:
            now = datetime.now(timezone.utc)
            end_time = session.end_time
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=timezone.utc)
            force = (now - end_time) <= timedelta(minutes=settings.current_session_gap_minutes)

        session_result = await container.session_intelligence_use_case.cluster_session(
            session,
            user_id,
            force=force,
        )
        container.recall_service.ingest_clustered_session(
            user_id=user_id,
            session_identifier=session_result.session_identifier,
            clusters=[c.model_dump() for c in session_result.clusters],
        )
        return session_result

    return router
