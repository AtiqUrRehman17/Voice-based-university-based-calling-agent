"""Audit the latest scraper manifest and the raw HTML/PDF artifacts."""
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from bs4 import BeautifulSoup
from config.constants import SCRAPE_MANIFEST_PATH, SCRAPER_TARGETS


GREEN, YELLOW, RED, CYAN, BOLD, RESET = "\033[92m", "\033[93m", "\033[91m", "\033[96m", "\033[1m", "\033[0m"


def report(color: str, label: str, message: str) -> None:
    print(f"  {color}{label}{RESET} {message}")


def main() -> int:
    print(f"\n{BOLD}{CYAN}UST Bannu scrape audit{RESET}")
    if not SCRAPE_MANIFEST_PATH.exists():
        report(RED, "FAIL", f"No scrape manifest at {SCRAPE_MANIFEST_PATH}. Run scripts/01_run_scraper.py first.")
        return 1
    try:
        manifest = json.loads(SCRAPE_MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        report(RED, "FAIL", f"Manifest cannot be read: {exc}")
        return 1

    pages = manifest.get("pages", [])
    pdfs = manifest.get("pdfs", [])
    saved_pages = [p for p in pages if p.get("ok") and p.get("saved_path")]
    failed_pages = [p for p in pages if not p.get("ok")]
    failed_pdfs = [p for p in pdfs if not p.get("ok")]
    print(f"  Started: {manifest.get('started_at', 'unknown')} | Finished: {manifest.get('finished_at', 'unknown')}")
    print(f"  HTML attempts: {len(pages)} | saved: {len(saved_pages)} | failed/skipped: {len(failed_pages)}")
    print(f"  PDF links: {len(pdfs)} | downloaded: {sum(bool(p.get('ok')) for p in pdfs)} | failed: {len(failed_pdfs)}")
    print(f"  Sitemap files checked: {len(manifest.get('sitemaps_checked', []))}")

    missing_seeds = []
    visited_urls = ({p.get("url") for p in pages} | {p.get("final_url") for p in pages} |
                    {p.get("url") for p in manifest.get("skipped", [])})
    configured_seeds = manifest.get("configured_seeds")
    if configured_seeds is None:
        configured_seeds = [
            {"category": category, "url": url}
            for category, targets in SCRAPER_TARGETS.items() for url in targets
        ]
    for category in SCRAPER_TARGETS:
        targets = [seed["url"] for seed in configured_seeds if seed["category"] == category]
        covered = sum(1 for url in targets if url in visited_urls)
        print(f"  {category:<20} configured seed coverage: {covered}/{len(targets)}")
        missing_seeds.extend((category, url) for url in targets if url not in visited_urls)

    empty_html = []
    for page in saved_pages:
        path = Path(page["saved_path"])
        if not path.is_absolute():
            path = ROOT_DIR / path
        if not path.exists() or path.stat().st_size == 0:
            empty_html.append(page.get("url", str(path)))
            continue
        soup = BeautifulSoup(path.read_bytes(), "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        if len(soup.get_text(" ", strip=True)) < 50:
            empty_html.append(page.get("url", str(path)))

    invalid_pdfs = []
    for item in pdfs:
        if not item.get("ok"):
            continue
        path = Path(item.get("saved_path", ""))
        if not path.exists() or path.stat().st_size < 5 or path.read_bytes()[:5] != b"%PDF-":
            invalid_pdfs.append(item.get("url", str(path)))

    if missing_seeds:
        report(RED, "FAIL", f"{len(missing_seeds)} configured seed URL(s) were not attempted")
        for category, url in missing_seeds[:20]:
            print(f"    [{category}] {url}")
    else:
        report(GREEN, "OK", "Every configured seed appears in the crawl manifest")

    if failed_pages:
        report(YELLOW, "WARN", f"{len(failed_pages)} page(s) failed or were skipped; details are in the manifest")
        for page in failed_pages[:10]:
            print(f"    {page.get('status')} {page.get('url')} — {page.get('error')}")
    else:
        report(GREEN, "OK", "All attempted pages were saved as HTML")
    if failed_pdfs:
        report(YELLOW, "WARN", f"{len(failed_pdfs)} PDF download(s) failed; details are in the manifest")
        for pdf in failed_pdfs[:10]:
            print(f"    {pdf.get('url')} — {pdf.get('error')}")
    if empty_html:
        report(RED, "FAIL", f"{len(empty_html)} saved HTML page(s) are missing or have little readable text")
        for url in empty_html[:10]:
            print(f"    {url}")
    else:
        report(GREEN, "OK", "Saved HTML artifacts exist and contain readable text")
    if invalid_pdfs:
        report(RED, "FAIL", f"{len(invalid_pdfs)} downloaded PDF(s) are missing or invalid")
        for url in invalid_pdfs[:10]:
            print(f"    {url}")
    elif not failed_pdfs and pdfs:
        report(GREEN, "OK", "Downloaded PDFs have valid PDF signatures")

    print(f"\n  Manifest: {SCRAPE_MANIFEST_PATH}")
    # A partial crawl is still reported in full; return failure only for absent seed coverage
    # or corrupt/empty artifacts so that the operator can inspect ordinary HTTP failures.
    return 1 if missing_seeds or empty_html or invalid_pdfs else 0


if __name__ == "__main__":
    raise SystemExit(main())
