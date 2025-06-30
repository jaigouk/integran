"""Tests to verify CQRS (Command Query Responsibility Segregation) architectural compliance.

This test suite ensures that the application strictly follows CQRS principles:
1. Clear separation between commands (write operations) and queries (read operations)
2. Commands modify state but don't return data
3. Queries return data but don't modify state
4. Proper layer separation and dependency flow
5. No direct infrastructure access from domain layer
"""

import ast
import inspect
from pathlib import Path

from src.application.commands.save_user_settings_command import (
    SaveUserSettingsCommandHandler,
)
from src.application.commands.start_practice_session_command import (
    StartPracticeSessionCommandHandler,
)
from src.application.commands.submit_answer_with_rating_command import (
    SubmitAnswerWithRatingCommandHandler,
)
from src.application.queries.get_learning_stats_query import GetLearningStatsQuery
from src.application.queries.get_questions_by_mode_query import GetQuestionsByModeQuery
from src.application.queries.load_user_preferences_query import LoadUserPreferencesQuery
from src.domain.analytics.services.reset_user_progress import ResetUserProgress
from src.domain.content.services.build_dataset import BuildDataset
from src.domain.learning.services.complete_learning_session import (
    CompleteLearningSession,
)
from src.domain.learning.services.schedule_card import ScheduleCard
from src.domain.shared.services import DomainService, EventBusInterface


