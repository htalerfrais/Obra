import logging
from collections import defaultdict
from typing import Dict, List, Tuple

from app.config import settings
from app.models.chat_models import SearchFilters
from app.models.session_models import ClusterItem, ClusterResult
from app.monitoring import get_request_id, metrics
from app.modules.shared.infrastructure.embedding_client import EmbeddingClient
from app.repositories.search_repository import SearchRepository

logger = logging.getLogger(__name__)


class SearchUseCase:
    def __init__(self, search_repository: SearchRepository, embedding_client: EmbeddingClient):
        self.search_repository = search_repository
        self.embedding_client = embedding_client

    async def search(
        self,
        user_id: int,
        filters: SearchFilters,
        limit_clusters: int = settings.search_limit_clusters,
        limit_items_per_cluster: int = settings.search_limit_items_per_cluster,
    ) -> Tuple[List[ClusterResult], List[ClusterItem]]:
        query = (filters.query_text or "").strip()
        if query == "*":
            query = ""

        query_embedding = None
        if query:
            embeddings = await self.embedding_client.embed_texts([query])
            if embeddings and embeddings[0]:
                query_embedding = embeddings[0]

        has_filters = any([filters.date_from, filters.date_to, filters.title_contains, filters.domain_contains])
        if not query_embedding and not has_filters:
            return [], []

        cluster_dicts = []
        if query_embedding or filters.date_from or filters.date_to:
            cluster_dicts = self.search_repository.search_clusters(
                user_id=user_id,
                query_embedding=query_embedding,
                limit=limit_clusters,
                date_from=filters.date_from,
                date_to=filters.date_to,
            )
        clusters = [self._dict_to_cluster_result(c) for c in cluster_dicts]
        cluster_ids = [c.get("id") for c in cluster_dicts if c.get("id") is not None]
        fetch_limit = limit_items_per_cluster * settings.search_overfetch_multiplier

        all_item_dicts: List[Dict] = []
        if cluster_ids:
            for cluster_id in cluster_ids:
                cluster_items = self.search_repository.search_items(
                    user_id=user_id,
                    query_embedding=query_embedding,
                    cluster_ids=[cluster_id],
                    limit=fetch_limit,
                    date_from=filters.date_from,
                    date_to=filters.date_to,
                    title_contains=filters.title_contains,
                    domain_contains=filters.domain_contains,
                )
                all_item_dicts.extend(self._deduplicate_item_dicts(cluster_items, limit_items_per_cluster))
        else:
            fallback_limit = limit_items_per_cluster * limit_clusters
            all_item_dicts = self.search_repository.search_items(
                user_id=user_id,
                query_embedding=query_embedding,
                cluster_ids=None,
                limit=fallback_limit * settings.search_overfetch_multiplier,
                date_from=filters.date_from,
                date_to=filters.date_to,
                title_contains=filters.title_contains,
                domain_contains=filters.domain_contains,
            )
            all_item_dicts = self._deduplicate_item_dicts(all_item_dicts, fallback_limit)

        items = [self._dict_to_cluster_item(i) for i in all_item_dicts]
        items_by_cluster: Dict[int, List[ClusterItem]] = defaultdict(list)
        for item_dict, item in zip(all_item_dicts, items):
            cid = item_dict.get("cluster_id")
            if cid:
                items_by_cluster[cid].append(item)

        logger.info(
            "search_results_clusters",
            extra={
                "request_id": get_request_id(),
                "total_clusters": len(clusters),
                "total_items": len(items),
                "clusters_detail": [
                    {"cluster_id": c.get("id"), "theme": c.get("name"), "items_count": len(items_by_cluster.get(c.get("id"), []))}
                    for c in cluster_dicts
                ],
            },
        )
        metrics.record_search(clusters_found=len(clusters), items_found=len(items))
        return clusters, items

    @staticmethod
    def _deduplicate_item_dicts(item_dicts: List[Dict], limit: int) -> List[Dict]:
        seen = set()
        result = []
        for item in item_dicts:
            key = ((item.get("title") or "").strip().lower(), (item.get("domain") or "").strip().lower())
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
            if len(result) >= limit:
                break
        return result

    @staticmethod
    def _dict_to_cluster_result(cluster_dict: dict) -> ClusterResult:
        cluster_id = cluster_dict.get("id")
        return ClusterResult(
            cluster_id=f"cluster_{cluster_id}" if cluster_id is not None else "cluster_unknown",
            theme=cluster_dict.get("name") or "Untitled",
            summary=cluster_dict.get("description") or "",
            items=[],
            embedding=cluster_dict.get("embedding"),
        )

    @staticmethod
    def _dict_to_cluster_item(item_dict: dict) -> ClusterItem:
        raw_semantics = item_dict.get("raw_semantics") or {}
        return ClusterItem(
            url=item_dict.get("url") or "",
            title=item_dict.get("title") or "Untitled",
            visit_time=item_dict.get("visit_time"),
            url_hostname=item_dict.get("domain"),
            url_pathname_clean=raw_semantics.get("url_pathname_clean"),
            url_search_query=raw_semantics.get("url_search_query"),
            embedding=item_dict.get("embedding"),
        )
