#!/usr/bin/env python3
"""CLI tool for building and managing the German integration exam knowledge base."""

import logging
import sys

import click
from rich.console import Console
from rich.logging import RichHandler

from src.core.settings import has_rag_config
from src.knowledge_base.rag_engine import RAGEngine

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)

logger = logging.getLogger(__name__)
console = Console()


@click.group()
def cli():
    """German Integration Exam Knowledge Base Management."""
    pass


@cli.command()
@click.option(
    "--force-refresh",
    is_flag=True,
    help="Force refresh content from sources even if cache exists",
)
@click.option(
    "--vector-store-dir",
    help="Directory for vector store persistence (default from settings)",
)
@click.option(
    "--collection-name",
    help="Name of the vector store collection (default from settings)",
)
@click.option(
    "--chunk-size",
    type=int,
    help="Size of text chunks for indexing (default from settings)",
)
@click.option(
    "--chunk-overlap",
    type=int,
    help="Overlap between text chunks (default from settings)",
)
def build(
    force_refresh: bool,
    vector_store_dir: str | None,
    collection_name: str | None,
    chunk_size: int | None,
    chunk_overlap: int | None,
):
    """Build the knowledge base from official sources."""
    try:
        console.print(
            "[bold cyan]Building German Integration Exam Knowledge Base[/bold cyan]"
        )

        # Check dependencies
        if not has_rag_config():
            console.print("[bold red]Missing RAG dependencies[/bold red]")
            console.print(
                "Install with: [bold]pip install chromadb sentence-transformers[/bold]"
            )
            console.print(
                "Optional for enhanced web scraping: [bold]pip install firecrawl-py[/bold]"
            )
            sys.exit(1)

        # Initialize RAG engine
        rag_engine = RAGEngine(
            vector_store_dir=vector_store_dir,
            collection_name=collection_name,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        # Build knowledge base
        success = rag_engine.build_knowledge_base(force_refresh=force_refresh)

        if success:
            # Show stats
            stats = rag_engine.get_knowledge_base_stats()
            console.print(
                "\n[bold green]✓ Knowledge base built successfully![/bold green]"
            )
            console.print(f"Total documents: {stats['total_documents']}")
            console.print(f"Collection: {stats['collection_name']}")
            console.print(f"Location: {stats['persist_directory']}")

            if stats["sources"]:
                console.print("\nSources:")
                for source, count in stats["sources"].items():
                    console.print(f"  • {source}: {count} documents")

            sys.exit(0)
        else:
            console.print("[bold red]✗ Failed to build knowledge base[/bold red]")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Error building knowledge base: {e}")
        sys.exit(1)


@cli.command()
@click.option(
    "--vector-store-dir",
    help="Directory for vector store persistence (default from settings)",
)
@click.option(
    "--collection-name",
    help="Name of the vector store collection (default from settings)",
)
def stats(vector_store_dir: str | None, collection_name: str | None):
    """Show knowledge base statistics."""
    try:
        rag_engine = RAGEngine(
            vector_store_dir=vector_store_dir, collection_name=collection_name
        )

        stats = rag_engine.get_knowledge_base_stats()

        console.print("[bold cyan]Knowledge Base Statistics[/bold cyan]")
        console.print(f"Total documents: {stats['total_documents']}")
        console.print(f"Collection: {stats['collection_name']}")
        console.print(f"Location: {stats['persist_directory']}")

        if stats["sources"]:
            console.print("\nDocument sources:")
            for source, count in stats["sources"].items():
                console.print(f"  • {source}: {count} documents")

        if stats["types"]:
            console.print("\nDocument types:")
            for doc_type, count in stats["types"].items():
                console.print(f"  • {doc_type}: {count} documents")

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        sys.exit(1)


@cli.command()
@click.argument("query")
@click.option("--k", default=3, help="Number of documents to retrieve")
@click.option(
    "--vector-store-dir",
    help="Directory for vector store persistence (default from settings)",
)
@click.option(
    "--collection-name",
    help="Name of the vector store collection (default from settings)",
)
def search(
    query: str, k: int, vector_store_dir: str | None, collection_name: str | None
):
    """Search the knowledge base."""
    try:
        rag_engine = RAGEngine(
            vector_store_dir=vector_store_dir, collection_name=collection_name
        )

        results = rag_engine.search_knowledge_base(query=query, k=k)

        console.print(f"[bold cyan]Search results for: '{query}'[/bold cyan]")
        console.print(f"Found {len(results)} documents")

        for i, doc in enumerate(results, 1):
            console.print(
                f"\n[bold]{i}. [/bold][green]{doc['metadata'].get('source', 'Unknown')}[/green]"
            )
            console.print(f"Score: {doc.get('score', 0.0):.3f}")
            console.print(f"Title: {doc['metadata'].get('title', 'No title')}")
            console.print(f"Content: {doc['content'][:200]}...")

    except Exception as e:
        logger.error(f"Error searching: {e}")
        sys.exit(1)


@cli.command()
@click.argument("query")
@click.option(
    "--vector-store-dir",
    help="Directory for vector store persistence (default from settings)",
)
@click.option(
    "--collection-name",
    help="Name of the vector store collection (default from settings)",
)
def test(query: str, vector_store_dir: str | None, collection_name: str | None):
    """Test RAG with a query."""
    try:
        rag_engine = RAGEngine(
            vector_store_dir=vector_store_dir, collection_name=collection_name
        )

        result = rag_engine.test_rag_query(query=query)

        console.print(f"[bold cyan]RAG Test: '{result['query']}'[/bold cyan]")
        console.print(f"Context used: {result['context_used']}")

        if result["results"]:
            console.print(f"\nRetrieved {len(result['results'])} documents:")
            for i, doc in enumerate(result["results"], 1):
                console.print(f"{i}. {doc['source']} (Score: {doc['score']:.3f})")
                console.print(f"   {doc['content']}")

        console.print("\n[bold green]Answer:[/bold green]")
        console.print(result["answer"])

    except Exception as e:
        logger.error(f"Error testing RAG: {e}")
        sys.exit(1)


@cli.command()
@click.option(
    "--vector-store-dir",
    help="Directory for vector store persistence (default from settings)",
)
@click.option(
    "--collection-name",
    help="Name of the vector store collection (default from settings)",
)
@click.confirmation_option(prompt="Are you sure you want to clear the knowledge base?")
def clear(vector_store_dir: str | None, collection_name: str | None):
    """Clear the knowledge base."""
    try:
        rag_engine = RAGEngine(
            vector_store_dir=vector_store_dir, collection_name=collection_name
        )

        success = rag_engine.clear_knowledge_base()

        if success:
            console.print("[bold green]✓ Knowledge base cleared[/bold green]")
        else:
            console.print("[bold red]✗ Failed to clear knowledge base[/bold red]")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Error clearing knowledge base: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
