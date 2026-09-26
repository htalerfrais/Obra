import math
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Dict, List, Optional

from app.models.recall_models import TopicTrackingItem, RecallHistoryEvent, TopicHistoryResponse
from app.modules.recall_engine.domain.models import QuizReviewOutcome

if TYPE_CHECKING:
    from app.repositories.session_repository import SessionRepository
    from app.repositories.topic_repository import TopicRepository


# Days of memory stability for a topic at full strength (strength=1.0).
BASE_STABILITY_DAYS = 14.0
# Minimum quiz score (0-1) that counts as a successful recall.
QUIZ_PASS_SCORE = 0.6


def stability_days(strength: float) -> float:
    return round(BASE_STABILITY_DAYS * max(0.1, strength), 4)


class RecallService:
    def __init__(self, topic_repository: "TopicRepository", session_repository: "SessionRepository"):
        self.topic_repository = topic_repository
        self.session_repository = session_repository

    def _compute_forgetting(self, days_since_last_seen: float, strength: float) -> float:
        """Ebbinghaus curve: retention R = exp(-t / S), forgetting = 1 - R."""
        retention = math.exp(-max(0.0, days_since_last_seen) / stability_days(strength))
        return round(1.0 - retention, 4)

    def _coerce_utc_naive(self, value: Optional[datetime]) -> Optional[datetime]:
        """
        Normalize datetimes to UTC-naive values for safe arithmetic/storage.
        The DB schema uses timezone-naive DateTime columns.
        """
        if value is None:
            return None
        if isinstance(value, str):
            # Accept both ISO strings with offset and trailing "Z".
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if not isinstance(value, datetime):
            return None
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

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
        observed_at = self._coerce_utc_naive(session.get("end_time"))
        if not observed_at:
            return

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
            cluster_db_id = cluster.get("id")
            self.topic_repository.add_observation(topic_id, session_id, observed_at, importance, cluster_id=cluster_db_id)

            current_state = existing_topics.get(topic_id, {}).get("recall_state") or {}
            self._strengthen_recall(topic_id, current_state, observed_at)

            # Snapshot strength post-reinforcement so history can reconstruct the curve
            post_strength = min(1.0, float(current_state.get("strength", 0.5)) + 0.08)
            self.topic_repository.create_recall_event(topic_id, "observed", {
                "session_identifier": session_identifier,
                "strength": post_strength,
                "forgetting_score": 0.0,
            })

    def record_quiz_review(self, user_id: int, topic_id: int, score: float, reviewed_at: datetime) -> Optional[QuizReviewOutcome]:
        """
        Update a topic's memory after a quiz (active recall, SM-2 style):
        a passed quiz strengthens the topic and spaces the next review further out,
        a failed one weakens it and brings the review back to tomorrow.
        """
        topic = self.topic_repository.get_topic_with_state(user_id, topic_id)
        if not topic:
            return None
        state = topic.get("recall_state") or {}
        strength = float(state.get("strength", 0.5))
        repetitions = int(state.get("repetitions", 0))
        score = min(1.0, max(0.0, score))

        if score >= QUIZ_PASS_SCORE:
            repetitions += 1
            strength = min(1.0, strength + 0.1 + 0.1 * score)
            interval_days = max(1, int(round(2 ** min(repetitions, 6))))
        else:
            repetitions = 0
            strength = max(0.1, strength - 0.15 * (1.0 - score))
            interval_days = 1

        reviewed_at = self._coerce_utc_naive(reviewed_at)
        next_review_at = reviewed_at + timedelta(days=interval_days)
        self.topic_repository.upsert_recall_state(
            topic_id=topic_id,
            forgetting_score=0.0,
            strength=strength,
            interval_days=interval_days,
            repetitions=repetitions,
            next_review_at=next_review_at,
            last_reviewed_at=reviewed_at,
        )
        self.topic_repository.create_recall_event(topic_id, "quiz", {
            "strength": strength,
            "forgetting_score": 0.0,
            "score": score,
        })
        return QuizReviewOutcome(
            strength=strength,
            interval_days=interval_days,
            next_review_at=next_review_at,
        )

    def list_topics(self, user_id: int, due_only: bool = False) -> List[TopicTrackingItem]:
        now = datetime.utcnow()
        rows = (
            self.topic_repository.list_due_topics(user_id, now)
            if due_only
            else self.topic_repository.list_topics_with_state(user_id)
        )
        result: List[TopicTrackingItem] = []
        for row in rows:
            state = row.get("recall_state") or {}
            strength = float(state.get("strength", 0.5))
            # Compute forgetting live so the list never shows a stale score between recomputes
            last_reviewed = self._coerce_utc_naive(state.get("last_reviewed_at"))
            if last_reviewed:
                days_since = (now - last_reviewed).total_seconds() / 86400.0
                forgetting_score = self._compute_forgetting(days_since, strength)
            else:
                forgetting_score = float(state.get("forgetting_score", 0.0))
            result.append(
                TopicTrackingItem(
                    topic_id=row["id"],
                    name=row["name"],
                    description=row.get("description"),
                    forgetting_score=forgetting_score,
                    strength=strength,
                    stability_days=stability_days(strength),
                    repetitions=int(state.get("repetitions", 0)),
                    next_review_at=state.get("next_review_at"),
                    last_reviewed_at=state.get("last_reviewed_at"),
                )
            )
        return result

    def recompute(self, user_id: int, topic_id: Optional[int] = None) -> int:
        rows = self.topic_repository.list_topics_with_state(user_id, limit=1000)
        updated = 0
        now = datetime.utcnow()
        for row in rows:
            if topic_id and row["id"] != topic_id:
                continue
            state = row.get("recall_state")
            if not state:
                continue
            last_reviewed = self._coerce_utc_naive(state.get("last_reviewed_at") or row.get("updated_at"))
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

    def get_topic_history(self, topic_id: int) -> TopicHistoryResponse:
        events = self.topic_repository.get_recall_events(topic_id)
        history: List[RecallHistoryEvent] = []
        for e in events:
            payload = e.get("payload") or {}
            strength = float(payload.get("strength", 0.5))
            forgetting_score = float(payload.get("forgetting_score", 0.0))
            history.append(RecallHistoryEvent(
                event_time=e["event_time"],
                event_type=e["event_type"],
                strength=strength,
                stability_days=stability_days(strength),
                forgetting_score=forgetting_score,
                session_identifier=payload.get("session_identifier"),
                score=payload.get("score"),
            ))
        return TopicHistoryResponse(topic_id=topic_id, events=history)
