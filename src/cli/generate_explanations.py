"""CLI entry point for generating explanations for exam questions."""

import logging
import sys

import click
from rich.console import Console
from rich.logging import RichHandler

from src.utils.explanation_generator import generate_explanations_cli

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)],
)

console = Console()


@click.command()
@click.option(
    "--batch-size",
    "-b",
    default=10,
    type=int,
    help="Number of questions to process in each batch (default: 10)",
)
@click.option(
    "--no-resume",
    is_flag=True,
    help="Start fresh instead of resuming from checkpoint",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output",
)
@click.option(
    "--use-rag",
    is_flag=True,
    help="Use RAG (Retrieval-Augmented Generation) for enhanced explanations",
)
def main(batch_size: int, no_resume: bool, verbose: bool, use_rag: bool) -> None:
    """Generate explanations for all exam questions using Gemini AI.

    This command will:
    - Load questions from data/extraction_checkpoint.json or data/questions.json
    - Generate clear explanations for each question
    - Save progress to data/explanations_checkpoint.json (resume supported)
    - Output final explanations to data/explanations.json

    The explanations help users understand:
    - Why the correct answer is right
    - Why other options are wrong
    - Key concepts to remember
    - Memory aids when helpful

    Example:
        integran-generate-explanations
        integran-generate-explanations --batch-size 20
        integran-generate-explanations --no-resume --verbose
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    console.print("\n[bold cyan]Integran Explanation Generator[/bold cyan]")
    console.print("=" * 50)

    if no_resume:
        console.print("[yellow]Starting fresh (ignoring checkpoint)...[/yellow]")
    else:
        console.print("[green]Will resume from checkpoint if available...[/green]")

    console.print(f"[blue]Batch size: {batch_size} questions[/blue]")
    if use_rag:
        console.print(
            "[bold magenta]Using RAG for enhanced explanations[/bold magenta]"
        )
    console.print()

    try:
        success = generate_explanations_cli(
            batch_size=batch_size,
            resume=not no_resume,
            use_rag=use_rag,
        )

        if success:
            console.print(
                "\n[bold green]✓ Explanation generation completed successfully![/bold green]"
            )
            console.print(
                "[green]Explanations saved to: data/explanations.json[/green]"
            )
            sys.exit(0)
        else:
            console.print(
                "\n[bold yellow]⚠ Explanation generation partially complete[/bold yellow]"
            )
            console.print(
                "[yellow]Check logs for details. You can resume later.[/yellow]"
            )
            sys.exit(1)

    except KeyboardInterrupt:
        console.print("\n[red]Interrupted by user. Progress saved to checkpoint.[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]Error: {e}[/bold red]")
        console.print(
            "[red]Check that your Gemini API credentials are configured.[/red]"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
