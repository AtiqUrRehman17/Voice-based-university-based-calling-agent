"""
settings.py - Environment and runtime configurations.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# Suppress harmless symlink warning on Windows for Hugging Face
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

# ---------------------------------------------------------------------------
# Pinecone Configuration
# ---------------------------------------------------------------------------
PINECONE_API_KEY = (
    os.getenv("PINECONE_API_KEY") or 
    os.getenv("PINCORNE_API_KEY") or 
    ""
)

PINECONE_INDEX_NAME = (
    os.getenv("PINECONE_INDEX_NAME") or 
    os.getenv("PINCORNE_INDEX_NAME") or 
    "ustb-voice-kb"
)

PINECONE_DIMENSION = int(os.getenv("PINECONE_DIMENSION", "384"))
PINECONE_METRIC = os.getenv("PINECONE_METRIC", "cosine")

# ---------------------------------------------------------------------------
# Hugging Face Configuration
# ---------------------------------------------------------------------------
HUGGINGFACE_API_KEY = (
    os.getenv("HUGGINGFACE_API_KEY") or 
    os.getenv("HF_TOKEN") or 
    ""
)

# Hugging Face LLM Model (e.g. meta-llama/Llama-3.1-8B-Instruct, Qwen/Qwen2.5-72B-Instruct)
HF_LLM_MODEL = os.getenv("HF_LLM_MODEL", "meta-llama/Llama-3.1-8B-Instruct")

# ---------------------------------------------------------------------------
# Embedding Configuration
# ---------------------------------------------------------------------------
# Options:
#  - 'huggingface' : Uses Hugging Face Inference API with your token
#  - 'local'       : Uses local SentenceTransformers (downloads model once, runs offline)
#  - 'openai'      : Uses OpenAI text-embedding-3-small
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "huggingface").lower()
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")

# OpenAI API key (optional)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Dimension map for known embedding models
DIMENSION_MAP = {
    "sentence-transformers/all-MiniLM-L6-v2": 384,
    "all-MiniLM-L6-v2": 384,
    "BAAI/bge-small-en-v1.5": 384,
    "bge-small-en-v1.5": 384,
    "BAAI/bge-base-en-v1.5": 768,
    "bge-base-en-v1.5": 768,
    "sentence-transformers/all-mpnet-base-v2": 768,
    "text-embedding-3-small": 1536,
    "text-embedding-ada-002": 1536,
}

def get_configured_dimension() -> int:
    """Returns dimension from map or user's PINECONE_DIMENSION."""
    return DIMENSION_MAP.get(EMBEDDING_MODEL_NAME, PINECONE_DIMENSION)

def validate_environment():
    """Validates that mandatory environment variables are present."""
    errors = []
    if not PINECONE_API_KEY:
        errors.append("PINECONE_API_KEY is missing in .env")
    if EMBEDDING_PROVIDER == "huggingface" and not HUGGINGFACE_API_KEY:
        errors.append("HUGGINGFACE_API_KEY is missing in .env (required for provider='huggingface')")

    if errors:
        for err in errors:
            print(f"[ERROR] {err}", file=sys.stderr)
        return False
    return True
