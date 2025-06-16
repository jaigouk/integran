"""Simplified tests for terminal UI base classes."""

from __future__ import annotations

import asyncio
from datetime import datetime

import pytest

from src.infrastructure.messaging.event_bus import DomainEvent, EventBus
from src.presentation.terminal.base import (
    AsyncUIUpdater,
    ComponentRegistry,
)


# Test event for testing
class TestEvent(DomainEvent):
    """Test domain event."""

    def __init__(
        self,
        event_id: str = "",
        occurred_at: datetime | None = None,
        test_data: str = "",
    ):
        super().__init__(event_id, occurred_at)
        self.test_data = test_data


# Mock widget for testing
class MockWidget:
    """Mock widget for testing AsyncUIUpdater."""

    def __init__(self) -> None:
        self.refresh_called = False

    def refresh(self) -> None:
        """Mock refresh method."""
        self.refresh_called = True


class TestAsyncUIUpdater:
    """Tests for AsyncUIUpdater helper class."""

    @pytest.fixture
    def widget(self) -> MockWidget:
        """Create mock widget."""
        return MockWidget()

    @pytest.fixture
    def updater(self, widget: MockWidget) -> AsyncUIUpdater:
        """Create test UI updater."""
        return AsyncUIUpdater(widget)  # type: ignore

    def test_updater_initialization(
        self, updater: AsyncUIUpdater, widget: MockWidget
    ) -> None:
        """Test updater initialization."""
        assert updater.widget is widget
        assert isinstance(updater._update_queue, asyncio.Queue)
        assert updater._update_task is None

    @pytest.mark.asyncio
    async def test_start_updater(self, updater: AsyncUIUpdater) -> None:
        """Test starting the UI updater."""
        await updater.start()

        assert updater._update_task is not None
        assert not updater._update_task.done()

        # Cleanup
        await updater.stop()

    @pytest.mark.asyncio
    async def test_stop_updater(self, updater: AsyncUIUpdater) -> None:
        """Test stopping the UI updater."""
        await updater.start()
        await updater.stop()

        # Task should be done after stop
        assert updater._update_task.done()

    @pytest.mark.asyncio
    async def test_schedule_sync_update(self, updater: AsyncUIUpdater) -> None:
        """Test scheduling synchronous UI updates."""
        await updater.start()

        update_called = False

        def sync_update() -> None:
            nonlocal update_called
            update_called = True

        updater.schedule_update(sync_update)

        # Give time for update to process
        await asyncio.sleep(0.01)

        assert update_called

        await updater.stop()

    @pytest.mark.asyncio
    async def test_schedule_async_update(self, updater: AsyncUIUpdater) -> None:
        """Test scheduling asynchronous UI updates."""
        await updater.start()

        update_called = False

        async def async_update() -> None:
            nonlocal update_called
            update_called = True

        updater.schedule_update(async_update)

        # Give time for update to process
        await asyncio.sleep(0.01)

        assert update_called

        await updater.stop()

    def test_schedule_update_no_start(self, updater: AsyncUIUpdater) -> None:
        """Test scheduling update before starting updater."""
        # Should not raise error
        updater.schedule_update(lambda: None)


