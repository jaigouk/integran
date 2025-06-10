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


def _start_interactive_menu(db_manager: DatabaseManager) -> None:
    """Start the interactive menu system."""
    while True:
        try:
            # Clear screen and show header
            console.clear()
            _display_welcome()
            
            # Get user language preference
            preferred_lang = db_manager.get_user_setting("preferred_language", "en")
            
            # Show current status
            stats = db_manager.get_learning_stats()
            console.print(f"[dim]Language: {preferred_lang.upper()} | "
                         f"Mastered: {stats.total_mastered} | "
                         f"Learning: {stats.total_learning} | "
                         f"New: {stats.total_new}[/dim]")
            console.print()

            # Display menu options
            console.print("[bold cyan]📚 Main Menu[/bold cyan]")
            console.print()
            console.print("1. 📚 Random Practice")
            console.print("2. 📖 Sequential Practice")  
            console.print("3. 🎯 Practice by Question Number")
            console.print("4. 📊 Category Practice")
            console.print("5. 🔄 Review Failed Questions")
            console.print("6. 📈 View Statistics")
            console.print("7. ⚙️  Settings")
            console.print("8. 🚪 Exit")
            console.print()

            # Get user choice
            choice = console.input("[bold green]Select option (1-8): [/bold green]").strip()

            # Handle menu selection
            if choice == "1":
                _handle_random_practice(db_manager)
            elif choice == "2":
                _handle_sequential_practice(db_manager)
            elif choice == "3":
                _handle_practice_by_number(db_manager)
            elif choice == "4":
                _handle_category_practice(db_manager)
            elif choice == "5":
                _handle_review_practice(db_manager)
            elif choice == "6":
                _display_detailed_stats(db_manager)
            elif choice == "7":
                _handle_settings_menu(db_manager)
            elif choice == "8":
                console.print("[yellow]👋 Thank you for using Integran! Goodbye![/yellow]")
                break
            else:
                console.print("[red]❌ Invalid option. Please choose 1-8.[/red]")
                console.input("[dim]Press Enter to continue...[/dim]")

        except KeyboardInterrupt:
            console.print("\n[yellow]👋 Goodbye![/yellow]")
            break
        except Exception as e:
            console.print(f"[red]❌ Error: {e}[/red]")
            console.input("[dim]Press Enter to continue...[/dim]")


def _handle_random_practice(db_manager: DatabaseManager) -> None:
    """Handle random practice mode."""
    console.clear()
    console.print("[bold blue]📚 Random Practice Mode[/bold blue]")
    console.print()
    
    # Ask how many questions to practice
    try:
        num_questions = console.input("[green]How many questions? (1-20, default 5): [/green]").strip()
        if not num_questions:
            num_questions = 5
        else:
            num_questions = int(num_questions)
            if num_questions < 1 or num_questions > 20:
                console.print("[yellow]Using default of 5 questions[/yellow]")
                num_questions = 5
    except ValueError:
        console.print("[yellow]Invalid input, using default of 5 questions[/yellow]")
        num_questions = 5
    
    # Get random questions
    questions = _get_random_questions(db_manager, num_questions)
    
    if not questions:
        console.print("[red]❌ No questions available for practice.[/red]")
        console.input("[dim]Press Enter to continue...[/dim]")
        return
    
    # Start practice session
    _run_practice_session(db_manager, questions, "Random Practice")


def _handle_sequential_practice(db_manager: DatabaseManager) -> None:
    """Handle sequential practice mode."""
    console.clear()
    console.print("[bold blue]📖 Sequential Practice Mode[/bold blue]")
    console.print()
    console.print("[yellow]🚧 Sequential practice coming soon![/yellow]")
    console.print("[dim]This will allow you to practice questions in order.[/dim]")
    console.print()
    console.input("[dim]Press Enter to return to main menu...[/dim]")


