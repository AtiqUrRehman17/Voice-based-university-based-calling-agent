"""
pinecone_manager.py - Manages Pinecone index lifecycle, connection, and namespace stats.
Includes auto-detection, auto-creation, and self-healing index initialization.
"""
import time
from typing import Dict, Any, List
from pinecone import Pinecone, ServerlessSpec
from config.settings import PINECONE_API_KEY, PINECONE_INDEX_NAME, PINECONE_DIMENSION, PINECONE_METRIC
from src.common.logger import logger

class PineconeManager:
    def __init__(self, api_key: str = PINECONE_API_KEY, index_name: str = PINECONE_INDEX_NAME):
        if not api_key:
            raise ValueError("Pinecone API Key is empty! Check your .env file.")
        self.api_key = api_key
        self.index_name = index_name.strip()
        self.pc = Pinecone(api_key=self.api_key)
        self._index = None

    def ensure_index_ready(self, dimension: int = PINECONE_DIMENSION, metric: str = PINECONE_METRIC):
        """
        Verifies that the index exists in Pinecone.
        If missing, discovers existing indexes or automatically creates it as Serverless.
        """
        try:
            existing_indexes = [idx.name for idx in self.pc.list_indexes()]
            logger.info(f"Available Pinecone indexes in your account: {existing_indexes}")

            # 1. Exact match found
            if self.index_name in existing_indexes:
                logger.info(f"Connected to existing index '{self.index_name}'")
                return

            # 2. Case-insensitive or near match
            for name in existing_indexes:
                if name.lower() == self.index_name.lower():
                    logger.info(f"Found matching index '{name}' (updating index_name to '{name}')")
                    self.index_name = name
                    return

            # 3. Index does not exist at all -> Automatically create it!
            logger.info(
                f"Index '{self.index_name}' not found in your Pinecone account. "
                f"Auto-creating Serverless index (dimension={dimension}, metric='{metric}', cloud='aws', region='us-east-1')..."
            )
            self.pc.create_index(
                name=self.index_name,
                dimension=dimension,
                metric=metric,
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )

            # Wait until ready
            logger.info("Waiting for Pinecone to initialize index...")
            while not self.pc.describe_index(self.index_name).status.get("ready", False):
                time.sleep(2)

            logger.info(f"[SUCCESS] Pinecone index '{self.index_name}' is ready for use!")

        except Exception as e:
            logger.error(f"Error checking or creating index '{self.index_name}': {e}")
            raise e

    def get_index(self):
        """Returns the Index instance, ensuring it exists first."""
        if self._index is None:
            self.ensure_index_ready()
            self._index = self.pc.Index(self.index_name)
        return self._index

    def get_index_dimension(self) -> int:
        """Inspects the Pinecone index metadata and returns its configured dimension."""
        try:
            self.ensure_index_ready()
            desc = self.pc.describe_index(self.index_name)
            dim = desc.dimension
            logger.info(f"Pinecone index '{self.index_name}' dimension: {dim}")
            return dim
        except Exception as e:
            logger.warning(f"Could not describe index '{self.index_name}': {e}. Using configured {PINECONE_DIMENSION}.")
            return PINECONE_DIMENSION

    def get_namespace_stats(self) -> Dict[str, Any]:
        """Returns a breakdown of vector counts per namespace."""
        try:
            index = self.get_index()
            stats = index.describe_index_stats()
            namespaces = stats.get("namespaces", {})
            total_count = stats.get("total_vector_count", 0)
            logger.info(f"Pinecone stats for '{self.index_name}': {total_count} total vectors across {len(namespaces)} namespaces.")
            return {
                "total_vector_count": total_count,
                "dimension": stats.get("dimension"),
                "namespaces": namespaces
            }
        except Exception as e:
            logger.error(f"Error fetching stats from Pinecone: {e}")
            return {}

    def upsert_vectors(self, vectors: List[Dict[str, Any]], namespace: str) -> int:
        """
        Upserts a list of vector dicts ({'id': ..., 'values': [...], 'metadata': {...}})
        into a designated namespace.
        """
        if not vectors:
            return 0
        index = self.get_index()
        batch_size = 50
        upserted_count = 0
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            index.upsert(vectors=batch, namespace=namespace)
            upserted_count += len(batch)
        logger.info(f"Upserted {upserted_count} vectors into namespace '{namespace}'")
        return upserted_count

    def clear_namespace(self, namespace: str):
        """Deletes all vectors inside a specific namespace."""
        try:
            index = self.get_index()
            index.delete(delete_all=True, namespace=namespace)
            logger.info(f"Cleared all vectors from namespace: '{namespace}'")
        except Exception as e:
            logger.warning(f"Could not clear namespace '{namespace}': {e}")