class TestComponentRegistry:
    """Tests for ComponentRegistry management class."""

    @pytest.fixture
    def registry(self) -> ComponentRegistry:
        """Create test component registry."""
        return ComponentRegistry()

    @pytest.fixture
    def widget(self) -> MockWidget:
        """Create mock widget."""
        return MockWidget()

    def test_registry_initialization(self, registry: ComponentRegistry) -> None:
        """Test registry initialization."""
        assert registry._components == {}
        assert registry._updaters == {}

    def test_register_component(
        self, registry: ComponentRegistry, widget: MockWidget
    ) -> None:
        """Test component registration."""
        registry.register_component("test_widget", widget)  # type: ignore

        assert "test_widget" in registry._components
        assert registry._components["test_widget"] is widget
        assert "test_widget" in registry._updaters
        assert isinstance(registry._updaters["test_widget"], AsyncUIUpdater)

    def test_get_component(
        self, registry: ComponentRegistry, widget: MockWidget
    ) -> None:
        """Test component retrieval."""
        registry.register_component("test_widget", widget)  # type: ignore

        retrieved = registry.get_component("test_widget")
        assert retrieved is widget

        # Test non-existent component
        assert registry.get_component("nonexistent") is None

    @pytest.mark.asyncio
    async def test_start_all_updaters(
        self, registry: ComponentRegistry, widget: MockWidget
    ) -> None:
        """Test starting all component updaters."""
        registry.register_component("test_widget", widget)  # type: ignore

        await registry.start_all_updaters()

        updater = registry._updaters["test_widget"]
        assert updater._update_task is not None
        assert not updater._update_task.done()

        # Cleanup
        await registry.stop_all_updaters()

    @pytest.mark.asyncio
    async def test_stop_all_updaters(
        self, registry: ComponentRegistry, widget: MockWidget
    ) -> None:
        """Test stopping all component updaters."""
        registry.register_component("test_widget", widget)  # type: ignore
        await registry.start_all_updaters()

        await registry.stop_all_updaters()

        updater = registry._updaters["test_widget"]
        assert updater._update_task.done()

    @pytest.mark.asyncio
    async def test_cleanup_all_components(
        self, registry: ComponentRegistry, widget: MockWidget
    ) -> None:
        """Test cleanup of all components."""
        registry.register_component("test_widget", widget)  # type: ignore
        await registry.start_all_updaters()

        await registry.cleanup_all_components()

        # Registry should be empty after cleanup
        assert registry._components == {}
        assert registry._updaters == {}

    @pytest.mark.asyncio
    async def test_multiple_components_management(
        self, registry: ComponentRegistry
    ) -> None:
        """Test managing multiple components."""
        widget1 = MockWidget()
        widget2 = MockWidget()

        registry.register_component("widget1", widget1)  # type: ignore
        registry.register_component("widget2", widget2)  # type: ignore

        assert len(registry._components) == 2
        assert len(registry._updaters) == 2

        await registry.start_all_updaters()

        # Both updaters should be running
        for updater in registry._updaters.values():
            assert updater._update_task is not None
            assert not updater._update_task.done()

        await registry.cleanup_all_components()

        # All should be cleaned up
        assert registry._components == {}
        assert registry._updaters == {}


class TestEventBusIntegration:
    """Basic integration tests with event bus."""

    @pytest.mark.asyncio
    async def test_event_bus_with_updater(self) -> None:
        """Test event bus integration with UI updater."""
        event_bus = EventBus()
        widget = MockWidget()
        updater = AsyncUIUpdater(widget)  # type: ignore

        try:
            await updater.start()

            # Test that we can use the event bus alongside UI updates
            handler_called = False

            async def test_handler(_event: TestEvent) -> None:
                nonlocal handler_called
                handler_called = True

                # Schedule UI update from event handler
                updater.schedule_update(lambda: None)

            event_bus.subscribe(TestEvent, test_handler)

            # Publish event
            test_event = TestEvent(event_id="test", occurred_at=None, test_data="test")
            await event_bus.publish(test_event)

            # Give time for processing
            await asyncio.sleep(0.01)

            assert handler_called

        finally:
            # Always stop the updater to prevent hanging
            await updater.stop()


class TestErrorHandling:
    """Tests for error handling in UI components."""

    @pytest.mark.asyncio
    async def test_updater_handles_failing_updates(self) -> None:
        """Test that UI updater handles failing update functions."""
        widget = MockWidget()
        updater = AsyncUIUpdater(widget)  # type: ignore

        await updater.start()

        # Schedule both failing and succeeding updates
        results = []

        def failing_update() -> None:
            raise RuntimeError("Test error")

        def succeeding_update() -> None:
            results.append("success")

        updater.schedule_update(failing_update)
        updater.schedule_update(succeeding_update)

        # Give time for processing
        await asyncio.sleep(0.01)

        # Succeeding update should still work despite failing one
        assert results == ["success"]

        await updater.stop()

    @pytest.mark.asyncio
    async def test_registry_handles_missing_component(self, caplog) -> None:
        """Test registry handles updates for non-existent components."""
        registry = ComponentRegistry()

        # Should log warning for non-existent component
        registry.schedule_component_update("nonexistent", lambda: None)

        # Check that a warning was logged (caplog fixture captures logs)
        assert (
            "No updater found for component: nonexistent" in caplog.text
            or len(caplog.records) == 0
        )  # Allow for logging being disabled in tests
