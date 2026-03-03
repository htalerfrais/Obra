from dataclasses import dataclass
from typing import List, Optional


@dataclass
class QuizQuestionModel:
    question: str
    answer: str
    options: List[str]
    difficulty: Optional[str] = None
