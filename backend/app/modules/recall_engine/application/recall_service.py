from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from app.models.recall_models import TopicTrackingItem
from app.repositories.session_repository import SessionRepository
from app.repositories.topic_repository import TopicRepository


class RecallService:
    def __init__(self, topic_repository: TopicRepository, session_repository: SessionRepository):
        self.topic_repository = topic_repository
        self.session_repository = session_repository

    def _compute_forgetting(self, days_since_last_seen: float, strength: float) -> float:
        base = min(1.0, days_since_last_seen / max(1.0, 14.0 * max(0.1, strength)))
        return round(base, 4)

    def _strengthen_recall(self, topic_id: int, current_state: Dict, observed_at: datetime) -> None:
        """Reinforce memory for a topic that was just observed."""
        repetitions = int(current_state.get("repetitions", 0)) + 1
        strength = min(1.0, float(current_state.get("strength", 0.5)) + 0.08)
        interval_days = max(1, int(round(2 ** min(repetitions, 6))))
        next_review_at = observed_at + timedelta(days=interval_days)
        forgetting_score = self._compute_forgetting(0.0, strength)
        self.topic_repository.upsert_recall_state(
            topic_id=topic_id,
            forgetting_score=forgetting_score,
            strength=strength,
            interval_days=interval_days,
            repetitions=repetitions,
            next_review_at=next_review_at,
            last_reviewed_at=observed_at,
        )

    def ingest_clustered_session(self, user_id: int, session_identifier: str, clusters: List[Dict]) -> None:
        session = self.session_repository.get_session_by_identifier(session_identifier)
        if not session:
            return
        session_id = session["id"]
        observed_at = datetime.fromisoformat(session["end_time"]) if isinstance(session["end_time"], str) else session["end_time"]

        # Preload existing topics+states for this user to avoid N+1 queries per cluster
        existing_topics: Dict[int, Dict] = {
            t["id"]: t for t in self.topic_repository.list_topics_with_state(user_id=user_id, limit=1000)
        }

        for cluster in clusters:
            # Only track clusters that represent learning / research / study activity
            if not cluster.get("is_learning"):
                continue

            topic_name = cluster.get("theme") or "Miscellaneous"
            topic_desc = cluster.get("summary") or ""
            cluster_embedding = cluster.get("embedding")

            # Semantic deduplication: reuse an existing topic if similar enough
            matched_existing = None
            if cluster_embedding:
                matched_existing = self.topic_repository.find_similar_topic(user_id, cluster_embedding)

            if matched_existing:
                topic_id = matched_existing["id"]
                # Refresh description/embedding with the latest cluster data
                self.topic_repository.get_or_create_topic(
                    user_id=user_id,
                    name=matched_existing["name"],
                    description=topic_desc or matched_existing.get("description"),
                    embedding=cluster_embedding or matched_existing.get("embedding"),
                )
            else:
                topic = self.topic_repository.get_or_create_topic(
                    user_id=user_id,
                    name=topic_name,
                    description=topic_desc,
                    embedding=cluster_embedding,
                )
                if not topic:
                    continue
                topic_id = topic["id"]

            item_count = len(cluster.get("items", []))
            importance = min(1.0, 0.3 + (item_count / 20.0))
            # cluster_id FK is nullable; we don't have the DB cluster row id from model_dump()
            self.topic_repository.add_observation(topic_id, session_id, observed_at, importance)

            current_state = existing_topics.get(topic_id, {}).get("recall_state") or {}
            self._strengthen_recall(topic_id, current_state, observed_at)
            self.topic_repository.create_recall_event(topic_id, "observed", {"session_identifier": session_identifier})

    def list_topics(self, user_id: int, due_only: bool = False) -> List[TopicTrackingItem]:
        now = datetime.now(timezone.utc)
        rows = (
            self.topic_repository.list_due_topics(user_id, now)
            if due_only
            else self.topic_repository.list_topics_with_state(user_id)
        )
        result: List[TopicTrackingItem] = []
        for row in rows:
            state = row.get("recall_state") or {}
            result.append(
                TopicTrackingItem(
                    topic_id=row["id"],
                    name=row["name"],
                    description=row.get("description"),
                    forgetting_score=float(state.get("forgetting_score", 0.0)),
                    strength=float(state.get("strength", 0.5)),
                    repetitions=int(state.get("repetitions", 0)),
                    next_review_at=state.get("next_review_at"),
                )
            )
        return result

    def recompute(self, user_id: int, topic_id: Optional[int] = None) -> int:
        rows = self.topic_repository.list_topics_with_state(user_id, limit=1000)
        updated = 0
        now = datetime.now(timezone.utc)
        for row in rows:
            if topic_id and row["id"] != topic_id:
                continue
            state = row.get("recall_state")
            if not state:
                continue
            last_reviewed = state.get("last_reviewed_at") or row.get("updated_at")
            if isinstance(last_reviewed, str):
                last_reviewed = datetime.fromisoformat(last_reviewed)
            if not last_reviewed:
                continue
            days_since = max(0.0, (now - last_reviewed).total_seconds() / 86400.0)
            strength = float(state.get("strength", 0.5))
            forgetting_score = self._compute_forgetting(days_since, strength)
            interval_days = int(state.get("interval_days", 1))
            repetitions = int(state.get("repetitions", 0))
            next_review_at = last_reviewed + timedelta(days=interval_days)
            self.topic_repository.upsert_recall_state(
                topic_id=row["id"],
                forgetting_score=forgetting_score,
                strength=strength,
                interval_days=interval_days,
                repetitions=repetitions,
                next_review_at=next_review_at,
                last_reviewed_at=last_reviewed,
            )
            updated += 1
        return updated
