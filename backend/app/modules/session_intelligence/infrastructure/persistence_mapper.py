from typing import Optional

from app.models.session_models import ClusterItem, ClusterResult, SessionClusteringResponse
from app.modules.session_intelligence.infrastructure.session_mapper import SessionMapper
from app.repositories.session_repository import SessionRepository


class SessionPersistenceMapper:
    def __init__(self, session_repository: SessionRepository):
        self.session_repository = session_repository

    def save(self, user_id: int, response: SessionClusteringResponse, replace_if_exists: bool = False) -> int:
        if replace_if_exists:
            self.session_repository.delete_session_by_identifier(response.session_identifier)

        session_dict = self.session_repository.create_session(
            user_id=user_id,
            session_identifier=response.session_identifier,
            start_time=response.session_start_time,
            end_time=response.session_end_time,
        )
        if not session_dict:
            raise ValueError("Failed to create session")
        session_id = session_dict["id"]

        for cluster in response.clusters:
            cluster_dict = self.session_repository.create_cluster(
                session_id=session_id,
                name=cluster.theme,
                description=cluster.summary,
                embedding=cluster.embedding or None,
            )
            if not cluster_dict:
                continue
            cluster_id = cluster_dict["id"]
            for item in cluster.items:
                self.session_repository.create_history_item(
                    cluster_id=cluster_id,
                    url=item.url,
                    title=item.title,
                    domain=item.url_hostname,
                    visit_time=item.visit_time,
                    raw_semantics={
                        "url_pathname_clean": item.url_pathname_clean,
                        "url_search_query": item.url_search_query,
                    },
                    embedding=item.embedding or None,
                )
        return session_id

    def load(self, session_identifier: str) -> Optional[SessionClusteringResponse]:
        graph = self.session_repository.get_session_graph(session_identifier)
        if not graph:
            return None
        return SessionMapper.to_clustering_response(graph)
