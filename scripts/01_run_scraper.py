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
    logger.info(f"Done! Raw pages stored in data/raw/html, PDFs in data/raw/pdfs")

if __name__ == "__main__":
    main()
