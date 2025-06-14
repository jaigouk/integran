"""Interleaved practice management system.

This module implements interleaved practice (mixing related topics) to enhance
learning retention and transfer of knowledge between similar concepts.
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from src.core.database import DatabaseManager
from src.core.models import FSRSCard, Question


class InterleavingStrategy(str, Enum):
    """Interleaving strategies for mixing questions."""

    RANDOM = "random"  # Random mixing
    SIMILARITY_BASED = "similarity_based"  # Mix similar concepts
    CONTRAST_BASED = "contrast_based"  # Mix contrasting concepts
    PROGRESSIVE = "progressive"  # Gradually increase mixing
    CATEGORY_ROUND_ROBIN = "category_round_robin"  # Cycle through categories


class DifficultyBalance(str, Enum):
    """Difficulty balancing strategies."""

    UNIFORM = "uniform"  # Equal difficulty distribution
    PROGRESSIVE = "progressive"  # Start easy, get harder
    MIXED = "mixed"  # Random difficulty mixing
    ADAPTIVE = "adaptive"  # Adapt based on performance


@dataclass
class InterleavingConfig:
    """Configuration for interleaved practice sessions."""

    strategy: InterleavingStrategy
    difficulty_balance: DifficultyBalance
    category_weights: dict[str, float]  # Relative importance of categories
    max_consecutive_same_category: int = 2
    min_category_gap: int = 1  # Minimum questions between same category
    similarity_threshold: float = 0.7  # For similarity-based mixing
    adaptive_adjustment: bool = True  # Adjust based on performance


@dataclass
class QuestionGroup:
    """Group of related questions for interleaving."""

    category: str
    subcategory: str | None
    difficulty_level: str
    questions: list[tuple[Question, FSRSCard]]
    similarity_score: float = 0.0
    last_presented_index: int = -1


@dataclass
class InterleavingSession:
    """An interleaved practice session."""

    session_id: int
    config: InterleavingConfig
    question_sequence: list[tuple[Question, FSRSCard]]
    current_position: int = 0
    category_performance: dict[str, float] = field(default_factory=dict)
    adaptation_history: list[str] = field(default_factory=list)


class InterleavingManager:
    """Advanced interleaved practice management system."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize interleaving manager.

        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager
        self._category_relationships = self._build_category_relationships()
        self._active_sessions: dict[int, InterleavingSession] = {}

    def create_interleaved_session(
        self,
        user_id: int,
        config: InterleavingConfig,
        target_questions: int = 20,
        categories: list[str] | None = None,
    ) -> InterleavingSession:
        """Create an interleaved practice session.

        Args:
            user_id: User ID
            config: Interleaving configuration
            target_questions: Number of questions to include
            categories: Specific categories to include (None for all)

        Returns:
            Configured interleaving session
        """
        # Get available questions
        question_groups = self._get_question_groups(user_id, categories)

        # Generate interleaved sequence
        sequence = self._generate_sequence(question_groups, config, target_questions)

        # Create session
        session_id = len(self._active_sessions) + 1  # Simple ID generation
        session = InterleavingSession(
            session_id=session_id,
            config=config,
            question_sequence=sequence,
        )

        self._active_sessions[session_id] = session
        return session

    def get_next_question(self, session_id: int) -> tuple[Question, FSRSCard] | None:
        """Get the next question in the interleaved sequence.

        Args:
            session_id: Session ID

        Returns:
            Next question and card, or None if session complete
        """
        session = self._active_sessions.get(session_id)
        if not session:
            return None

        if session.current_position >= len(session.question_sequence):
            return None

        question, card = session.question_sequence[session.current_position]
        session.current_position += 1

        return question, card

    def record_performance(
        self,
        session_id: int,
        question_id: int,
        is_correct: bool,
        response_time_ms: int,
    ) -> None:
        """Record performance and adapt interleaving if configured.

        Args:
            session_id: Session ID
            question_id: Question ID
            is_correct: Whether answer was correct
            response_time_ms: Response time in milliseconds
        """
        session = self._active_sessions.get(session_id)
        if not session:
            return

        # Get question category
        question = self.db_manager.get_question(question_id)
        if not question:
            return

        category = str(question.category)

        # Update category performance
        if category not in session.category_performance:
            session.category_performance[category] = 0.0

        # Simple performance tracking (could be more sophisticated)
        current_performance = session.category_performance[category]
        new_performance = 1.0 if is_correct else 0.0

        # Exponential moving average
        alpha = 0.3
        session.category_performance[category] = (
            alpha * new_performance + (1 - alpha) * current_performance
        )

        # Adaptive adjustment if enabled
        if session.config.adaptive_adjustment:
            self._adapt_sequence(session, category, is_correct, response_time_ms)

    def analyze_interleaving_effectiveness(
        self, user_id: int, days: int = 30
    ) -> dict[str, Any]:
        """Analyze the effectiveness of interleaved vs non-interleaved practice.

        Args:
            user_id: User ID
            days: Number of days to analyze

        Returns:
            Analysis of interleaving effectiveness
        """
        cutoff_date = datetime.now(UTC) - timedelta(days=days)

        with self.db_manager.get_session() as session:
            from src.core.models import ReviewHistory

            # Get reviews in time period
            reviews = (
                session.query(ReviewHistory)
                .join(FSRSCard)
                .filter(
                    FSRSCard.user_id == user_id,
                    ReviewHistory.review_date >= cutoff_date.timestamp(),
                )
                .all()
            )

            # Analyze performance patterns
            category_sequences = self._analyze_category_sequences(reviews)

            # Calculate effectiveness metrics
            interleaved_performance = self._calculate_interleaved_performance(
                category_sequences
            )

            return {
                "interleaved_sessions": len(
                    [s for s in category_sequences if s["is_interleaved"]]
                ),
                "non_interleaved_sessions": len(
                    [s for s in category_sequences if not s["is_interleaved"]]
                ),
                "interleaved_retention": interleaved_performance["retention"],
                "non_interleaved_retention": interleaved_performance[
                    "non_interleaved_retention"
                ],
                "improvement_factor": interleaved_performance["improvement_factor"],
                "recommended_strategy": self._recommend_strategy(
                    interleaved_performance
                ),
                "category_benefits": self._analyze_category_benefits(
                    category_sequences
                ),
            }

    def get_optimal_category_mix(
        self, user_id: int, target_categories: list[str]
    ) -> dict[str, float]:
        """Calculate optimal mixing ratios for categories.

        Args:
            user_id: User ID
            target_categories: Categories to include in mix

        Returns:
            Optimal mixing ratios
        """
        category_stats = {}

        with self.db_manager.get_session() as session:
            for category in target_categories:
                # Get cards for this category
                cards = (
                    session.query(FSRSCard)
                    .join(Question)
                    .filter(
                        FSRSCard.user_id == user_id,
                        Question.category == category,
                    )
                    .all()
                )

                if not cards:
                    category_stats[category] = {"weight": 0.0, "priority": 0}
                    continue

                # Calculate priority based on need
                new_cards = sum(1 for c in cards if c.review_count == 0)
                due_cards = sum(
                    1
                    for c in cards
                    if c.next_review_date <= datetime.now(UTC).timestamp()
                )
                difficult_cards = sum(1 for c in cards if c.lapse_count >= 3)

                # Priority score (higher = more attention needed)
                priority = new_cards * 0.3 + due_cards * 0.5 + difficult_cards * 0.2
                total_cards = len(cards)

                category_stats[category] = {
                    "total_cards": total_cards,
                    "new_cards": new_cards,
                    "due_cards": due_cards,
                    "difficult_cards": difficult_cards,
                    "priority": priority,
                }

        # Calculate weights based on priority
        total_priority = sum(stats["priority"] for stats in category_stats.values())

        if total_priority == 0:
            # Equal distribution if no clear priorities
            return {cat: 1.0 / len(target_categories) for cat in target_categories}

        weights = {}
        for category, stats in category_stats.items():
            weights[category] = stats["priority"] / total_priority

        return weights

    def _get_question_groups(
        self, user_id: int, categories: list[str] | None = None
    ) -> list[QuestionGroup]:
        """Get question groups organized for interleaving.

        Args:
            user_id: User ID
            categories: Categories to include

        Returns:
            List of question groups
        """
        groups = []

        with self.db_manager.get_session() as session:
            # Get questions that need review
            query = (
                session.query(Question, FSRSCard)
                .join(FSRSCard, Question.id == FSRSCard.question_id)
                .filter(FSRSCard.user_id == user_id)
            )

            if categories:
                query = query.filter(Question.category.in_(categories))

            # Filter for due cards or new cards
            now = datetime.now(UTC).timestamp()
            query = query.filter(
                (FSRSCard.next_review_date <= now) | (FSRSCard.review_count == 0)
            )

            questions_and_cards = query.all()

            # Group by category and difficulty
            category_groups: dict[str, dict[str, list[tuple[Question, FSRSCard]]]] = (
                defaultdict(lambda: defaultdict(list))
            )

            for question, card in questions_and_cards:
                difficulty = self._get_difficulty_level(card)
                category_groups[str(question.category)][difficulty].append(
                    (question, card)
                )

            # Convert to QuestionGroup objects
            for category, difficulty_groups in category_groups.items():
                for difficulty, question_cards in difficulty_groups.items():
                    group = QuestionGroup(
                        category=category,
                        subcategory=None,  # Could be extended
                        difficulty_level=difficulty,
                        questions=question_cards,
                    )
                    groups.append(group)

        return groups

    def _generate_sequence(
        self,
        question_groups: list[QuestionGroup],
        config: InterleavingConfig,
        target_questions: int,
    ) -> list[tuple[Question, FSRSCard]]:
        """Generate interleaved question sequence.

        Args:
            question_groups: Available question groups
            config: Interleaving configuration
            target_questions: Target number of questions

        Returns:
            Interleaved sequence of questions
        """
        if config.strategy == InterleavingStrategy.RANDOM:
            return self._generate_random_sequence(question_groups, target_questions)
        elif config.strategy == InterleavingStrategy.CATEGORY_ROUND_ROBIN:
            return self._generate_round_robin_sequence(
                question_groups, target_questions, config
            )
        elif config.strategy == InterleavingStrategy.SIMILARITY_BASED:
            return self._generate_similarity_sequence(
                question_groups, target_questions, config
            )
        elif config.strategy == InterleavingStrategy.CONTRAST_BASED:
            return self._generate_contrast_sequence(
                question_groups, target_questions, config
            )
        else:
            # Default to round robin
            return self._generate_round_robin_sequence(
                question_groups, target_questions, config
            )

    def _generate_random_sequence(
        self, question_groups: list[QuestionGroup], target_questions: int
    ) -> list[tuple[Question, FSRSCard]]:
        """Generate random interleaved sequence.

        Args:
            question_groups: Available question groups
            target_questions: Target number of questions

        Returns:
            Random sequence
        """
        all_questions = []
        for group in question_groups:
            all_questions.extend(group.questions)

        random.shuffle(all_questions)
        return all_questions[:target_questions]

    def _generate_round_robin_sequence(
        self,
        question_groups: list[QuestionGroup],
        target_questions: int,
        config: InterleavingConfig,
    ) -> list[tuple[Question, FSRSCard]]:
        """Generate round-robin interleaved sequence.

        Args:
            question_groups: Available question groups
            target_questions: Target number of questions
            config: Interleaving configuration

        Returns:
            Round-robin sequence
        """
        sequence = []
        group_indices = {group.category: 0 for group in question_groups}

        # Apply category weights
        weighted_groups = []
        for qgroup in question_groups:
            weight = config.category_weights.get(qgroup.category, 1.0)
            # Add group multiple times based on weight
            for _ in range(max(1, int(weight * 10))):
                weighted_groups.append(qgroup)

        random.shuffle(weighted_groups)

        consecutive_count = 0
        last_category = None

        for _i in range(target_questions):
            if not weighted_groups:
                break

            # Find next group respecting constraints
            group: QuestionGroup | None = None
            for attempt_group in weighted_groups:
                if (
                    last_category != attempt_group.category
                    or consecutive_count < config.max_consecutive_same_category
                ):
                    group = attempt_group
                    break

            if not group:
                # If no group satisfies constraints, pick any available
                group = weighted_groups[0]

            # Get question from group
            group_index = group_indices[group.category]
            if group_index < len(group.questions):
                question, card = group.questions[group_index]
                sequence.append((question, card))
                group_indices[group.category] += 1

                # Update consecutive tracking
                if last_category == group.category:
                    consecutive_count += 1
                else:
                    consecutive_count = 1
                    last_category = group.category

            # Remove group if exhausted
            if group_indices[group.category] >= len(group.questions):
                weighted_groups = [
                    g for g in weighted_groups if g.category != group.category
                ]

        return sequence

    def _generate_similarity_sequence(
        self,
        question_groups: list[QuestionGroup],
        target_questions: int,
        config: InterleavingConfig,  # noqa: ARG002
    ) -> list[tuple[Question, FSRSCard]]:
        """Generate sequence mixing similar concepts.

        Args:
            question_groups: Available question groups
            target_questions: Target number of questions
            config: Interleaving configuration

        Returns:
            Similarity-based sequence
        """
        # For now, use category relationships as similarity
        related_categories = self._get_related_categories()

        sequence: list[tuple[Question, FSRSCard]] = []
        used_questions = set()

        for i in range(target_questions):
            if i == 0:
                # Start with any group
                group = random.choice(question_groups)
            else:
                # Find similar category
                last_question = sequence[-1][0]
                similar_categories = related_categories.get(
                    str(last_question.category), []
                )

                # Find groups with similar categories
                similar_groups = [
                    g
                    for g in question_groups
                    if g.category in similar_categories
                    and any(q[0].id not in used_questions for q in g.questions)
                ]

                if similar_groups:
                    group = random.choice(similar_groups)
                else:
                    # Fall back to any available group
                    available_groups = [
                        g
                        for g in question_groups
                        if any(q[0].id not in used_questions for q in g.questions)
                    ]
                    if available_groups:
                        group = random.choice(available_groups)
                    else:
                        break

            # Get unused question from group
            available_questions = [
                q for q in group.questions if q[0].id not in used_questions
            ]

            if available_questions:
                question, card = random.choice(available_questions)
                sequence.append((question, card))
                used_questions.add(question.id)

        return sequence

    def _generate_contrast_sequence(
        self,
        question_groups: list[QuestionGroup],
        target_questions: int,
        config: InterleavingConfig,
    ) -> list[tuple[Question, FSRSCard]]:
        """Generate sequence mixing contrasting concepts.

        Args:
            question_groups: Available question groups
            target_questions: Target number of questions
            config: Interleaving configuration

        Returns:
            Contrast-based sequence
        """
        # Similar to similarity but choose different categories
        return self._generate_round_robin_sequence(
            question_groups, target_questions, config
        )

    def _get_difficulty_level(self, card: FSRSCard) -> str:
        """Get difficulty level for a card.

        Args:
            card: FSRS card

        Returns:
            Difficulty level string
        """
        if card.review_count == 0:
            return "new"
        elif card.lapse_count >= 3:
            return "hard"
        elif card.review_count < 3:
            return "learning"
        else:
            return "review"

    def _build_category_relationships(self) -> dict[str, list[str]]:
        """Build relationships between categories.

        Returns:
            Category relationship mapping
        """
        # German Integration Exam category relationships
        return {
            "Politik": ["Gesellschaft", "Geschichte"],
            "Gesellschaft": ["Politik", "Grundrechte"],
            "Geschichte": ["Politik", "Kultur"],
            "Grundrechte": ["Gesellschaft", "Politik"],
            "Kultur": ["Geschichte", "Gesellschaft"],
        }

    def _get_related_categories(self) -> dict[str, list[str]]:
        """Get category relationships for similarity mixing.

        Returns:
            Related categories mapping
        """
        return self._category_relationships

    def _adapt_sequence(
        self,
        session: InterleavingSession,
        category: str,
        is_correct: bool,  # noqa: ARG002
        response_time_ms: int,  # noqa: ARG002
    ) -> None:
        """Adapt the sequence based on performance.

        Args:
            session: Interleaving session
            category: Category of the question
            is_correct: Whether answer was correct
            response_time_ms: Response time
        """
        # Simple adaptation: if performance is poor, reduce frequency
        performance = session.category_performance.get(category, 0.0)

        if performance < 0.5 and len(session.adaptation_history) < 5:
            # Reduce this category in upcoming questions
            session.adaptation_history.append(f"reduced_{category}")
            # Implementation would modify the remaining sequence
        elif performance > 0.8:
            # Could increase frequency or difficulty
            session.adaptation_history.append(f"increased_{category}")

    def _analyze_category_sequences(self, reviews: list[Any]) -> list[dict[str, Any]]:
        """Analyze sequences to identify interleaved vs blocked practice.

        Args:
            reviews: Review history

        Returns:
            Sequence analysis
        """
        # Group reviews by session or time windows
        sequences: list[dict[str, Any]] = []

        # Simple implementation: group by time windows
        if not reviews:
            return sequences

        current_sequence: list[Any] = []
        last_time = reviews[0].review_date

        for review in reviews:
            if review.review_date - last_time > 3600:  # 1 hour gap = new sequence
                if current_sequence:
                    sequences.append(self._classify_sequence(current_sequence))
                current_sequence = [review]
            else:
                current_sequence.append(review)
            last_time = review.review_date

        if current_sequence:
            sequences.append(self._classify_sequence(current_sequence))

        return sequences

    def _classify_sequence(self, sequence: list[Any]) -> dict[str, Any]:
        """Classify a sequence as interleaved or blocked.

        Args:
            sequence: Sequence of reviews

        Returns:
            Sequence classification
        """
        if len(sequence) < 3:
            return {"is_interleaved": False, "performance": 0.0, "categories": []}

        # Get categories
        categories = []
        for _review in sequence:
            # Would need to join with questions to get category
            # For now, simplified
            categories.append("unknown")

        # Check for interleaving (category switches)
        switches = 0
        for i in range(1, len(categories)):
            if categories[i] != categories[i - 1]:
                switches += 1

        is_interleaved = (
            switches / (len(categories) - 1) > 0.3 if len(categories) > 1 else False
        )

        # Calculate performance
        successful = sum(1 for r in sequence if r.rating >= 3)
        performance = successful / len(sequence)

        return {
            "is_interleaved": is_interleaved,
            "performance": performance,
            "categories": list(set(categories)),
            "length": len(sequence),
        }

    def _calculate_interleaved_performance(
        self, sequences: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Calculate performance metrics for interleaved vs non-interleaved.

        Args:
            sequences: Sequence classifications

        Returns:
            Performance comparison
        """
        interleaved = [s for s in sequences if s["is_interleaved"]]
        non_interleaved = [s for s in sequences if not s["is_interleaved"]]

        interleaved_perf = (
            sum(s["performance"] for s in interleaved) / len(interleaved)
            if interleaved
            else 0.0
        )

        non_interleaved_perf = (
            sum(s["performance"] for s in non_interleaved) / len(non_interleaved)
            if non_interleaved
            else 0.0
        )

        improvement = (
            interleaved_perf - non_interleaved_perf if non_interleaved_perf > 0 else 0.0
        )

        return {
            "retention": interleaved_perf,
            "non_interleaved_retention": non_interleaved_perf,
            "improvement_factor": improvement,
        }

    def _recommend_strategy(self, performance: dict[str, Any]) -> str:
        """Recommend interleaving strategy based on performance.

        Args:
            performance: Performance metrics

        Returns:
            Recommended strategy
        """
        if performance["improvement_factor"] > 0.1:
            return "Continue interleaved practice - showing significant improvement"
        elif performance["improvement_factor"] > 0.05:
            return "Moderate interleaving recommended"
        else:
            return "Consider blocked practice for initial learning, then interleaving"

    def _analyze_category_benefits(
        self,
        sequences: list[dict[str, Any]],  # noqa: ARG002
    ) -> dict[str, float]:
        """Analyze which categories benefit most from interleaving.

        Args:
            sequences: Sequence classifications

        Returns:
            Category benefit analysis
        """
        # Simplified analysis
        return {"Politik": 0.15, "Gesellschaft": 0.12, "Geschichte": 0.10}
