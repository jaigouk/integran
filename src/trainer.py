"""Main entry point for the Integran German Integration Exam trainer (Phase 1.8)."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.text import Text

from src.core.database import DatabaseManager

console = Console()


@click.command()
@click.option(
    "--mode",
    type=click.Choice(["random", "sequential", "category", "review"]),
    default="random",
    help="Practice mode to start with",
)
@click.option(
    "--category",
    type=str,
    help="Specific category to practice (use with --mode category)",
)
@click.option(
    "--review",
    is_flag=True,
    help="Start in review mode for failed questions",
)
@click.option(
    "--export-stats",
    is_flag=True,
    help="Export progress statistics and exit",
)
@click.option(
    "--stats",
    is_flag=True,
    help="Display learning statistics and exit",
)
@click.option(
    "--reset",
    is_flag=True,
    help="Reset all progress data",
)
@click.version_option(version="0.1.0", prog_name="integran")
def main(
    mode: str,
    category: str | None,
    review: bool,
    export_stats: bool,
    stats: bool,
    reset: bool,
) -> None:
    """Integran - Interactive trainer for German Integration Exam.

    A terminal-based application to help you prepare for the Leben in Deutschland test
    through interactive practice sessions, spaced repetition, and progress tracking.
    """
    try:
        # Initialize database
        db_manager = DatabaseManager()

        # Handle special flags first
        if reset:
            _handle_reset(db_manager)
            return

        if stats:
            _display_stats(db_manager)
            return

        if export_stats:
            _export_stats(db_manager)
            return

        # Check if questions are loaded
        questions_file = Path("data/questions.json")
        if not questions_file.exists():
            console.print(
                "[red]Error: Questions file not found at data/questions.json[/red]"
            )
            console.print(
                "[yellow]Please run 'integran-setup' first to initialize the database.[/yellow]"
            )
            sys.exit(1)

        # Start the trainer application
        _start_trainer(db_manager, mode, category, review)

    except KeyboardInterrupt:
        console.print("\n[yellow]Training session interrupted. Goodbye![/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def _handle_reset(db_manager: DatabaseManager) -> None:
    """Handle progress reset with confirmation."""
    console.print("[yellow]This will reset ALL your progress data![/yellow]")
    if click.confirm("Are you sure you want to continue?"):
        db_manager.reset_progress()
        console.print("[green]✅ Progress reset successfully![/green]")
    else:
        console.print("[blue]Reset cancelled.[/blue]")


def _display_stats(db_manager: DatabaseManager) -> None:
    """Display learning statistics."""
    stats = db_manager.get_learning_stats()

    console.print("\n[bold blue]📊 Learning Statistics[/bold blue]")
    console.print("=" * 40)
    console.print(f"📚 Mastered Questions: {stats.total_mastered}")
    console.print(f"📖 Learning Questions: {stats.total_learning}")
    console.print(f"🆕 New Questions: {stats.total_new}")
    console.print(f"⏰ Due for Review: {stats.overdue_count}")
    console.print(f"📅 Next Review: {stats.next_review_count}")
    console.print(f"📈 Average Difficulty: {stats.average_easiness:.2f}")
    console.print(f"🔥 Study Streak: {stats.study_streak} days")
    console.print()


def _export_stats(db_manager: DatabaseManager) -> None:
    """Export statistics to file."""
    stats = db_manager.get_learning_stats()

    # Create export file
    export_path = Path("data/stats_export.txt")
    export_path.parent.mkdir(parents=True, exist_ok=True)

    with open(export_path, "w", encoding="utf-8") as f:
        f.write("Integran Learning Statistics\\n")
        f.write("=" * 40 + "\\n")
        f.write(f"Mastered Questions: {stats.total_mastered}\\n")
        f.write(f"Learning Questions: {stats.total_learning}\\n")
        f.write(f"New Questions: {stats.total_new}\\n")
        f.write(f"Due for Review: {stats.overdue_count}\\n")
        f.write(f"Next Review: {stats.next_review_count}\\n")
        f.write(f"Average Difficulty: {stats.average_easiness:.2f}\\n")
        f.write(f"Study Streak: {stats.study_streak} days\\n")

    console.print(f"[green]✅ Statistics exported to {export_path}[/green]")


def _start_trainer(
    db_manager: DatabaseManager,
    mode: str,
    category: str | None,
    review: bool,
) -> None:
    """Start the main trainer application."""
    # Display welcome message
    _display_welcome()

    # Override mode if review flag is set
    if review:
        mode = "review"

    # Start the appropriate mode
    if mode == "review":
        _start_review_mode(db_manager)
    elif mode == "category" and category:
        _start_category_mode(db_manager, category)
    else:
        _start_interactive_menu(db_manager)


def _display_welcome() -> None:
    """Display welcome message and logo."""
    title = Text("Integran - German Integration Exam Trainer", style="bold blue")
    console.print()
    console.print("╔" + "═" * 48 + "╗")
    console.print("║" + " " * 48 + "║")
    console.print("║" + title.plain.center(48) + "║")
    console.print("║" + " " * 48 + "║")
    console.print("╚" + "═" * 48 + "╝")
    console.print()


def _start_review_mode(db_manager: DatabaseManager) -> None:
    """Start review mode for questions due for review."""
    questions = db_manager.get_questions_for_review()

    if not questions:
        console.print("[green]🎉 No questions due for review! Well done![/green]")
        return

    console.print(
        f"[blue]📚 Starting review session with {len(questions)} questions[/blue]"
    )
    # TODO: Implement question presentation logic
    console.print("[yellow]Review mode implementation coming soon![/yellow]")


def _start_category_mode(db_manager: DatabaseManager, category: str) -> None:
    """Start category-specific practice mode."""
    questions = db_manager.get_questions_by_category(category)

    if not questions:
        console.print(f"[red]No questions found for category: {category}[/red]")
        return

    console.print(
        f"[blue]📖 Starting practice with {len(questions)} questions from {category}[/blue]"
    )
    # TODO: Implement question presentation logic
    console.print("[yellow]Category mode implementation coming soon![/yellow]")


def _start_interactive_menu(_: DatabaseManager) -> None:
    """Start the interactive menu system."""
    console.print("[blue]🎮 Starting interactive menu[/blue]")
    console.print()
    console.print("Available options:")
    console.print("1. 📚 Random Practice")
    console.print("2. 📖 Sequential Practice")
    console.print("3. 🎯 Practice by Category")
    console.print("4. 🔄 Review Questions")
    console.print("5. 📊 View Statistics")
    console.print("6. ⚙️  Settings")
    console.print("7. 🚪 Exit")
    console.print()

    # TODO: Implement full menu system
    console.print("[yellow]Full interactive menu implementation coming soon![/yellow]")
    console.print(
        "[blue]For now, use command line options like --stats or --review[/blue]"
    )


if __name__ == "__main__":
    main()
