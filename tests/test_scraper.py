"""
test_scraper.py - Unit tests for spider and PDF downloader utilities.
"""
import pytest
from src.scraper.pdf_downloader import PDFDownloader
from config.constants import SCRAPER_TARGETS, BASE_URL

def test_pdf_url_extraction():
    downloader = PDFDownloader()
    sample_html = """
    <html>
        <body>
            <a href="/downloads/prospectus_2024.pdf">Prospectus</a>
            <a href="https://www.ustb.edu.pk/fee_schedule.pdf">Fee PDF</a>
            <a href="/about-us">About</a>
        </body>
    </html>
    """
    pdf_urls = downloader.extract_pdf_urls_from_html(sample_html, BASE_URL)
    assert len(pdf_urls) == 2
    assert any("prospectus_2024.pdf" in url for url in pdf_urls)
    assert any("fee_schedule.pdf" in url for url in pdf_urls)

def test_filename_sanitization():
    downloader = PDFDownloader()
    dirty_name = "fee:structure/2024*fall?.pdf"
    clean_name = downloader.sanitize_filename(dirty_name)
    assert ":" not in clean_name
    assert "*" not in clean_name
    assert "?" not in clean_name

def test_scraper_targets_configuration():
    assert "admissions" in SCRAPER_TARGETS
    assert "fees" in SCRAPER_TARGETS
    assert "programs_classes" in SCRAPER_TARGETS
    assert "campus_admin" in SCRAPER_TARGETS
