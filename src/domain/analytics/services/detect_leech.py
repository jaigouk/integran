"""Leech detection and intervention system.

This module identifies difficult questions (leeches) that require special attention
and provides intervention strategies to help users overcome learning obstacles.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.infrastructure.database.database import DatabaseManager

from src.domain.content.models.question_models import Question
from src.domain.learning.models.learning_models import (
    FSRSCard,
    LeechCard,
    ReviewHistory,
)


class LeechSeverity(str, Enum):
    """Severity levels for leech cards."""

    MILD = "mild"  # 3-5 lapses
    MODERATE = "moderate"  # 6-8 lapses
    SEVERE = "severe"  # 9+ lapses


class InterventionType(str, Enum):
    """Types of interventions for leech cards."""

    ADDITIONAL_PRACTICE = "additional_practice"
    SPACED_REPETITION = "spaced_repetition"
    CONCEPT_BREAKDOWN = "concept_breakdown"
    MNEMONIC_SUGGESTION = "mnemonic_suggestion"
    SUSPEND_TEMPORARILY = "suspend_temporarily"
    EXPERT_EXPLANATION = "expert_explanation"


@dataclass
class LeechAnalysis:
    """Analysis of a leech card."""

    card: FSRSCard
    question: Question
    severity: LeechSeverity
    lapse_count: int
    success_rate: float
    average_response_time: float
    difficulty_trend: str  # "increasing", "stable", "decreasing"
    common_mistakes: list[str]
    last_success_date: datetime | None
    intervention_history: list[InterventionType]


@dataclass
class InterventionStrategy:
    """Recommended intervention strategy for a leech."""

    intervention_type: InterventionType
    priority: int  # 1=highest, 5=lowest
    description: str
    estimated_effectiveness: float  # 0.0-1.0
    time_investment: str  # "low", "medium", "high"
    success_rate: float  # Historical success rate of this intervention


@dataclass
class LeechReport:
    """Comprehensive leech detection report."""

    user_id: int
    total_leeches: int
    new_leeches: int  # Detected since last report
    resolved_leeches: int  # No longer problematic
    by_severity: dict[LeechSeverity, int]
    by_category: dict[str, int]
    intervention_recommendations: list[tuple[LeechAnalysis, list[InterventionStrategy]]]
    overall_leech_rate: float  # Percentage of total cards
    trend: str  # "improving", "stable", "worsening"


class LeechDetector:
    """Advanced leech detection and intervention system."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize leech detector.

        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager

    def detect_leeches(
        self,
        user_id: int = 1,
        threshold: int = 8,
        force_redetection: bool = False,
    ) -> list[LeechAnalysis]:
        """Detect leech cards using advanced criteria.

        Args:
            user_id: User ID
            threshold: Minimum lapse count for leech detection
            force_redetection: Whether to re-analyze existing leeches

        Returns:
            List of leech analyses
        """
        leeches = []

        with self.db_manager.get_session() as session:
            # Get cards with high lapse counts
            potential_leeches = (
                session.query(FSRSCard)
                .filter(
                    FSRSCard.user_id == user_id,
                    FSRSCard.lapse_count >= threshold,
                )
                .all()
            )

            for card in potential_leeches:
                # Skip if already analyzed and not forcing redetection
                if not force_redetection:
                    existing = (
                        session.query(LeechCard).filter_by(card_id=card.card_id).first()
                    )
                    if existing:
                        continue

                # Analyze the card
                analysis = self._analyze_leech_card(card, session)
                if analysis:
                    leeches.append(analysis)

                    # Record in database if new
                    if force_redetection or not existing:
                        leech_record = LeechCard(
                            card_id=card.card_id,
                            question_id=card.question_id,
                            lapse_count=card.lapse_count,
                            leech_threshold=threshold,
                            detected_at=datetime.now(UTC).timestamp(),
                        )
                        session.add(leech_record)

            session.commit()

        return leeches

    def get_intervention_strategies(
        self, analysis: LeechAnalysis
    ) -> list[InterventionStrategy]:
        """Get recommended intervention strategies for a leech.

        Args:
            analysis: Leech analysis

        Returns:
            List of intervention strategies ordered by priority
        """
        strategies = []

        # Strategy 1: Additional spaced practice
        if analysis.success_rate < 0.3:
            strategies.append(
                InterventionStrategy(
                    intervention_type=InterventionType.ADDITIONAL_PRACTICE,
                    priority=1,
                    description="Increase review frequency with shorter intervals",
                    estimated_effectiveness=0.7,
                    time_investment="medium",
                    success_rate=0.65,
                )
            )

        # Strategy 2: Concept breakdown
        if analysis.severity in [LeechSeverity.MODERATE, LeechSeverity.SEVERE]:
            strategies.append(
                InterventionStrategy(
                    intervention_type=InterventionType.CONCEPT_BREAKDOWN,
                    priority=2,
                    description="Break complex concept into smaller, manageable parts",
                    estimated_effectiveness=0.8,
                    time_investment="high",
                    success_rate=0.75,
                )
            )

        # Strategy 3: Mnemonic suggestion
        if analysis.average_response_time > 10000:  # >10 seconds
            strategies.append(
                InterventionStrategy(
                    intervention_type=InterventionType.MNEMONIC_SUGGESTION,
                    priority=3,
                    description="Create memory aid or mnemonic device",
                    estimated_effectiveness=0.6,
                    time_investment="low",
                    success_rate=0.55,
                )
            )

        # Strategy 4: Expert explanation
        if analysis.question.category in ["Politik", "Geschichte"]:  # Complex topics
            strategies.append(
                InterventionStrategy(
                    intervention_type=InterventionType.EXPERT_EXPLANATION,
                    priority=2,
                    description="Provide detailed expert explanation with context",
                    estimated_effectiveness=0.75,
                    time_investment="medium",
                    success_rate=0.70,
                )
            )

        # Strategy 5: Temporary suspension (last resort)
        if analysis.severity == LeechSeverity.SEVERE and analysis.success_rate < 0.2:
            strategies.append(
                InterventionStrategy(
                    intervention_type=InterventionType.SUSPEND_TEMPORARILY,
                    priority=5,
                    description="Temporarily suspend and revisit after other concepts are mastered",
                    estimated_effectiveness=0.5,
                    time_investment="low",
                    success_rate=0.60,
                )
            )

        return sorted(strategies, key=lambda s: s.priority)

    def generate_leech_report(self, user_id: int = 1) -> LeechReport:
        """Generate comprehensive leech report.

        Args:
            user_id: User ID

        Returns:
            Comprehensive leech report
        """
        current_leeches = self.detect_leeches(user_id)

        # Calculate statistics
        severity_counts = dict.fromkeys(LeechSeverity, 0)
        category_counts: dict[str, int] = {}

        for analysis in current_leeches:
            severity_counts[analysis.severity] += 1
            category = str(analysis.question.category)
            category_counts[category] = category_counts.get(category, 0) + 1

        # Get intervention recommendations
        recommendations = []
        for analysis in current_leeches:
            strategies = self.get_intervention_strategies(analysis)
            recommendations.append((analysis, strategies))

        # Calculate overall leech rate
        with self.db_manager.get_session() as session:
            total_cards = session.query(FSRSCard).filter_by(user_id=user_id).count()

        leech_rate = len(current_leeches) / total_cards if total_cards > 0 else 0

        # Determine trend (simplified)
        trend = "stable"
        if leech_rate > 0.15:  # >15% leeches
            trend = "worsening"
        elif leech_rate < 0.05:  # <5% leeches
            trend = "improving"

        return LeechReport(
            user_id=user_id,
            total_leeches=len(current_leeches),
            new_leeches=len(current_leeches),  # TODO: Calculate actual new leeches
            resolved_leeches=0,  # TODO: Calculate resolved leeches
            by_severity=severity_counts,
            by_category=category_counts,
            intervention_recommendations=recommendations,
            overall_leech_rate=round(leech_rate, 3),
            trend=trend,
        )

    def apply_intervention(
        self,
        card_id: int,
        intervention_type: InterventionType,
        notes: str = "",
    ) -> bool:
        """Apply an intervention to a leech card.

        Args:
            card_id: Card ID
            intervention_type: Type of intervention
            notes: Optional notes about the intervention

        Returns:
            True if intervention was applied successfully
        """
        with self.db_manager.get_session() as session:
            leech = session.query(LeechCard).filter_by(card_id=card_id).first()
            if not leech:
                return False

            # Record intervention
            leech.action_taken = intervention_type.value
            leech.action_date = datetime.now(UTC).timestamp()
            leech.user_notes = notes

            # Apply specific intervention logic
            if intervention_type == InterventionType.SUSPEND_TEMPORARILY:
                leech.is_suspended = True
                # Also update the FSRS card to prevent it from appearing
                card = session.query(FSRSCard).filter_by(card_id=card_id).first()
                if card:
                    # Set next review to far future
                    card.next_review_date = (
                        datetime.now(UTC) + timedelta(days=90)
                    ).timestamp()

            elif intervention_type == InterventionType.ADDITIONAL_PRACTICE:
                # Reduce stability to increase review frequency
                card = session.query(FSRSCard).filter_by(card_id=card_id).first()
                if card:
                    card.stability = max(0.1, float(card.stability) * 0.5)
                    card.next_review_date = datetime.now(UTC).timestamp()

            session.commit()
            return True

    def get_leech_statistics(self, user_id: int = 1) -> dict[str, Any]:
        """Get overall leech statistics.

        Args:
            user_id: User ID

        Returns:
            Leech statistics
        """
        with self.db_manager.get_session() as session:
            # Get all leeches
            leeches = (
                session.query(LeechCard)
                .join(FSRSCard)
                .filter(FSRSCard.user_id == user_id)
                .all()
            )

            total_cards = session.query(FSRSCard).filter_by(user_id=user_id).count()

            # Calculate statistics
            active_leeches = [leech for leech in leeches if not leech.is_suspended]
            suspended_leeches = [leech for leech in leeches if leech.is_suspended]

            avg_lapse_count = (
                sum(leech.lapse_count for leech in leeches) / len(leeches)
                if leeches
                else 0
            )

            # Get category breakdown
            category_stats = {}
            for leech in leeches:
                question = (
                    session.query(Question).filter_by(id=leech.question_id).first()
                )
                if question:
                    category = question.category
                    if category not in category_stats:
                        category_stats[category] = {
                            "total": 0,
                            "active": 0,
                            "suspended": 0,
                        }
                    category_stats[category]["total"] += 1
                    if leech.is_suspended:
                        category_stats[category]["suspended"] += 1
                    else:
                        category_stats[category]["active"] += 1

        return {
            "total_leeches": len(leeches),
            "active_leeches": len(active_leeches),
            "suspended_leeches": len(suspended_leeches),
            "leech_rate": len(leeches) / total_cards if total_cards > 0 else 0,
            "average_lapse_count": round(avg_lapse_count, 1),
            "category_breakdown": category_stats,
            "intervention_success_rate": self._calculate_intervention_success_rate(
                user_id
            ),
        }

    def _analyze_leech_card(self, card: FSRSCard, session: Any) -> LeechAnalysis | None:
        """Analyze a potential leech card.

        Args:
            card: FSRS card to analyze
            session: Database session

        Returns:
            Leech analysis or None if not a leech
        """
        # Get question
        question = session.query(Question).filter_by(id=card.question_id).first()
        if not question:
            return None

        # Get review history
        reviews = (
            session.query(ReviewHistory)
            .filter_by(card_id=card.card_id)
            .order_by(ReviewHistory.review_date.desc())
            .all()
        )

        if not reviews:
            return None

        # Calculate success rate
        successful_reviews = sum(1 for r in reviews if r.rating >= 3)
        success_rate = successful_reviews / len(reviews)

        # Calculate average response time
        response_times = [r.response_time_ms for r in reviews if r.response_time_ms]
        avg_response_time = (
            sum(response_times) / len(response_times) if response_times else 0
        )

        # Determine severity
        severity = self._categorize_by_difficulty(int(card.lapse_count), success_rate)

        # Analyze difficulty trend (simplified)
        recent_reviews = reviews[:5]  # Last 5 reviews
        if len(recent_reviews) >= 3:
            recent_success = sum(1 for r in recent_reviews if r.rating >= 3)
            older_reviews = reviews[5:10] if len(reviews) > 5 else []
            if older_reviews:
                older_success = sum(1 for r in older_reviews if r.rating >= 3)
                older_rate = older_success / len(older_reviews)
                recent_rate = recent_success / len(recent_reviews)

                if recent_rate > older_rate + 0.2:
                    difficulty_trend = "decreasing"
                elif recent_rate < older_rate - 0.2:
                    difficulty_trend = "increasing"
                else:
                    difficulty_trend = "stable"
            else:
                difficulty_trend = "stable"
        else:
            difficulty_trend = "stable"

        # Find last success
        last_success = None
        for review in reviews:
            if review.rating >= 3:
                last_success = datetime.fromtimestamp(review.review_date, UTC)
                break

        return LeechAnalysis(
            card=card,
            question=question,
            severity=severity,
            lapse_count=int(card.lapse_count),
            success_rate=success_rate,
            average_response_time=avg_response_time,
            difficulty_trend=difficulty_trend,
            common_mistakes=[],  # TODO: Analyze common wrong answers
            last_success_date=last_success,
            intervention_history=[],  # TODO: Track intervention history
        )

    def _categorize_by_difficulty(
        self, lapse_count: int, success_rate: float
    ) -> LeechSeverity:
        """Categorize leech severity based on lapse count and success rate.

        Args:
            lapse_count: Number of lapses
            success_rate: Success rate (0.0 to 1.0)

        Returns:
            Leech severity level
        """
        # Primary categorization by lapse count
        if lapse_count >= 9:
            severity = LeechSeverity.SEVERE
        elif lapse_count >= 6:
            severity = LeechSeverity.MODERATE
        else:
            severity = LeechSeverity.MILD

        # Adjust based on success rate for borderline cases
        if success_rate < 0.2 and severity == LeechSeverity.MODERATE:
            severity = LeechSeverity.SEVERE
        elif success_rate > 0.6 and severity == LeechSeverity.MODERATE:
            severity = LeechSeverity.MILD

        return severity

    def _calculate_intervention_success_rate(self, user_id: int) -> float:
        """Calculate success rate of interventions.

        Args:
            user_id: User ID

        Returns:
            Intervention success rate
        """
        with self.db_manager.get_session() as session:
            # Get leeches with interventions
            treated_leeches = (
                session.query(LeechCard)
                .join(FSRSCard)
                .filter(
                    FSRSCard.user_id == user_id,
                    LeechCard.action_taken.isnot(None),
                )
                .all()
            )

            if not treated_leeches:
                return 0.0

            # Check how many improved after intervention
            improved = 0
            for leech in treated_leeches:
                # Check if lapse count decreased after intervention
                card = session.query(FSRSCard).filter_by(card_id=leech.card_id).first()
                if card and leech.action_date:
                    # Get reviews after intervention
                    post_intervention_reviews = (
                        session.query(ReviewHistory)
                        .filter(
                            ReviewHistory.card_id == card.card_id,
                            ReviewHistory.review_date > leech.action_date,
                        )
                        .all()
                    )

                    if post_intervention_reviews:
                        success_count = sum(
                            1 for r in post_intervention_reviews if r.rating >= 3
                        )
                        if success_count / len(post_intervention_reviews) > 0.5:
                            improved += 1

            return improved / len(treated_leeches)
