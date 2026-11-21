"""
test_rag.py - Unit tests for data schemas and Pinecone namespace isolation.
"""
import pytest
from src.common.schemas import VoiceChunk, SearchResult
from config.constants import ALL_NAMESPACES, NAMESPACE_ADMISSIONS, NAMESPACE_FEES

def test_voice_chunk_schema():
    chunk = VoiceChunk(
        id="fees_fact_001",
        namespace="fees",
        title="Tuition Fees",
        text="Tuition is Rs. 40,000",
        spoken_text="Tuition is 40,000 Pakistani Rupees",
        metadata={"program": "BS CS", "amount": 40000}
    )
    assert chunk.namespace == "fees"
    assert chunk.metadata["amount"] == 40000
    assert "Pakistani Rupees" in chunk.spoken_text

def test_search_result_schema():
    result = SearchResult(
        id="adm_001",
        score=0.912,
        namespace="admissions",
        text="Eligibility is 50% F.Sc",
        spoken_text="Eligibility is 50 percent in F S c",
        metadata={"level": "undergraduate"}
    )
    assert result.score > 0.9
    assert result.namespace == "admissions"

def test_namespaces_configured():
    assert len(ALL_NAMESPACES) == 4
    assert NAMESPACE_ADMISSIONS in ALL_NAMESPACES
    assert NAMESPACE_FEES in ALL_NAMESPACES
