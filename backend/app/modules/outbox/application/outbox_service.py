from typing import Any, Dict, Optional
import uuid

from app.modules.shared.ports import EventPublisherPort
from app.repositories.outbox_repository import OutboxRepository


class OutboxPublisher(EventPublisherPort):
    def __init__(self, outbox_repository: OutboxRepository):
        self.outbox_repository = outbox_repository

    def publish(
        self,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload: Dict[str, Any],
        event_version: int = 1,
        idempotency_key: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        dedup_key = idempotency_key or f"{aggregate_type}:{aggregate_id}:{event_type}:v{event_version}:{uuid.uuid4()}"
        return self.outbox_repository.enqueue(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            event_version=event_version,
            idempotency_key=dedup_key,
            payload=payload,
        )