def _handle_practice_by_number(db_manager: DatabaseManager) -> None:
    """Handle practice by question number."""
    console.clear()
    console.print("[bold blue]🎯 Practice by Question Number[/bold blue]")
    console.print()
    
    try:
        question_id = console.input("[green]Enter question number (1-460): [/green]")
        question_id = int(question_id.strip())
        
        if 1 <= question_id <= 460:
            # Get detailed question data
            question_data = db_manager.get_question_with_multilingual_answers(question_id, "en")
            if question_data:
                console.print(f"[green]✅ Found Question {question_id}[/green]")
                console.print()
                console.print(f"[bold blue]Question:[/bold blue] {question_data['question']}")
                console.print()
                
                # Show options
                console.print("[cyan]Options:[/cyan]")
                for i, option in enumerate(question_data['options'], 1):
                    console.print(f"  {i}. {option}")
                
                console.print()
                console.print(f"[green]Correct Answer:[/green] {question_data['correct']}")
                console.print(f"[dim]Category: {question_data.get('category', 'Unknown')} | "
                             f"Difficulty: {question_data.get('difficulty', 'Unknown')}[/dim]")
                
                # Show image information if available
                if question_data.get('has_images') and question_data.get('images'):
                    console.print()
                    console.print("[yellow]🖼️  Image Information:[/yellow]")
                    for i, img in enumerate(question_data['images'], 1):
                        img_path = img.get('path', '')
                        description = img.get('description', 'No description')
                        if 'placeholder' in img_path:
                            console.print(f"  Bild {i}: [dim]{img_path} (placeholder)[/dim]")
                        else:
                            console.print(f"  Bild {i}: [green]{img_path}[/green]")
                            console.print(f"           [dim]{description}[/dim]")
                
                console.print()
                console.print("[dim]💡 In the future app, images will be displayed visually[/dim]")
            else:
                console.print(f"[red]❌ Question {question_id} not found.[/red]")
        else:
            console.print("[red]❌ Please enter a number between 1 and 460.[/red]")
            
    except ValueError:
        console.print("[red]❌ Please enter a valid number.[/red]")
    
    console.print()
    console.input("[dim]Press Enter to return to main menu...[/dim]")


def _handle_category_practice(db_manager: DatabaseManager) -> None:
    """Handle category practice mode."""
    console.clear()
    console.print("[bold blue]📊 Category Practice Mode[/bold blue]")
    console.print()
    
    # Get available categories (simplified for now)
    console.print("[green]Available categories:[/green]")
    categories = ["Grundrechte", "Geschichte", "Föderalismus", "Rechtssystem", "Geografie"]
    
    for i, category in enumerate(categories, 1):
        console.print(f"{i}. {category}")
    
    console.print()
    console.print("[yellow]🚧 Category selection coming soon![/yellow]")
    console.print("[dim]This will show questions from specific categories.[/dim]")
    console.print()
    console.input("[dim]Press Enter to return to main menu...[/dim]")


def _handle_review_practice(db_manager: DatabaseManager) -> None:
    """Handle review practice mode."""
    console.clear()
    console.print("[bold blue]🔄 Review Failed Questions[/bold blue]")
    console.print()
    
    # Get questions for review
    questions = db_manager.get_questions_for_review()
    
    if not questions:
        console.print("[green]🎉 No questions due for review! Great job![/green]")
    else:
        console.print(f"[yellow]📚 {len(questions)} questions due for review[/yellow]")
        console.print("[dim]Review system coming soon![/dim]")
    
    console.print()
    console.input("[dim]Press Enter to return to main menu...[/dim]")


def _display_detailed_stats(db_manager: DatabaseManager) -> None:
    """Display detailed statistics."""
    console.clear()
    console.print("[bold blue]📈 Detailed Statistics[/bold blue]")
    console.print("=" * 50)
    
    stats = db_manager.get_learning_stats()
    
    console.print(f"[green]📚 Mastered Questions:[/green] {stats.total_mastered}")
    console.print(f"[yellow]📖 Learning Questions:[/yellow] {stats.total_learning}")
    console.print(f"[blue]🆕 New Questions:[/blue] {stats.total_new}")
    console.print(f"[red]⏰ Due for Review:[/red] {stats.overdue_count}")
    console.print(f"[cyan]📅 Next Review:[/cyan] {stats.next_review_count}")
    console.print(f"[magenta]📈 Average Difficulty:[/magenta] {stats.average_easiness:.2f}")
    console.print(f"[bold green]🔥 Study Streak:[/bold green] {stats.study_streak} days")
    
    # Phase 1.8 specific stats
    console.print(f"[purple]🖼️ Image Questions Completed:[/purple] {stats.image_questions_completed}")
    console.print(f"[dim]🌍 Preferred Language:[/dim] {stats.preferred_language.upper()}")
    
    console.print()
    console.input("[dim]Press Enter to return to main menu...[/dim]")


