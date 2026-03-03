from datetime import datetime
from typing import Dict, List, Optional

from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.session_repository import SessionRepository


class BrowsingQueryUseCase:
    def __init__(self, session_repository: SessionRepository, analytics_repository: AnalyticsRepository):
        self.session_repository = session_repository
        self.analytics_repository = analytics_repository

    def list_sessions(
        self,
        user_id: int,
        limit: int = 10,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[Dict]:
        return self.session_repository.get_sessions_by_user(
            user_id=user_id,
            limit=limit,
            date_from=date_from,
            date_to=date_to,
        )

    def get_stats(self, user_id: int, top_domains_limit: int = 10) -> Dict:
        return {
            "stats": self.analytics_repository.get_user_browsing_stats(user_id),
            "top_domains": self.analytics_repository.get_top_domains(user_id, limit=top_domains_limit),
        }
