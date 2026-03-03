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


class TopicTrackingResponse(BaseModel):
    topics: List[TopicTrackingItem]


class RecomputeRecallRequest(BaseModel):
    topic_id: Optional[int] = None
