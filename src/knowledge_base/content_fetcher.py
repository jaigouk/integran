"""Fetch and process content from official German integration test sources."""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import track

from src.core.settings import get_settings

try:
    from firecrawl import FirecrawlApp

    FIRECRAWL_AVAILABLE = True
except ImportError:
    FIRECRAWL_AVAILABLE = False
    FirecrawlApp = None

try:
    from pypdf import PdfReader

    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False
    PdfReader = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)
console = Console()


class ContentFetcher:
    """Fetches content from BAMF and other official sources."""

    def __init__(self, cache_dir: Path | None = None):
        # Get settings
        settings = get_settings()

        # Set cache directory
        if cache_dir is None:
            cache_dir = Path(settings.knowledge_base_cache_dir)
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Firecrawl if API key available
        self.firecrawl = None
        if FIRECRAWL_AVAILABLE and settings.firecrawl_api_key:
            self.firecrawl = FirecrawlApp(api_key=settings.firecrawl_api_key)

        self.sources = {
            "bamf_main": "https://www.bamf.de/DE/Themen/Integration/ZugewanderteTeilnehmende/Einbuergerung/einbuergerung-node.html",
            "bamf_test_info": "https://www.bamf.de/DE/Themen/Integration/ZugewanderteTeilnehmende/OnlineTestcenter/online-testcenter-node.html",
            "gesetze": "https://www.gesetze-im-internet.de/gg/",
            "bpb": "https://www.bpb.de/themen/politisches-system/politik-einfach-fuer-alle/",
            "integration_course": "https://www.bamf.de/DE/Themen/Integration/ZugewanderteTeilnehmende/Integrationskurse/integrationskurse-node.html",
        }

        self.pdf_sources = {
            "gesamtfragenkatalog": [
                "https://www.bamf.de/SharedDocs/Anlagen/DE/Integration/Einbuergerung/gesamtfragenkatalog-lebenindeutschland.pdf",
                "https://www.bamf.de/SharedDocs/Anlagen/DE/Integration/Einbuergerung/gesamtfragenkatalog-einbuergerungstest.pdf",
            ],
            "grundgesetz": "https://www.bmi.bund.de/SharedDocs/downloads/DE/publikationen/themen/verfassung/grundgesetz.pdf",
            "integration_handbook": "https://www.bamf.de/SharedDocs/Anlagen/DE/Integration/Integrationskurse/Kurstraeger/Konzeptleitfaden/curriculum-integrationskurs.pdf",
        }

    def fetch_all_content(
        self, force_refresh: bool = False
    ) -> dict[str, list[dict[str, Any]]]:
        """Fetch content from all sources."""
        console.print(
            "[bold cyan]Fetching content from official sources...[/bold cyan]"
        )

        all_content: dict[str, list[dict[str, Any]]] = {
            "web_pages": [],
            "pdfs": [],
            "structured_data": [],
        }

        # Check if we have recent cache
        if not force_refresh and self._has_recent_cache():
            console.print("[green]Using cached content (less than 7 days old)[/green]")
            return self._load_cached_content()

        # Fetch web content
        console.print("\n[yellow]Fetching web pages...[/yellow]")
        for name, url in track(
            self.sources.items(), description="Fetching web content"
        ):
            content = self._fetch_web_content(name, url)
            if content:
                all_content["web_pages"].append(content)

        # Fetch PDF content
        console.print("\n[yellow]Fetching PDF documents...[/yellow]")
        for name, urls in self.pdf_sources.items():
            if isinstance(urls, str):
                urls = [urls]

            for url in urls:
                content = self._fetch_pdf_content(name, url)
                if content:
                    all_content["pdfs"].append(content)

        # Fetch structured data (using specific scrapers)
        console.print("\n[yellow]Fetching structured data...[/yellow]")
        structured_content = self._fetch_structured_data()
        all_content["structured_data"].extend(structured_content)

        # Save cache
        self._save_cache(all_content)

        return all_content

    def _fetch_web_content(self, name: str, url: str) -> dict[str, Any] | None:
        """Fetch content from a web page."""
        try:
            if self.firecrawl:
                # Use Firecrawl for better content extraction
                result = self.firecrawl.scrape_url(
                    url,
                    params={
                        "pageOptions": {
                            "onlyMainContent": True,
                            "includeHtml": False,
                            "waitFor": 2000,
                        }
                    },
                )

                if result and "data" in result:
                    return {
                        "source": name,
                        "url": url,
                        "title": result["data"].get("metadata", {}).get("title", ""),
                        "content": result["data"].get("markdown", ""),
                        "metadata": result["data"].get("metadata", {}),
                        "type": "web_page",
                        "fetched_at": datetime.now().isoformat(),
                    }
            else:
                # Fallback to requests + BeautifulSoup
                response = requests.get(url, timeout=30)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, "html.parser")

                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()

                # Extract main content
                main_content = (
                    soup.find("main") or soup.find("div", class_="content") or soup.body
                )

                if main_content:
                    text = main_content.get_text(separator="\n", strip=True)

                    return {
                        "source": name,
                        "url": url,
                        "title": soup.title.string if soup.title else "",
                        "content": text,
                        "metadata": {
                            "description": soup.find(
                                "meta", attrs={"name": "description"}
                            )["content"]
                            if soup.find("meta", attrs={"name": "description"})
                            else ""
                        },
                        "type": "web_page",
                        "fetched_at": datetime.now().isoformat(),
                    }

        except Exception as e:
            logger.error(f"Error fetching {name} from {url}: {e}")

        return None

    def _fetch_pdf_content(self, name: str, url: str) -> dict[str, Any] | None:
        """Fetch and extract content from PDF."""
        if not PYPDF_AVAILABLE:
            logger.warning("pypdf not available, skipping PDF content")
            return None

        try:
            # Download PDF
            response = requests.get(url, timeout=60)
            response.raise_for_status()

            # Save temporarily
            temp_path = (
                self.cache_dir / f"{name}_{datetime.now().strftime('%Y%m%d')}.pdf"
            )
            with open(temp_path, "wb") as f:
                f.write(response.content)

            # Extract text
            reader = PdfReader(temp_path)
            text_content = []

            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    text_content.append(f"Page {page_num + 1}:\n{text}")

            return {
                "source": name,
                "url": url,
                "title": f"{name} PDF Document",
                "content": "\n\n".join(text_content),
                "metadata": {
                    "num_pages": len(reader.pages),
                    "pdf_info": reader.metadata if hasattr(reader, "metadata") else {},
                },
                "type": "pdf",
                "fetched_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error fetching PDF {name} from {url}: {e}")
            return None

    def _fetch_structured_data(self) -> list[dict[str, Any]]:
        """Fetch structured data like German states, important dates, etc."""
        structured_data = []

        # German federal states information
        states_data = {
            "source": "german_states",
            "type": "structured_data",
            "title": "German Federal States Information",
            "content": self._get_states_info(),
            "metadata": {"category": "geography"},
            "fetched_at": datetime.now().isoformat(),
        }
        structured_data.append(states_data)

        # Important historical dates
        history_data = {
            "source": "german_history",
            "type": "structured_data",
            "title": "Important Dates in German History",
            "content": self._get_history_info(),
            "metadata": {"category": "history"},
            "fetched_at": datetime.now().isoformat(),
        }
        structured_data.append(history_data)

        # Political system information
        politics_data = {
            "source": "german_politics",
            "type": "structured_data",
            "title": "German Political System",
            "content": self._get_politics_info(),
            "metadata": {"category": "politics"},
            "fetched_at": datetime.now().isoformat(),
        }
        structured_data.append(politics_data)

        return structured_data

    def _get_states_info(self) -> str:
        """Get information about German federal states."""
        states_info = """
        Die 16 Bundesländer Deutschlands:

        1. Baden-Württemberg - Hauptstadt: Stuttgart
        2. Bayern (Freistaat) - Hauptstadt: München
        3. Berlin - Stadtstaat
        4. Brandenburg - Hauptstadt: Potsdam
        5. Bremen (Freie Hansestadt) - Stadtstaat
        6. Hamburg (Freie und Hansestadt) - Stadtstaat
        7. Hessen - Hauptstadt: Wiesbaden
        8. Mecklenburg-Vorpommern - Hauptstadt: Schwerin
        9. Niedersachsen - Hauptstadt: Hannover
        10. Nordrhein-Westfalen - Hauptstadt: Düsseldorf
        11. Rheinland-Pfalz - Hauptstadt: Mainz
        12. Saarland - Hauptstadt: Saarbrücken
        13. Sachsen (Freistaat) - Hauptstadt: Dresden
        14. Sachsen-Anhalt - Hauptstadt: Magdeburg
        15. Schleswig-Holstein - Hauptstadt: Kiel
        16. Thüringen (Freistaat) - Hauptstadt: Erfurt

        Stadtstaaten: Berlin, Bremen, Hamburg
        Flächenstaaten: Alle anderen 13 Bundesländer
        """
        return states_info

    def _get_history_info(self) -> str:
        """Get important historical information."""
        history_info = """
        Wichtige Daten der deutschen Geschichte:

        1933-1945: Zeit des Nationalsozialismus
        - 30. Januar 1933: Hitler wird Reichskanzler
        - 9. November 1938: Reichspogromnacht
        - 1. September 1939: Beginn des Zweiten Weltkriegs
        - 8. Mai 1945: Ende des Zweiten Weltkriegs in Europa

        1949: Gründung der Bundesrepublik Deutschland und der DDR
        - 23. Mai 1949: Verkündung des Grundgesetzes
        - 7. Oktober 1949: Gründung der DDR

        1961-1989: Berliner Mauer
        - 13. August 1961: Bau der Berliner Mauer
        - 9. November 1989: Fall der Berliner Mauer

        1990: Deutsche Wiedervereinigung
        - 3. Oktober 1990: Tag der Deutschen Einheit
        """
        return history_info

    def _get_politics_info(self) -> str:
        """Get information about the German political system."""
        politics_info = """
        Das politische System Deutschlands:

        Staatsform: Parlamentarische Demokratie, Bundesrepublik

        Verfassungsorgane:
        1. Bundestag - Parlament, vom Volk gewählt
        2. Bundesrat - Vertretung der Länder
        3. Bundesregierung - Exekutive, geführt vom Bundeskanzler
        4. Bundespräsident - Staatsoberhaupt
        5. Bundesverfassungsgericht - Höchstes Gericht

        Gewaltenteilung:
        - Legislative (Gesetzgebung): Bundestag und Bundesrat
        - Exekutive (Ausführung): Bundesregierung
        - Judikative (Rechtsprechung): Gerichte

        Wahlsystem:
        - Wahlrecht ab 18 Jahren
        - Allgemein, unmittelbar, frei, gleich und geheim
        - 5%-Hürde für Parteien
        """
        return politics_info

    def _has_recent_cache(self) -> bool:
        """Check if cache is less than 7 days old."""
        cache_file = self.cache_dir / "content_cache.json"
        if not cache_file.exists():
            return False

        try:
            with open(cache_file, encoding="utf-8") as f:
                cache_data = json.load(f)
                cached_date = datetime.fromisoformat(cache_data.get("cached_at", ""))
                return datetime.now() - cached_date < timedelta(days=7)
        except Exception:
            return False

    def _load_cached_content(self) -> dict[str, list[dict[str, Any]]]:
        """Load content from cache."""
        cache_file = self.cache_dir / "content_cache.json"
        with open(cache_file, encoding="utf-8") as f:
            return json.load(f)["content"]  # type: ignore[no-any-return]

    def _save_cache(self, content: dict[str, list[dict[str, Any]]]) -> None:
        """Save content to cache."""
        cache_file = self.cache_dir / "content_cache.json"
        cache_data = {"cached_at": datetime.now().isoformat(), "content": content}
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
