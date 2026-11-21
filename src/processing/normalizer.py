"""
normalizer.py - Normalizes textual facts for natural Text-To-Speech (TTS) pronunciation.
"""
import re
from typing import List
from config.constants import ACRONYM_MAP

class VoiceNormalizer:
    def __init__(self):
        self.acronym_map = ACRONYM_MAP

    def normalize_currency(self, text: str) -> str:
        """
        Converts Pakistani currency representations into natural spoken text.
        e.g., 'Rs. 45,000/-' -> '45,000 Pakistani Rupees'
        Uses \b word boundary so words like 'offers 4' are not affected.
        """
        # Match '\bRs. 45,000/-' or '\bRs 45000' or '\bPKR 45,000'
        text = re.sub(r"\bRs\.?\s*(\d+[\d,]*)(?:\s*/-)?", r"\1 Pakistani Rupees", text, flags=re.IGNORECASE)
        text = re.sub(r"\bPKR\s*(\d+[\d,]*)(?:\s*/-)?", r"\1 Pakistani Rupees", text, flags=re.IGNORECASE)
        # Strip trailing /- notation
        text = text.replace("/-", "")
        return text

    def expand_academic_acronyms(self, text: str) -> str:
        """Expands academic acronyms so voice models don't mispronounce them."""
        for pattern, replacement in self.acronym_map.items():
            text = re.sub(pattern, replacement, text)
        return text

    def clean_voice_symbols(self, text: str) -> str:
        """Removes punctuation and markdown characters that sound awkward in voice output."""
        # Remove asterisks, hashtags, underscores, brackets
        text = re.sub(r"[\*#_\[\]\(\)<>\|]", " ", text)
        # Normalize double dashes or long dashes
        text = re.sub(r"—|–|-{2,}", ", ", text)
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def format_table_row_for_voice(self, row: List[str], header: List[str] = None) -> str:
        """
        Converts a raw tabular row into a natural spoken sentence.
        Example: ['BS Software Engineering', '42,000', '5,000', '47,000']
        """
        if len(row) < 2:
            return ""

        subject = row[0].strip()
        details = []

        if header and len(header) == len(row):
            for h, val in zip(header[1:], row[1:]):
                if val and val.strip():
                    details.append(f"{h.strip()} is {val.strip()}")
            sentence = f"For {subject}, " + ", and ".join(details) + "."
        else:
            # Generic fallback
            sentence = f"For {subject}, the recorded amounts are " + ", ".join(row[1:]) + "."

        return self.to_spoken_form(sentence)

    def to_spoken_form(self, text: str) -> str:
        """Full pipeline: normalizes currency, expands acronyms, and cleans voice symbols."""
        text = self.normalize_currency(text)
        text = self.expand_academic_acronyms(text)
        text = self.clean_voice_symbols(text)
        return text
