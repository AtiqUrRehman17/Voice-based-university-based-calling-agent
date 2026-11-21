"""
schemas.py - Pydantic data models for documents, voice chunks, and search results.
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class RawDocument(BaseModel):
    """Represents a raw scraped HTML page or PDF document."""
    id: str
    source_url: str
    category: str
    title: str
    content: str
    source_type: str = Field(description="'html' or 'pdf'")

class VoiceChunk(BaseModel):
    """Represents a voice-ready, atomic chunk stored in Pinecone."""
    id: str
    namespace: str
    title: str
    text: str
    spoken_text: str = Field(description="Normalized conversational text with spelled out numbers and currency")
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SearchResult(BaseModel):
    """Represents a retrieved document match from Pinecone."""
    id: str
    score: float
    namespace: str
    text: str
    spoken_text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
