from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app, container
from app.models.chat_models import ChatResponse
from app.models.quiz_models import GenerateQuizResponse, QuizQuestion, SubmitQuizResponse
from app.models.session_models import ClusterItem, ClusterResult, SessionClusteringResponse


client = TestClient(app)


def test_cluster_session_triggers_recall_ingest(monkeypatch):
    async def fake_get_user(_token):
        return {"id": 1}

    async def fake_cluster(_session, _user_id, force=False):
        return SessionClusteringResponse(
            session_identifier="u1:test",
            session_start_time=datetime.utcnow() - timedelta(minutes=10),
            session_end_time=datetime.utcnow(),
            clusters=[
                ClusterResult(
                    cluster_id="c1",
                    theme="Test",
                    summary="Test summary",
                    items=[
                        ClusterItem(
                            url="https://example.com",
                            title="Example",
                            visit_time=datetime.utcnow(),
                            url_hostname="example.com",
                        )
                    ],
                )
            ],
        )

    called = {"ingested": False}

    def fake_ingest(**kwargs):
        called["ingested"] = True

    monkeypatch.setattr(container.user_service, "get_user_from_token", fake_get_user)
    monkeypatch.setattr(container.session_intelligence_use_case, "cluster_session", fake_cluster)
    monkeypatch.setattr(container.recall_service, "ingest_clustered_session", fake_ingest)

    payload = {
        "user_token": "token",
        "session_identifier": "test",
        "start_time": datetime.utcnow().isoformat(),
        "end_time": datetime.utcnow().isoformat(),
        "items": [{"url": "https://example.com", "title": "Example", "visit_time": datetime.utcnow().isoformat()}],
    }
    response = client.post("/cluster-session", json=payload)
    assert response.status_code == 200
    assert called["ingested"] is True


def test_chat_contract(monkeypatch):
    async def fake_process(_request):
        return ChatResponse(
            response="hello",
            conversation_id="c1",
            timestamp=datetime.utcnow(),
            provider="google",
            model="x",
            sources=None,
        )

    monkeypatch.setattr(container.chat_use_case, "process_message", fake_process)
    response = client.post("/chat", json={"message": "hello", "provider": "google", "history": []})
    assert response.status_code == 200
    assert response.json()["response"] == "hello"


def test_quiz_generate_and_submit_contract(monkeypatch):
    async def fake_get_user(_token):
        return {"id": 1}

    async def fake_generate(**kwargs):
        return GenerateQuizResponse(
            quiz_set_id=42,
            title="Quiz - Topic",
            created_at=datetime.utcnow(),
            questions=[QuizQuestion(id=1, question="Q?", options=["A", "B"], answer="A")],
        )

    def fake_submit(**kwargs):
        return SubmitQuizResponse(attempt_id=100, score=1.0, total_items=1)

    monkeypatch.setattr(container.user_service, "get_user_from_token", fake_get_user)
    monkeypatch.setattr(container.learning_content_service, "generate_quiz", fake_generate)
    monkeypatch.setattr(container.learning_content_service, "submit_quiz", fake_submit)

    gen = client.post(
        "/quiz/generate",
        params={"user_token": "token"},
        json={"topic_name": "Topic", "question_count": 1},
    )
    assert gen.status_code == 200
    assert gen.json()["quiz_set_id"] == 42

    submit = client.post(
        "/quiz/42/submit",
        params={"user_token": "token"},
        json={"answers": [{"question_id": 1, "answer": "A"}]},
    )
    assert submit.status_code == 200
    assert submit.json()["score"] == 1.0
