"""
chunker.py - Chunks textual information into atomic voice-friendly chunks.
"""
import uuid
from typing import List, Dict, Any
from src.common.schemas import VoiceChunk
from src.processing.normalizer import VoiceNormalizer

class VoiceChunker:
    def __init__(self, max_words: int = 120):
        self.max_words = max_words
        self.normalizer = VoiceNormalizer()

    def chunk_sentences(
        self,
        sentences: List[str],
        namespace: str,
        title: str,
        metadata: Dict[str, Any] = None
    ) -> List[VoiceChunk]:
        """
        Groups sequential sentences into atomic units optimized for voice retrieval.
        Each chunk is under max_words so the voice agent can synthesize it in sub-second time.
        """
        chunks: List[VoiceChunk] = []
        current_sentences = []
        current_word_count = 0
        metadata = metadata or {}

        for sentence in sentences:
            sentence_words = len(sentence.split())
            if current_word_count + sentence_words > self.max_words and current_sentences:
                # Flush current chunk
                raw_text = " ".join(current_sentences)
                spoken_text = self.normalizer.to_spoken_form(raw_text)
                chunk_id = f"{namespace}_{uuid.uuid4().hex[:8]}"

                chunks.append(VoiceChunk(
                    id=chunk_id,
                    namespace=namespace,
                    title=title,
                    text=raw_text,
                    spoken_text=spoken_text,
                    metadata=metadata
                ))
                current_sentences = []
                current_word_count = 0

            current_sentences.append(sentence)
            current_word_count += sentence_words

        # Flush remaining sentences
        if current_sentences:
            raw_text = " ".join(current_sentences)
            spoken_text = self.normalizer.to_spoken_form(raw_text)
            chunk_id = f"{namespace}_{uuid.uuid4().hex[:8]}"
            chunks.append(VoiceChunk(
                id=chunk_id,
                namespace=namespace,
                title=title,
                text=raw_text,
                spoken_text=spoken_text,
                metadata=metadata
            ))

        return chunks

    def chunk_table_rows(
        self,
        table_rows: List[List[str]],
        namespace: str,
        title: str,
        metadata: Dict[str, Any] = None
    ) -> List[VoiceChunk]:
        """Converts each row in a tabular fee structure into an individual atomic VoiceChunk."""
        chunks = []
        header = table_rows[0] if table_rows else []
        data_rows = table_rows[1:] if len(table_rows) > 1 else table_rows

        for row in data_rows:
            spoken_sentence = self.normalizer.format_table_row_for_voice(row, header)
            if not spoken_sentence:
                continue

            chunk_id = f"{namespace}_row_{uuid.uuid4().hex[:8]}"
            chunks.append(VoiceChunk(
                id=chunk_id,
                namespace=namespace,
                title=title,
                text=" | ".join(row),
                spoken_text=spoken_sentence,
                metadata={**(metadata or {}), "source_type": "table_row"}
            ))

        return chunks
