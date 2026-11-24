"""
embedder.py - Universal embedding generator for Pinecone RAG.
Supports:
1. Hugging Face Inference API (via huggingface_hub InferenceClient)
2. Local SentenceTransformers (runs locally, free, cached offline)
3. OpenAI Embeddings API
"""
from typing import List
from config.settings import (
    EMBEDDING_PROVIDER, 
    EMBEDDING_MODEL_NAME, 
    HUGGINGFACE_API_KEY,
    OPENAI_API_KEY, 
    get_configured_dimension
)
from src.common.logger import logger

class Embedder:
    def __init__(self, provider: str = EMBEDDING_PROVIDER, model_name: str = EMBEDDING_MODEL_NAME):
        self.provider = provider.lower()
        self.model_name = model_name
        self._local_model = None
        self._transformer_model = None
        self._transformer_tokenizer = None
        self._openai_client = None
        self._hf_client = None

        # 1. Hugging Face Inference API
        if self.provider == "huggingface":
            try:
                from huggingface_hub import InferenceClient
                self._hf_client = InferenceClient(
                    token=HUGGINGFACE_API_KEY,
                    model=self.model_name
                )
                logger.info(f"Initialized Hugging Face API Embedder with model '{self.model_name}'")
            except Exception as e:
                logger.warning(f"Could not initialize HF API client: {e}. Falling back to local SentenceTransformers.")
                self.provider = "local"

        # 2. OpenAI API
        elif self.provider == "openai":
            try:
                from openai import OpenAI
                self._openai_client = OpenAI(api_key=OPENAI_API_KEY)
                logger.info(f"Initialized OpenAI Embedder with model '{self.model_name}'")
            except Exception as e:
                logger.warning(f"Could not initialize OpenAI embedder: {e}. Falling back to local SentenceTransformers.")
                self.provider = "local"

        # 3. Local SentenceTransformers (fallback or explicit choice)
        if self.provider == "local":
            self._load_local_model()

    def _load_local_model(self) -> bool:
        """Load the configured model locally, with Transformers as an ST-free fallback."""
        try:
            from sentence_transformers import SentenceTransformer
            self._local_model = SentenceTransformer(self.model_name)
            logger.info(f"Initialized Local Embedder with SentenceTransformer '{self.model_name}'")
            return True
        except Exception as sentence_transformers_error:
            logger.warning(
                f"Could not load SentenceTransformer '{self.model_name}': "
                f"{sentence_transformers_error}. Trying direct Transformers mean pooling."
            )

        try:
            from transformers import AutoModel, AutoTokenizer
            self._transformer_tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._transformer_model = AutoModel.from_pretrained(self.model_name)
            self._transformer_model.eval()
            logger.info(f"Initialized direct Transformers Embedder with '{self.model_name}'")
            return True
        except Exception as transformers_error:
            logger.error(
                f"Could not load '{self.model_name}' with Transformers: {transformers_error}. "
                "Install sentence-transformers (recommended) or transformers and torch."
            )
            return False

    @property
    def dimension(self) -> int:
        """Returns the vector dimension produced by this embedder."""
        if self._local_model is not None:
            return self._local_model.get_sentence_embedding_dimension()
        if self._transformer_model is not None:
            return int(self._transformer_model.config.hidden_size)
        return get_configured_dimension()

    def embed_text(self, text: str) -> List[float]:
        """Generates embedding for a single string."""
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings for a batch of strings."""
        if not texts:
            return []

        # Hugging Face Inference API
        if self.provider == "huggingface" and self._hf_client is not None:
            try:
                import numpy as np
                embeddings = []
                for text in texts:
                    res = self._hf_client.feature_extraction(text)
                    # Handle numpy array or nested lists
                    arr = np.array(res)
                    if arr.ndim == 2:
                        # Mean pool over token dimension (seq_len, dim) -> (dim,)
                        vec = np.mean(arr, axis=0).tolist()
                    elif arr.ndim == 3:
                        # (1, seq_len, dim) -> (dim,)
                        vec = np.mean(arr[0], axis=0).tolist()
                    else:
                        vec = arr.flatten().tolist()
                    embeddings.append(vec)
                return embeddings
            except Exception as e:
                logger.warning(f"HF API embedding failed: {e}. Falling back to local '{self.model_name}'.")
                self.provider = "local"
                if self._local_model is None and self._transformer_model is None:
                    self._load_local_model()
                return self._embed_local(texts)

        # OpenAI API
        if self.provider == "openai" and self._openai_client is not None:
            try:
                res = self._openai_client.embeddings.create(
                    input=texts,
                    model=self.model_name
                )
                return [item.embedding for item in res.data]
            except Exception as e:
                logger.error(f"OpenAI embedding error: {e}")
                raise e

        # Local SentenceTransformers
        if self.provider == "local":
            return self._embed_local(texts)

        raise RuntimeError("No working embedding model available!")

    def _embed_local(self, texts: List[str]) -> List[List[float]]:
        if self._local_model is not None:
            embeddings = self._local_model.encode(
                texts,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
            return embeddings.tolist()

        if self._transformer_model is not None and self._transformer_tokenizer is not None:
            import torch

            inputs = self._transformer_tokenizer(
                texts,
                padding=True,
                truncation=True,
                return_tensors="pt",
            )
            with torch.no_grad():
                token_embeddings = self._transformer_model(**inputs).last_hidden_state
                mask = inputs["attention_mask"].unsqueeze(-1).to(token_embeddings.dtype)
                summed = (token_embeddings * mask).sum(dim=1)
                counts = mask.sum(dim=1).clamp(min=1)
                embeddings = summed / counts
            return embeddings.cpu().tolist()

        raise RuntimeError(
            f"No local embedding backend could load '{self.model_name}'. "
            "Install the project's requirements in the active virtual environment."
        )