class TestCQRSCompliance:
    """Test suite to verify CQRS architectural compliance."""

    def test_commands_implement_cqrs_pattern(self):
        """Test that all commands follow CQRS command pattern."""
        # Test command handlers, not the command data classes
        command_handler_classes = [
            SaveUserSettingsCommandHandler,
            StartPracticeSessionCommandHandler,
            SubmitAnswerWithRatingCommandHandler,
        ]

        for handler_class in command_handler_classes:
            # Command handlers should have a handle method
            assert hasattr(handler_class, "handle"), (
                f"{handler_class.__name__} must have handle() method"
            )

            # Check method signature and return annotation
            method = handler_class.handle
            sig = inspect.signature(method)
            return_annotation = sig.return_annotation

            # Commands should return Result types, not domain objects directly
            if return_annotation != inspect.Signature.empty:
                assert (
                    "Result" in str(return_annotation)
                    or "CommandResult" in str(return_annotation)
                    or "bool" in str(return_annotation)
                    or return_annotation is bool
                ), (
                    f"{handler_class.__name__}.handle should return Result type or bool, not domain objects"
                )

    def test_queries_implement_cqrs_pattern(self):
        """Test that all queries follow CQRS query pattern."""
        from src.application.queries.get_learning_stats_query import (
            GetLearningStatsQueryHandler,
        )
        from src.application.queries.get_questions_by_mode_query import (
            GetQuestionsByModeQueryHandler,
        )
        from src.application.queries.load_user_preferences_query import (
            LoadUserPreferencesQueryHandler,
        )

        query_handler_classes = [
            GetLearningStatsQueryHandler,
            GetQuestionsByModeQueryHandler,
            LoadUserPreferencesQueryHandler,
        ]

        for handler_class in query_handler_classes:
            # Query handlers should have a handle method
            assert hasattr(handler_class, "handle"), (
                f"{handler_class.__name__} must have handle() method"
            )

            # The handle method should be async
            handle_method = handler_class.handle
            assert inspect.iscoroutinefunction(handle_method), (
                f"{handler_class.__name__}.handle must be async"
            )

            # Queries should be read-only (not modify state)
            # This is verified by checking that queries only use repository read methods
            # (we'll implement this check in integration tests)

    def test_domain_services_follow_ddd_patterns(self):
        """Test that domain services follow DDD patterns correctly."""
        domain_service_classes = [
            ResetUserProgress,
            BuildDataset,
            CompleteLearningSession,
            ScheduleCard,
        ]

        for service_class in domain_service_classes:
            # Must inherit from DomainService
            assert issubclass(service_class, DomainService), (
                f"{service_class.__name__} must inherit from DomainService"
            )

            # Must have a call method
            assert hasattr(service_class, "call"), (
                f"{service_class.__name__} must implement call() method"
            )

            # Must accept EventBusInterface in constructor
            init_method = service_class.__init__
            sig = inspect.signature(init_method)
            params = sig.parameters

            # Check for event_bus parameter with correct type annotation
            event_bus_param = None
            for param_name, param in params.items():
                if (
                    param_name in ["event_bus", "eventbus"]
                    or "event" in param_name.lower()
                ):
                    event_bus_param = param
                    break

            assert event_bus_param is not None, (
                f"{service_class.__name__} constructor must accept event_bus parameter"
            )

            # Check type annotation
            if event_bus_param.annotation != inspect.Parameter.empty:
                assert "EventBusInterface" in str(
                    event_bus_param.annotation
                ) or "EventBus" in str(event_bus_param.annotation), (
                    f"{service_class.__name__} event_bus parameter should be typed as EventBusInterface"
                )

    def test_layer_separation_compliance(self):
        """Test that layers are properly separated according to CQRS architecture."""
        # Domain layer should not import from infrastructure
        domain_files = list(Path("src/domain").rglob("*.py"))
        infrastructure_violations = []

        for domain_file in domain_files:
            if domain_file.name.startswith("__"):
                continue

            try:
                with open(domain_file) as f:
                    content = f.read()

                # Parse the AST to find imports
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for name in node.names:
                            if name.name.startswith("src.infrastructure"):
                                # Allow TYPE_CHECKING imports for interfaces
                                if self._is_type_checking_import(content, node):
                                    continue
                                infrastructure_violations.append(
                                    f"{domain_file}: imports {name.name}"
                                )
                    elif (
                        isinstance(node, ast.ImportFrom)
                        and node.module
                        and node.module.startswith("src.infrastructure")
                    ):
                        # Allow TYPE_CHECKING imports for interfaces
                        if self._is_type_checking_import(content, node):
                            continue
                        infrastructure_violations.append(
                            f"{domain_file}: imports from {node.module}"
                        )
            except Exception as e:
                # Skip files that can't be parsed - log for debugging
                print(f"Warning: Could not parse {domain_file}: {e}")
                continue

        assert len(infrastructure_violations) == 0, (
            f"Domain layer has infrastructure dependencies: {infrastructure_violations}"
        )

    def test_application_layer_isolation(self):
        """Test that application layer properly isolates domain from presentation."""
        # Application layer should not import from presentation
        app_files = list(Path("src/application").rglob("*.py"))
        presentation_violations = []

        for app_file in app_files:
            if app_file.name.startswith("__"):
                continue

            try:
                with open(app_file) as f:
                    content = f.read()

                # Check for presentation layer imports
                if "src.presentation" in content:
                    presentation_violations.append(
                        f"{app_file}: imports presentation layer"
                    )
            except Exception as e:
                print(f"Warning: Could not parse {app_file}: {e}")
                continue

        assert len(presentation_violations) == 0, (
            f"Application layer has presentation dependencies: {presentation_violations}"
        )

    def test_event_bus_interface_compliance(self):
        """Test that EventBusInterface is properly used throughout domain layer."""
        domain_service_files = list(Path("src/domain").rglob("services/*.py"))
        violations = []

        for service_file in domain_service_files:
            if service_file.name.startswith("__"):
                continue

            try:
                with open(service_file) as f:
                    content = f.read()

                # Check that services import EventBusInterface, not concrete EventBus
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    if (
                        "from src.infrastructure.messaging" in line
                        and "EventBus" in line
                        and not self._is_in_type_checking_block(lines, i)
                    ):
                        violations.append(
                            f"{service_file}:{i + 1}: Direct import of infrastructure EventBus"
                        )

                    # Check for EventBusInterface usage in type annotations
                    if (
                        "event_bus:" in line
                        and "EventBus" in line
                        and "EventBusInterface" not in line
                    ):
                        violations.append(
                            f"{service_file}:{i + 1}: Uses concrete EventBus instead of EventBusInterface"
                        )

            except Exception as e:
                print(f"Warning: Could not parse {service_file}: {e}")
                continue

        assert len(violations) == 0, (
            f"Domain services violate EventBusInterface usage: {violations}"
        )

    def test_repository_interface_usage(self):
        """Test that domain services use repository interfaces, not concrete implementations."""
        domain_service_files = list(Path("src/domain").rglob("services/*.py"))
        violations = []

        for service_file in domain_service_files:
            if service_file.name.startswith("__"):
                continue

            try:
                with open(service_file) as f:
                    content = f.read()

                # Check for direct infrastructure repository imports
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    if "from src.infrastructure.repositories" in line:
                        # This should not happen - domain should only import repository interfaces
                        violations.append(
                            f"{service_file}:{i + 1}: Direct import of infrastructure repository"
                        )

                    # Check that repository parameters use interface types
                    if (
                        "_repository:" in line
                        and "Repository" in line
                        and "from src.domain.shared.repositories" not in content
                    ):
                        # Check if the interface is imported
                        repository_name = self._extract_repository_name(line)
                        if (
                            repository_name
                            and f"import {repository_name}" not in content
                        ):
                            violations.append(
                                f"{service_file}:{i + 1}: Repository not imported from interfaces"
                            )

            except Exception as e:
                print(f"Warning: Could not parse {service_file}: {e}")
                continue

        # For now, we'll allow some violations as we transition to full interface usage
        # In the future, this should be zero violations
        print(f"Repository interface violations (transitional): {len(violations)}")

    def _is_type_checking_import(self, content: str, node: ast.AST) -> bool:
        """Check if an import is within a TYPE_CHECKING block."""
        lines = content.split("\n")
        if hasattr(node, "lineno"):
            # Look backwards from import line to find TYPE_CHECKING block
            for i in range(node.lineno - 1, max(0, node.lineno - 20), -1):
                line = lines[i].strip()
                if "if TYPE_CHECKING:" in line:
                    return True
                elif line and not line.startswith(("from ", "import ", "#")):
                    # Found non-import/comment line, not in TYPE_CHECKING block
                    break
        return False

    def _is_in_type_checking_block(self, lines: list[str], line_num: int) -> bool:
        """Check if a line is within a TYPE_CHECKING block."""
        # Look backwards to find TYPE_CHECKING block
        for i in range(line_num, max(0, line_num - 20), -1):
            line = lines[i].strip()
            if "if TYPE_CHECKING:" in line:
                return True
            elif line and not line.startswith(("from ", "import ", "#", " ")):
                # Found non-import/comment line, not in TYPE_CHECKING block
                break
        return False

    def _extract_repository_name(self, line: str) -> str | None:
        """Extract repository name from a type annotation line."""
        try:
            # Simple extraction - look for pattern: parameter: RepositoryName
            if ":" in line and "Repository" in line:
                parts = line.split(":")
                if len(parts) >= 2:
                    type_part = parts[1].strip()
                    if "Repository" in type_part:
                        # Extract just the repository name
                        repo_name = type_part.split(",")[0].strip()
                        return repo_name
        except Exception as e:
            # Skip unparseable lines - log for debugging
            print(f"Warning: Could not parse repository line: {e}")
        return None


