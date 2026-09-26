import json
import random
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from app.config import settings
from app.models.llm_models import LLMRequest
from app.models.quiz_models import (
    GenerateQuizResponse,
    QuizItemOutcome,
    QuizQuestion,
    SubmitQuizRequest,
    SubmitQuizResponse,
)
from app.modules.learning_content.domain.models import QuizGenerationError, QuizNotFoundError
from app.modules.shared.infrastructure.llm_client import LLMClient
from app.repositories.learning_repository import LearningRepository
from app.repositories.topic_repository import TopicRepository

if TYPE_CHECKING:
    from app.modules.recall_engine.application.recall_service import RecallService


class LearningContentService:
    def __init__(
        self,
        llm_service: LLMClient,
        learning_repository: LearningRepository,
        topic_repository: TopicRepository,
        recall_service: "RecallService",
    ):
        self.llm_service = llm_service
        self.learning_repository = learning_repository
        self.topic_repository = topic_repository
        self.recall_service = recall_service

    async def generate_quiz(
        self,
        user_id: int,
        topic_id: Optional[int],
        topic_name: Optional[str],
        question_count: int,
    ) -> GenerateQuizResponse:
        resolved_topic_name = topic_name or "General browsing topic"
        topic_description = ""
        if topic_id:
            topic = self.topic_repository.get_topic_with_state(user_id, topic_id)
            if not topic:
                raise QuizNotFoundError(f"Topic {topic_id} not found")
            resolved_topic_name = topic["name"]
            topic_description = topic.get("description") or ""

        context = f"\nContext on what the user studied: {topic_description}" if topic_description else ""
        prompt = (
            f"Create {question_count} multiple-choice quiz questions to test someone's knowledge of "
            f"'{resolved_topic_name}'.{context}\n"
            "Rules:\n"
            "- Each question has exactly 4 options and exactly one correct option.\n"
            "- 'answer' must be copied verbatim from 'options'.\n"
            "- Test understanding of the concepts, not trivia about websites.\n"
            "- Write in the same language as the topic name and context.\n"
            "Return ONLY a JSON array where each item has: question, answer, options (4 strings), "
            "difficulty (easy|medium|hard)."
        )
        response = await self.llm_service.generate_text(
            LLMRequest(
                prompt=prompt,
                provider=settings.default_provider,
                max_tokens=2000,
                temperature=0.4,
            )
        )
        questions = self._parse_questions(response.generated_text, question_count)
        if not questions:
            raise QuizGenerationError("The model did not return any valid question")

        quiz_set = self.learning_repository.create_quiz_set(
            user_id=user_id,
            topic_id=topic_id,
            title=f"Quiz - {resolved_topic_name}",
            metadata_json={"source": "llm_generated"},
        )
        if not quiz_set:
            raise ValueError("Failed to create quiz set")

        persisted_questions: List[QuizQuestion] = []
        for q in questions:
            created = self.learning_repository.create_quiz_item(
                quiz_set_id=quiz_set["id"],
                question=q.question,
                answer=q.answer,
                distractors=q.options,
                difficulty=q.difficulty,
            )
            if created:
                persisted_questions.append(
                    QuizQuestion(
                        id=created["id"],
                        question=q.question,
                        options=q.options,
                        answer=q.answer,
                        difficulty=q.difficulty,
                    )
                )

        return GenerateQuizResponse(
            quiz_set_id=quiz_set["id"],
            title=quiz_set["title"],
            questions=persisted_questions,
            created_at=datetime.fromisoformat(quiz_set["created_at"]) if isinstance(quiz_set["created_at"], str) else quiz_set["created_at"],
        )

    def _parse_questions(self, raw: str, question_count: int) -> List[QuizQuestion]:
        try:
            start = raw.find("[")
            end = raw.rfind("]")
            parsed = json.loads(raw[start:end + 1] if start != -1 and end != -1 else raw)
        except Exception:
            parsed = []
        if not isinstance(parsed, list):
            return []
        questions: List[QuizQuestion] = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            question = str(item.get("question") or "").strip()
            answer = str(item.get("answer") or "").strip()
            raw_options = item.get("options") or []
            if not (question and answer and isinstance(raw_options, list)):
                continue
            options = [str(o).strip() for o in raw_options if str(o).strip()][:4]
            # The correct answer must be one of the options, otherwise the question is unanswerable
            matching = [o for o in options if o.lower() == answer.lower()]
            if not matching or len(options) < 2:
                continue
            answer = matching[0]
            # LLMs tend to put the correct answer first: shuffle so its position gives nothing away
            random.shuffle(options)
            questions.append(
                QuizQuestion(
                    question=question,
                    answer=answer,
                    options=options,
                    difficulty=item.get("difficulty"),
                )
            )
            if len(questions) >= question_count:
                break
        return questions

    def submit_quiz(self, user_id: int, quiz_set_id: int, payload: SubmitQuizRequest) -> SubmitQuizResponse:
        quiz_set = self.learning_repository.get_quiz_set_with_items(quiz_set_id)
        if not quiz_set or quiz_set.get("user_id") != user_id:
            raise QuizNotFoundError(f"Quiz set {quiz_set_id} not found")
        items = quiz_set.get("items", [])
        answer_map = {a.question_id: a.answer for a in payload.answers}

        outcomes: List[QuizItemOutcome] = []
        for item in items:
            user_answer = answer_map.get(item["id"])
            correct_answer = str(item.get("answer", ""))
            is_correct = bool(user_answer and user_answer.strip().lower() == correct_answer.strip().lower())
            outcomes.append(QuizItemOutcome(question_id=item["id"], is_correct=is_correct, correct_answer=correct_answer))

        total_items = len(items)
        correct = sum(1 for o in outcomes if o.is_correct)
        score = float(correct / total_items) if total_items else 0.0
        attempt = self.learning_repository.create_attempt(quiz_set_id, user_id, score, total_items)
        if not attempt:
            raise ValueError("Failed to create quiz attempt")
        for outcome in outcomes:
            self.learning_repository.create_item_result(
                quiz_attempt_id=attempt["id"],
                quiz_item_id=outcome.question_id,
                user_answer=answer_map.get(outcome.question_id),
                is_correct=outcome.is_correct,
            )

        review = None
        if quiz_set.get("topic_id") and total_items:
            review = self.recall_service.record_quiz_review(
                user_id=user_id,
                topic_id=quiz_set["topic_id"],
                score=score,
                reviewed_at=datetime.utcnow(),
            )

        return SubmitQuizResponse(
            attempt_id=attempt["id"],
            score=score,
            total_items=total_items,
            results=outcomes,
            next_review_at=review.next_review_at if review else None,
            interval_days=review.interval_days if review else None,
        )
