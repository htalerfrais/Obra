from datetime import datetime
from typing import Dict, List, Optional

from app.config import settings
from app.models.database_models import Topic, TopicObservation, TopicRecallState, RecallEvent
from .base_repository import BaseRepository


class TopicRepository(BaseRepository):
    def find_similar_topic(self, user_id: int, embedding: List[float], threshold: Optional[float] = None) -> Optional[Dict]:
        """Return the closest existing topic for this user if cosine similarity >= threshold, else None."""
        if threshold is None:
            threshold = settings.topic_similarity_threshold

        def operation(db):
            row = (
                db.query(Topic)
                .filter(Topic.user_id == user_id, Topic.embedding.isnot(None))
                .order_by(Topic.embedding.cosine_distance(embedding))
                .first()
            )
            if row is None:
                return None
            # pgvector cosine_distance returns 1 - cosine_similarity
            from sqlalchemy import text
            result = db.execute(
                text(
                    "SELECT 1 - (embedding <=> CAST(:emb AS vector)) AS similarity "
                    "FROM topics WHERE id = :tid"
                ),
                {"emb": str(embedding), "tid": row.id},
            ).fetchone()
            if result and result.similarity >= threshold:
                return self._to_dict(row)
            return None

        return self._execute(operation, "Failed to find similar topic")

    def get_or_create_topic(self, user_id: int, name: str, description: Optional[str] = None, embedding: Optional[list] = None) -> Optional[Dict]:
        def operation(db):
            topic = db.query(Topic).filter(Topic.user_id == user_id, Topic.name == name).first()
            if topic:
                if description:
                    topic.description = description
                if embedding:
                    topic.embedding = embedding
                db.add(topic)
                db.flush()
                db.refresh(topic)
                return self._to_dict(topic)
            topic = Topic(user_id=user_id, name=name, description=description, embedding=embedding)
            db.add(topic)
            db.flush()
            db.refresh(topic)
            return self._to_dict(topic)

        return self._execute(operation, "Failed to get/create topic")

    def add_observation(self, topic_id: int, session_id: int, observed_at: datetime, importance_score: float, cluster_id: Optional[int] = None) -> Optional[Dict]:
        def operation(db):
            obs = TopicObservation(
                topic_id=topic_id,
                session_id=session_id,
                cluster_id=cluster_id,
                observed_at=observed_at,
                importance_score=importance_score,
            )
            db.add(obs)
            db.flush()
            db.refresh(obs)
            return self._to_dict(obs)

        return self._execute(operation, "Failed to add topic observation")

    def upsert_recall_state(
        self,
        topic_id: int,
        forgetting_score: float,
        strength: float,
        interval_days: int,
        repetitions: int,
        next_review_at: Optional[datetime],
        last_reviewed_at: Optional[datetime] = None,
    ) -> Optional[Dict]:
        def operation(db):
            state = db.query(TopicRecallState).filter(TopicRecallState.topic_id == topic_id).first()
            if not state:
                state = TopicRecallState(topic_id=topic_id)
            state.forgetting_score = forgetting_score
            state.strength = strength
            state.interval_days = interval_days
            state.repetitions = repetitions
            state.next_review_at = next_review_at
            state.last_reviewed_at = last_reviewed_at
            db.add(state)
            db.flush()
            db.refresh(state)
            return self._to_dict(state)

        return self._execute(operation, "Failed to upsert recall state")

    def create_recall_event(self, topic_id: int, event_type: str, payload: Optional[dict] = None) -> Optional[Dict]:
        def operation(db):
            event = RecallEvent(topic_id=topic_id, event_type=event_type, payload=payload)
            db.add(event)
            db.flush()
            db.refresh(event)
            return self._to_dict(event)

        return self._execute(operation, "Failed to create recall event")

    def list_due_topics(self, user_id: int, now: datetime) -> List[Dict]:
        def operation(db):
            rows = (
                db.query(Topic, TopicRecallState)
                .join(TopicRecallState, TopicRecallState.topic_id == Topic.id)
                .filter(Topic.user_id == user_id)
                .filter(TopicRecallState.next_review_at.isnot(None))
                .filter(TopicRecallState.next_review_at <= now)
                .order_by(TopicRecallState.next_review_at.asc())
                .all()
            )
            result = []
            for topic, state in rows:
                topic_dict = self._to_dict(topic)
                topic_dict["recall_state"] = self._to_dict(state)
                result.append(topic_dict)
            return result

        result = self._execute(operation, "Failed to list due topics")
        return result if isinstance(result, list) else []

    def list_topics_with_state(self, user_id: int, limit: int = 100) -> List[Dict]:
        def operation(db):
            rows = (
                db.query(Topic, TopicRecallState)
                .outerjoin(TopicRecallState, TopicRecallState.topic_id == Topic.id)
                .filter(Topic.user_id == user_id)
                .order_by(Topic.updated_at.desc())
                .limit(limit)
                .all()
            )
            result = []
            for topic, state in rows:
                topic_dict = self._to_dict(topic)
                topic_dict["recall_state"] = self._to_dict(state) if state else None
                result.append(topic_dict)
            return result

        result = self._execute(operation, "Failed to list topics")
        return result if isinstance(result, list) else []
