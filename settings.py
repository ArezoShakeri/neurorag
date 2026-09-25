"""Single source of truth for configuration, shared across ingestion, agent, and backend."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parent


class Settings(BaseSettings):
    """Environment-driven configuration. See .env.example for all supported values."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM provider
    llm_provider: str = "ollama"  # "ollama" | "anthropic"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b-instruct"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-haiku-4-5"
    llm_max_output_tokens: int = 700  # bounds worst-case decode time; typical answers are well under this

    # Embeddings
    embedding_model_name: str = "pritamdeka/S-PubMedBert-MS-MARCO"

    # Vector store
    chroma_persist_dir: Path = REPO_ROOT / "database" / "chroma_store"
    chroma_collection_name: str = "alzheimer_papers"

    # Retrieval / ingestion
    ncbi_api_key: str | None = None
    unpaywall_email: str = "example@example.com"
    contact_email: str = "example@example.com"

    # Agent behavior
    default_num_papers: int = 5
    max_num_papers: int = 25
    retrieval_candidate_k: int = 15

    # Per-conversation live corpus refresh (first message of a new session only)
    conversation_refresh_max_results: int = 20

    # Voice input (local speech-to-text)
    whisper_model_size: str = "base"  # tiny|base|small|medium|large-v3 — bigger = more accurate, slower

    # Backend
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # Frontend
    backend_url: str = "http://localhost:8000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
