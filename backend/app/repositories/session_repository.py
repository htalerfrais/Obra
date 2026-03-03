from typing import Dict, List, Optional
from datetime import datetime

from sqlalchemy.orm import joinedload

from app.models.database_models import Session, Cluster, HistoryItem
from .base_repository import BaseRepository


class SessionRepository(BaseRepository):
    def get_session_by_identifier(self, session_identifier: str) -> Optional[Dict]:
        def operation(db):
            session = db.query(Session).filter(Session.session_identifier == session_identifier).first()
            return self._to_dict(session) if session else None
        return self._execute(operation, "Failed to get session by identifier")

    def create_session(self, user_id: int, session_identifier: str, start_time: datetime, end_time: datetime) -> Optional[Dict]:
        def operation(db):
            session = Session(
                user_id=user_id,
                session_identifier=session_identifier,
                start_time=start_time,
                end_time=end_time,
            )
            db.add(session)
            db.flush()
            db.refresh(session)
            return self._to_dict(session)
        return self._execute(operation, "Failed to create session")

    def delete_session_by_identifier(self, session_identifier: str) -> bool:
        def operation(db):
            session = db.query(Session).filter(Session.session_identifier == session_identifier).first()
            if not session:
                return False
            db.delete(session)
            return True
        result = self._execute(operation, "Failed to delete session")
        return bool(result)

    def create_cluster(self, session_id: int, name: str, description: Optional[str], embedding: Optional[list]) -> Optional[Dict]:
        def operation(db):
            cluster = Cluster(
                session_id=session_id,
                name=name,
                description=description,
                embedding=embedding,
            )
            db.add(cluster)
            db.flush()
            db.refresh(cluster)
            return self._to_dict(cluster)
        return self._execute(operation, "Failed to create cluster")

    def create_history_item(
        self,
        cluster_id: int,
        url: str,
        title: Optional[str],
        domain: Optional[str],
        visit_time: datetime,
        raw_semantics: Optional[dict],
        embedding: Optional[list],
    ) -> Optional[Dict]:
        def operation(db):
            item = HistoryItem(
                cluster_id=cluster_id,
                url=url,
                title=title,
                domain=domain,
                visit_time=visit_time,
                raw_semantics=raw_semantics,
                embedding=embedding,
            )
            db.add(item)
            db.flush()
            db.refresh(item)
            return self._to_dict(item)
        return self._execute(operation, "Failed to create history item")

    def get_session_graph(self, session_identifier: str) -> Optional[Dict]:
        def operation(db):
            session = (
                db.query(Session)
                .options(joinedload(Session.clusters).joinedload(Cluster.history_items))
                .filter(Session.session_identifier == session_identifier)
                .first()
            )
            if not session:
                return None
            session_dict = self._to_dict(session)
            clusters = []
            for cluster in session.clusters:
                cluster_dict = self._to_dict(cluster)
                cluster_dict["items"] = [self._to_dict(item) for item in cluster.history_items]
                clusters.append(cluster_dict)
            session_dict["clusters"] = clusters
            return session_dict
        return self._execute(operation, "Failed to load session graph")

    def get_session_by_id(self, session_id: int) -> Optional[Dict]:
        def operation(db):
            session = db.query(Session).filter(Session.id == session_id).first()
            return self._to_dict(session) if session else None
        return self._execute(operation, "Failed to get session by id")

    def get_sessions_by_user(
        self,
        user_id: int,
        limit: int = 10,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[Dict]:
        def operation(db):
            query = db.query(Session).filter(Session.user_id == user_id)
            if date_from:
                query = query.filter(Session.end_time >= date_from)
            if date_to:
                query = query.filter(Session.start_time <= date_to)
            rows = query.order_by(Session.start_time.desc()).limit(limit).all()
            result = []
            for session in rows:
                session_dict = self._to_dict(session)
                clusters = db.query(Cluster.name).filter(Cluster.session_id == session.id).all()
                session_dict["cluster_names"] = [c[0] for c in clusters]
                result.append(session_dict)
            return result
        result = self._execute(operation, "Failed to list sessions")
        return result if isinstance(result, list) else []
