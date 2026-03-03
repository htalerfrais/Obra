from dataclasses import dataclass
from typing import List, Optional


@dataclass
class TopicCluster:
    cluster_id: str
    theme: str
    summary: str
    item_count: int
    embedding: Optional[List[float]] = None
