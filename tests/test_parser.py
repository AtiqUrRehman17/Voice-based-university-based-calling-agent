"""
test_parser.py - Unit tests for HTML parser, voice normalizer, and chunker.
"""
import pytest
from src.parsers.html_parser import HTMLParser
from src.processing.normalizer import VoiceNormalizer
from src.processing.cleaner import TextCleaner
from src.processing.chunker import VoiceChunker

def test_html_parser_strips_scripts_and_extracts_tables():
    parser = HTMLParser()
    sample_html = """
    <html>
        <head><title>UST Bannu Admissions</title></head>
        <body>
            <script>console.log('noise');</script>
            <nav><a href="/">Home</a></nav>
            <h1>BS Computer Science Admission</h1>
            <p>The program duration is four years with eight semesters.</p>
            <table>
                <tr><th>Program</th><th>Fee</th></tr>
                <tr><td>BS CS</td><td>Rs. 42,000/-</td></tr>
            </table>
            <footer>Copyright 2024 USTB</footer>
        </body>
    </html>
    """
    res = parser.parse_string(sample_html)
    assert res["title"] == "UST Bannu Admissions"
    assert len(res["tables"]) == 1
    assert res["tables"][0][1][0] == "BS CS"
    assert any("program duration is four years" in s for s in res["sections"])

def test_voice_normalizer_currency_and_acronyms():
    norm = VoiceNormalizer()
    raw = "The fee for BS CS is Rs. 42,500/- per semester."
    spoken = norm.to_spoken_form(raw)
    assert "Pakistani Rupees" in spoken
    assert "/-" not in spoken
    assert "Computer Science" in spoken

def test_cleaner_boilerplate_detection():
    cleaner = TextCleaner()
    assert cleaner.is_boilerplate("Copyright © 2024 UST Bannu. All rights reserved.") is True
    assert cleaner.is_boilerplate("Follow us on Facebook and Twitter.") is True
    assert cleaner.is_boilerplate("Admissions are open for Fall 2024 in all departments.") is False

def test_chunker_atomic_chunks():
    chunker = VoiceChunker(max_words=20)
    sentences = [
        "First sentence explaining admission eligibility for undergraduate students.",
        "Second sentence covering entrance test details and criteria.",
        "Third sentence giving application submission deadlines and fee challan details.",
    ]
    chunks = chunker.chunk_sentences(sentences, namespace="admissions", title="Eligibility")
    assert len(chunks) >= 1
    assert chunks[0].namespace == "admissions"
    assert chunks[0].spoken_text != ""
