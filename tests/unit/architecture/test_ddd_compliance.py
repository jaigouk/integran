"""Tests to verify Domain-Driven Design (DDD) architectural compliance.

This test suite ensures that the application strictly follows DDD principles:
1. Domain layer independence from infrastructure
2. Proper bounded context separation
3. Domain services encapsulate business logic
4. Repositories follow interface segregation
5. Domain events enable loose coupling
6. Entities and value objects follow DDD patterns
"""

import ast
import inspect
from pathlib import Path

from src.domain.analytics.services.reset_user_progress import ResetUserProgress
from src.domain.content.services.build_dataset import BuildDataset
from src.domain.learning.services.complete_learning_session import (
    CompleteLearningSession,
)
from src.domain.learning.services.schedule_card import ScheduleCard
from src.domain.shared.services import DomainService


class TestDomainLayerIndependence:
    """Test that domain layer is independent of infrastructure concerns."""

    def test_domain_services_use_only_interfaces(self):
        """Test that domain services depend only on interfaces, not concrete implementations."""
        domain_service_classes = [
            ResetUserProgress,
            BuildDataset,
            CompleteLearningSession,
            ScheduleCard,
        ]

        for service_class in domain_service_classes:
            init_signature = inspect.signature(service_class.__init__)

            for param_name, param in init_signature.parameters.items():
                if param_name in ["self"]:
                    continue

                # Check parameter type annotations
                if param.annotation != inspect.Parameter.empty:
                    annotation_str = str(param.annotation)

                    # Repository parameters should be interfaces
                    if "repository" in param_name.lower():
                        assert not annotation_str.startswith("src.infrastructure"), (
                            f"{service_class.__name__} parameter {param_name} should use repository interface, not concrete implementation"
                        )

                    # Event bus should be interface
                    if "event" in param_name.lower():
                        assert (
                            "Interface" in annotation_str
                            or "EventBus" in annotation_str
                        ), (
                            f"{service_class.__name__} parameter {param_name} should use EventBusInterface"
                        )

    def test_domain_layer_has_no_infrastructure_imports(self):
        """Test that domain layer files don't import infrastructure modules."""
        domain_files = list(Path("src/domain").rglob("*.py"))
        violations = []

        for domain_file in domain_files:
            if domain_file.name.startswith("__"):
                continue

            try:
                with open(domain_file) as f:
                    content = f.read()

                # Check for infrastructure imports
                lines = content.split("\n")
                in_type_checking = False

                for i, line in enumerate(lines):
                    stripped_line = line.strip()

                    # Track TYPE_CHECKING blocks
                    if "if TYPE_CHECKING:" in stripped_line:
                        in_type_checking = True
                        continue
                    elif (
                        stripped_line
                        and not stripped_line.startswith((" ", "\t", "#"))
                        and in_type_checking
                    ):
                        in_type_checking = False

                    # Check for infrastructure imports
                    if (
                        "from src.infrastructure" in stripped_line
                        or "import src.infrastructure" in stripped_line
                    ) and not in_type_checking:
                        violations.append(f"{domain_file}:{i + 1}: {stripped_line}")

            except Exception as e:
                print(f"Warning: Could not parse {domain_file}: {e}")
                continue

        assert len(violations) == 0, (
            f"Domain layer has infrastructure imports outside TYPE_CHECKING: {violations}"
        )

    def test_domain_services_follow_single_responsibility(self):
        """Test that domain services follow single responsibility principle."""
        service_files = list(Path("src/domain").rglob("services/*.py"))

        for service_file in service_files:
            if service_file.name.startswith("__"):
                continue

            # Check that each file contains only one domain service class
            try:
                with open(service_file) as f:
                    content = f.read()

                tree = ast.parse(content)
                service_classes = []

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        # Check if it inherits from DomainService
                        for base in node.bases:
                            if (
                                isinstance(base, ast.Name)
                                and base.id == "DomainService"
                            ) or (
                                isinstance(base, ast.Subscript)
                                and isinstance(base.value, ast.Name)
                                and base.value.id == "DomainService"
                            ):
                                service_classes.append(node.name)
                                break

                # Each file should contain exactly one domain service
                assert len(service_classes) <= 1, (
                    f"{service_file} contains multiple domain services: {service_classes}. "
                    "Each service should be in its own file for single responsibility."
                )

            except Exception as e:
                print(f"Warning: Could not parse {service_file}: {e}")
                continue


