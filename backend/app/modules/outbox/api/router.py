from fastapi import APIRouter

from app.modules.outbox.application.outbox_worker import OutboxWorker


def build_router(container) -> APIRouter:
    router = APIRouter(prefix="/workers", tags=["outbox"])

    @router.post("/outbox/run")
    async def run_outbox_worker(batch_size: int = 20):
        worker = OutboxWorker(
            outbox_repository=container.outbox_repository,
            handlers=container.outbox_handlers,
        )
        processed = worker.run_once(batch_size=batch_size)
        return {"processed": processed}

    return router
