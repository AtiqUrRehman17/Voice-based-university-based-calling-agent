"""Discovers and safely downloads linked PDF documents."""
import hashlib
import re
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import unquote, urlsplit

from config.constants import RAW_PDF_DIR, SCRAPER_REQUEST_DELAY_SECONDS, SCRAPER_RETRIES
from src.common.file_utils import ensure_dir
from src.common.logger import logger


class PDFDownloader:
    def __init__(self, output_dir: Path = RAW_PDF_DIR,
                 request_delay: float = SCRAPER_REQUEST_DELAY_SECONDS,
                 retries: int = SCRAPER_RETRIES):
        self.output_dir = ensure_dir(output_dir)
        self.ssl_context = ssl.create_default_context()
        self.request_delay = request_delay
        self.retries = retries
        self._last_request_at = 0.0

    @staticmethod
    def is_pdf_url(url: str) -> bool:
        path = urlsplit(url).path.lower()
        return path.endswith(".pdf")

    def sanitize_filename(self, filename: str) -> str:
        filename = unquote(filename)
        filename = re.sub(r'[\\/*?:"<>|\x00-\x1f]', "_", filename)
        return filename.strip(" .") or "document.pdf"

    def extract_pdf_urls_from_html(self, html_content: str, base_url: str) -> list[str]:
        """Compatibility helper for callers that need PDF link extraction."""
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin
        soup = BeautifulSoup(html_content, "html.parser")
        urls = {urljoin(base_url, a["href"].strip()) for a in soup.find_all("a", href=True)
                if self.is_pdf_url(urljoin(base_url, a["href"].strip()))}
        return sorted(urls)

    def download_pdf(self, pdf_url: str, category: str, source_url: str = "") -> dict:
        """Download a PDF atomically; URL hash prevents basename collisions."""
        result = {"url": pdf_url, "source_url": source_url, "category": category,
                  "ok": False, "status": None, "content_type": "", "saved_path": "", "error": ""}
        try:
            basename = self.sanitize_filename(Path(urlsplit(pdf_url).path).name or "document.pdf")
            digest = hashlib.sha256(pdf_url.encode("utf-8")).hexdigest()[:12]
            destination = self.output_dir / f"{category}_{Path(basename).stem}_{digest}.pdf"
            if destination.exists() and destination.stat().st_size > 0:
                result.update({"ok": True, "status": 200, "content_type": "application/pdf",
                               "saved_path": str(destination), "already_present": True})
                return result

            request = urllib.request.Request(
                pdf_url,
                headers={"User-Agent": "USTBKnowledgeBaseBot/1.0 (university information indexing)"},
            )
            last_error = "request failed"
            body = b""
            content_type = ""
            status = None
            for attempt in range(self.retries + 1):
                wait = self.request_delay - (time.monotonic() - self._last_request_at)
                if wait > 0:
                    time.sleep(wait)
                self._last_request_at = time.monotonic()
                try:
                    with urllib.request.urlopen(request, context=self.ssl_context, timeout=30) as response:
                        body = response.read()
                        content_type = response.headers.get_content_type()
                        status = response.status
                    break
                except urllib.error.HTTPError as exc:
                    status = exc.code
                    last_error = f"HTTP {exc.code}: {exc.reason}"
                    retryable = status == 429 or status >= 500
                except Exception as exc:
                    status = None
                    last_error = f"{type(exc).__name__}: {exc}"
                    retryable = True
                if attempt >= self.retries or not retryable:
                    result.update({"status": status, "error": last_error})
                    return result
                time.sleep(min(2 ** attempt, 8))
            result.update({"status": status, "content_type": content_type})
            if status is None or not (200 <= status < 300):
                result["error"] = f"HTTP {status}"
                return result
            if content_type != "application/pdf" and not body.lstrip().startswith(b"%PDF-"):
                result["error"] = f"response is not a PDF (content type: {content_type})"
                return result
            if not body.startswith(b"%PDF-"):
                result["error"] = "response body does not have a PDF signature"
                return result

            temporary = destination.with_suffix(destination.suffix + ".part")
            temporary.write_bytes(body)
            temporary.replace(destination)
            result.update({"ok": True, "saved_path": str(destination), "bytes": len(body)})
            logger.info(f"[PDF] Saved {destination.name} ({len(body)} bytes) from {pdf_url}")
        except Exception as exc:
            result["error"] = f"{type(exc).__name__}: {exc}"
            logger.warning(f"[PDF FAILED] {pdf_url}: {result['error']}")
        return result