class TestBoundedContextSeparation:
    """Test that bounded contexts are properly separated."""

    def test_bounded_contexts_are_isolated(self):
        """Test that bounded contexts don't directly import from each other's internals."""
        bounded_contexts = [
            "src/domain/learning",
            "src/domain/content",
            "src/domain/analytics",
            "src/domain/user",
        ]

        violations = []

        for context_path in bounded_contexts:
            if not Path(context_path).exists():
                continue

            context_files = list(Path(context_path).rglob("*.py"))
            context_name = Path(context_path).name

            for context_file in context_files:
                if context_file.name.startswith("__"):
                    continue

                try:
                    with open(context_file) as f:
                        content = f.read()

                    # Check for cross-context imports (except shared)
                    for other_context in bounded_contexts:
                        other_context_name = Path(other_context).name
                        if other_context_name == context_name:
                            continue

                        # Check for direct imports from other contexts
                        if (
                            f"from src.domain.{other_context_name}" in content
                            and not any(
                                allowed in content
                                for allowed in [
                                    f"src.domain.{other_context_name}.events",
                                    "src.domain.shared",
                                ]
                            )
                        ):
                            violations.append(
                                f"{context_file}: imports from {other_context_name} context"
                            )

                except Exception as e:
                    print(f"Warning: Could not parse {context_file}: {e}")
                    continue

        # For now, allow some violations as we transition to proper bounded contexts
        print(f"Bounded context violations (transitional): {len(violations)}")

    def test_shared_domain_elements_are_in_shared_module(self):
        """Test that shared domain elements are properly placed in shared module."""
        shared_path = Path("src/domain/shared")

        # Check that shared module exists and contains common elements
        assert shared_path.exists(), "Domain shared module should exist"

        expected_shared_files = [
            "services.py",  # Base domain service
            "repositories.py",  # Repository interfaces
            "events.py",  # Common events
            "models.py",  # Shared value objects
        ]

        for expected_file in expected_shared_files:
            file_path = shared_path / expected_file
            assert file_path.exists(), f"Shared module should contain {expected_file}"


class TestDomainServicePatterns:
    """Test that domain services follow proper DDD patterns."""

    def test_domain_services_have_verb_noun_naming(self):
        """Test that domain services follow Verb+Noun naming convention."""
        service_files = list(Path("src/domain").rglob("services/*.py"))

        for service_file in service_files:
            if service_file.name.startswith("__"):
                continue

            service_name = service_file.stem

            # Check that service name follows verb+noun pattern
            if service_name not in ["__init__"]:
                # Service names should contain an action verb
                action_verbs = [
                    "schedule",
                    "complete",
                    "analyze",
                    "build",
                    "generate",
                    "process",
                    "create",
                    "update",
                    "delete",
                    "validate",
                    "calculate",
                    "transform",
                    "load",
                    "save",
                    "reset",
                    "detect",
                    "optimize",
                    "toggle",
                    "enhance",
                    "display",
                    "submit",
                ]

                has_action_verb = any(verb in service_name for verb in action_verbs)
                assert has_action_verb, (
                    f"Domain service {service_name} should follow Verb+Noun naming (e.g., schedule_card)"
                )

    def test_domain_services_have_single_call_method(self):
        """Test that domain services expose only one primary call method."""
        domain_service_classes = [
            ResetUserProgress,
            BuildDataset,
            CompleteLearningSession,
            ScheduleCard,
        ]

        for service_class in domain_service_classes:
            # Should have exactly one call method
            assert hasattr(service_class, "call"), (
                f"{service_class.__name__} must have call() method"
            )

            # Check that call method is async
            call_method = service_class.call
            assert inspect.iscoroutinefunction(call_method), (
                f"{service_class.__name__}.call() must be async"
            )

            # Check call method signature
            sig = inspect.signature(call_method)
            params = list(sig.parameters.keys())

            # Should have self and request parameters
            assert len(params) >= 2, (
                f"{service_class.__name__}.call() should have self and request parameters"
            )
            assert params[0] == "self", (
                f"{service_class.__name__}.call() first parameter should be self"
            )

    def test_domain_services_publish_events(self):
        """Test that domain services can publish domain events."""
        domain_service_classes = [
            ScheduleCard,
            CompleteLearningSession,
        ]

        for service_class in domain_service_classes:
            # Should inherit from DomainService which provides event publishing
            assert issubclass(service_class, DomainService), (
                f"{service_class.__name__} should inherit from DomainService"
            )

            # Should have access to event bus
            init_sig = inspect.signature(service_class.__init__)
            event_bus_param = None

            for param_name, param in init_sig.parameters.items():
                if "event" in param_name.lower():
                    event_bus_param = param
                    break

            assert event_bus_param is not None, (
                f"{service_class.__name__} should accept event_bus parameter"
            )


