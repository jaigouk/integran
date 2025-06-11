#!/usr/bin/env python3
"""Monitor extraction progress in real-time."""

import json
import time
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn

console = Console()

def monitor_progress():
    """Monitor extraction progress from checkpoint file."""
    checkpoint_path = Path("data/direct_extraction_checkpoint.json")
    
    console.print("[bold blue]Extraction Progress Monitor[/bold blue]")
    console.print("Press Ctrl+C to stop monitoring\n")
    
    last_processed = 0
    start_time = time.time()
    
    try:
        while True:
            if checkpoint_path.exists():
                try:
                    with open(checkpoint_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    metadata = data.get("metadata", {})
                    current_processed = metadata.get("last_processed", 0)
                    total_questions = metadata.get("total_questions", 0)
                    progress_pct = metadata.get("progress_percentage", 0)
                    status = metadata.get("status", "unknown")
                    image_count = metadata.get("has_images_count", 0)
                    state_count = metadata.get("state_questions_count", 0)
                    
                    # Clear screen and show progress
                    console.clear()
                    console.print("[bold blue]📊 Extraction Progress Monitor[/bold blue]\n")
                    
                    # Create progress table
                    table = Table(show_header=True, header_style="bold magenta")
                    table.add_column("Metric", style="cyan")
                    table.add_column("Value", style="green")
                    
                    table.add_row("Progress", f"{current_processed}/460 questions ({progress_pct}%)")
                    table.add_row("Status", status.title())
                    table.add_row("Questions extracted", str(total_questions))
                    table.add_row("Image questions", str(image_count))
                    table.add_row("State questions", str(state_count))
                    
                    # Calculate speed
                    elapsed = time.time() - start_time
                    if elapsed > 0 and current_processed > last_processed:
                        questions_per_second = (current_processed - last_processed) / elapsed
                        remaining = 460 - current_processed
                        eta_seconds = remaining / questions_per_second if questions_per_second > 0 else 0
                        eta_minutes = eta_seconds / 60
                        
                        table.add_row("Speed", f"{questions_per_second:.2f} questions/sec")
                        table.add_row("ETA", f"{eta_minutes:.1f} minutes")
                    
                    table.add_row("Runtime", f"{elapsed/60:.1f} minutes")
                    
                    console.print(table)
                    
                    # Progress bar
                    with Progress(
                        TextColumn("[progress.description]{task.description}"),
                        BarColumn(),
                        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                        TimeRemainingColumn(),
                    ) as progress:
                        task = progress.add_task("Extracting...", total=460)
                        progress.update(task, completed=current_processed)
                        time.sleep(0.1)  # Brief pause to show the bar
                    
                    if status == "completed":
                        console.print("\n[bold green]🎉 Extraction completed![/bold green]")
                        break
                        
                    last_processed = current_processed
                    
                except Exception as e:
                    console.print(f"[red]Error reading checkpoint: {e}[/red]")
            
            else:
                console.print("[yellow]Waiting for extraction to start...[/yellow]")
            
            time.sleep(5)  # Update every 5 seconds
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitoring stopped by user[/yellow]")

if __name__ == "__main__":
    monitor_progress()