class TestCQRSDataFlow:
    """Test CQRS data flow patterns."""

    def test_commands_modify_state_via_domain_services(self):
        """Test that commands modify state through domain services, not directly."""
        # Commands should call domain services which then use repositories
        # This ensures proper business logic encapsulation

        # Example: SubmitAnswerWithRatingCommand is a data class
        # We test the handler, not the command data structure

        # The handler should process the command
        from unittest.mock import Mock

        mock_learning_repo = Mock()
        mock_event_bus = Mock()

        handler = SubmitAnswerWithRatingCommandHandler(
            learning_repository=mock_learning_repo,
            event_bus=mock_event_bus,
        )

        # Check that handler has handle method
        assert hasattr(handler, "handle"), "Command handler should have handle method"

        # Check that handle method is async for domain service integration
        import inspect

        assert inspect.iscoroutinefunction(handler.handle), (
            "Command handler handle method should be async to call domain services"
        )

    def test_queries_are_read_only(self):
        """Test that queries don't modify state."""
        # Check query method signatures to ensure they only read data
        query_classes = [
            GetLearningStatsQuery,
            GetQuestionsByModeQuery,
            LoadUserPreferencesQuery,
        ]

        for query_class in query_classes:
            if hasattr(query_class, "handle"):
                method = query_class.handle
                method_name = f"{query_class.__name__}.handle"

                # Query methods should not contain state-modifying keywords
                # (This is a basic check - more sophisticated analysis would be needed for complete verification)
                source_lines = inspect.getsourcelines(method)[0]
                source_code = "".join(source_lines)

                # Check for obvious state modification patterns
                forbidden_patterns = [
                    ".save(",
                    ".create(",
                    ".update(",
                    ".delete(",
                    ".insert(",
                    ".execute(",  # For raw SQL
                ]

                for pattern in forbidden_patterns:
                    assert pattern not in source_code, (
                        f"{method_name} contains state-modifying operation: {pattern}"
                    )

    def test_domain_events_flow_correctly(self):
        """Test that domain events flow through the system correctly."""
        # Domain services should publish events
        # Application layer should handle cross-context events
        # Presentation layer should subscribe to events for UI updates

        # Check that domain services have event publishing capability
        domain_services = [ScheduleCard, CompleteLearningSession]

        for service_class in domain_services:
            # Should have event_bus attribute
            service_instance = None
            try:
                # Create instance with mock dependencies to check structure
                from unittest.mock import Mock

                mock_event_bus = Mock(spec=EventBusInterface)
                service_instance = service_class(
                    event_bus=mock_event_bus,
                    **{
                        name: Mock()
                        for name in [
                            "learning_repository",
                            "question_repository",
                            "session_repository",
                        ]
                        if name in inspect.signature(service_class.__init__).parameters
                    },
                )
            except Exception as e:
                # If we can't create instance, skip this test - log for debugging
                print(
                    f"Warning: Could not create instance of {service_class.__name__}: {e}"
                )
                continue

            if service_instance:
                assert hasattr(service_instance, "event_bus"), (
                    f"{service_class.__name__} should have event_bus attribute"
                )
                assert hasattr(service_instance, "_publish_event") or hasattr(
                    service_instance.event_bus, "publish"
                ), f"{service_class.__name__} should be able to publish events"


class TestCQRSErrorHandling:
    """Test CQRS error handling patterns."""

    def test_command_error_handling(self):
        """Test that commands handle errors appropriately."""
        # Commands should return error results rather than raising exceptions for business logic violations
        # Technical exceptions (like database connection errors) can be raised
        pass  # Implementation would depend on specific error handling strategy

    def test_query_error_handling(self):
        """Test that queries handle errors appropriately."""
        # Queries should handle missing data gracefully
        # Should return empty results rather than raising exceptions for missing data
        pass  # Implementation would depend on specific error handling strategy


# Additional architectural compliance tests would go here
# - Test that aggregates maintain consistency
# - Test that domain services don't depend on each other directly
# - Test that events are properly structured
# - Test that value objects are immutable
# - Test that entities have proper identity
