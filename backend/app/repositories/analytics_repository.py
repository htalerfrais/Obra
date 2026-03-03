from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import func

from app.models.database_models import Cluster, HistoryItem, Session
from .base_repository import BaseRepository


class AnalyticsRepository(BaseRepository):
    def get_user_browsing_stats(self, user_id: int) -> Optional[Dict]:
        def operation(db):
            session_count = db.query(func.count(Session.id)).filter(Session.user_id == user_id).scalar()
            cluster_count = db.query(func.count(Cluster.id)).join(Session).filter(Session.user_id == user_id).scalar()
            item_count = db.query(func.count(HistoryItem.id)).join(Cluster).join(Session).filter(Session.user_id == user_id).scalar()
            earliest = db.query(func.min(Session.start_time)).filter(Session.user_id == user_id).scalar()
            latest = db.query(func.max(Session.end_time)).filter(Session.user_id == user_id).scalar()
            return {
                "session_count": session_count or 0,
                "cluster_count": cluster_count or 0,
                "item_count": item_count or 0,
                "earliest_session": earliest.isoformat() if earliest else None,
                "latest_session": latest.isoformat() if latest else None,
            }

        return self._execute(operation, "Failed to get browsing stats")

    def get_top_domains(self, user_id: int, limit: int = 10) -> List[Dict]:
        def operation(db):
            rows = (
                db.query(HistoryItem.domain, func.count(HistoryItem.id).label("page_count"))
                .join(Cluster)
                .join(Session)
                .filter(Session.user_id == user_id)
                .filter(HistoryItem.domain.isnot(None))
                .group_by(HistoryItem.domain)
                .order_by(func.count(HistoryItem.id).desc())
                .limit(limit)
                .all()
            )
            return [{"domain": row[0], "count": row[1]} for row in rows]

        result = self._execute(operation, "Failed to get top domains")
        return result if isinstance(result, list) else []
