from datetime import datetime
from typing import Dict, List, Optional

from app.models.database_models import OutboxEvent
from .base_repository import BaseRepository


class OutboxRepository(BaseRepository):
    def enqueue(
        self,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload: dict,
        event_version: int = 1,
        idempotency_key: Optional[str] = None,
    ) -> Optional[Dict]:
        def operation(db):
            existing = None
            if idempotency_key:
                existing = db.query(OutboxEvent).filter(OutboxEvent.idempotency_key == idempotency_key).first()
            if existing:
                return self._to_dict(existing)
            event = OutboxEvent(
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                event_type=event_type,
                event_version=event_version,
                idempotency_key=idempotency_key or f"{aggregate_type}:{aggregate_id}:{event_type}:{datetime.utcnow().isoformat()}",
                payload=payload,
                status="pending",
            )
            db.add(event)
            db.flush()
            db.refresh(event)
            return self._to_dict(event)
        return self._execute(operation, "Failed to enqueue outbox event")

    def claim_pending(self, batch_size: int = 50) -> List[Dict]:
        def operation(db):
            events = (
                db.query(OutboxEvent)
                .filter(OutboxEvent.status == "pending")
                .order_by(OutboxEvent.created_at.asc())
                .limit(batch_size)
                .all()
            )
            for event in events:
                event.status = "processing"
                db.add(event)
            db.flush()
            return [self._to_dict(e) for e in events]
        result = self._execute(operation, "Failed to claim outbox events")
        return result if isinstance(result, list) else []

    def mark_sent(self, event_id: int) -> bool:
        def operation(db):
            event = db.query(OutboxEvent).filter(OutboxEvent.id == event_id).first()
            if not event:
                return False
            event.status = "sent"
            event.published_at = datetime.utcnow()
            db.add(event)
            return True
        return bool(self._execute(operation, "Failed to mark event as sent"))

    def mark_failed(self, event_id: int, error: str) -> bool:
        def operation(db):
            event = db.query(OutboxEvent).filter(OutboxEvent.id == event_id).first()
            if not event:
                return False
            event.status = "failed"
            event.retries = (event.retries or 0) + 1
            event.last_error = error[:5000]
            db.add(event)
            return True
        return bool(self._execute(operation, "Failed to mark event as failed"))

    def requeue_failed(self, max_retries: int = 5) -> int:
        def operation(db):
            events = (
                db.query(OutboxEvent)
                .filter(OutboxEvent.status == "failed")
                .filter(OutboxEvent.retries < max_retries)
                .all()
            )
            for event in events:
                event.status = "pending"
                db.add(event)
            return len(events)
        result = self._execute(operation, "Failed to requeue failed events")
        return int(result) if isinstance(result, int) else 0
