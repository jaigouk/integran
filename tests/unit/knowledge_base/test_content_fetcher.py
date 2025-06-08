"""Tests for content fetcher functionality."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import requests

from src.knowledge_base.content_fetcher import ContentFetcher


class TestContentFetcher:
    """Test content fetcher functionality."""

    def setup_method(self):
        """Setup for each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_dir = Path(self.temp_dir)

    @patch("src.knowledge_base.content_fetcher.get_settings")
    def test_init_with_default_cache_dir(self, mock_get_settings):
        """Test initialization with default cache directory."""
        mock_settings = Mock()
        mock_settings.knowledge_base_cache_dir = "data/knowledge_base/raw"
        mock_settings.firecrawl_api_key = ""
        mock_get_settings.return_value = mock_settings

        with patch("src.knowledge_base.content_fetcher.FIRECRAWL_AVAILABLE", False):
            fetcher = ContentFetcher()

            assert "knowledge_base/raw" in str(fetcher.cache_dir)
            assert fetcher.firecrawl is None

    @patch("src.knowledge_base.content_fetcher.get_settings")
    @patch("src.knowledge_base.content_fetcher.FirecrawlApp")
    def test_init_with_firecrawl(self, mock_firecrawl_app, mock_get_settings):
        """Test initialization with Firecrawl API key."""
        mock_settings = Mock()
        mock_settings.knowledge_base_cache_dir = str(self.test_dir)
        mock_settings.firecrawl_api_key = "test-api-key"
        mock_get_settings.return_value = mock_settings

        mock_firecrawl_instance = Mock()
        mock_firecrawl_app.return_value = mock_firecrawl_instance

        with patch("src.knowledge_base.content_fetcher.FIRECRAWL_AVAILABLE", True):
            fetcher = ContentFetcher()

            assert fetcher.firecrawl == mock_firecrawl_instance
            mock_firecrawl_app.assert_called_once_with(api_key="test-api-key")

    @patch("src.knowledge_base.content_fetcher.get_settings")
    def test_init_custom_cache_dir(self, mock_get_settings):
        """Test initialization with custom cache directory."""
        mock_settings = Mock()
        mock_settings.firecrawl_api_key = ""
        mock_get_settings.return_value = mock_settings

        with patch("src.knowledge_base.content_fetcher.FIRECRAWL_AVAILABLE", False):
            fetcher = ContentFetcher(cache_dir=self.test_dir)

            assert fetcher.cache_dir == self.test_dir
            assert self.test_dir.exists()

    @patch("src.knowledge_base.content_fetcher.get_settings")
    def test_has_recent_cache_true(self, mock_get_settings):
        """Test cache detection when recent cache exists."""
        mock_settings = Mock()
        mock_settings.knowledge_base_cache_dir = str(self.test_dir)
        mock_settings.firecrawl_api_key = ""
        mock_get_settings.return_value = mock_settings

        # Create cache file with recent timestamp
        cache_file = self.test_dir / "content_cache.json"
        cache_data = {
            "cached_at": datetime.now().isoformat(),
            "content": {"web_pages": [], "pdfs": [], "structured_data": []},
        }
        cache_file.write_text(json.dumps(cache_data))

        with patch("src.knowledge_base.content_fetcher.FIRECRAWL_AVAILABLE", False):
            fetcher = ContentFetcher(cache_dir=self.test_dir)
            assert fetcher._has_recent_cache() is True

    @patch("src.knowledge_base.content_fetcher.get_settings")
    def test_has_recent_cache_false_old(self, mock_get_settings):
        """Test cache detection when cache is old."""
        mock_settings = Mock()
        mock_settings.knowledge_base_cache_dir = str(self.test_dir)
        mock_settings.firecrawl_api_key = ""
        mock_get_settings.return_value = mock_settings

        # Create cache file with old timestamp (8 days ago)
        cache_file = self.test_dir / "content_cache.json"
        old_date = datetime.now() - timedelta(days=8)
        cache_data = {
            "cached_at": old_date.isoformat(),
            "content": {"web_pages": [], "pdfs": [], "structured_data": []},
        }
        cache_file.write_text(json.dumps(cache_data))

        with patch("src.knowledge_base.content_fetcher.FIRECRAWL_AVAILABLE", False):
            fetcher = ContentFetcher(cache_dir=self.test_dir)
            assert fetcher._has_recent_cache() is False

    @patch("src.knowledge_base.content_fetcher.get_settings")
    def test_has_recent_cache_false_no_file(self, mock_get_settings):
        """Test cache detection when no cache file exists."""
        mock_settings = Mock()
        mock_settings.knowledge_base_cache_dir = str(self.test_dir)
        mock_settings.firecrawl_api_key = ""
        mock_get_settings.return_value = mock_settings

        with patch("src.knowledge_base.content_fetcher.FIRECRAWL_AVAILABLE", False):
            fetcher = ContentFetcher(cache_dir=self.test_dir)
            assert fetcher._has_recent_cache() is False

    @patch("src.knowledge_base.content_fetcher.get_settings")
    @patch("requests.get")
    def test_fetch_web_content_without_firecrawl(
        self, mock_requests_get, mock_get_settings
    ):
        """Test web content fetching without Firecrawl."""
        mock_settings = Mock()
        mock_settings.knowledge_base_cache_dir = str(self.test_dir)
        mock_settings.firecrawl_api_key = ""
        mock_get_settings.return_value = mock_settings

        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b"""
        <html>
            <head><title>Test Page</title></head>
            <body>
                <main>
                    <h1>Main Content</h1>
                    <p>This is the main content.</p>
                </main>
                <script>console.log('remove me');</script>
            </body>
        </html>
        """
        mock_requests_get.return_value = mock_response

        with patch("src.knowledge_base.content_fetcher.FIRECRAWL_AVAILABLE", False):
            fetcher = ContentFetcher(cache_dir=self.test_dir)
            result = fetcher._fetch_web_content("test_source", "https://example.com")

            assert result is not None
            assert result["source"] == "test_source"
            assert result["url"] == "https://example.com"
            assert result["title"] == "Test Page"
            assert "Main Content" in result["content"]
            assert "console.log" not in result["content"]  # Script should be removed
            assert result["type"] == "web_page"

    @patch("src.knowledge_base.content_fetcher.get_settings")
    @patch("src.knowledge_base.content_fetcher.FirecrawlApp")
    def test_fetch_web_content_with_firecrawl(
        self, mock_firecrawl_app, mock_get_settings
    ):
        """Test web content fetching with Firecrawl."""
        mock_settings = Mock()
        mock_settings.knowledge_base_cache_dir = str(self.test_dir)
        mock_settings.firecrawl_api_key = "test-key"
        mock_get_settings.return_value = mock_settings

        # Mock Firecrawl response
        mock_firecrawl_instance = Mock()
        mock_firecrawl_instance.scrape_url.return_value = {
            "data": {
                "markdown": "# Main Content\n\nThis is the main content.",
                "metadata": {"title": "Test Page", "description": "Test description"},
            }
        }
        mock_firecrawl_app.return_value = mock_firecrawl_instance

        with patch("src.knowledge_base.content_fetcher.FIRECRAWL_AVAILABLE", True):
            fetcher = ContentFetcher(cache_dir=self.test_dir)
            result = fetcher._fetch_web_content("test_source", "https://example.com")

            assert result is not None
            assert result["source"] == "test_source"
            assert result["url"] == "https://example.com"
            assert result["title"] == "Test Page"
            assert "Main Content" in result["content"]
            assert result["type"] == "web_page"

    @patch("src.knowledge_base.content_fetcher.get_settings")
    @patch("requests.get")
    def test_fetch_web_content_failure(self, mock_requests_get, mock_get_settings):
        """Test web content fetching failure."""
        mock_settings = Mock()
        mock_settings.knowledge_base_cache_dir = str(self.test_dir)
        mock_settings.firecrawl_api_key = ""
        mock_get_settings.return_value = mock_settings

        # Mock failed HTTP response
        mock_requests_get.side_effect = requests.RequestException("Network error")

        with patch("src.knowledge_base.content_fetcher.FIRECRAWL_AVAILABLE", False):
            fetcher = ContentFetcher(cache_dir=self.test_dir)
            result = fetcher._fetch_web_content("test_source", "https://example.com")

            assert result is None

    @patch("src.knowledge_base.content_fetcher.get_settings")
    @patch("src.knowledge_base.content_fetcher.PYPDF_AVAILABLE", True)
    @patch("src.knowledge_base.content_fetcher.PdfReader")
    @patch("requests.get")
    def test_fetch_pdf_content_success(
        self, mock_requests_get, mock_pdf_reader, mock_get_settings
    ):
        """Test PDF content fetching success."""
        mock_settings = Mock()
        mock_settings.knowledge_base_cache_dir = str(self.test_dir)
        mock_settings.firecrawl_api_key = ""
        mock_get_settings.return_value = mock_settings

        # Mock successful PDF download
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b"fake pdf content"
        mock_requests_get.return_value = mock_response

        # Mock PDF reader
        mock_page1 = Mock()
        mock_page1.extract_text.return_value = "Page 1 content"
        mock_page2 = Mock()
        mock_page2.extract_text.return_value = "Page 2 content"

        mock_reader_instance = Mock()
        mock_reader_instance.pages = [mock_page1, mock_page2]
        mock_reader_instance.metadata = {"title": "Test PDF"}
        mock_pdf_reader.return_value = mock_reader_instance

        with (
            patch("src.knowledge_base.content_fetcher.FIRECRAWL_AVAILABLE", False),
            patch("builtins.open", mock_open()),
        ):
            fetcher = ContentFetcher(cache_dir=self.test_dir)
            result = fetcher._fetch_pdf_content(
                "test_pdf", "https://example.com/test.pdf"
            )

            assert result is not None
            assert result["source"] == "test_pdf"
            assert result["url"] == "https://example.com/test.pdf"
            assert "Page 1 content" in result["content"]
            assert "Page 2 content" in result["content"]
            assert result["type"] == "pdf"
            assert result["metadata"]["num_pages"] == 2

    @patch("src.knowledge_base.content_fetcher.get_settings")
    def test_fetch_pdf_content_not_available(self, mock_get_settings):
        """Test PDF content fetching when pypdf is not available."""
        mock_settings = Mock()
        mock_settings.knowledge_base_cache_dir = str(self.test_dir)
        mock_settings.firecrawl_api_key = ""
        mock_get_settings.return_value = mock_settings

        with (
            patch("src.knowledge_base.content_fetcher.PYPDF_AVAILABLE", False),
            patch("src.knowledge_base.content_fetcher.FIRECRAWL_AVAILABLE", False),
        ):
            fetcher = ContentFetcher(cache_dir=self.test_dir)
            result = fetcher._fetch_pdf_content(
                "test_pdf", "https://example.com/test.pdf"
            )

            assert result is None

    @patch("src.knowledge_base.content_fetcher.get_settings")
    def test_fetch_structured_data(self, mock_get_settings):
        """Test structured data fetching."""
        mock_settings = Mock()
        mock_settings.knowledge_base_cache_dir = str(self.test_dir)
        mock_settings.firecrawl_api_key = ""
        mock_get_settings.return_value = mock_settings

        with patch("src.knowledge_base.content_fetcher.FIRECRAWL_AVAILABLE", False):
            fetcher = ContentFetcher(cache_dir=self.test_dir)
            structured_data = fetcher._fetch_structured_data()

            assert len(structured_data) == 3  # states, history, politics
            assert any(item["source"] == "german_states" for item in structured_data)
            assert any(item["source"] == "german_history" for item in structured_data)
            assert any(item["source"] == "german_politics" for item in structured_data)

            # Check content contains expected German terms
            states_item = next(
                item for item in structured_data if item["source"] == "german_states"
            )
            assert "Bundesländer" in states_item["content"]
            assert "Baden-Württemberg" in states_item["content"]

    @patch("src.knowledge_base.content_fetcher.get_settings")
    def test_load_cached_content(self, mock_get_settings):
        """Test loading cached content."""
        mock_settings = Mock()
        mock_settings.knowledge_base_cache_dir = str(self.test_dir)
        mock_settings.firecrawl_api_key = ""
        mock_get_settings.return_value = mock_settings

        # Create cache file
        cache_file = self.test_dir / "content_cache.json"
        cache_data = {
            "cached_at": datetime.now().isoformat(),
            "content": {
                "web_pages": [{"source": "test", "content": "cached content"}],
                "pdfs": [],
                "structured_data": [],
            },
        }
        cache_file.write_text(json.dumps(cache_data))

        with patch("src.knowledge_base.content_fetcher.FIRECRAWL_AVAILABLE", False):
            fetcher = ContentFetcher(cache_dir=self.test_dir)
            content = fetcher._load_cached_content()

            assert content["web_pages"][0]["content"] == "cached content"

    @patch("src.knowledge_base.content_fetcher.get_settings")
    def test_save_cache(self, mock_get_settings):
        """Test saving content cache."""
        mock_settings = Mock()
        mock_settings.knowledge_base_cache_dir = str(self.test_dir)
        mock_settings.firecrawl_api_key = ""
        mock_get_settings.return_value = mock_settings

        with patch("src.knowledge_base.content_fetcher.FIRECRAWL_AVAILABLE", False):
            fetcher = ContentFetcher(cache_dir=self.test_dir)

            content = {
                "web_pages": [{"source": "test", "content": "test content"}],
                "pdfs": [],
                "structured_data": [],
            }

            fetcher._save_cache(content)

            # Verify cache file was created
            cache_file = self.test_dir / "content_cache.json"
            assert cache_file.exists()

            # Verify cache content
            with open(cache_file) as f:
                cache_data = json.load(f)

            assert "cached_at" in cache_data
            assert cache_data["content"] == content

    @patch("src.knowledge_base.content_fetcher.get_settings")
    def test_get_states_info(self, mock_get_settings):
        """Test German states information generation."""
        mock_settings = Mock()
        mock_settings.knowledge_base_cache_dir = str(self.test_dir)
        mock_settings.firecrawl_api_key = ""
        mock_get_settings.return_value = mock_settings

        with patch("src.knowledge_base.content_fetcher.FIRECRAWL_AVAILABLE", False):
            fetcher = ContentFetcher(cache_dir=self.test_dir)
            states_info = fetcher._get_states_info()

            assert "16 Bundesländer" in states_info
            assert "Baden-Württemberg" in states_info
            assert "Stuttgart" in states_info
            assert "Stadtstaaten" in states_info

    @patch("src.knowledge_base.content_fetcher.get_settings")
    def test_get_history_info(self, mock_get_settings):
        """Test German history information generation."""
        mock_settings = Mock()
        mock_settings.knowledge_base_cache_dir = str(self.test_dir)
        mock_settings.firecrawl_api_key = ""
        mock_get_settings.return_value = mock_settings

        with patch("src.knowledge_base.content_fetcher.FIRECRAWL_AVAILABLE", False):
            fetcher = ContentFetcher(cache_dir=self.test_dir)
            history_info = fetcher._get_history_info()

            assert "1933-1945" in history_info
            assert "Nationalsozialismus" in history_info
            assert "3. Oktober 1990" in history_info
            assert "Wiedervereinigung" in history_info

    @patch("src.knowledge_base.content_fetcher.get_settings")
    def test_get_politics_info(self, mock_get_settings):
        """Test German politics information generation."""
        mock_settings = Mock()
        mock_settings.knowledge_base_cache_dir = str(self.test_dir)
        mock_settings.firecrawl_api_key = ""
        mock_get_settings.return_value = mock_settings

        with patch("src.knowledge_base.content_fetcher.FIRECRAWL_AVAILABLE", False):
            fetcher = ContentFetcher(cache_dir=self.test_dir)
            politics_info = fetcher._get_politics_info()

            assert "Parlamentarische Demokratie" in politics_info
            assert "Gewaltenteilung" in politics_info
            assert "Bundestag" in politics_info
            assert "5%-Hürde" in politics_info
