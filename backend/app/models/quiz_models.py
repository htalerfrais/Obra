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
    question_count: int = 5


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


class SubmitQuizResponse(BaseModel):
    attempt_id: int
    score: float
    total_items: int
