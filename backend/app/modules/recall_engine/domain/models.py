from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class RecallState:
    topic_id: int
    forgetting_score: float
    strength: float
    next_review_at: Optional[datetime]
