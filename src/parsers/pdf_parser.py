"""
pdf_parser.py - Robust table and text extractor for fee schedules and prospectus PDFs.
Suppresses noisy PDF font warnings and applies fast extraction for large document collections.
"""
import logging
import warnings
from pathlib import Path
from src.common.logger import logger

# Suppress noisy internal warnings from pdfminer & pypdf
warnings.filterwarnings("ignore")
for _name in ["pdfminer", "pdfminer.pdffont", "pdfminer.pdfparser", "pdfminer.pdfinterp", "pypdf", "pdfplumber"]:
    logging.getLogger(_name).setLevel(logging.ERROR)


class PDFParser:
    def __init__(self):
        pass

    def parse_pdf(self, pdf_path: str, extract_tables: bool = True) -> dict:
        """
        Extracts running text and structured tables from a PDF file.
        Returns {'text_blocks': [...], 'tables': [...]}
        """
        text_blocks = []
        tables = []
        pdf_file = Path(pdf_path)

        if not pdf_file.exists():
            logger.warning(f"PDF file does not exist: {pdf_path}")
            return {"text_blocks": [], "tables": []}

        # 1. Attempt extraction using pdfplumber (best for fee tables)
        try:
            import pdfplumber
            with pdfplumber.open(pdf_file) as pdf:
                # Limit page scan for large documents (e.g. 100-page merit lists) to prevent runaway lag
                pages_to_scan = pdf.pages[:10] if len(pdf.pages) > 10 else pdf.pages

                for page in pages_to_scan:
                    # Only do compute-heavy table geometric analysis if requested (e.g. fee structures)
                    if extract_tables:
                        try:
                            extracted = page.extract_tables()
                            for t in extracted:
                                cleaned_rows = []
                                for row in t:
                                    cleaned_row = [str(cell).strip() for cell in row if cell is not None]
                                    if any(cleaned_row):
                                        cleaned_rows.append(cleaned_row)
                                if cleaned_rows:
                                    tables.append(cleaned_rows)
                        except Exception:
                            pass

                    # Extract regular text
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            lines = [line.strip() for line in page_text.split("\n") if len(line.strip()) > 15]
                            text_blocks.extend(lines)
                    except Exception:
                        pass

            return {"text_blocks": text_blocks, "tables": tables}

        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"pdfplumber extraction error on {pdf_file.name}: {e}")

        # 2. Fast Fallback using pypdf for text
        try:
            import pypdf
            reader = pypdf.PdfReader(str(pdf_file))
            pages = reader.pages[:10] if len(reader.pages) > 10 else reader.pages
            for page in pages:
                t = page.extract_text()
                if t:
                    lines = [line.strip() for line in t.split("\n") if len(line.strip()) > 15]
                    text_blocks.extend(lines)
        except Exception as e:
            logger.error(f"pypdf extraction error on {pdf_file.name}: {e}")

        return {"text_blocks": text_blocks, "tables": tables}
