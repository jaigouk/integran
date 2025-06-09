"""Enhanced content fetcher using Firecrawl LLM-extract for structured content."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.core.settings import get_settings

try:
    from firecrawl import FirecrawlApp

    FIRECRAWL_AVAILABLE = True
except ImportError:
    FIRECRAWL_AVAILABLE = False
    FirecrawlApp = None

logger = logging.getLogger(__name__)


class GermanLegalDocument(BaseModel):
    """Schema for extracting German legal/integration content."""

    title: str = Field(description="Title of the document or section")
    content_type: str = Field(
        description="Type of content: law, regulation, guide, etc."
    )
    key_points: list[str] = Field(description="Main points or key information")
    relevant_articles: list[str] = Field(
        description="Relevant Grundgesetz articles or legal references"
    )
    integration_relevance: str = Field(
        description="How this relates to German integration/citizenship"
    )
    summary: str = Field(description="Brief summary of the content")


class HistoricalEvent(BaseModel):
    """Schema for extracting historical information."""

    event_name: str = Field(description="Name of the historical event")
    date: str = Field(description="Date or time period")
    significance: str = Field(
        description="Why this event is important for integration test"
    )
    key_facts: list[str] = Field(description="Important facts to remember")
    related_concepts: list[str] = Field(description="Related historical concepts")


class PoliticalConcept(BaseModel):
    """Schema for extracting political system information."""

    concept_name: str = Field(description="Name of the political concept")
    definition: str = Field(description="Clear definition")
    how_it_works: str = Field(description="How this concept works in Germany")
    importance: str = Field(description="Why this is important for residents")
    examples: list[str] = Field(description="Practical examples")


class FirecrawlContentFetcher:
    """Enhanced content fetcher using Firecrawl LLM-extract."""

    def __init__(self) -> None:
        """Initialize the Firecrawl content fetcher."""
        if not FIRECRAWL_AVAILABLE:
            raise ImportError(
                "firecrawl-py package is required. Install with: pip install firecrawl-py"
            )

        settings = get_settings()
        if not settings.firecrawl_api_key:
            raise ValueError(
                "FIRECRAWL_API_KEY is required. Get one from https://www.firecrawl.dev/"
            )

        self.client = FirecrawlApp(api_key=settings.firecrawl_api_key)
        self.cache_dir = Path(settings.knowledge_base_cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Official German sources for integration content
        self.sources = {
            "legal": [
                "https://www.gesetze-im-internet.de/gg/",
                "https://www.bundesverfassungsgericht.de/",
                "https://www.bundestag.de/parlament/aufgaben",
                "https://www.bundesrat.de/DE/aufgaben-funktion/aufgaben-funktion-node.html",
            ],
            "integration": [
                "https://www.bamf.de/DE/Themen/Integration/ZugewanderteTeilnehmende/Einbuergerung/einbuergerung-node.html",
                "https://www.bamf.de/DE/Themen/Integration/ZugewanderteTeilnehmende/Integrationskurse/integrationskurse-node.html",
                "https://www.bmi.bund.de/DE/themen/verfassung/staatsbuergerschaft/einbuergerung/einbuergerung-node.html",
            ],
            "history": [
                "https://www.bpb.de/themen/deutsche-einheit/",
                "https://www.bpb.de/themen/nationalsozialismus-zweiter-weltkrieg/",
                "https://www.bpb.de/themen/politisches-system/grundgesetz/",
            ],
            "political_system": [
                "https://www.bpb.de/themen/politisches-system/politik-einfach-fuer-alle/",
                "https://www.bundestag.de/parlament",
                "https://www.bundesregierung.de/breg-de/themen/deutsche-einheit",
            ],
        }

    def extract_official_content(
        self, force_refresh: bool = False
    ) -> list[dict[str, Any]]:
        """Extract structured content from official German sources."""
        cache_file = self.cache_dir / "firecrawl_extracts.json"

        # Check cache
        if not force_refresh and cache_file.exists():
            try:
                with open(cache_file, encoding="utf-8") as f:
                    cached_data = json.load(f)
                    cached_time = datetime.fromisoformat(cached_data["extracted_at"])
                    # Use cache if less than 24 hours old
                    if (
                        datetime.now(UTC) - cached_time.replace(tzinfo=UTC)
                    ).total_seconds() < 86400:
                        logger.info("Using cached Firecrawl extracts")
                        return cached_data["extracts"]
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")

        logger.info("Extracting structured content using Firecrawl LLM-extract...")
        all_extracts = []

        # Extract legal documents
        for url in self.sources["legal"]:
            extracts = self._extract_legal_content(url)
            all_extracts.extend(extracts)

        # Extract integration information
        for url in self.sources["integration"]:
            extracts = self._extract_integration_content(url)
            all_extracts.extend(extracts)

        # Extract historical information
        for url in self.sources["history"]:
            extracts = self._extract_historical_content(url)
            all_extracts.extend(extracts)

        # Extract political system information
        for url in self.sources["political_system"]:
            extracts = self._extract_political_content(url)
            all_extracts.extend(extracts)

        # Cache results
        cache_data = {
            "extracted_at": datetime.now(UTC).isoformat(),
            "extracts": all_extracts,
        }
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Extracted {len(all_extracts)} structured documents")
        return all_extracts

    def _extract_legal_content(self, url: str) -> list[dict[str, Any]]:
        """Extract legal content using LLM-extract."""
        try:
            result = self.client.extract_with_llm(
                url=url,
                schema=GermanLegalDocument.model_json_schema(),
                prompt="""Extract key legal information relevant to German integration and citizenship.
                Focus on:
                - Constitutional principles (Grundgesetz)
                - Rights and duties of residents
                - Legal procedures for integration
                - Important legal concepts for the integration exam

                Provide accurate, exam-relevant information.""",
            )

            if result and "data" in result:
                return [
                    {
                        "source": "legal",
                        "url": url,
                        "type": "legal_document",
                        "extracted_data": result["data"],
                        "extracted_at": datetime.now(UTC).isoformat(),
                    }
                ]

        except Exception as e:
            logger.error(f"Failed to extract legal content from {url}: {e}")

        return []

    def _extract_integration_content(self, url: str) -> list[dict[str, Any]]:
        """Extract integration-specific content."""
        try:
            result = self.client.extract_with_llm(
                url=url,
                schema=GermanLegalDocument.model_json_schema(),
                prompt="""Extract information about German integration courses and citizenship requirements.
                Focus on:
                - Integration course requirements
                - Citizenship application process
                - Required documents and procedures
                - Rights and obligations of residents
                - Cultural and social integration aspects

                Provide practical, exam-relevant information.""",
            )

            if result and "data" in result:
                return [
                    {
                        "source": "integration",
                        "url": url,
                        "type": "integration_guide",
                        "extracted_data": result["data"],
                        "extracted_at": datetime.now(UTC).isoformat(),
                    }
                ]

        except Exception as e:
            logger.error(f"Failed to extract integration content from {url}: {e}")

        return []

    def _extract_historical_content(self, url: str) -> list[dict[str, Any]]:
        """Extract historical information."""
        try:
            result = self.client.extract_with_llm(
                url=url,
                schema=HistoricalEvent.model_json_schema(),
                prompt="""Extract important historical events and periods relevant to German integration exam.
                Focus on:
                - Key dates in German history (1933-1945, 1949, 1961, 1989, 1990)
                - Nazi period and World War II
                - Division and reunification of Germany
                - Development of democracy in Germany
                - Important historical figures and events

                Provide factual, exam-relevant historical information.""",
            )

            if result and "data" in result:
                return [
                    {
                        "source": "history",
                        "url": url,
                        "type": "historical_event",
                        "extracted_data": result["data"],
                        "extracted_at": datetime.now(UTC).isoformat(),
                    }
                ]

        except Exception as e:
            logger.error(f"Failed to extract historical content from {url}: {e}")

        return []

    def _extract_political_content(self, url: str) -> list[dict[str, Any]]:
        """Extract political system information."""
        try:
            result = self.client.extract_with_llm(
                url=url,
                schema=PoliticalConcept.model_json_schema(),
                prompt="""Extract information about the German political system and democratic principles.
                Focus on:
                - Federal structure and federalism
                - Separation of powers (Gewaltenteilung)
                - Electoral system and democracy
                - Role of Bundestag, Bundesrat, government
                - Constitutional principles and basic rights
                - European Union and Germany's role

                Provide clear, exam-relevant explanations of political concepts.""",
            )

            if result and "data" in result:
                return [
                    {
                        "source": "political_system",
                        "url": url,
                        "type": "political_concept",
                        "extracted_data": result["data"],
                        "extracted_at": datetime.now(UTC).isoformat(),
                    }
                ]

        except Exception as e:
            logger.error(f"Failed to extract political content from {url}: {e}")

        return []

    def get_enhanced_context(
        self, query: str, max_results: int = 5
    ) -> list[dict[str, Any]]:
        """Get enhanced context for a specific query."""
        all_extracts = self.extract_official_content()

        # Simple keyword matching for now
        # In a production system, you'd use vector similarity search
        relevant_extracts = []
        query_lower = query.lower()

        for extract in all_extracts:
            extracted_data = extract.get("extracted_data", {})

            # Check various fields for relevance
            relevance_score = 0

            # Check title
            title = extracted_data.get("title", "")
            if any(word in title.lower() for word in query_lower.split()):
                relevance_score += 3

            # Check summary
            summary = extracted_data.get("summary", "")
            if any(word in summary.lower() for word in query_lower.split()):
                relevance_score += 2

            # Check key points
            key_points = extracted_data.get("key_points", [])
            for point in key_points:
                if any(word in point.lower() for word in query_lower.split()):
                    relevance_score += 1

            if relevance_score > 0:
                extract["relevance_score"] = relevance_score
                relevant_extracts.append(extract)

        # Sort by relevance and return top results
        relevant_extracts.sort(key=lambda x: x["relevance_score"], reverse=True)
        return relevant_extracts[:max_results]

    def has_firecrawl_config(self) -> bool:
        """Check if Firecrawl is properly configured."""
        settings = get_settings()
        return bool(FIRECRAWL_AVAILABLE and settings.firecrawl_api_key)