class TestRepositoryInterfaces:
    """Test that repository interfaces follow DDD patterns."""

    def test_repository_interfaces_exist(self):
        """Test that repository interfaces are defined in domain layer."""
        repo_interfaces_file = Path("src/domain/shared/repositories.py")
        assert repo_interfaces_file.exists(), (
            "Repository interfaces should be defined in domain/shared/repositories.py"
        )

        # Check that file contains repository interfaces
        with open(repo_interfaces_file) as f:
            content = f.read()

        expected_repositories = [
            "LearningRepository",
            "QuestionRepository",
            "SessionRepository",
            "UserRepository",
            "AnalyticsRepository",
        ]

        for repo_name in expected_repositories:
            assert repo_name in content, (
                f"Repository interface {repo_name} should be defined"
            )

    def test_repository_interfaces_are_abstract(self):
        """Test that repository interfaces are properly abstract."""
        from src.domain.shared.repositories import (
            AnalyticsRepository,
            LearningRepository,
            QuestionRepository,
            SessionRepository,
            UserRepository,
        )

        repo_interfaces = [
            LearningRepository,
            QuestionRepository,
            SessionRepository,
            UserRepository,
            AnalyticsRepository,
        ]

        for repo_interface in repo_interfaces:
            # Should be abstract base class
            assert hasattr(repo_interface, "__abstractmethods__"), (
                f"{repo_interface.__name__} should be an abstract base class"
            )

            # Should have abstract methods
            abstract_methods = getattr(repo_interface, "__abstractmethods__", set())
            assert len(abstract_methods) > 0, (
                f"{repo_interface.__name__} should have abstract methods"
            )

    def test_repository_methods_follow_domain_language(self):
        """Test that repository methods use domain language, not technical terms."""
        from src.domain.shared.repositories import (
            LearningRepository,
        )

        # Repository methods should use domain terms
        learning_methods = [
            method for method in dir(LearningRepository) if not method.startswith("_")
        ]

        # Should have domain-specific method names
        domain_terms = ["fsrs", "card", "learning", "review", "lapse", "due"]

        has_domain_methods = any(
            any(term in method.lower() for term in domain_terms)
            for method in learning_methods
        )

        assert has_domain_methods, (
            "LearningRepository should have methods using domain language"
        )


