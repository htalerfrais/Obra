import json
from datetime import datetime
from typing import List, Optional

from app.config import settings
from app.models.llm_models import LLMRequest
from app.models.quiz_models import GenerateQuizResponse, QuizQuestion, SubmitQuizRequest, SubmitQuizResponse
from app.modules.shared.infrastructure.llm_client import LLMClient
from app.repositories.learning_repository import LearningRepository
from app.repositories.topic_repository import TopicRepository


class LearningContentService:
    def __init__(self, llm_service: LLMClient, learning_repository: LearningRepository, topic_repository: TopicRepository):
        self.llm_service = llm_service
        self.learning_repository = learning_repository
        self.topic_repository = topic_repository

    async def generate_quiz(
        self,
        user_id: int,
        topic_id: Optional[int],
        topic_name: Optional[str],
        question_count: int,
    ) -> GenerateQuizResponse:
        resolved_topic_name = topic_name or "General browsing topic"
        if topic_id:
            topics = self.topic_repository.list_topics_with_state(user_id, limit=200)
            for topic in topics:
                if topic["id"] == topic_id:
                    resolved_topic_name = topic["name"]
                    break

        prompt = (
            f"Create {question_count} multiple-choice quiz questions about '{resolved_topic_name}'. "
            "Return ONLY JSON array where each item has: question, answer, options (4 strings), difficulty."
        )
        response = await self.llm_service.generate_text(
            LLMRequest(
                prompt=prompt,
                provider=settings.default_provider,
                max_tokens=2000,
                temperature=0.4,
            )
        )
        questions = self._parse_questions(response.generated_text, question_count, resolved_topic_name)
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

    def _parse_questions(self, raw: str, question_count: int, topic_name: str) -> List[QuizQuestion]:
        try:
            start = raw.find("[")
            end = raw.rfind("]")
            parsed = json.loads(raw[start:end + 1] if start != -1 and end != -1 else raw)
        except Exception:
            parsed = []
        questions: List[QuizQuestion] = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            question = str(item.get("question") or "").strip()
            answer = str(item.get("answer") or "").strip()
            options = item.get("options") or []
            if question and answer and isinstance(options, list) and len(options) >= 2:
                questions.append(
                    QuizQuestion(
                        question=question,
                        answer=answer,
                        options=[str(o) for o in options[:4]],
                        difficulty=item.get("difficulty"),
                    )
                )
            if len(questions) >= question_count:
                break
        if questions:
            return questions
        # safe fallback without external dependency
        return [
            QuizQuestion(
                question=f"Which statement best describes {topic_name}?",
                answer="A core topic explored in your browsing history.",
                options=[
                    "A core topic explored in your browsing history.",
                    "A random unrelated subject.",
                    "A browser setting.",
                    "An operating system process.",
                ],
                difficulty="easy",
            )
            for _ in range(question_count)
        ]

    def submit_quiz(self, user_id: int, quiz_set_id: int, payload: SubmitQuizRequest) -> SubmitQuizResponse:
        quiz_set = self.learning_repository.get_quiz_set_with_items(quiz_set_id)
        if not quiz_set:
            raise ValueError("Quiz set not found")
        items = quiz_set.get("items", [])
        answer_map = {a.question_id: a.answer for a in payload.answers}
        correct = 0
        for item in items:
            user_answer = answer_map.get(item["id"])
            if user_answer and user_answer.strip().lower() == str(item.get("answer", "")).strip().lower():
                correct += 1
        total_items = len(items)
        score = float(correct / total_items) if total_items else 0.0
        attempt = self.learning_repository.create_attempt(quiz_set_id, user_id, score, total_items)
        if not attempt:
            raise ValueError("Failed to create quiz attempt")
        for item in items:
            user_answer = answer_map.get(item["id"])
            is_correct = bool(user_answer and user_answer.strip().lower() == str(item.get("answer", "")).strip().lower())
            self.learning_repository.create_item_result(
                quiz_attempt_id=attempt["id"],
                quiz_item_id=item["id"],
                user_answer=user_answer,
                is_correct=is_correct,
            )
        return SubmitQuizResponse(attempt_id=attempt["id"], score=score, total_items=total_items)
