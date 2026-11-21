"""
retriever.py - Low-latency, namespace-targeted search engine.
Queries strictly within a single namespace to eliminate cross-domain hallucinations.
"""
import time
from typing import List, Optional
from config.constants import ALL_NAMESPACES
from src.common.logger import logger
from src.common.schemas import SearchResult
from src.rag.embedder import Embedder
from src.rag.pinecone_manager import PineconeManager

class USTBRetriever:
    def __init__(self, pinecone_manager: PineconeManager = None, embedder: Embedder = None):
        self.pm = pinecone_manager or PineconeManager()
        
        target_dim = self.pm.get_index_dimension()
        if embedder is not None:
            self.embedder = embedder
        else:
            from config.settings import EMBEDDING_PROVIDER, EMBEDDING_MODEL_NAME
            if target_dim == 1536:
                self.embedder = Embedder(provider="openai", model_name="text-embedding-3-small")
            elif target_dim == 768:
                model_768 = EMBEDDING_MODEL_NAME if "768" in str(EMBEDDING_MODEL_NAME) or "bge-base" in str(EMBEDDING_MODEL_NAME) or "mpnet" in str(EMBEDDING_MODEL_NAME) else "BAAI/bge-base-en-v1.5"
                self.embedder = Embedder(provider=EMBEDDING_PROVIDER, model_name=model_768)
            else:
                self.embedder = Embedder(provider=EMBEDDING_PROVIDER, model_name=EMBEDDING_MODEL_NAME)

        self.index = self.pm.get_index()

    def query_namespace(
        self,
        namespace: str,
        query: str,
        top_k: int = 3,
        min_score: float = 0.35
    ) -> List[SearchResult]:
        """
        Searches ONLY inside the targeted namespace.
        Latency target: < 20ms for vector search.
        """
        start_time = time.time()

        # 1. Generate query embedding
        query_vector = self.embedder.embed_text(query)

        # 2. Query Pinecone with strict namespace constraint
        try:
            response = self.index.query(
                namespace=namespace,
                vector=query_vector,
                top_k=top_k,
                include_metadata=True
            )
        except Exception as e:
            logger.error(f"Pinecone query failed in namespace '{namespace}': {e}")
            return []

        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(f"Query in namespace '{namespace}' completed in {elapsed_ms:.1f}ms (Hits: {len(response.matches)})")

        # 3. Format results
        results = []
        for match in response.matches:
            if match.score < min_score:
                continue

            metadata = match.metadata or {}
            results.append(SearchResult(
                id=match.id,
                score=match.score,
                namespace=namespace,
                text=metadata.get("text", ""),
                spoken_text=metadata.get("spoken_text", metadata.get("text", "")),
                metadata=metadata
            ))

        return results

    def get_voice_context(self, namespace: str, query: str, top_k: int = 2) -> str:
        """
        Convenience function for LiveKit Voice Agent:
        Returns directly formatted spoken text for the LLM prompt.
        """
        results = self.query_namespace(namespace=namespace, query=query, top_k=top_k)
        if not results:
            return "No official records found for this specific inquiry."

        facts = [f"- {res.spoken_text}" for res in results]
        return "\n".join(facts)
