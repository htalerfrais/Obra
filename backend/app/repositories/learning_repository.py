from typing import Dict, List, Optional

from app.models.database_models import QuizSet, QuizItem, QuizAttempt, QuizItemResult
from .base_repository import BaseRepository


class LearningRepository(BaseRepository):
    def create_quiz_set(self, user_id: int, topic_id: Optional[int], title: str, metadata_json: Optional[dict] = None) -> Optional[Dict]:
        def operation(db):
            quiz_set = QuizSet(
                user_id=user_id,
                topic_id=topic_id,
                title=title,
                metadata_json=metadata_json,
                status="ready",
            )
            db.add(quiz_set)
            db.flush()
            db.refresh(quiz_set)
            return self._to_dict(quiz_set)
        return self._execute(operation, "Failed to create quiz set")

    def create_quiz_item(
        self,
        quiz_set_id: int,
        question: str,
        answer: str,
        distractors: Optional[List[str]] = None,
        difficulty: Optional[str] = None,
    ) -> Optional[Dict]:
        def operation(db):
            item = QuizItem(
                quiz_set_id=quiz_set_id,
                question=question,
                answer=answer,
                distractors=distractors,
                difficulty=difficulty,
            )
            db.add(item)
            db.flush()
            db.refresh(item)
            return self._to_dict(item)
        return self._execute(operation, "Failed to create quiz item")

    def get_quiz_set_with_items(self, quiz_set_id: int) -> Optional[Dict]:
        def operation(db):
            quiz_set = db.query(QuizSet).filter(QuizSet.id == quiz_set_id).first()
            if not quiz_set:
                return None
            items = db.query(QuizItem).filter(QuizItem.quiz_set_id == quiz_set_id).all()
            result = self._to_dict(quiz_set)
            result["items"] = [self._to_dict(i) for i in items]
            return result
        return self._execute(operation, "Failed to load quiz set")

    def create_attempt(self, quiz_set_id: int, user_id: int, score: float, total_items: int) -> Optional[Dict]:
        def operation(db):
            attempt = QuizAttempt(
                quiz_set_id=quiz_set_id,
                user_id=user_id,
                score=score,
                total_items=total_items,
            )
            db.add(attempt)
            db.flush()
            db.refresh(attempt)
            return self._to_dict(attempt)
        return self._execute(operation, "Failed to create quiz attempt")

    def create_item_result(self, quiz_attempt_id: int, quiz_item_id: int, user_answer: Optional[str], is_correct: bool) -> Optional[Dict]:
        def operation(db):
            result = QuizItemResult(
                quiz_attempt_id=quiz_attempt_id,
                quiz_item_id=quiz_item_id,
                user_answer=user_answer,
                is_correct=is_correct,
            )
            db.add(result)
            db.flush()
            db.refresh(result)
            return self._to_dict(result)
        return self._execute(operation, "Failed to create quiz item result")
