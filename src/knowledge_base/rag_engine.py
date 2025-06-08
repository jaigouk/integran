"""Clean RAG engine implementation without LangChain."""

import logging
from typing import Any

from rich.console import Console
from rich.progress import track

from src.core.settings import get_settings
from src.knowledge_base.content_fetcher import ContentFetcher
from src.knowledge_base.text_splitter import create_text_splitter
from src.knowledge_base.vector_store import VectorStore
from src.utils.gemini_client import GeminiClient

logger = logging.getLogger(__name__)
console = Console()


class RAGEngine:
    """Retrieval-Augmented Generation engine for German integration exam explanations."""

    def __init__(
        self,
        vector_store_dir: str | None = None,
        collection_name: str | None = None,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ):
        # Get settings for defaults
        settings = get_settings()

        # Use settings defaults if not provided
        vector_store_dir = vector_store_dir or settings.vector_store_dir
        collection_name = collection_name or settings.vector_collection_name
        chunk_size = chunk_size or settings.chunk_size
        chunk_overlap = chunk_overlap or settings.chunk_overlap

        # Initialize components
        self.content_fetcher = ContentFetcher()
        self.text_splitter = create_text_splitter(
            splitter_type="recursive",
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        self.vector_store = VectorStore(
            collection_name=collection_name,
            persist_directory=vector_store_dir,
            embedding_model=settings.embedding_model,
        )
        self.gemini_client = GeminiClient()

        logger.info("RAG engine initialized")

    def build_knowledge_base(self, force_refresh: bool = False) -> bool:
        """Build the knowledge base by fetching and indexing content."""
        try:
            console.print("[bold cyan]Building knowledge base...[/bold cyan]")

            # Check if knowledge base already exists and is recent
            kb_info = self.vector_store.get_collection_info()
            if not force_refresh and kb_info.get("count", 0) > 0:
                console.print(
                    f"[green]Knowledge base already exists with {kb_info['count']} documents[/green]"
                )
                return True

            # Fetch content from sources
            all_content = self.content_fetcher.fetch_all_content(
                force_refresh=force_refresh
            )

            if not any(all_content.values()):
                logger.error("No content fetched from sources")
                return False

            # Process and index content
            total_docs = 0

            # Process web pages
            if all_content["web_pages"]:
                console.print("[yellow]Processing web pages...[/yellow]")
                for content in track(
                    all_content["web_pages"], description="Indexing web pages"
                ):
                    docs = self._process_content(content)
                    if docs:
                        self._index_documents(docs)
                        total_docs += len(docs)

            # Process PDFs
            if all_content["pdfs"]:
                console.print("[yellow]Processing PDFs...[/yellow]")
                for content in track(all_content["pdfs"], description="Indexing PDFs"):
                    docs = self._process_content(content)
                    if docs:
                        self._index_documents(docs)
                        total_docs += len(docs)

            # Process structured data
            if all_content["structured_data"]:
                console.print("[yellow]Processing structured data...[/yellow]")
                for content in track(
                    all_content["structured_data"],
                    description="Indexing structured data",
                ):
                    docs = self._process_content(content)
                    if docs:
                        self._index_documents(docs)
                        total_docs += len(docs)

            console.print(
                f"[bold green]✓ Knowledge base built with {total_docs} documents[/bold green]"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to build knowledge base: {e}")
            console.print(f"[bold red]✗ Failed to build knowledge base: {e}[/bold red]")
            return False

    def _process_content(self, content: dict[str, Any]) -> list[dict[str, Any]]:
        """Process content into documents."""
        if not content.get("content"):
            return []

        # Split content into chunks
        chunks = self.text_splitter.split_text(content["content"])

        # Create documents with metadata
        documents = []
        for i, chunk in enumerate(chunks):
            doc = {
                "content": chunk,
                "metadata": {
                    "source": content.get("source", "unknown"),
                    "title": content.get("title", ""),
                    "url": content.get("url", ""),
                    "type": content.get("type", "document"),
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "fetched_at": content.get("fetched_at", ""),
                    **content.get("metadata", {}),
                },
            }
            documents.append(doc)

        return documents

    def _index_documents(self, documents: list[dict[str, Any]]) -> None:
        """Index documents in the vector store."""
        if not documents:
            return

        texts = [doc["content"] for doc in documents]
        metadatas = [doc["metadata"] for doc in documents]

        self.vector_store.add_documents(texts=texts, metadatas=metadatas)

    def search_knowledge_base(
        self,
        query: str,
        k: int = 4,
        source_filter: str | None = None,
        type_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search the knowledge base for relevant documents."""
        # Build where clause for filtering
        where = {}
        if source_filter:
            where["source"] = source_filter
        if type_filter:
            where["type"] = type_filter

        # Search for similar documents
        results = self.vector_store.similarity_search(
            query=query, k=k, where=where if where else None
        )

        return results

    def generate_explanation_with_rag(
        self,
        question: str,
        correct_answer: str,
        options: dict[str, str],
        category: str = "",
        max_context_length: int = 3000,
    ) -> dict[str, Any]:
        """Generate explanation using RAG."""
        try:
            # Build search query
            search_query = f"{question} {correct_answer} {category}"

            # Search for relevant context
            context_docs = self.search_knowledge_base(
                query=search_query,
                k=6,  # Get more documents for better context
            )

            # Build context from retrieved documents
            context_parts = []
            total_length = 0

            for doc in context_docs:
                content = doc["content"]
                source = doc["metadata"].get("source", "")

                # Add source information
                context_part = f"[Quelle: {source}]\n{content}"

                # Check if adding this would exceed max length
                if total_length + len(context_part) > max_context_length:
                    break

                context_parts.append(context_part)
                total_length += len(context_part)

            context = "\n\n".join(context_parts)

            # Create system prompt for explanations
            system_prompt = """Du bist ein erfahrener Lehrer für den deutschen Einbürgerungstest.
Erstelle klare, verständliche Erklärungen basierend auf den gegebenen Kontextinformationen.

ANFORDERUNGEN:
1. Erkläre auf Deutsch in einfacher, klarer Sprache
2. Erkläre WARUM die richtige Antwort richtig ist
3. Erkläre KURZ warum die anderen Optionen falsch sind
4. Nutze die Kontextinformationen für historische/rechtliche Details
5. Gib einen Merksatz oder eine Eselsbrücke, falls hilfreich
6. Fokussiere auf das Verständnis des Konzepts"""

            # Build the query
            options_text = "\n".join(
                [f"{letter}: {text}" for letter, text in options.items()]
            )
            query = f"""Frage: {question}

Antwortoptionen:
{options_text}

Richtige Antwort: {correct_answer}
Kategorie: {category}

Erstelle eine ausführliche Erklärung, warum diese Antwort richtig ist und warum die anderen falsch sind."""

            # Generate explanation with context
            explanation = self.gemini_client.generate_with_context(
                query=query,
                context=context,
                system_prompt=system_prompt,
                max_output_tokens=2048,
                temperature=0.3,
            )

            # Extract key concepts from the context
            key_concepts = self.gemini_client.extract_key_concepts(
                text=context, max_concepts=5
            )

            return {
                "explanation": explanation,
                "key_concepts": key_concepts,
                "context_sources": [
                    doc["metadata"].get("source", "") for doc in context_docs
                ],
                "context_used": len(context_parts) > 0,
            }

        except Exception as e:
            logger.error(f"Failed to generate RAG explanation: {e}")
            # Fallback to simple explanation without context
            return self._generate_fallback_explanation(
                question, correct_answer, options
            )

    def _generate_fallback_explanation(
        self, question: str, correct_answer: str, options: dict[str, str]
    ) -> dict[str, Any]:
        """Generate fallback explanation without RAG context."""
        try:
            options_text = "\n".join(
                [f"{letter}: {text}" for letter, text in options.items()]
            )

            prompt = f"""Erkläre kurz, warum die folgende Antwort beim deutschen Einbürgerungstest richtig ist:

Frage: {question}
Antwortoptionen:
{options_text}
Richtige Antwort: {correct_answer}

Gib eine klare Erklärung auf Deutsch."""

            explanation = self.gemini_client.generate_text(
                prompt=prompt, max_output_tokens=1024, temperature=0.3
            )

            return {
                "explanation": explanation,
                "key_concepts": [],
                "context_sources": [],
                "context_used": False,
            }

        except Exception as e:
            logger.error(f"Failed to generate fallback explanation: {e}")
            return {
                "explanation": "Erklärung konnte nicht generiert werden.",
                "key_concepts": [],
                "context_sources": [],
                "context_used": False,
            }

    def get_knowledge_base_stats(self) -> dict[str, Any]:
        """Get statistics about the knowledge base."""
        kb_info = self.vector_store.get_collection_info()

        # Get source distribution
        source_docs = self.vector_store.search_by_metadata(
            where={},
            limit=1000,  # Get a sample to analyze
        )

        sources = {}
        types = {}
        for doc in source_docs:
            source = doc["metadata"].get("source", "unknown")
            doc_type = doc["metadata"].get("type", "unknown")

            sources[source] = sources.get(source, 0) + 1
            types[doc_type] = types.get(doc_type, 0) + 1

        return {
            "total_documents": kb_info.get("count", 0),
            "collection_name": kb_info.get("name", ""),
            "persist_directory": kb_info.get("persist_directory", ""),
            "sources": sources,
            "types": types,
        }

    def clear_knowledge_base(self) -> bool:
        """Clear the knowledge base."""
        try:
            self.vector_store.delete_collection()
            console.print("[yellow]Knowledge base cleared[/yellow]")
            return True
        except Exception as e:
            logger.error(f"Failed to clear knowledge base: {e}")
            return False

    def test_rag_query(self, query: str, k: int = 3) -> dict[str, Any]:
        """Test RAG with a simple query."""
        try:
            # Search for relevant documents
            results = self.search_knowledge_base(query=query, k=k)

            if not results:
                return {
                    "query": query,
                    "results": [],
                    "answer": "Keine relevanten Dokumente gefunden.",
                    "context_used": False,
                }

            # Build context
            context = "\n\n".join([doc["content"] for doc in results])

            # Generate answer
            answer = self.gemini_client.generate_with_context(
                query=query, context=context, max_output_tokens=1024
            )

            return {
                "query": query,
                "results": [
                    {
                        "content": doc["content"][:200] + "...",
                        "source": doc["metadata"].get("source", ""),
                        "score": doc.get("score", 0.0),
                    }
                    for doc in results
                ],
                "answer": answer,
                "context_used": True,
            }

        except Exception as e:
            logger.error(f"RAG test query failed: {e}")
            return {
                "query": query,
                "results": [],
                "answer": f"Fehler: {e}",
                "context_used": False,
            }
