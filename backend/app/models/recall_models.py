from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class TopicTrackingItem(BaseModel):
    topic_id: int
    name: str
    description: Optional[str] = None
    forgetting_score: float = 0.0
    strength: float = 0.5
    repetitions: int = 0
    next_review_at: Optional[datetime] = None
    last_reviewed_at: Optional[datetime] = None


class TopicTrackingResponse(BaseModel):
    topics: List[TopicTrackingItem]


class RecomputeRecallRequest(BaseModel):
    topic_id: Optional[int] = None


class RecallHistoryEvent(BaseModel):
    event_time: datetime
    event_type: str
    strength: float
    forgetting_score: float
    session_identifier: Optional[str] = None


class TopicHistoryResponse(BaseModel):
    topic_id: int
    events: List[RecallHistoryEvent]
