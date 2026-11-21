"""
indexer.py - Loads processed JSON chunks, embeds them, and upserts them into Pinecone namespaces.
"""
from pathlib import Path
from typing import List, Dict, Any
from config.constants import PROCESSED_FILES, ALL_NAMESPACES
from src.common.logger import logger
from src.common.file_utils import load_json
from src.rag.embedder import Embedder
from src.rag.pinecone_manager import PineconeManager

class USTBIndexer:
    def __init__(self, pinecone_manager: PineconeManager = None, embedder: Embedder = None):
        self.pm = pinecone_manager or PineconeManager()
        
        # Check Pinecone Index Dimension to align with Embedder
        target_dim = self.pm.get_index_dimension()
        
        # Pick embedder matching Pinecone index dimension
        if embedder is not None:
            self.embedder = embedder
        else:
            from config.settings import EMBEDDING_PROVIDER, EMBEDDING_MODEL_NAME
            if target_dim == 1536:
                logger.info("Pinecone dimension is 1536. Using OpenAI text-embedding-3-small.")
                self.embedder = Embedder(provider="openai", model_name="text-embedding-3-small")
            elif target_dim == 768:
                model_768 = EMBEDDING_MODEL_NAME if "768" in str(EMBEDDING_MODEL_NAME) or "bge-base" in str(EMBEDDING_MODEL_NAME) or "mpnet" in str(EMBEDDING_MODEL_NAME) else "BAAI/bge-base-en-v1.5"
                logger.info(f"Pinecone dimension is 768. Using {model_768} via {EMBEDDING_PROVIDER}.")
                self.embedder = Embedder(provider=EMBEDDING_PROVIDER, model_name=model_768)
            else:
                logger.info(f"Pinecone dimension is {target_dim}. Using {EMBEDDING_MODEL_NAME} via {EMBEDDING_PROVIDER}.")
                self.embedder = Embedder(provider=EMBEDDING_PROVIDER, model_name=EMBEDDING_MODEL_NAME)

    def index_namespace(self, namespace: str, json_file: Path) -> int:
        """Indexes a single processed JSON file into its designated Pinecone namespace."""
        chunks = load_json(json_file)
        if not chunks:
            logger.warning(f"No records found in {json_file}. Skipping namespace '{namespace}'.")
            return 0

        logger.info(f"Indexing {len(chunks)} items into namespace: '{namespace}'...")

        # Clear existing vectors in this namespace so we don't keep obsolete duplicate chunks
        self.pm.clear_namespace(namespace)

        # Extract texts to embed (embed the clean spoken text for voice semantic search)
        texts_to_embed = [item.get("spoken_text") or item.get("text", "") for item in chunks]
        embeddings = self.embedder.embed_batch(texts_to_embed)

        vectors_to_upsert = []
        for idx, item in enumerate(chunks):
            chunk_id = item.get("id") or f"{namespace}_{idx}"
            text = item.get("text", "")
            spoken_text = item.get("spoken_text", text)
            title = item.get("title", "")
            metadata = item.get("metadata", {})

            # Prepare Pinecone payload (Pinecone metadata must be primitive types)
            flattened_metadata = {
                "text": text[:1000],  # Keep within Pinecone 40KB metadata limit
                "spoken_text": spoken_text[:1000],
                "title": title[:200],
                "namespace": namespace,
            }
            # Add extra string/numeric metadata tags
            for k, v in metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    flattened_metadata[k] = v

            vectors_to_upsert.append({
                "id": chunk_id,
                "values": embeddings[idx],
                "metadata": flattened_metadata
            })

        upserted_count = self.pm.upsert_vectors(vectors_to_upsert, namespace=namespace)
        logger.info(f"[SUCCESS] Indexed {upserted_count} chunks in namespace '{namespace}'")
        return upserted_count

    def index_all(self) -> Dict[str, int]:
        """Indexes all 4 standard namespaces from their respective JSON files."""
        summary = {}
        for namespace in ALL_NAMESPACES:
            json_file = PROCESSED_FILES.get(namespace)
            if json_file and json_file.exists():
                count = self.index_namespace(namespace, json_file)
                summary[namespace] = count
            else:
                logger.warning(f"File for namespace '{namespace}' not found at {json_file}")
                summary[namespace] = 0
        return summary
