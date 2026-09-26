import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from app.models.quiz_models import QuizAnswerItem, SubmitQuizRequest
from app.modules.learning_content.application.learning_content_service import LearningContentService
from app.modules.learning_content.domain.models import QuizNotFoundError
from app.modules.recall_engine.application.recall_service import RecallService


REVIEWED_AT = datetime(2026, 9, 1, 12, 0, 0)


def _recall_service(state):
    repo = MagicMock()
    repo.get_topic_with_state.return_value = {"id": 7, "name": "Rust", "recall_state": state}
    return RecallService(topic_repository=repo, session_repository=MagicMock()), repo


def test_passed_quiz_strengthens_and_spaces_review():
    service, repo = _recall_service({"strength": 0.5, "repetitions": 2})

    outcome = service.record_quiz_review(user_id=1, topic_id=7, score=0.8, reviewed_at=REVIEWED_AT)

    assert outcome.strength > 0.5
    assert outcome.interval_days == 8  # 2^3 after the third successful repetition
    assert outcome.next_review_at == REVIEWED_AT + timedelta(days=8)
    state_kwargs = repo.upsert_recall_state.call_args.kwargs
    assert state_kwargs["repetitions"] == 3
    assert state_kwargs["last_reviewed_at"] == REVIEWED_AT
    event_type, payload = repo.create_recall_event.call_args.args[1:]
    assert event_type == "quiz"
    assert payload["score"] == 0.8


def test_failed_quiz_weakens_and_reviews_tomorrow():
    service, repo = _recall_service({"strength": 0.5, "repetitions": 4})

    outcome = service.record_quiz_review(user_id=1, topic_id=7, score=0.2, reviewed_at=REVIEWED_AT)

    assert outcome.strength < 0.5
    assert outcome.interval_days == 1
    assert repo.upsert_recall_state.call_args.kwargs["repetitions"] == 0


def test_quiz_review_ignores_foreign_topic():
    service, repo = _recall_service(None)
    repo.get_topic_with_state.return_value = None

    assert service.record_quiz_review(user_id=1, topic_id=7, score=1.0, reviewed_at=REVIEWED_AT) is None
    repo.upsert_recall_state.assert_not_called()


def _learning_service(quiz_set, recall_service=None):
    learning_repo = MagicMock()
    learning_repo.get_quiz_set_with_items.return_value = quiz_set
    learning_repo.create_attempt.return_value = {"id": 100}
    return LearningContentService(
        llm_service=MagicMock(),
        learning_repository=learning_repo,
        topic_repository=MagicMock(),
        recall_service=recall_service or MagicMock(),
    )


QUIZ_SET = {
    "id": 42,
    "user_id": 1,
    "topic_id": 7,
    "items": [
        {"id": 1, "answer": "Borrow checker"},
        {"id": 2, "answer": "Ownership"},
    ],
}


def test_submit_scores_and_updates_topic_recall():
    recall = MagicMock()
    recall.record_quiz_review.return_value = MagicMock(interval_days=4, next_review_at=REVIEWED_AT)
    service = _learning_service(QUIZ_SET, recall)

    result = service.submit_quiz(
        user_id=1,
        quiz_set_id=42,
        payload=SubmitQuizRequest(answers=[
            QuizAnswerItem(question_id=1, answer="borrow checker"),
            QuizAnswerItem(question_id=2, answer="Lifetimes"),
        ]),
    )

    assert result.score == 0.5
    assert [r.is_correct for r in result.results] == [True, False]
    assert result.results[1].correct_answer == "Ownership"
    assert result.interval_days == 4
    assert recall.record_quiz_review.call_args.kwargs["score"] == 0.5


def test_submit_rejects_other_users_quiz():
    service = _learning_service({**QUIZ_SET, "user_id": 2})

    with pytest.raises(QuizNotFoundError):
        service.submit_quiz(user_id=1, quiz_set_id=42, payload=SubmitQuizRequest(answers=[]))


def test_parse_drops_questions_whose_answer_is_not_an_option():
    service = _learning_service(QUIZ_SET)
    raw = "Here you go:\n" + json.dumps([
        {"question": "Q1?", "answer": "B", "options": ["A", "B", "C", "D"], "difficulty": "easy"},
        {"question": "Q2?", "answer": "Z", "options": ["A", "B", "C", "D"]},
    ])

    questions = service._parse_questions(raw, question_count=5)

    assert len(questions) == 1
    assert questions[0].answer == "B"
    assert sorted(questions[0].options) == ["A", "B", "C", "D"]


def test_parse_returns_nothing_on_garbage():
    assert _learning_service(QUIZ_SET)._parse_questions("sorry, I can't", question_count=5) == []
