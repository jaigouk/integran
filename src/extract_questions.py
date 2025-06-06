"""CLI utility for extracting questions from PDF using Gemini Pro 2.5."""

from __future__ import annotations

import logging
from pathlib import Path

import click
from rich.console import Console

from src.core.settings import get_settings, has_gemini_config
from src.utils.pdf_extractor import extract_questions_to_csv

console = Console()
logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--pdf-path",
    default=None,
    help="Path to the PDF file (uses default from settings if not provided)",
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "--csv-path",
    default=None,
    help="Path to save CSV file (uses default from settings if not provided)",
    type=click.Path(path_type=Path),
)
@click.option(
    "--force",
    is_flag=True,
    help="Force extraction even if CSV already exists",
)
@click.version_option(version="0.1.0", prog_name="integran-extract-questions")
def main(pdf_path: Path | None, csv_path: Path | None, force: bool) -> None:
    """Extract questions from PDF using Gemini Pro 2.5.

    This utility is used to generate the questions CSV file from the official PDF.
    Requires Gemini API configuration (can be set via .env file or environment variables).

    Normal users don't need to run this as the CSV should be pre-generated.
    """
    settings = get_settings()

    # Use defaults from settings if not provided
    if pdf_path is None:
        pdf_path = Path(settings.pdf_path)
    if csv_path is None:
        csv_path = Path(settings.questions_csv_path)

    console.print("[bold blue]Integran Question Extractor[/bold blue]")
    console.print(f"PDF: {pdf_path}")
    console.print(f"CSV: {csv_path}")

    # Check if PDF exists
    if not pdf_path.exists():
        console.print(f"[red]❌ PDF file not found: {pdf_path}[/red]")
        console.print("Make sure the PDF file exists at the specified path.")
        raise click.ClickException(f"PDF file not found: {pdf_path}")

    # Check if CSV already exists
    if csv_path.exists() and not force:
        console.print(f"[yellow]CSV file already exists: {csv_path}[/yellow]")
        console.print("Use --force to overwrite existing file")
        return

    # Check if Gemini configuration is available
    if not has_gemini_config():
        console.print("[yellow]⚠️  Gemini API not configured[/yellow]")
        console.print("To extract questions from PDF, configure Gemini API:")
        console.print("1. Copy .env.example to .env")
        console.print("2. Set GEMINI_API_KEY and GCP_PROJECT_ID")
        console.print("3. Optionally set GCP_REGION (defaults to us-central1)")
        console.print("")
        console.print("Or set environment variables directly:")
        console.print("- GEMINI_API_KEY")
        console.print("- GCP_PROJECT_ID")
        console.print("- GCP_REGION")
        return

    console.print("[blue]Starting extraction with Gemini Pro 2.5...[/blue]")

    try:
        success = extract_questions_to_csv(pdf_path, csv_path)

        if success:
            console.print(
                f"[green]✅ Successfully extracted questions to {csv_path}[/green]"
            )
        else:
            console.print("[red]❌ Extraction failed or skipped[/red]")
            console.print("Check the logs for more details.")

    except Exception as e:
        console.print(f"[red]❌ Error during extraction: {e}[/red]")
        raise click.ClickException(str(e)) from e


if __name__ == "__main__":
    main()
