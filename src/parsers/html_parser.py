"""
html_parser.py - Extracts clean text, headings, and tables from raw HTML pages.
"""
from bs4 import BeautifulSoup
from src.common.logger import logger

class HTMLParser:
    def __init__(self):
        # Elements that add noise and should be stripped
        self.ignored_tags = [
            "script", "style", "nav", "footer", "header", 
            "aside", "noscript", "iframe", "svg"
        ]

    def parse_file(self, file_path: str) -> dict:
        """Parses a local HTML file and returns clean title, sections, and tables."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                html_text = f.read()
            return self.parse_string(html_text)
        except Exception as e:
            logger.error(f"Error parsing HTML file {file_path}: {e}")
            return {"title": "", "sections": [], "tables": []}

    def parse_string(self, html_text: str) -> dict:
        """Parses HTML string into structured textual sections."""
        soup = BeautifulSoup(html_text, "html.parser")

        # Strip noisy tags
        for tag in soup(self.ignored_tags):
            tag.decompose()

        # Extract Title
        title = soup.title.string.strip() if soup.title and soup.title.string else "UST Bannu"

        # Extract Tables
        extracted_tables = []
        for table in soup.find_all("table"):
            rows_data = []
            for row in table.find_all("tr"):
                cols = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
                if any(cols):
                    rows_data.append(cols)
            if rows_data:
                extracted_tables.append(rows_data)
            table.decompose()  # Remove table after extraction to avoid duplicate text

        # Extract meaningful sections (paragraphs, list items, headings)
        sections = []
        for elem in soup.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
            text = elem.get_text(separator=" ", strip=True)
            if len(text) > 15:  # Filter out trivial 1-word crumbs
                sections.append(text)

        return {
            "title": title,
            "sections": sections,
            "tables": extracted_tables
        }