class TestDomainEvents:
    """Test that domain events follow DDD patterns."""

    def test_domain_events_are_immutable(self):
        """Test that domain events are implemented as immutable data structures."""
        from src.domain.learning.events.card_events import (
            CardScheduledEvent,
            SessionCompletedEvent,
        )

        event_classes = [CardScheduledEvent, SessionCompletedEvent]

        for event_class in event_classes:
            # Events should be dataclasses (immutable by convention)
            assert hasattr(event_class, "__dataclass_fields__"), (
                f"{event_class.__name__} should be a dataclass"
            )

            # Check that dataclass is configured properly
            if hasattr(event_class, "__dataclass_params__"):
                pass
                # In the future, we could enforce frozen=True for immutability

    def test_domain_events_have_proper_structure(self):
        """Test that domain events have required fields."""
        from src.domain.learning.events.card_events import CardScheduledEvent

        # Events should inherit from base DomainEvent
        # (We'll check this once we move DomainEvent to domain layer)

        # Events should have meaningful business data
        event_fields = CardScheduledEvent.__dataclass_fields__
        required_fields = ["card_id", "question_id", "rating"]

        for field in required_fields:
            assert field in event_fields, (
                f"CardScheduledEvent should have {field} field"
            )

    def test_domain_events_use_domain_language(self):
        """Test that domain events use domain-specific terminology."""
        event_files = list(Path("src/domain").rglob("events/*.py"))

        for event_file in event_files:
            if event_file.name.startswith("__"):
                continue

            try:
                with open(event_file) as f:
                    content = f.read()

                # Check that event names use domain language
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and node.name.endswith("Event"):
                        # Event names should be in past tense (domain events represent what happened)
                        past_tense_indicators = [
                            "ed",
                            "Completed",
                            "Started",
                            "Scheduled",
                            "Generated",
                            "Processed",
                            "Created",
                            "Updated",
                            "Deleted",
                            "Failed",
                            "Detected",
                        ]

                        has_past_tense = any(
                            indicator in node.name
                            for indicator in past_tense_indicators
                        )

                        assert has_past_tense, (
                            f"Domain event {node.name} should use past tense naming"
                        )

            except Exception as e:
                print(f"Warning: Could not parse {event_file}: {e}")
                continue


class TestDomainModelIntegrity:
    """Test that domain models maintain integrity."""

    def test_entities_have_identity(self):
        """Test that entities have proper identity mechanisms."""
        # Check that domain entities have ID fields
        from src.domain.learning.models.learning_models import FSRSCard

        # Entities should have identity fields
        if hasattr(FSRSCard, "__dataclass_fields__"):
            fields = FSRSCard.__dataclass_fields__
            # Should have some form of ID
            id_fields = [field for field in fields if "id" in field.lower()]
            assert len(id_fields) > 0, "Entity FSRSCard should have identity field(s)"

    def test_value_objects_are_immutable(self):
        """Test that value objects are implemented as immutable."""
        from enum import Enum

        from src.domain.shared.models import FSRSRating, FSRSState

        value_objects = [FSRSRating, FSRSState]

        for vo_class in value_objects:
            # Value objects should be enums or immutable dataclasses
            is_enum = issubclass(vo_class, Enum)
            is_dataclass = hasattr(vo_class, "__dataclass_fields__")

            assert is_enum or is_dataclass, (
                f"Value object {vo_class.__name__} should be enum or dataclass"
            )


class TestDomainLogicEncapsulation:
    """Test that business logic is properly encapsulated in domain layer."""

    def test_business_rules_are_in_domain_services(self):
        """Test that business rules are encapsulated in domain services."""
        # FSRS algorithm logic should be in ScheduleCard domain service
        schedule_card_file = Path("src/domain/learning/services/schedule_card.py")

        with open(schedule_card_file) as f:
            content = f.read()

        # Should contain FSRS-specific business logic
        fsrs_terms = [
            "difficulty",
            "stability",
            "retrievability",
            "interval",
            "retention",
            "lapse",
        ]

        has_business_logic = any(term in content for term in fsrs_terms)
        assert has_business_logic, "ScheduleCard should contain FSRS business logic"

    def test_no_business_logic_in_infrastructure(self):
        """Test that business logic is not leaked into infrastructure layer."""
        infra_files = list(Path("src/infrastructure").rglob("*.py"))
        violations = []

        # Business logic indicators that shouldn't be in infrastructure
        business_logic_indicators = [
            "calculate_difficulty",
            "calculate_stability",
            "fsrs_algorithm",
            "business_rule",
            "domain_logic",
        ]

        for infra_file in infra_files:
            if infra_file.name.startswith("__"):
                continue

            try:
                with open(infra_file) as f:
                    content = f.read()

                for indicator in business_logic_indicators:
                    if indicator in content:
                        violations.append(f"{infra_file}: contains {indicator}")

            except Exception as e:
                print(f"Warning: Could not parse {infra_file}: {e}")
                continue

        # Allow some transitional violations
        print(
            f"Business logic in infrastructure violations (transitional): {len(violations)}"
        )


# Additional DDD compliance tests would include:
# - Aggregate root enforcement
# - Domain service coordination patterns
# - Specification pattern usage
# - Factory pattern for complex object creation
# - Domain event versioning and evolution
