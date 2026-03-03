from typing import Callable, Dict
import logging

from app.repositories.outbox_repository import OutboxRepository

logger = logging.getLogger(__name__)


class OutboxWorker:
    def __init__(self, outbox_repository: OutboxRepository, handlers: Dict[str, Callable[[dict], None]]):
        self.outbox_repository = outbox_repository
        self.handlers = handlers

    def run_once(self, batch_size: int = 20) -> int:
        processed = 0
        events = self.outbox_repository.claim_pending(batch_size=batch_size)
        for event in events:
            event_id = event["id"]
            event_type = event["event_type"]
            event_version = int(event.get("event_version", 1))
            payload = event["payload"]
            handler = self.handlers.get(f"{event_type}.v{event_version}") or self.handlers.get(event_type)
            if not handler:
                self.outbox_repository.mark_failed(event_id, f"No handler for event_type={event_type}.v{event_version}")
                continue
            try:
                handler(payload)
                self.outbox_repository.mark_sent(event_id)
                processed += 1
            except Exception as exc:
                logger.exception("Outbox handler failed for event_id=%s", event_id)
                self.outbox_repository.mark_failed(event_id, str(exc))
        return processed
