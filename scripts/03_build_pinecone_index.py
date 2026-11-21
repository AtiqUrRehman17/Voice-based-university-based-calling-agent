"""
03_build_pinecone_index.py - Reads processed chunks and upserts them into Pinecone namespaces.
"""
import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from config.settings import validate_environment, PINECONE_INDEX_NAME
from src.rag.pinecone_manager import PineconeManager
from src.rag.indexer import USTBIndexer
from src.common.logger import logger

def main():
    logger.info("=====================================================")
    logger.info(f"   Building Pinecone Index: '{PINECONE_INDEX_NAME}'   ")
    logger.info("=====================================================")

    if not validate_environment():
        logger.error("Environment validation failed. Please check your .env file.")
        sys.exit(1)

    pm = PineconeManager()
    
    # 1. Fetch current index dimension and stats
    dim = pm.get_index_dimension()
    logger.info(f"Connected to Pinecone Index '{PINECONE_INDEX_NAME}' with dimension: {dim}")

    # 2. Run Indexer across all namespaces
    indexer = USTBIndexer(pinecone_manager=pm)
    summary = indexer.index_all()

    # 3. Print final report
    logger.info("=====================================================")
    logger.info("              INDEXING SUMMARY REPORT                ")
    logger.info("=====================================================")
    total = 0
    for ns, count in summary.items():
        logger.info(f" Namespace '{ns:20s}' : {count} vectors")
        total += count
    logger.info(f" Total Vectors Indexed      : {total}")
    logger.info("=====================================================")

    # 4. Check Pinecone server stats
    stats = pm.get_namespace_stats()
    logger.info(f"Live Pinecone Stats: {stats}")

if __name__ == "__main__":
    main()
