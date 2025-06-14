"""CLI command for direct PDF extraction."""

from pathlib import Path

import click
from rich.console import Console

from src.direct_pdf_processor import DirectPDFProcessor

console = Console()


@click.command()
@click.option(
    "--pdf-path",
    default="data/gesamtfragenkatalog-lebenindeutschland.pdf",
    help="Path to the PDF file",
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "--checkpoint-path",
    default="data/direct_extraction_checkpoint.json",
    help="Path to save/load checkpoint",
    type=click.Path(path_type=Path),
)
@click.option(
    "--final-output",
    default="data/direct_extraction.json",
    help="Path to save final extracted questions",
    type=click.Path(path_type=Path),
)
@click.option(
    "--batch-size",
    default=1,
    help="Number of questions to process per batch",
    type=int,
)
def main(
    pdf_path: Path, checkpoint_path: Path, final_output: Path, batch_size: int
) -> None:
    """Extract questions directly from PDF using Gemini with transparent checkpointing."""

    console.print("[bold blue]Direct PDF Extraction with Checkpoint[/bold blue]")
    console.print(f"PDF: {pdf_path}")
    console.print(f"Checkpoint: {checkpoint_path}")
    console.print(f"Final output: {final_output}")
    console.print(f"Batch size: {batch_size}")

    try:
        processor = DirectPDFProcessor()

        # Check existing checkpoint
        import json

        if checkpoint_path.exists():
            try:
                with open(checkpoint_path, encoding="utf-8") as f:
                    checkpoint_data = json.load(f)
                last_processed = checkpoint_data["metadata"].get("last_processed", 0)
                total_questions = checkpoint_data["metadata"].get("total_questions", 0)
                progress_pct = checkpoint_data["metadata"].get("progress_percentage", 0)

                console.print(
                    f"[yellow]💾 Found checkpoint: {total_questions} questions, last processed: {last_processed} ({progress_pct}%)[/yellow]"
                )

                if last_processed >= 460:
                    console.print("[green]✓ Extraction already completed![/green]")
                    # Copy to final output
                    import shutil

                    shutil.copy2(checkpoint_path, final_output)
                    return
            except Exception as e:
                console.print(
                    f"[yellow]Warning: Could not read checkpoint: {e}[/yellow]"
                )

        # Start extraction with checkpoint
        questions = processor.process_full_pdf_in_batches(
            pdf_path, checkpoint_path, batch_size
        )

        # Copy final result to output location
        if checkpoint_path.exists():
            import shutil

            shutil.copy2(checkpoint_path, final_output)

        console.print(
            f"[green]✓ Successfully extracted {len(questions)} questions[/green]"
        )
        console.print(f"[green]✓ Final output saved to: {final_output}[/green]")

    except Exception as e:
        console.print(f"[red]❌ Extraction failed: {e}[/red]")
        # Show checkpoint info even on failure
        if checkpoint_path.exists():
            try:
                import json

                with open(checkpoint_path, encoding="utf-8") as f:
                    checkpoint_data = json.load(f)
                last_processed = checkpoint_data["metadata"].get("last_processed", 0)
                console.print(
                    f"[yellow]💾 Checkpoint preserved: {last_processed}/460 questions extracted[/yellow]"
                )
            except Exception as checkpoint_err:
                # Log checkpoint read error but continue with main error handling
                console.print(
                    f"[dim]Note: Could not read checkpoint info: {checkpoint_err}[/dim]"
                )
        raise click.ClickException(str(e)) from e


if __name__ == "__main__":
    main()
