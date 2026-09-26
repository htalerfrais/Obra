import math
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from app.modules.recall_engine.application.recall_service import RecallService, stability_days


def _service() -> RecallService:
    return RecallService(topic_repository=MagicMock(), session_repository=MagicMock())


def test_forgetting_is_zero_right_after_review():
    assert _service()._compute_forgetting(0.0, 0.5) == 0.0


def test_forgetting_follows_exponential_decay():
    strength = 0.5
    s = stability_days(strength)
    # At t = S, retention should be 1/e (Ebbinghaus), not 0 as with a linear model
    assert _service()._compute_forgetting(s, strength) == pytest.approx(1 - math.exp(-1), abs=1e-3)


def test_stronger_topics_are_forgotten_slower():
    service = _service()
    assert service._compute_forgetting(5.0, 0.9) < service._compute_forgetting(5.0, 0.3)


def test_list_topics_computes_forgetting_live():
    repo = MagicMock()
    last_reviewed = datetime.utcnow() - timedelta(days=7)
    repo.list_topics_with_state.return_value = [
        {
            "id": 1,
            "name": "Rust ownership",
            "recall_state": {
                "forgetting_score": 0.0,  # stale value stored at review time
                "strength": 0.5,
                "repetitions": 1,
                "last_reviewed_at": last_reviewed,
                "next_review_at": last_reviewed + timedelta(days=2),
            },
        }
    ]
    service = RecallService(topic_repository=repo, session_repository=MagicMock())

    [topic] = service.list_topics(user_id=1)

    assert topic.stability_days == stability_days(0.5)
    assert topic.forgetting_score == pytest.approx(1 - math.exp(-7 / stability_days(0.5)), abs=1e-3)
