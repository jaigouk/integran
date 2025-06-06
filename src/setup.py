"""Setup script for Integran German Integration Exam trainer."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console

from src.core.database import DatabaseManager

console = Console()


@click.command()
@click.option(
    "--force",
    is_flag=True,
    help="Force reinitialize even if data exists",
)
@click.option(
    "--questions-file",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to questions JSON file",
)
@click.version_option(version="0.1.0", prog_name="integran-setup")
def main(force: bool, questions_file: Path | None) -> None:
    """Initialize Integran database and load questions.

    This command sets up the database schema and loads the German Integration
    Exam questions from the questions.json file.
    """
    try:
        console.print("[bold blue]🚀 Integran Setup[/bold blue]")
        console.print()

        # Initialize database
        console.print("[blue]📄 Initializing database...[/blue]")
        db_manager = DatabaseManager()

        # Determine questions file path
        if questions_file is None:
            questions_file = Path("data/questions.json")

        # Check if setup already completed
        data_dir = Path("data")
        if (
            not force
            and data_dir.exists()
            and (data_dir / "trainer.db").exists()
            and not click.confirm(
                "Database already exists. Do you want to reinitialize?"
            )
        ):
            console.print("[yellow]Setup cancelled.[/yellow]")
            return

        # Create data directory
        data_dir.mkdir(exist_ok=True)

        # Load questions if file exists
        if questions_file.exists():
            console.print(f"[blue]📚 Loading questions from {questions_file}...[/blue]")
            try:
                count = db_manager.load_questions(questions_file)
                console.print(
                    f"[green]✅ Successfully loaded {count} questions![/green]"
                )
            except Exception as e:
                console.print(f"[red]❌ Error loading questions: {e}[/red]")
                sys.exit(1)
        else:
            console.print("[yellow]⚠️  Questions file not found.[/yellow]")
            console.print(f"[yellow]Expected location: {questions_file}[/yellow]")

            if click.confirm("Do you want to create a sample questions file?"):
                _create_sample_questions(questions_file)
                console.print(
                    f"[green]✅ Sample questions created at {questions_file}[/green]"
                )
                console.print("[blue]📚 Loading sample questions...[/blue]")
                count = db_manager.load_questions(questions_file)
                console.print(
                    f"[green]✅ Successfully loaded {count} questions![/green]"
                )
            else:
                console.print(
                    "[yellow]Setup completed without questions. "
                    "Add questions.json and run setup again.[/yellow]"
                )

        # Create config file if it doesn't exist
        _create_config_file()

        console.print()
        console.print("[bold green]🎉 Setup completed successfully![/bold green]")
        console.print()
        console.print("[blue]Next steps:[/blue]")
        console.print("1. Run 'integran' to start the trainer")
        console.print("2. Use 'integran --help' to see all options")
        console.print("3. Use 'integran --stats' to view your progress")
        console.print()

    except KeyboardInterrupt:
        console.print("\n[yellow]Setup interrupted.[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Setup failed: {e}[/red]")
        sys.exit(1)


def _create_sample_questions(questions_file: Path) -> None:
    """Create a sample questions file for testing."""
    sample_questions = [
        {
            "id": 1,
            "question": "In Deutschland dürfen Menschen offen etwas gegen die Regierung sagen, weil …",
            "options": [
                "hier Religionsfreiheit gilt.",
                "die Menschen Steuern zahlen.",
                "die Menschen das Wahlrecht haben.",
                "hier Meinungsfreiheit gilt.",
            ],
            "correct": "hier Meinungsfreiheit gilt.",
            "category": "Grundrechte",
            "difficulty": "medium",
        },
        {
            "id": 2,
            "question": "Was ist eine Aufgabe von Wahlhelfern / Wahlhelferinnen in Deutschland?",
            "options": [
                "Sie helfen alten Menschen beim Wählen.",
                "Sie schreiben die Wahlprogramme.",
                "Sie geben Tipps für die Wahl.",
                "Sie zählen die Stimmen aus.",
            ],
            "correct": "Sie zählen die Stimmen aus.",
            "category": "Demokratie und Wahlen",
            "difficulty": "easy",
        },
        {
            "id": 3,
            "question": "Welche Länder wurden nach dem Zweiten Weltkrieg in Deutschland von Großbritannien besetzt?",
            "options": [
                "Nordrhein-Westfalen, Schleswig-Holstein, Hamburg, Niedersachsen",
                "Bayern, Baden-Württemberg, Hessen, Rheinland-Pfalz",
                "Sachsen, Thüringen, Sachsen-Anhalt",
                "Brandenburg, Mecklenburg-Vorpommern, Berlin",
            ],
            "correct": "Nordrhein-Westfalen, Schleswig-Holstein, Hamburg, Niedersachsen",
            "category": "Geschichte",
            "difficulty": "hard",
        },
    ]

    questions_file.parent.mkdir(parents=True, exist_ok=True)
    with open(questions_file, "w", encoding="utf-8") as f:
        json.dump(sample_questions, f, ensure_ascii=False, indent=2)


def _create_config_file() -> None:
    """Create a default configuration file."""
    config_file = Path("data/config.json")

    if config_file.exists():
        return

    default_config = {
        "repetition_interval": 3,
        "max_daily_questions": 50,
        "show_explanations": True,
        "color_mode": "auto",
        "terminal_width": "auto",
        "question_timeout": 60,
        "auto_save": True,
        "spaced_repetition": True,
    }

    config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(default_config, f, indent=2)

    console.print(f"[green]✅ Configuration file created at {config_file}[/green]")


if __name__ == "__main__":
    main()
