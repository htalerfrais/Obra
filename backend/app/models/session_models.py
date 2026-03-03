from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class HistoryItem(BaseModel):
    """Individual browsing history item"""
    url: str
    title: str
    visit_time: datetime
    # Optional enriched URL features from the extension
    url_hostname: Optional[str] = None
    url_pathname_clean: Optional[str] = None
    url_search_query: Optional[str] = None


class SemanticGroup(BaseModel):
    """
    A group of HistoryItems sharing the same title + hostname.
    Used for compression during clustering to reduce embedding calls and LLM tokens.
    """
    group_key: str  # "title::hostname" used for grouping
    title: str
    hostname: str
    item_count: int
    # Representative example for LLM context
    example_visit_time: datetime
    example_pathname_clean: Optional[str] = None
    # All items in this group (for decompression)
    items: List[HistoryItem]
    # Embedding computed once for the group
    embedding: Optional[List[float]] = None


class HistorySession(BaseModel):
    """A session of browsing history items grouped by time"""
    user_token: str  # Google OAuth token - validated server-side to get user identity
    session_identifier: str
    start_time: datetime
    end_time: datetime
    items: List[HistoryItem]
    duration_minutes: Optional[int] = None
    
    def model_post_init(self, __context):
        if self.duration_minutes is None:
            delta = self.end_time - self.start_time
            self.duration_minutes = int(delta.total_seconds() / 60)



# ClusterItem and ClusterResult models === create ===> SessionClusteringResponse
class ClusterItem(BaseModel):
    """A history item within a cluster"""
    url: str
    title: str
    visit_time: datetime
    # Optional enriched URL features propagated from HistoryItem
    url_hostname: Optional[str] = None
    url_pathname_clean: Optional[str] = None
    url_search_query: Optional[str] = None
    embedding: Optional[List[float]] = None

class ClusterResult(BaseModel):
    """Result of clustering algorithm"""
    cluster_id: str
    theme: str
    summary: str
    items: List[ClusterItem]
    embedding: Optional[List[float]] = None
    is_learning: bool = False

class SessionClusteringResponse(BaseModel):
    """Response model for session-based clustering"""
    session_identifier: str
    session_start_time: datetime
    session_end_time: datetime
    clusters: List[ClusterResult]


    
