from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class QuizQuestion(BaseModel):
    id: Optional[int] = None
    question: str
    options: List[str] = Field(default_factory=list)
    answer: str
    difficulty: Optional[str] = None


class GenerateQuizRequest(BaseModel):
    topic_id: Optional[int] = None
    topic_name: Optional[str] = None
    session_identifier: Optional[str] = None
    question_count: int = Field(5, ge=1, le=15)


class GenerateQuizResponse(BaseModel):
    quiz_set_id: int
    title: str
    questions: List[QuizQuestion]
    created_at: datetime


class QuizAnswerItem(BaseModel):
    question_id: int
    answer: str


class SubmitQuizRequest(BaseModel):
    answers: List[QuizAnswerItem]


class QuizItemOutcome(BaseModel):
    question_id: int
    is_correct: bool
    correct_answer: str


class SubmitQuizResponse(BaseModel):
    attempt_id: int
    score: float
    total_items: int
    results: List[QuizItemOutcome] = Field(default_factory=list)
    # Recall update for the quiz's topic (absent for quizzes without a topic)
    next_review_at: Optional[datetime] = None
    interval_days: Optional[int] = None
