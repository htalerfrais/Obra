from typing import Optional

from app.models.session_models import HistorySession, SessionClusteringResponse
from app.modules.shared.ports import EventPublisherPort
from app.modules.session_intelligence.infrastructure.clustering_engine import ClusteringEngine


class SessionIntelligenceUseCase:
    """
    Application-level orchestration for session clustering.
    Keeps API compatibility while isolating event publication and orchestration.
    """

    def __init__(self, clustering_engine: ClusteringEngine, event_publisher: Optional[EventPublisherPort] = None):
        self.clustering_engine = clustering_engine
        self.event_publisher = event_publisher

    async def cluster_session(self, session: HistorySession, user_id: int, force: bool = False) -> SessionClusteringResponse:
        response = await self.clustering_engine.cluster_session(session, user_id, force=force)
        if self.event_publisher:
            self.event_publisher.publish(
                aggregate_type="session",
                aggregate_id=response.session_identifier,
                event_type="SessionClustered",
                payload={
                    "user_id": user_id,
                    "session_identifier": response.session_identifier,
                    "cluster_count": len(response.clusters),
                },
                event_version=1,
                idempotency_key=f"session:{response.session_identifier}:clustered:v1",
            )
        return response
