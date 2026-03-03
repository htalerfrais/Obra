from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float, Boolean
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from datetime import datetime
from pgvector.sqlalchemy import Vector

# Base class for all models
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    google_user_id = Column(String, unique=True, nullable=False, index=True)
    token = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, google_user_id='{self.google_user_id}')>"


class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_identifier = Column(String, nullable=False, unique=True, index=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    user = relationship("User", back_populates="sessions")
    clusters = relationship("Cluster", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Session(id={self.id}, user_id={self.user_id}, session_identifier='{self.session_identifier}')>"


class Cluster(Base):
    """
    Cluster model - represents thematic groups within a session
    
    Relationships:
    - One cluster belongs to one session
    - One cluster has many history items
    """
    __tablename__ = "clusters"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    embedding = Column(Vector(768), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    session = relationship("Session", back_populates="clusters")
    history_items = relationship("HistoryItem", back_populates="cluster", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Cluster(id={self.id}, session_id={self.session_id}, name='{self.name}')>"


class HistoryItem(Base):
    __tablename__ = "history_items"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cluster_id = Column(Integer, ForeignKey("clusters.id", ondelete="CASCADE"), nullable=False, index=True)
    url = Column(String, nullable=False)
    title = Column(String, nullable=True)
    domain = Column(String, nullable=True)
    visit_time = Column(DateTime, nullable=False)
    raw_semantics = Column(JSON, nullable=True)
    embedding = Column(Vector(768), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    cluster = relationship("Cluster", back_populates="history_items")
    
    def __repr__(self):
        return f"<HistoryItem(id={self.id}, cluster_id={self.cluster_id}, url='{self.url}')>"


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    embedding = Column(Vector(768), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


class TopicObservation(Base):
    __tablename__ = "topic_observations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    cluster_id = Column(Integer, ForeignKey("clusters.id", ondelete="SET NULL"), nullable=True, index=True)
    observed_at = Column(DateTime, nullable=False)
    importance_score = Column(Float, nullable=False, default=0.5)
    source = Column(String, nullable=False, default="clustering")
    created_at = Column(DateTime, default=func.now(), nullable=False)


class TopicRecallState(Base):
    __tablename__ = "topic_recall_state"

    id = Column(Integer, primary_key=True, autoincrement=True)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    strength = Column(Float, nullable=False, default=0.5)
    forgetting_score = Column(Float, nullable=False, default=0.0)
    interval_days = Column(Integer, nullable=False, default=1)
    repetitions = Column(Integer, nullable=False, default=0)
    next_review_at = Column(DateTime, nullable=True, index=True)
    last_reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


class RecallEvent(Base):
    __tablename__ = "recall_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String, nullable=False)  # due, reviewed, snoozed
    event_time = Column(DateTime, nullable=False, default=func.now())
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)


class QuizSet(Base):
    __tablename__ = "quiz_sets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String, nullable=False)
    status = Column(String, nullable=False, default="ready")
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)


class QuizItem(Base):
    __tablename__ = "quiz_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quiz_set_id = Column(Integer, ForeignKey("quiz_sets.id", ondelete="CASCADE"), nullable=False, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    distractors = Column(JSON, nullable=True)
    difficulty = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quiz_set_id = Column(Integer, ForeignKey("quiz_sets.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    score = Column(Float, nullable=False, default=0.0)
    total_items = Column(Integer, nullable=False, default=0)
    submitted_at = Column(DateTime, default=func.now(), nullable=False)


class QuizItemResult(Base):
    __tablename__ = "quiz_item_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quiz_attempt_id = Column(Integer, ForeignKey("quiz_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    quiz_item_id = Column(Integer, ForeignKey("quiz_items.id", ondelete="CASCADE"), nullable=False, index=True)
    user_answer = Column(Text, nullable=True)
    is_correct = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    aggregate_type = Column(String, nullable=False, index=True)
    aggregate_id = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    event_version = Column(Integer, nullable=False, default=1)
    idempotency_key = Column(String, nullable=False, unique=True, index=True)
    payload = Column(JSON, nullable=False)
    status = Column(String, nullable=False, default="pending", index=True)  # pending, processing, sent, failed
    retries = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)

