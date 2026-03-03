from typing import List, Optional

from app.models.session_models import ClusterItem, ClusterResult, SessionClusteringResponse


class SessionMapper:
    @staticmethod
    def to_clustering_response(session_graph: dict) -> Optional[SessionClusteringResponse]:
        if not session_graph:
            return None
        clusters_data = session_graph.get("clusters", [])
        clusters: List[ClusterResult] = []
        for cluster in clusters_data:
            items: List[ClusterItem] = []
            for item in cluster.get("items", []):
                raw_semantics = item.get("raw_semantics") or {}
                items.append(
                    ClusterItem(
                        url=item.get("url", ""),
                        title=item.get("title") or "Untitled",
                        visit_time=item.get("visit_time"),
                        url_hostname=item.get("domain"),
                        url_pathname_clean=raw_semantics.get("url_pathname_clean"),
                        url_search_query=raw_semantics.get("url_search_query"),
                        embedding=item.get("embedding"),
                    )
                )
            clusters.append(
                ClusterResult(
                    cluster_id=f"cluster_{cluster.get('id')}",
                    theme=cluster.get("name") or "Untitled",
                    summary=cluster.get("description") or "",
                    items=items,
                    embedding=cluster.get("embedding"),
                )
            )
        return SessionClusteringResponse(
            session_identifier=session_graph["session_identifier"],
            session_start_time=session_graph["start_time"],
            session_end_time=session_graph["end_time"],
            clusters=clusters,
        )
