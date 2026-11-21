"""
01_run_scraper.py - Scrapes ustb.edu.pk and downloads official PDFs.
"""
import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from src.scraper.spider import USTBSpider
from src.common.logger import logger

def main():
    logger.info("=====================================================")
    logger.info("   Starting UST Bannu Web Scraper & PDF Downloader   ")
    logger.info("=====================================================")
    spider = USTBSpider()
    report = spider.run()
    summary = report.get("summary", {})
    logger.info(
        "Done! Saved %(pages_saved)s/%(pages_attempted)s HTML pages and "
        "%(pdfs_downloaded)s/%(pdfs_found)s PDFs. Audit manifest: %(manifest)s",
        {**summary, "manifest": "data/interim/scrape_manifest.json"},
    )

if __name__ == "__main__":
    main()
