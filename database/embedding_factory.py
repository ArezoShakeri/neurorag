"""Embedding model provider — swappable via EMBEDDING_MODEL_NAME so the rest of the codebase
never hardcodes a specific model."""

from functools import lru_cache

from langchain_core.embeddings import Embeddings
from langchain_huggingface import HuggingFaceEmbeddings

from settings import get_settings


@lru_cache
def get_embedding_model() -> Embeddings:
    """Local, open-source sentence-transformers model. Loaded once and reused (loading is slow)."""
    settings = get_settings()
    return HuggingFaceEmbeddings(
        model_name=settings.embedding_model_name,
        encode_kwargs={"normalize_embeddings": True},
    )
