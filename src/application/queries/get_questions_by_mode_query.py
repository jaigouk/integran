"""Query handler for getting questions by practice mode following CQRS pattern."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from src.domain.content.models.question_models import Question
from src.domain.shared.repositories import LearningRepository, QuestionRepository
from src.domain.user.models.user_models import FederalState, UserPreferences

logger = logging.getLogger(__name__)


@dataclass
class GetQuestionsByModeQuery:
    """Query for getting questions by practice mode."""

    practice_mode: str
    user_preferences: UserPreferences | None = None
    user_id: int = 1
    limit: int = 1
    # State for cycling through questions
    category_index: int = 0
    question_indices: dict[str, int] | None = None
    last_question_id: int = 0


@dataclass
class GetQuestionsByModeResult:
    """Result of getting questions by practice mode."""

    success: bool
    question: Question | None = None
    next_state: dict[str, Any] | None = None  # State to maintain for cycling
    error_message: str | None = None


class GetQuestionsByModeQueryHandler:
    """Handler for getting questions by practice mode following CQRS pattern."""

    def __init__(
        self,
        question_repository: QuestionRepository,
        learning_repository: LearningRepository | None = None,
    ):
        """Initialize with question and learning repositories."""
        self.question_repository = question_repository
        self.learning_repository = learning_repository

    async def handle(self, query: GetQuestionsByModeQuery) -> GetQuestionsByModeResult:
        """Handle the query to get questions by practice mode."""
        try:
            if query.practice_mode == "failed":
                return await self._get_review_questions(query)
            elif query.practice_mode == "random":
                return await self._get_random_questions(query)
            elif query.practice_mode == "sequential":
                return await self._get_sequential_questions(query)
            elif query.practice_mode == "category":
                return await self._get_category_questions(query)
            elif query.practice_mode == "images":
                return await self._get_image_questions(query)
            else:
                return await self._get_default_question(query)

        except Exception as e:
            logger.error(
                f"Error getting questions by mode '{query.practice_mode}': {e}"
            )
            return GetQuestionsByModeResult(
                success=False, error_message=f"Failed to get questions: {e}"
            )

    async def _apply_federal_state_filtering(
        self, questions: list[Question], user_preferences: UserPreferences | None
    ) -> list[Question]:
        """Apply federal state filtering to questions based on user preferences.

        Args:
            questions: List of questions to filter
            user_preferences: User preferences containing federal state selection

        Returns:
            Filtered list of questions based on federal state preference
        """
        if not user_preferences:
            return questions

        federal_state = user_preferences.federal_state

        # If GENERAL is selected, return all questions (no filtering)
        if federal_state == FederalState.GENERAL:
            return questions

        # Get state-specific questions for the selected federal state
        state_questions = await self.question_repository.get_questions_by_state(
            state=federal_state.value
        )

        # Get general questions (questions not specific to any state)
        general_questions = await self.question_repository.get_questions_by_state(
            state=None
        )

        # Create a set of IDs for questions we should include
        allowed_question_ids = set()

        # Add state-specific questions
        for question in state_questions:
            allowed_question_ids.add(question.id)

        # Add general questions
        for question in general_questions:
            allowed_question_ids.add(question.id)

        # Filter the original questions to only include those that match the federal state
        filtered_questions = [q for q in questions if q.id in allowed_question_ids]

        return filtered_questions

    async def _get_review_questions(
        self, query: GetQuestionsByModeQuery
    ) -> GetQuestionsByModeResult:
        """Get questions that were previously answered incorrectly."""
        questions = await self.question_repository.get_questions_for_review(
            user_id=query.user_id,
            limit=query.limit * 10,  # Get more questions for filtering
        )

        # Apply federal state filtering
        filtered_questions = await self._apply_federal_state_filtering(
            questions, query.user_preferences
        )

        if filtered_questions:
            # Take the first question after filtering
            selected_questions = filtered_questions[: query.limit]
            return GetQuestionsByModeResult(
                success=True, question=selected_questions[0]
            )
        return GetQuestionsByModeResult(
            success=False,
            error_message="No failed questions available for review. Answer some questions incorrectly first!",
        )

    async def _get_random_questions(
        self, query: GetQuestionsByModeQuery
    ) -> GetQuestionsByModeResult:
        """Get random questions with optional FSRS filtering."""
        # Check if user wants FSRS filtering for random mode
        use_fsrs_filtering = (
            (query.user_preferences and query.user_preferences.random_mode_uses_fsrs)
            if query.user_preferences
            else True
        )  # Default to True

        if use_fsrs_filtering:
            # Use FSRS-aware filtering to get due/new/learning cards
            questions = await self.question_repository.get_questions_for_active_learning(
                user_id=query.user_id,
                desired_retention=query.user_preferences.desired_retention_rate
                if query.user_preferences
                else 0.90,
                stability_threshold=query.user_preferences.mastery_stability_threshold
                if query.user_preferences
                else 30,
                retrievability_threshold=query.user_preferences.retrievability_exclusion_threshold
                if query.user_preferences
                else 0.9,
                include_leeches=True,
                limit=100,  # Get more questions for randomization
            )
        else:
            # Fall back to cycling through categories (original behavior)
            categories = ["Geschichte", "Politik", "Recht", "Kultur", "Geographie"]
            current_category_index = query.category_index

            # Cycle through categories
            for _attempt in range(len(categories)):
                category = categories[current_category_index % len(categories)]
                questions = await self.question_repository.get_questions_by_category(
                    category=category
                )

                # Apply federal state filtering
                filtered_questions = await self._apply_federal_state_filtering(
                    questions, query.user_preferences
                )

                if filtered_questions:
                    # Take the first question after filtering
                    next_category_index = (current_category_index + 1) % len(categories)
                    return GetQuestionsByModeResult(
                        success=True,
                        question=filtered_questions[0],
                        next_state={"category_index": next_category_index},
                    )

                current_category_index = (current_category_index + 1) % len(categories)

            return GetQuestionsByModeResult(
                success=False, error_message="No questions found in any category"
            )

        # Apply federal state filtering to FSRS questions
        filtered_questions = await self._apply_federal_state_filtering(
            questions, query.user_preferences
        )

        if filtered_questions:
            import random

            # Randomly select a question from the FSRS-filtered pool
            question = random.choice(filtered_questions)
            return GetQuestionsByModeResult(success=True, question=question)

        return GetQuestionsByModeResult(
            success=False,
            error_message="No questions available for practice with FSRS filtering",
        )

    async def _get_sequential_questions(
        self, query: GetQuestionsByModeQuery
    ) -> GetQuestionsByModeResult:
        """Get questions in sequential order with FSRS-aware filtering."""
        # Check if user wants FSRS filtering for sequential mode
        use_fsrs_filtering = (
            (
                query.user_preferences
                and query.user_preferences.sequential_mode_uses_fsrs
            )
            if query.user_preferences
            else True
        )  # Default to True

        if use_fsrs_filtering:
            # Use FSRS-aware filtering to exclude well-mastered questions
            questions = await self.question_repository.get_questions_for_active_learning(
                user_id=query.user_id,
                desired_retention=query.user_preferences.desired_retention_rate
                if query.user_preferences
                else 0.90,
                stability_threshold=query.user_preferences.mastery_stability_threshold
                if query.user_preferences
                else 30,
                retrievability_threshold=query.user_preferences.retrievability_exclusion_threshold
                if query.user_preferences
                else 0.9,
                include_leeches=True,
                limit=500,  # Get more questions for cycling
            )
        else:
            # Fall back to original behavior - get all questions
            questions = await self.question_repository.get_all_questions()

        # Apply federal state filtering
        filtered_questions = await self._apply_federal_state_filtering(
            questions, query.user_preferences
        )

        if filtered_questions and query.last_question_id < len(filtered_questions):
            # Get the question at the current index
            question = filtered_questions[query.last_question_id]
            return GetQuestionsByModeResult(
                success=True,
                question=question,
                next_state={"last_question_id": query.last_question_id + 1},
            )
        return GetQuestionsByModeResult(
            success=False, error_message="No more questions available for practice"
        )

    async def _get_category_questions(
        self, query: GetQuestionsByModeQuery
    ) -> GetQuestionsByModeResult:
        """Get questions from specific categories."""
        # Simple category implementation - could be enhanced
        categories = ["Geschichte", "Politik", "Recht", "Kultur", "Geographie"]
        if query.category_index < len(categories):
            category = categories[query.category_index]
            questions = await self.question_repository.get_questions_by_category(
                category=category
            )

            # Apply federal state filtering
            filtered_questions = await self._apply_federal_state_filtering(
                questions, query.user_preferences
            )

            if filtered_questions:
                return GetQuestionsByModeResult(
                    success=True, question=filtered_questions[0]
                )

        return GetQuestionsByModeResult(
            success=False, error_message="No questions found for category"
        )

    async def _get_image_questions(
        self, query: GetQuestionsByModeQuery
    ) -> GetQuestionsByModeResult:
        """Get image questions with optional FSRS filtering."""
        # Check if user wants FSRS filtering for image mode
        use_fsrs_filtering = (
            (query.user_preferences and query.user_preferences.image_mode_uses_fsrs)
            if query.user_preferences
            else True
        )  # Default to True

        if use_fsrs_filtering:
            # Get FSRS-aware questions first, then filter for images
            active_questions = await self.question_repository.get_questions_for_active_learning(
                user_id=query.user_id,
                desired_retention=query.user_preferences.desired_retention_rate
                if query.user_preferences
                else 0.90,
                stability_threshold=query.user_preferences.mastery_stability_threshold
                if query.user_preferences
                else 30,
                retrievability_threshold=query.user_preferences.retrievability_exclusion_threshold
                if query.user_preferences
                else 0.9,
                include_leeches=True,
                limit=500,  # Get more questions for filtering
            )

            # Filter for image questions only
            questions = [q for q in active_questions if q.is_image_question]
        else:
            # Fall back to all image questions (original behavior)
            questions = await self.question_repository.get_image_questions()

        # Apply federal state filtering
        filtered_questions = await self._apply_federal_state_filtering(
            questions, query.user_preferences
        )

        if filtered_questions:
            # Use last_question_id to cycle through image questions sequentially
            question_index = query.last_question_id % len(filtered_questions)
            question = filtered_questions[question_index]

            # Update state for next question
            next_state = {
                "last_question_id": (query.last_question_id + 1)
                % len(filtered_questions)
            }

            return GetQuestionsByModeResult(
                success=True, question=question, next_state=next_state
            )
        return GetQuestionsByModeResult(
            success=False,
            error_message="No image questions available for practice with FSRS filtering",
        )

    async def _get_default_question(
        self, query: GetQuestionsByModeQuery
    ) -> GetQuestionsByModeResult:
        """Get a default question when mode is not recognized."""
        questions = await self.question_repository.get_all_questions()

        # Apply federal state filtering
        filtered_questions = await self._apply_federal_state_filtering(
            questions, query.user_preferences
        )

        if filtered_questions:
            return GetQuestionsByModeResult(
                success=True, question=filtered_questions[0]
            )
        return GetQuestionsByModeResult(
            success=False, error_message="No questions available"
        )