def _handle_settings_menu(db_manager: DatabaseManager) -> None:
    """Handle settings menu."""
    while True:
        console.clear()
        console.print("[bold blue]⚙️  Settings[/bold blue]")
        console.print("=" * 30)
        
        # Get current settings
        current_lang = db_manager.get_user_setting("preferred_language", "en")
        
        console.print(f"[dim]Current Language: {current_lang.upper()}[/dim]")
        console.print()
        console.print("1. 🌍 Change Language")
        console.print("2. 🔄 Reset Progress")
        console.print("3. 📊 Export Statistics")
        console.print("4. ↩️  Back to Main Menu")
        console.print()
        
        choice = console.input("[green]Select option (1-4): [/green]").strip()
        
        if choice == "1":
            _handle_language_settings(db_manager)
        elif choice == "2":
            _handle_reset_confirmation(db_manager)
        elif choice == "3":
            _export_stats(db_manager)
            console.input("[dim]Press Enter to continue...[/dim]")
        elif choice == "4":
            break
        else:
            console.print("[red]❌ Invalid option. Please choose 1-4.[/red]")
            console.input("[dim]Press Enter to continue...[/dim]")


def _handle_language_settings(db_manager: DatabaseManager) -> None:
    """Handle language selection."""
    console.clear()
    console.print("[bold blue]🌍 Language Settings[/bold blue]")
    console.print("=" * 30)
    
    languages = {
        "en": "🇺🇸 English",
        "de": "🇩🇪 German (Deutsch)",
        "tr": "🇹🇷 Turkish (Türkçe)",
        "uk": "🇺🇦 Ukrainian (Українська)",
        "ar": "🇸🇦 Arabic (العربية)"
    }
    
    current_lang = db_manager.get_user_setting("preferred_language", "en")
    console.print(f"[dim]Current: {languages.get(current_lang, 'Unknown')}[/dim]")
    console.print()
    
    console.print("[green]Available languages:[/green]")
    for code, name in languages.items():
        marker = "✅" if code == current_lang else "  "
        console.print(f"{marker} {code.upper()}. {name}")
    
    console.print()
    console.print("[yellow]⚠️  Note: Currently only English answers are available.[/yellow]")
    console.print("[dim]Other languages will be added in future updates.[/dim]")
    console.print()
    
    choice = console.input("[green]Select language (en/de/tr/uk/ar) or Enter to cancel: [/green]").strip().lower()
    
    if choice in languages:
        db_manager.set_user_setting("preferred_language", choice)
        console.print(f"[green]✅ Language set to {languages[choice]}[/green]")
    elif choice == "":
        console.print("[blue]Language unchanged.[/blue]")
    else:
        console.print("[red]❌ Invalid language code.[/red]")
    
    console.print()
    console.input("[dim]Press Enter to continue...[/dim]")


def _handle_reset_confirmation(db_manager: DatabaseManager) -> None:
    """Handle progress reset with confirmation."""
    console.clear()
    console.print("[bold red]🔄 Reset Progress[/bold red]")
    console.print("=" * 30)
    console.print()
    console.print("[yellow]⚠️  This will permanently delete ALL your progress data:[/yellow]")
    console.print("   • All practice session history")
    console.print("   • All learning progress")
    console.print("   • All statistics")
    console.print("   • All spaced repetition data")
    console.print()
    console.print("[red]This action CANNOT be undone![/red]")
    console.print()
    
    confirmation = console.input("[bold red]Type 'RESET' to confirm, or anything else to cancel: [/bold red]")
    
    if confirmation.strip() == "RESET":
        console.print()
        console.print("[yellow]🔄 Resetting progress...[/yellow]")
        db_manager.reset_progress()
        console.print("[green]✅ Progress reset successfully![/green]")
    else:
        console.print("[blue]Reset cancelled.[/blue]")
    
    console.print()
    console.input("[dim]Press Enter to continue...[/dim]")


def _get_random_questions(db_manager: DatabaseManager, limit: int = 5):
    """Get random questions for practice (simplified implementation)."""
    # For now, just get first few questions - will improve later
    with db_manager.get_session() as session:
        from src.core.models import Question
        return session.query(Question).limit(limit).all()


if __name__ == "__main__":
    main()
