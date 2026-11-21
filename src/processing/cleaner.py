"""
cleaner.py - General text hygiene, deduplication, and noise suppression.
"""
import re
from typing import List

class TextCleaner:
    def __init__(self):
        self.boilerplate_patterns = [
            r"Copyright\s+©.*",
            r"All\s+rights\s+reserved.*",
            r"Designed\s+and\s+Developed\s+by.*",
            r"Follow\s+us\s+on\s+Facebook.*",
            r"Powered\s+by.*",
            r"^Home\s*>\s*.*",  # Breadcrumbs
            r"Content\s+not\s+available\.?",  # University placeholder
            r"Page\s+under\s+construction",
            r"S\.NO\s+ADM\s+NO\s+STUDENT\s+NAME.*",  # Student table header crumbs
        ]

    def is_boilerplate(self, text: str) -> bool:
        """Checks if a string is standard website footer or nav boilerplate."""
        for pattern in self.boilerplate_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def clean_text_block(self, text: str) -> str:
        """Removes excess whitespace, non-printable characters, and trims lines."""
        # Replace multiple spaces/newlines
        text = re.sub(r"[\r\t\f]", " ", text)
        text = re.sub(r"\n+", "\n", text)
        text = re.sub(r" +", " ", text)
        return text.strip()

    def filter_and_deduplicate(self, sentences: List[str]) -> List[str]:
        """Cleans and deduplicates a list of sentences/paragraphs."""
        seen = set()
        cleaned_list = []
        for s in sentences:
            clean = self.clean_text_block(s)
            if len(clean) < 20:  # Skip tiny fragments
                continue
            if self.is_boilerplate(clean):
                continue
            normalized_key = clean.lower()
            if normalized_key not in seen:
                seen.add(normalized_key)
                cleaned_list.append(clean)
        return cleaned_list
