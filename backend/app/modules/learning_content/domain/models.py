from dataclasses import dataclass
from typing import List, Optional


@dataclass
class QuizQuestionModel:
    question: str
    answer: str
    options: List[str]
    difficulty: Optional[str] = None


class QuizNotFoundError(Exception):
    """The quiz set or topic does not exist or belongs to another user."""


class QuizGenerationError(Exception):
    """The LLM did not return any usable question."""
