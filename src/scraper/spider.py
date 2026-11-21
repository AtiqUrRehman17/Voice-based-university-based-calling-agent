"""
spider.py - Web crawler for UST Bannu website.
"""
import ssl
import urllib.request
from pathlib import Path
from bs4 import BeautifulSoup
from config.constants import SCRAPER_TARGETS, RAW_HTML_DIR, BASE_URL
from src.scraper.pdf_downloader import PDFDownloader
from src.common.logger import logger
from src.common.file_utils import ensure_dir

class USTBSpider:
    def __init__(self, output_dir: Path = RAW_HTML_DIR):
        self.output_dir = ensure_dir(output_dir)
        self.pdf_downloader = PDFDownloader()
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        self.visited_urls = set()

    def fetch_url(self, url: str) -> str:
        """Fetches raw HTML string from a URL."""
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        try:
            with urllib.request.urlopen(req, context=self.ssl_context, timeout=15) as res:
                return res.read().decode("utf-8", errors="ignore")
        except Exception as e:
            logger.warning(f"Could not fetch {url}: {e}")
            return ""

    def run(self) -> dict:
        """
        Executes crawler over all category target URLs defined in constants.
        Returns a summary report of crawled pages and downloaded PDFs.
        """
        report = {"html_saved": [], "pdfs_downloaded": []}

        for category, urls in SCRAPER_TARGETS.items():
            logger.info(f"--- Crawling category: {category} ({len(urls)} target URLs) ---")
            for idx, url in enumerate(urls):
                if url in self.visited_urls:
                    continue
                self.visited_urls.add(url)

                html_content = self.fetch_url(url)
                if not html_content:
                    continue

                # Save raw HTML
                safe_filename = f"{category}_page_{idx}.html"
                file_path = self.output_dir / safe_filename
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                report["html_saved"].append(str(file_path))
                logger.info(f"[HTML] Saved: {safe_filename}")

                # Check for downloadable PDFs on this page
                pdf_urls = self.pdf_downloader.extract_pdf_urls_from_html(html_content, url)
                for pdf_url in pdf_urls:
                    downloaded_path = self.pdf_downloader.download_pdf(pdf_url, category)
                    if downloaded_path:
                        report["pdfs_downloaded"].append(downloaded_path)

        logger.info(
            f"Crawling complete! Saved {len(report['html_saved'])} HTML pages "
            f"and {len(report['pdfs_downloaded'])} PDFs."
        )
        return report
