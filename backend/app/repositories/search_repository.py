from datetime import datetime
from typing import Dict, List, Optional

from app.models.database_models import Cluster, HistoryItem, Session
from .base_repository import BaseRepository


class SearchRepository(BaseRepository):
    def search_clusters(
        self,
        user_id: int,
        query_embedding: Optional[List[float]],
        limit: int,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[Dict]:
        def operation(db):
            query = db.query(Cluster).join(Session).filter(Session.user_id == user_id)
            if date_from:
                query = query.filter(Session.end_time >= date_from)
            if date_to:
                query = query.filter(Session.start_time <= date_to)
            if query_embedding:
                query = query.filter(Cluster.embedding.isnot(None))
                query = query.order_by(Cluster.embedding.cosine_distance(query_embedding))
            else:
                query = query.order_by(Session.start_time.desc())
            return [self._to_dict(c) for c in query.limit(limit).all()]

        result = self._execute(operation, "Failed to search clusters")
        return result if isinstance(result, list) else []

    def search_items(
        self,
        user_id: int,
        query_embedding: Optional[List[float]],
        limit: int,
        cluster_ids: Optional[List[int]] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        title_contains: Optional[str] = None,
        domain_contains: Optional[str] = None,
    ) -> List[Dict]:
        def operation(db):
            query = db.query(HistoryItem).join(Cluster).join(Session).filter(Session.user_id == user_id)
            if query_embedding:
                query = query.filter(HistoryItem.embedding.isnot(None))
            if cluster_ids:
                query = query.filter(HistoryItem.cluster_id.in_(cluster_ids))
            if date_from:
                query = query.filter(HistoryItem.visit_time >= date_from)
            if date_to:
                query = query.filter(HistoryItem.visit_time <= date_to)
            if title_contains:
                query = query.filter(HistoryItem.title.ilike(f"%{title_contains}%"))
            if domain_contains:
                query = query.filter(HistoryItem.domain.ilike(f"%{domain_contains}%"))
            if query_embedding:
                query = query.order_by(HistoryItem.embedding.cosine_distance(query_embedding))
            else:
                query = query.order_by(HistoryItem.visit_time.desc())
            return [self._to_dict(i) for i in query.limit(limit).all()]

        result = self._execute(operation, "Failed to search items")
        return result if isinstance(result, list) else []
