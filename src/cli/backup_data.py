"""CLI utility for backing up and restoring question data."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
def cli():
    """Backup and restore question data files."""
    pass


@cli.command()
@click.option(
    "--suffix",
    default=None,
    help="Custom suffix for backup files (default: timestamp)",
)
@click.option(
    "--include-explanations",
    is_flag=True,
    help="Also backup explanations.json file",
)
def backup(suffix: str | None, include_explanations: bool) -> None:
    """Create backups of question data files.

    Creates timestamped backups of:
    - data/questions.csv
    - data/questions.json
    - data/explanations.json (if --include-explanations)
    """
    if suffix is None:
        suffix = datetime.now().strftime("%Y%m%d_%H%M%S")

    console.print(f"[blue]Creating backups with suffix: {suffix}[/blue]")

    files_to_backup = [
        Path("data/questions.csv"),
        Path("data/questions.json"),
    ]

    if include_explanations:
        files_to_backup.append(Path("data/explanations.json"))

    backups_created = []

    for file_path in files_to_backup:
        if file_path.exists():
            backup_path = (
                file_path.parent / f"{file_path.stem}_backup_{suffix}{file_path.suffix}"
            )
            shutil.copy2(file_path, backup_path)
            backups_created.append((file_path, backup_path))
            console.print(f"[green]✅ Backed up {file_path} → {backup_path}[/green]")
        else:
            console.print(f"[yellow]⚠️  File not found: {file_path}[/yellow]")

    if backups_created:
        console.print(
            f"\n[green]Successfully created {len(backups_created)} backups[/green]"
        )


@cli.command()
@click.option(
    "--suffix",
    required=True,
    help="Suffix of the backup files to restore",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be restored without actually doing it",
)
def restore(suffix: str, dry_run: bool) -> None:
    """Restore question data from backup files.

    Restores files from backups with the specified suffix.
    """
    console.print(f"[blue]Looking for backups with suffix: {suffix}[/blue]")

    files_to_restore = [
        ("questions.csv", Path("data/questions.csv")),
        ("questions.json", Path("data/questions.json")),
        ("explanations.json", Path("data/explanations.json")),
    ]

    restore_candidates = []

    for _base_name, original_path in files_to_restore:
        backup_path = (
            original_path.parent
            / f"{original_path.stem}_backup_{suffix}{original_path.suffix}"
        )
        if backup_path.exists():
            restore_candidates.append((backup_path, original_path))

    if not restore_candidates:
        console.print(f"[red]❌ No backup files found with suffix: {suffix}[/red]")
        return

    # Show what will be restored
    table = Table(title="Files to Restore")
    table.add_column("Backup File", style="cyan")
    table.add_column("→", style="white")
    table.add_column("Original File", style="green")

    for backup_path, original_path in restore_candidates:
        table.add_row(str(backup_path), "→", str(original_path))

    console.print(table)

    if dry_run:
        console.print("\n[yellow]Dry run mode - no files were changed[/yellow]")
        return

    # Confirm restoration
    if not click.confirm("\nDo you want to restore these files?"):
        console.print("[yellow]Restoration cancelled[/yellow]")
        return

    # Perform restoration
    for backup_path, original_path in restore_candidates:
        shutil.copy2(backup_path, original_path)
        console.print(f"[green]✅ Restored {backup_path} → {original_path}[/green]")

    console.print(
        f"\n[green]Successfully restored {len(restore_candidates)} files[/green]"
    )


@cli.command()
def list() -> None:
    """List all available backup files."""
    data_dir = Path("data")

    if not data_dir.exists():
        console.print("[red]Data directory not found[/red]")
        return

    backup_files = list(data_dir.glob("*_backup_*"))

    if not backup_files:
        console.print("[yellow]No backup files found[/yellow]")
        return

    # Group backups by suffix
    backups_by_suffix = {}
    for backup_file in backup_files:
        # Extract suffix from filename
        parts = backup_file.stem.split("_backup_")
        if len(parts) == 2:
            suffix = parts[1]
            if suffix not in backups_by_suffix:
                backups_by_suffix[suffix] = []
            backups_by_suffix[suffix].append(backup_file)

    # Display backups
    for suffix in sorted(backups_by_suffix.keys(), reverse=True):
        console.print(f"\n[blue]Backup set: {suffix}[/blue]")
        for backup_file in sorted(backups_by_suffix[suffix]):
            size = backup_file.stat().st_size / 1024  # KB
            console.print(f"  - {backup_file.name} ({size:.1f} KB)")


@cli.command()
@click.argument("backup_file", type=click.Path(exists=True, path_type=Path))
def preview(backup_file: Path) -> None:
    """Preview contents of a backup file."""
    console.print(f"[blue]Preview of {backup_file}[/blue]\n")

    if backup_file.suffix == ".json":
        # Preview JSON file
        with open(backup_file, encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            console.print(f"Total items: {len(data)}")
            if data:
                console.print("\nFirst 3 items:")
                for i, item in enumerate(data[:3]):
                    console.print(f"\n[cyan]Item {i + 1}:[/cyan]")
                    if "id" in item:
                        console.print(f"  ID: {item['id']}")
                    if "question" in item:
                        console.print(f"  Question: {item['question'][:80]}...")
                    if "is_image_question" in item:
                        console.print(f"  Image question: {item['is_image_question']}")
        else:
            console.print(f"Data type: {type(data).__name__}")

    elif backup_file.suffix == ".csv":
        # Preview CSV file
        import csv

        with open(backup_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        console.print(f"Total rows: {len(rows)}")
        if rows:
            console.print(f"Columns: {', '.join(rows[0].keys())}")
            console.print("\nFirst 3 rows:")
            for i, row in enumerate(rows[:3]):
                console.print(f"\n[cyan]Row {i + 1}:[/cyan]")
                console.print(f"  ID: {row.get('id', 'N/A')}")
                console.print(f"  Question: {row.get('question', 'N/A')[:80]}...")
                console.print(
                    f"  Image question: {row.get('is_image_question', 'N/A')}"
                )


def main():
    """Entry point for the backup CLI."""
    cli()


if __name__ == "__main__":
    main()
