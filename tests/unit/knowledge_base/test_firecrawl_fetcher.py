"""Tests for the Firecrawl content fetcher."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from src.knowledge_base.firecrawl_fetcher import (
    OFFICIAL_GERMAN_SOURCES,
    FirecrawlContentFetcher,
)


class TestFirecrawlContentFetcher:
    """Tests for FirecrawlContentFetcher class."""

    @patch("src.knowledge_base.firecrawl_fetcher.FirecrawlApp")
    def test_initialization_with_api_key(self, mock_firecrawl_app):
        """Test initialization with API key."""
        with patch.dict("os.environ", {"FIRECRAWL_API_KEY": "test_key"}):
            fetcher = FirecrawlContentFetcher()

        mock_firecrawl_app.assert_called_once_with(api_key="test_key")
        assert fetcher.firecrawl_app is not None
        assert fetcher.cache_dir.name == "firecrawl_cache"

    @patch("src.knowledge_base.firecrawl_fetcher.FirecrawlApp")
    def test_initialization_without_api_key(self, mock_firecrawl_app):
        """Test initialization without API key."""
        with patch.dict("os.environ", {}, clear=True):
            fetcher = FirecrawlContentFetcher()

        # Should not call FirecrawlApp
        mock_firecrawl_app.assert_not_called()
        assert fetcher.firecrawl_app is None

    @patch("src.knowledge_base.firecrawl_fetcher.logger")
    @patch("src.knowledge_base.firecrawl_fetcher.FirecrawlApp")
    def test_initialization_firecrawl_error(self, mock_firecrawl_app, mock_logger):
        """Test initialization when Firecrawl fails."""
        mock_firecrawl_app.side_effect = Exception("Firecrawl init failed")

        with patch.dict("os.environ", {"FIRECRAWL_API_KEY": "test_key"}):
            fetcher = FirecrawlContentFetcher()

        assert fetcher.firecrawl_app is None
        mock_logger.warning.assert_called()

    def test_official_german_sources_list(self):
        """Test that official German sources are properly defined."""
        assert len(OFFICIAL_GERMAN_SOURCES) > 0
        assert "bundesregierung.de" in OFFICIAL_GERMAN_SOURCES
        assert "bundestag.de" in OFFICIAL_GERMAN_SOURCES
        assert "gesetze-im-internet.de" in OFFICIAL_GERMAN_SOURCES

    @patch("src.knowledge_base.firecrawl_fetcher.FirecrawlApp")
    def test_extract_official_content_no_api(self, mock_firecrawl_app):
        """Test extract_official_content when no API key is available."""
        with patch.dict("os.environ", {}, clear=True):
            fetcher = FirecrawlContentFetcher()

        result = fetcher.extract_official_content()

        # Should return empty list
        assert result == []

    @patch("src.knowledge_base.firecrawl_fetcher.FirecrawlApp")
    @patch("builtins.open")
    @patch("src.knowledge_base.firecrawl_fetcher.Path.exists")
    @patch("json.load")
    def test_extract_official_content_cached(
        self, mock_json_load, mock_exists, mock_open, mock_firecrawl_app
    ):
        """Test extract_official_content with cached data."""
        mock_exists.return_value = True
        cached_data = [
            {
                "url": "https://test.de",
                "extracted_data": {"title": "Test", "content": "Test content"},
                "extracted_at": "2025-01-09T12:00:00",
            }
        ]
        mock_json_load.return_value = cached_data

        with patch.dict("os.environ", {"FIRECRAWL_API_KEY": "test_key"}):
            fetcher = FirecrawlContentFetcher()

        result = fetcher.extract_official_content()

        # Should return cached data
        assert len(result) == 1
        assert result[0]["url"] == "https://test.de"

    @patch("src.knowledge_base.firecrawl_fetcher.FirecrawlApp")
    @patch("src.knowledge_base.firecrawl_fetcher.Path.exists")
    def test_extract_official_content_fresh(self, mock_exists, mock_firecrawl_app):
        """Test extract_official_content with fresh extraction."""
        mock_exists.return_value = False  # No cache

        # Mock Firecrawl app
        mock_app = Mock()
        mock_firecrawl_app.return_value = mock_app
        mock_app.llm_extract.return_value = {
            "success": True,
            "data": {
                "title": "Test Title",
                "summary": "Test summary",
                "key_points": ["Point 1", "Point 2"],
                "legal_references": ["BGB §1", "GG Art. 1"],
            },
        }

        with (
            patch.dict("os.environ", {"FIRECRAWL_API_KEY": "test_key"}),
            patch("builtins.open", create=True),
            patch("json.dump"),
        ):
            fetcher = FirecrawlContentFetcher()
            result = fetcher.extract_official_content()

        # Should extract from all sources
        assert len(result) == len(OFFICIAL_GERMAN_SOURCES)
        assert all("extracted_data" in item for item in result)

    @patch("src.knowledge_base.firecrawl_fetcher.FirecrawlApp")
    def test_get_enhanced_context_no_api(self, mock_firecrawl_app):
        """Test get_enhanced_context when no API is available."""
        with patch.dict("os.environ", {}, clear=True):
            fetcher = FirecrawlContentFetcher()

        result = fetcher.get_enhanced_context("test query")

        # Should return empty list
        assert result == []

    @patch("src.knowledge_base.firecrawl_fetcher.FirecrawlApp")
    def test_get_enhanced_context_with_cached_data(self, mock_firecrawl_app):
        """Test get_enhanced_context using cached extracts."""
        mock_app = Mock()
        mock_firecrawl_app.return_value = mock_app

        # Mock cached data
        cached_extracts = [
            {
                "url": "https://bundestag.de/test",
                "extracted_data": {
                    "title": "Bundestag Information",
                    "summary": "Information about German parliament",
                    "key_points": ["Parliament", "Democracy", "Elections"],
                },
            },
            {
                "url": "https://bundesregierung.de/test",
                "extracted_data": {
                    "title": "Government Information",
                    "summary": "Information about German government",
                    "key_points": ["Government", "Chancellor", "Ministers"],
                },
            },
        ]

        with (
            patch.dict("os.environ", {"FIRECRAWL_API_KEY": "test_key"}),
            patch.object(
                fetcher, "extract_official_content", return_value=cached_extracts
            ),
        ):
            fetcher = FirecrawlContentFetcher()
            result = fetcher.get_enhanced_context("parliament elections", max_results=1)

        # Should return most relevant result
        assert len(result) <= 1
        assert any(
            "parliament" in item["extracted_data"]["summary"].lower() for item in result
        )

    def test_get_extraction_schema(self):
        """Test the extraction schema definition."""
        with patch("src.knowledge_base.firecrawl_fetcher.FirecrawlApp"):
            fetcher = FirecrawlContentFetcher()

        schema = fetcher._get_extraction_schema()

        # Verify schema structure
        assert "type" in schema
        assert schema["type"] == "object"
        assert "properties" in schema

        properties = schema["properties"]
        expected_fields = [
            "title",
            "summary",
            "key_points",
            "legal_references",
            "relevant_facts",
        ]
        for field in expected_fields:
            assert field in properties

    @patch("src.knowledge_base.firecrawl_fetcher.logger")
    @patch("src.knowledge_base.firecrawl_fetcher.FirecrawlApp")
    def test_error_handling_during_extraction(self, mock_firecrawl_app, mock_logger):
        """Test error handling during content extraction."""
        # Mock Firecrawl app to raise exception
        mock_app = Mock()
        mock_firecrawl_app.return_value = mock_app
        mock_app.llm_extract.side_effect = Exception("Extraction failed")

        with (
            patch.dict("os.environ", {"FIRECRAWL_API_KEY": "test_key"}),
            patch(
                "src.knowledge_base.firecrawl_fetcher.Path.exists", return_value=False
            ),
            patch("builtins.open", create=True),
            patch("json.dump"),
        ):
            fetcher = FirecrawlContentFetcher()
            result = fetcher.extract_official_content()

        # Should handle errors gracefully
        assert isinstance(result, list)
        mock_logger.error.assert_called()

    def test_relevance_scoring(self):
        """Test relevance scoring for context retrieval."""
        with patch("src.knowledge_base.firecrawl_fetcher.FirecrawlApp"):
            fetcher = FirecrawlContentFetcher()

        # Mock extracts
        extracts = [
            {
                "extracted_data": {
                    "title": "German Parliament",
                    "summary": "Information about the Bundestag and elections",
                    "key_points": ["parliament", "elections", "democracy"],
                }
            },
            {
                "extracted_data": {
                    "title": "German Economy",
                    "summary": "Information about economic policies",
                    "key_points": ["economy", "policies", "trade"],
                }
            },
        ]

        # Test relevance scoring
        query = "parliament elections"
        scored = fetcher._score_relevance(extracts, query)

        # First extract should score higher (contains both "parliament" and "elections")
        assert len(scored) == 2
        assert scored[0][1] > scored[1][1]  # Higher relevance score

    @patch("src.knowledge_base.firecrawl_fetcher.FirecrawlApp")
    def test_cache_management(self, mock_firecrawl_app):
        """Test cache file management."""
        with (
            patch.dict("os.environ", {"FIRECRAWL_API_KEY": "test_key"}),
            patch(
                "src.knowledge_base.firecrawl_fetcher.Path.exists", return_value=False
            ),
            patch("builtins.open", create=True) as mock_open,
            patch("json.dump") as mock_json_dump,
        ):
            mock_app = Mock()
            mock_firecrawl_app.return_value = mock_app
            mock_app.llm_extract.return_value = {
                "success": True,
                "data": {"title": "Test", "summary": "Test"},
            }

            fetcher = FirecrawlContentFetcher()
            fetcher.extract_official_content()

        # Should attempt to save cache
        mock_json_dump.assert_called()

    @patch("src.knowledge_base.firecrawl_fetcher.FirecrawlApp")
    def test_force_refresh_ignores_cache(self, mock_firecrawl_app):
        """Test that force_refresh ignores existing cache."""
        with (
            patch.dict("os.environ", {"FIRECRAWL_API_KEY": "test_key"}),
            patch(
                "src.knowledge_base.firecrawl_fetcher.Path.exists", return_value=True
            ),
            patch("builtins.open", create=True),
            patch("json.dump"),
        ):
            mock_app = Mock()
            mock_firecrawl_app.return_value = mock_app
            mock_app.llm_extract.return_value = {
                "success": True,
                "data": {"title": "Fresh", "summary": "Fresh extract"},
            }

            fetcher = FirecrawlContentFetcher()
            result = fetcher.extract_official_content(force_refresh=True)

        # Should perform fresh extraction despite cache existing
        mock_app.llm_extract.assert_called()
        assert len(result) > 0


class TestFirecrawlContentFetcherIntegration:
    """Integration tests for FirecrawlContentFetcher."""

    @pytest.mark.slow
    def test_placeholder_for_integration_tests(self):
        """Placeholder for future integration tests.

        Future tests might include:
        - Real API calls to Firecrawl (when API key available)
        - Performance testing with large content extraction
        - Cache persistence and retrieval testing
        """
        assert True, "Structure ready for integration tests"
