"""
pdf_downloader.py - Discovers and downloads PDF circulars and prospectuses.
"""
import re
import urllib.request
import ssl
from pathlib import Path
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from config.constants import RAW_PDF_DIR
from src.common.logger import logger
from src.common.file_utils import ensure_dir

class PDFDownloader:
    def __init__(self, output_dir: Path = RAW_PDF_DIR):
        self.output_dir = ensure_dir(output_dir)
        # Permissive SSL context for university servers that may have self-signed or incomplete cert chains
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    def sanitize_filename(self, filename: str) -> str:
        """Removes illegal characters from filenames."""
        return re.sub(r'[\\/*?:"<>|]', "_", filename)

    def extract_pdf_urls_from_html(self, html_content: str, base_url: str) -> list[str]:
        """Finds all PDF links in an HTML document."""
        soup = BeautifulSoup(html_content, "html.parser")
        pdf_urls = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].strip()
            if href.lower().endswith(".pdf") or ".pdf?" in href.lower():
                full_url = urljoin(base_url, href)
                pdf_urls.append(full_url)
        return list(set(pdf_urls))

    def download_pdf(self, pdf_url: str, category: str) -> str:
        """
        Downloads a single PDF file and saves it with a category prefix.
        Returns the saved file path as string, or empty string on failure.
        """
        try:
            parsed = urlparse(pdf_url)
            raw_filename = Path(parsed.path).name or "document.pdf"
            clean_name = self.sanitize_filename(raw_filename)
            dest_path = self.output_dir / f"{category}_{clean_name}"

            if dest_path.exists():
                logger.info(f"PDF already downloaded: {dest_path.name}")
                return str(dest_path)

            logger.info(f"Downloading PDF: {pdf_url} -> {dest_path.name}")
            req = urllib.request.Request(
                pdf_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )

            with urllib.request.urlopen(req, context=self.ssl_context, timeout=25) as response:
                content = response.read()
                with open(dest_path, "wb") as f:
                    f.write(content)

            logger.info(f"Downloaded successfully: {dest_path.name} ({len(content)} bytes)")
            return str(dest_path)
        except Exception as e:
            logger.warning(f"Failed to download PDF {pdf_url}: {e}")
            return ""
