"""Main entry point for the Integran terminal UI application."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

from src.infrastructure.containers.main_container import MainContainer
from src.presentation.terminal.trainer_app import TrainerApp

# Configure logging with Rich
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)

logger = logging.getLogger(__name__)
console = Console()


async def main() -> None:
    """Main entry point for the terminal UI."""
    try:
        # Initialize the main dependency injection container
        container = MainContainer()

        # Ensure database is initialized
        db_path = Path.home() / ".integran" / "trainer.db"
        if not db_path.exists():
            console.print(
                "[yellow]Database not found. Please run 'integran-setup' first.[/yellow]"
            )
            sys.exit(1)

        # Create and run the Textual app
        app = TrainerApp(
            event_bus=container.get_event_bus(),
            session_workflow=container.get_session_workflow(),
            query_service=container.get_query_service(),
            analytics_service=container.get_analytics_service(),
            user_repository=container.get_user_container().get_repository(),
            container=container,  # Pass the full container for service access
        )

        logger.info("Starting Integran Terminal UI...")
        await app.run_async()

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Fatal error in main")
        sys.exit(1)


def run() -> None:
    """Run the async main function."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
