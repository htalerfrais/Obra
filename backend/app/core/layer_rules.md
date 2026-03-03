# Layer dependency rules

## Canonical module layout

Each module under `app/modules/<module_name>/` follows:

- `domain/`: business entities and rules only
- `application/`: use-cases and orchestration
- `infrastructure/`: adapters for DB/LLM/HTTP/broker
- `api/`: FastAPI routers and request/response contract mapping

## Import constraints

1. `domain` MUST NOT import:
   - `fastapi`
   - `sqlalchemy`
   - `httpx`
   - `langchain` / `langgraph`
2. `application` MUST NOT import framework web modules (`fastapi`) directly.
3. `api` can import `application` and models.
4. `main.py` only bootstraps app and includes routers.
5. Cross-module interactions should happen through use-cases or shared ports.

## Route -> use-case mapping

| Route | Module | Use case |
|---|---|---|
| `POST /cluster-session` | `session_intelligence` | `SessionIntelligenceUseCase.cluster_session` |
| `POST /chat` | `assistant` | `ChatUseCase.process_message` |
| `GET /tracking/topics` | `recall_engine` | `RecallService.list_topics` |
| `POST /tracking/recompute` | `recall_engine` | `RecallService.recompute` |
| `POST /quiz/generate` | `learning_content` | `LearningContentService.generate_quiz` |
| `POST /quiz/{quiz_set_id}/submit` | `learning_content` | `LearningContentService.submit_quiz` |
| `POST /workers/outbox/run` | `outbox` | `OutboxWorker.run_once` |
