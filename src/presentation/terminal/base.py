"""Base classes for event-driven terminal UI components."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from abc import abstractmethod
from collections.abc import Callable
from typing import Any

from rich.console import Console
from textual.app import App
from textual.widget import Widget

from src.infrastructure.messaging.event_bus import DomainEvent, EventBus

logger = logging.getLogger(__name__)


class EventAwareWidget(Widget):
    """Base widget class with event subscription support."""

    def __init__(self, event_bus: EventBus, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.event_bus = event_bus
        self._event_subscriptions: list[tuple[type[DomainEvent], Callable]] = []

    def subscribe_to_event(
        self, event_type: type[DomainEvent], handler: Callable
    ) -> None:
        """Subscribe to a domain event type."""
        self.event_bus.subscribe(event_type, handler)
        self._event_subscriptions.append((event_type, handler))
        logger.debug(f"{self.__class__.__name__} subscribed to {event_type.__name__}")

    async def on_mount(self) -> None:
        """Called when widget is mounted - setup event subscriptions."""
        await self.setup_event_subscriptions()

    async def on_unmount(self) -> None:
        """Called when widget is unmounted - cleanup event subscriptions."""
        await self.cleanup_event_subscriptions()

    @abstractmethod
    async def setup_event_subscriptions(self) -> None:
        """Setup event subscriptions for this widget."""
        pass

    async def cleanup_event_subscriptions(self) -> None:
        """Cleanup event subscriptions to prevent memory leaks."""
        for event_type, handler in self._event_subscriptions:
            self.event_bus.unsubscribe(event_type, handler)
            logger.debug(
                f"{self.__class__.__name__} unsubscribed from {event_type.__name__}"
            )
        self._event_subscriptions.clear()

    async def refresh_ui(self) -> None:
        """Refresh UI components (override in subclasses)."""
        self.refresh()


class EventAwareApp(App):
    """Base application class with event bus integration."""

    def __init__(self, event_bus: EventBus, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.event_bus = event_bus
        self.console = Console()

    async def on_mount(self) -> None:
        """Called when app is mounted."""
        await self.setup_event_handlers()
        logger.info(f"{self.__class__.__name__} mounted with event bus")

    @abstractmethod
    async def setup_event_handlers(self) -> None:
        """Setup global event handlers for this app."""
        pass

    async def publish_event(self, event: DomainEvent) -> None:
        """Publish event through the event bus."""
        await self.event_bus.publish(event)
        logger.debug(f"Published {event.__class__.__name__} from UI")


class AsyncUIUpdater:
    """Helper class for async UI updates from event handlers."""

    def __init__(self, widget: EventAwareWidget) -> None:
        self.widget = widget
        self._update_queue: asyncio.Queue[Callable] = asyncio.Queue()
        self._update_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the UI update processor."""
        if self._update_task is None or self._update_task.done():
            self._update_task = asyncio.create_task(self._process_updates())
            logger.debug(f"Started UI updater for {self.widget.__class__.__name__}")

    async def stop(self) -> None:
        """Stop the UI update processor."""
        if self._update_task and not self._update_task.done():
            self._update_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._update_task
            logger.debug(f"Stopped UI updater for {self.widget.__class__.__name__}")

    def schedule_update(self, update_func: Callable) -> None:
        """Schedule a UI update function to be executed."""
        try:
            self._update_queue.put_nowait(update_func)
        except asyncio.QueueFull:
            logger.warning(f"UI update queue full for {self.widget.__class__.__name__}")

    async def _process_updates(self) -> None:
        """Process queued UI updates."""
        while True:
            try:
                update_func = await self._update_queue.get()
                await self._execute_update(update_func)
                self._update_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing UI update: {e}")

    async def _execute_update(self, update_func: Callable) -> None:
        """Execute a single UI update function."""
        try:
            if asyncio.iscoroutinefunction(update_func):
                await update_func()
            else:
                update_func()
        except Exception as e:
            logger.error(f"Error executing UI update: {e}")


class ComponentRegistry:
    """Registry for managing UI components and their lifecycle."""

    def __init__(self) -> None:
        self._components: dict[str, EventAwareWidget] = {}
        self._updaters: dict[str, AsyncUIUpdater] = {}

    def register_component(self, name: str, component: EventAwareWidget) -> None:
        """Register a UI component."""
        self._components[name] = component
        self._updaters[name] = AsyncUIUpdater(component)
        logger.debug(f"Registered component: {name}")

    def get_component(self, name: str) -> EventAwareWidget | None:
        """Get a registered component by name."""
        return self._components.get(name)

    async def start_all_updaters(self) -> None:
        """Start UI updaters for all registered components."""
        for name, updater in self._updaters.items():
            await updater.start()
            logger.debug(f"Started updater for component: {name}")

    async def stop_all_updaters(self) -> None:
        """Stop UI updaters for all registered components."""
        for name, updater in self._updaters.items():
            await updater.stop()
            logger.debug(f"Stopped updater for component: {name}")

    def schedule_component_update(self, name: str, update_func: Callable) -> None:
        """Schedule update for a specific component."""
        updater = self._updaters.get(name)
        if updater:
            updater.schedule_update(update_func)
        else:
            logger.warning(f"No updater found for component: {name}")

    async def cleanup_all_components(self) -> None:
        """Cleanup all registered components."""
        await self.stop_all_updaters()

        for name, component in self._components.items():
            if hasattr(component, "cleanup_event_subscriptions"):
                await component.cleanup_event_subscriptions()
            logger.debug(f"Cleaned up component: {name}")

        self._components.clear()
        self._updaters.clear()
        logger.info("All components cleaned up")
