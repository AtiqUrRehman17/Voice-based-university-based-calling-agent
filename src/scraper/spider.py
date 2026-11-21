"""Bounded same-site crawler for UST Bannu pages and linked documents."""
import hashlib
import json
import re
import ssl
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup

from config.constants import (
    BASE_URL, SCRAPE_MANIFEST_PATH, SCRAPER_MAX_DEPTH, SCRAPER_MAX_PAGES,
    SCRAPER_REQUEST_DELAY_SECONDS, SCRAPER_RETRIES, SCRAPER_TARGETS,
)
from src.common.file_utils import ensure_dir
from src.common.logger import logger
from src.scraper.pdf_downloader import PDFDownloader


class USTBSpider:
    """Crawl configured seeds, sitemap URLs, and eligible same-host links."""

    USER_AGENT = "USTBKnowledgeBaseBot/1.0 (university information indexing)"
    TRACKING_PARAMETERS = {"fbclid", "gclid", "mc_cid", "mc_eid"}

    def __init__(self, output_dir: Path = None, max_pages: int = SCRAPER_MAX_PAGES,
                 max_depth: int = SCRAPER_MAX_DEPTH,
                 request_delay: float = SCRAPER_REQUEST_DELAY_SECONDS,
                 retries: int = SCRAPER_RETRIES):
        from config.constants import RAW_HTML_DIR
        self.output_dir = ensure_dir(output_dir or RAW_HTML_DIR)
        self.pdf_downloader = PDFDownloader()
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.request_delay = request_delay
        self.retries = retries
        self.visited_urls = set()
        self._last_request_at = 0.0
        self._ssl_context = ssl.create_default_context()
        self._robots = self._load_robots()
        self._pdf_urls = set()

    @property
    def allowed_host(self) -> str:
        return (urlsplit(BASE_URL).hostname or "").lower()

    def normalize_url(self, url: str, base_url: str = BASE_URL) -> str:
        """Resolve and canonicalize an HTTP URL while retaining meaningful query parameters."""
        absolute = urljoin(base_url, url.strip())
        try:
            parts = urlsplit(absolute)
            port = parts.port
        except ValueError:
            return ""
        if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
            return ""
        host = parts.hostname.lower()
        base_host = self.allowed_host
        base_apex = base_host[4:] if base_host.startswith("www.") else base_host
        if host in {base_apex, f"www.{base_apex}"}:
            host = base_host
        netloc = host
        if port and not ((parts.scheme.lower() == "https" and port == 443) or
                         (parts.scheme.lower() == "http" and port == 80)):
            netloc = f"{host}:{port}"
        query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                 if k.lower() not in self.TRACKING_PARAMETERS]
        query.sort()
        path = re.sub(r"/{2,}", "/", parts.path or "/")
        return urlunsplit((parts.scheme.lower(), netloc, path, urlencode(query), ""))

    def is_allowed_url(self, url: str) -> bool:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        base_apex = self.allowed_host[4:] if self.allowed_host.startswith("www.") else self.allowed_host
        return host in {self.allowed_host, base_apex}

    def _load_robots(self) -> RobotFileParser:
        parser = RobotFileParser()
        robots_url = urljoin(BASE_URL, "/robots.txt")
        parser.set_url(robots_url)
        try:
            req = urllib.request.Request(robots_url, headers={"User-Agent": self.USER_AGENT})
            with urllib.request.urlopen(req, context=self._ssl_context, timeout=15) as response:
                parser.parse(response.read().decode("utf-8", errors="replace").splitlines())
            logger.info(f"Loaded crawl rules from {robots_url}")
        except Exception as exc:
            # A missing/unreachable robots file is recorded, but does not prevent crawling.
            parser.parse([])
            logger.warning(f"Could not read robots.txt ({exc}); continuing with bounded crawl")
        return parser

    def _polite_wait(self) -> None:
        robots_delay = self._robots.crawl_delay(self.USER_AGENT) or self._robots.crawl_delay("*") or 0
        minimum_delay = max(self.request_delay, float(robots_delay))
        wait = minimum_delay - (time.monotonic() - self._last_request_at)
        if wait > 0:
            time.sleep(wait)
        self._last_request_at = time.monotonic()

    def fetch_url(self, url: str) -> dict:
        """Fetch URL and return body plus auditable HTTP metadata; standard TLS checks apply."""
        last_error = "request failed"
        for attempt in range(self.retries + 1):
            self._polite_wait()
            req = urllib.request.Request(url, headers={"User-Agent": self.USER_AGENT})
            try:
                with urllib.request.urlopen(req, context=self._ssl_context, timeout=20) as res:
                    body = res.read()
                    return {
                        "ok": 200 <= res.status < 300,
                        "status": res.status,
                        "final_url": self.normalize_url(res.geturl()),
                        "content_type": res.headers.get_content_type(),
                        "body": body,
                        "error": "" if 200 <= res.status < 300 else f"HTTP {res.status}",
                    }
            except urllib.error.HTTPError as exc:
                last_error = f"HTTP {exc.code}: {exc.reason}"
                status = exc.code
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                status = None
            retryable_status = status is None or status == 429 or (status is not None and status >= 500)
            if attempt < self.retries and retryable_status:
                time.sleep(min(2 ** attempt, 8))
            elif not retryable_status:
                break
        return {"ok": False, "status": status, "final_url": url,
                "content_type": "", "body": b"", "error": last_error}

    def _category_for_url(self, url: str, inherited: str = "campus_admin") -> str:
        text = url.lower()
        rules = ("rule", "policy", "hostel", "regulation", "migration", "downloads")
        fees = ("fee", "fees", "challan", "payment")
        admissions = ("admission", "apply", "merit", "test-result", "advertisement")
        programs = ("dept-content", "department", "program", "faculty", "course")
        if any(term in text for term in rules):
            return "rules_policies"
        if any(term in text for term in fees):
            return "fees"
        if any(term in text for term in admissions):
            return "admissions"
        if any(term in text for term in programs):
            return "programs_classes"
        return inherited

    def discover_sitemap_urls(self) -> tuple[list[str], list[str]]:
        """Read sitemap locations advertised by robots.txt and the conventional sitemap URL."""
        candidates = list(self._robots.site_maps() or [])
        candidates.append(urljoin(BASE_URL, "/sitemap.xml"))
        pages, checked = set(), set()
        queue = deque(self.normalize_url(u) for u in candidates)
        while queue:
            sitemap_url = queue.popleft()
            if not sitemap_url or sitemap_url in checked or not self.is_allowed_url(sitemap_url):
                continue
            checked.add(sitemap_url)
            if not self._robots.can_fetch(self.USER_AGENT, sitemap_url):
                continue
            result = self.fetch_url(sitemap_url)
            if not result["ok"]:
                continue
            try:
                root = ET.fromstring(result["body"])
            except ET.ParseError:
                continue
            for loc in root.iter():
                if loc.tag.rsplit("}", 1)[-1].lower() != "loc" or not loc.text:
                    continue
                found = self.normalize_url(loc.text.strip(), sitemap_url)
                if not self.is_allowed_url(found):
                    continue
                if urlsplit(found).path.lower().endswith(".xml"):
                    queue.append(found)
                else:
                    pages.add(found)
        logger.info(f"Sitemap discovery checked {len(checked)} sitemap(s), found {len(pages)} page URL(s)")
        return sorted(pages), sorted(checked)

    def _save_page(self, category: str, url: str, html: bytes) -> Path:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
        path = urlsplit(url).path.rstrip("/").split("/")[-1] or "home"
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", path)[:60].strip("_") or "page"
        destination = self.output_dir / f"{category}_{slug}_{digest}.html"
        destination.write_bytes(html)
        return destination

    def _extract_links(self, html: bytes, base_url: str) -> tuple[list[str], list[str], list[dict]]:
        soup = BeautifulSoup(html, "html.parser")
        pages, pdfs = set(), set()
        skipped = []
        for tag in soup.find_all(["a", "area"], href=True):
            href = tag.get("href", "").strip()
            if not href or href.startswith(("mailto:", "tel:", "javascript:")):
                continue
            candidate = self.normalize_url(href, base_url)
            if not candidate:
                continue
            if not self.is_allowed_url(candidate):
                skipped.append({"url": candidate, "reason": "outside allowed university host"})
                continue
            if self.pdf_downloader.is_pdf_url(candidate):
                pdfs.add(candidate)
            elif self._is_html_candidate(candidate):
                pages.add(candidate)
            else:
                skipped.append({"url": candidate, "reason": "unsupported linked file type"})
        return sorted(pages), sorted(pdfs), skipped

    @staticmethod
    def _is_html_candidate(url: str) -> bool:
        path = urlsplit(url).path.lower()
        return not path.rsplit("/", 1)[-1].endswith((
            ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".zip", ".doc", ".docx",
            ".xls", ".xlsx", ".ppt", ".pptx", ".mp4", ".mp3", ".css", ".js", ".xml",
        ))

    def run(self) -> dict:
        """Crawl in breadth-first order and write a JSON manifest for every outcome."""
        started = datetime.now(timezone.utc).isoformat()
        report = {"started_at": started, "base_url": BASE_URL, "limits": {
            "max_pages": self.max_pages, "max_depth": self.max_depth,
            "request_delay_seconds": self.request_delay, "retries": self.retries,
        }, "sitemaps_checked": [], "discovered_urls": [], "pages": [], "pdfs": [], "skipped": []}

        sitemap_urls, checked_sitemaps = self.discover_sitemap_urls()
        report["sitemaps_checked"] = checked_sitemaps
        queued = set()
        queue = deque()

        def enqueue(url: str, category: str, depth: int, parent: str = "") -> None:
            normalized = self.normalize_url(url)
            if not normalized or normalized in queued or not self.is_allowed_url(normalized):
                return
            queued.add(normalized)
            classified = self._category_for_url(normalized, category)
            queue.append((normalized, classified, depth, parent))
            report["discovered_urls"].append({
                "url": normalized, "category": classified, "depth": depth,
                "discovered_from": parent,
            })

        for category, urls in SCRAPER_TARGETS.items():
            for url in urls:
                enqueue(url, category, 0)
        report["configured_seeds"] = [
            {"category": category, "url": self.normalize_url(url)}
            for category, urls in SCRAPER_TARGETS.items() for url in urls
        ]
        for url in sitemap_urls:
            enqueue(url, self._category_for_url(url), 0, "sitemap")

        while queue and len(report["pages"]) < self.max_pages:
            url, category, depth, parent = queue.popleft()
            if url in self.visited_urls:
                continue
            self.visited_urls.add(url)
            if not self._robots.can_fetch(self.USER_AGENT, url):
                report["skipped"].append({"url": url, "reason": "disallowed by robots.txt"})
                continue

            fetched = self.fetch_url(url)
            entry = {"url": url, "category": category, "depth": depth,
                     "discovered_from": parent, "status": fetched["status"],
                     "final_url": fetched["final_url"], "content_type": fetched["content_type"],
                     "saved_path": "", "ok": False, "error": fetched["error"]}
            final_url = fetched["final_url"] or url
            if not fetched["ok"]:
                report["pages"].append(entry)
                logger.warning(f"[FETCH FAILED] {url}: {fetched['error']}")
                continue
            if not self.is_allowed_url(final_url):
                entry["error"] = f"redirected outside allowed host to {final_url}"
                report["pages"].append(entry)
                continue
            if "html" not in fetched["content_type"].lower():
                entry["error"] = f"unexpected content type: {fetched['content_type']}"
                report["pages"].append(entry)
                continue

            path = self._save_page(category, final_url, fetched["body"])
            entry.update({"ok": True, "saved_path": str(path), "error": ""})
            report["pages"].append(entry)
            logger.info(f"[HTML {len(report['pages'])}] Saved {path.name} from {final_url}")

            page_links, pdf_links, excluded_links = self._extract_links(fetched["body"], final_url)
            report["skipped"].extend(excluded_links)
            for pdf_url in pdf_links:
                if pdf_url in self._pdf_urls:
                    continue
                self._pdf_urls.add(pdf_url)
                pdf_result = self.pdf_downloader.download_pdf(pdf_url, category, source_url=final_url)
                report["pdfs"].append(pdf_result)
            if depth < self.max_depth:
                for child in page_links:
                    enqueue(child, self._category_for_url(child, category), depth + 1, final_url)

        if queue:
            report["skipped"].extend(
                {"url": url, "reason": "max_pages reached"} for url, _, _, _ in queue
            )
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        report["summary"] = {
            "pages_discovered": len(queued),
            "pages_attempted": len(report["pages"]),
            "pages_saved": sum(1 for p in report["pages"] if p["ok"]),
            "pages_failed_or_skipped": sum(1 for p in report["pages"] if not p["ok"]) + len(report["skipped"]),
            "pdfs_found": len(report["pdfs"]),
            "pdfs_downloaded": sum(1 for p in report["pdfs"] if p["ok"]),
        }
        ensure_dir(SCRAPE_MANIFEST_PATH.parent)
        SCRAPE_MANIFEST_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"Crawl complete: {report['summary']}; manifest: {SCRAPE_MANIFEST_PATH}")
        return report
