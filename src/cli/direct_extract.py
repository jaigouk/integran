"""CLI command for direct PDF extraction."""

import click
from rich.console import Console

from src.direct_pdf_processor import DirectPDFProcessor
from pathlib import Path

console = Console()


@click.command()
@click.option(
    "--pdf-path",
    default="data/gesamtfragenkatalog-lebenindeutschland.pdf",
    help="Path to the PDF file",
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "--output-path",
    default="data/direct_extraction.json",
    help="Path to save extracted questions",
    type=click.Path(path_type=Path),
)
@click.option(
    "--batch-size",
    default=50,
    help="Number of questions to process per batch",
    type=int,
)
def main(pdf_path: Path, output_path: Path, batch_size: int):
    """Extract questions directly from PDF using Gemini File API."""
    
    console.print("[bold blue]Direct PDF Extraction[/bold blue]")
    console.print(f"PDF: {pdf_path}")
    console.print(f"Output: {output_path}")
    console.print(f"Batch size: {batch_size}")
    
    try:
        processor = DirectPDFProcessor()
        questions = processor.process_full_pdf_in_batches(pdf_path, batch_size)
        
        # Save final results
        final_dataset = {
            "questions": questions,
            "metadata": {
                "total_questions": len(questions),
                "extraction_method": "direct_pdf_file_api",
                "has_images_count": len([q for q in questions if q.get("has_images")]),
                "state_questions_count": len([q for q in questions if q.get("question_type") == "state_specific"])
            }
        }
        
        import json
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(final_dataset, f, ensure_ascii=False, indent=2)
            
        console.print(f"[green]✓ Successfully extracted {len(questions)} questions[/green]")
        console.print(f"[green]✓ Image questions: {final_dataset['metadata']['has_images_count']}[/green]")
        console.print(f"[green]✓ State questions: {final_dataset['metadata']['state_questions_count']}[/green]")
        console.print(f"[green]✓ Saved to: {output_path}[/green]")
        
    except Exception as e:
        console.print(f"[red]❌ Extraction failed: {e}[/red]")
        raise click.ClickException(str(e))


if __name__ == "__main__":
    main()