from app.core.container import build_container
from app.modules.outbox.application.outbox_worker import OutboxWorker


def main() -> None:
    container = build_container()
    worker = OutboxWorker(
        outbox_repository=container.outbox_repository,
        handlers=container.outbox_handlers,
    )
    processed = worker.run_once(batch_size=50)
    print(f"Processed {processed} outbox event(s)")


if __name__ == "__main__":
    main()
