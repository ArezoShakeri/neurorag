"""FastAPI app entrypoint. Run with: uvicorn backend.main:app --reload"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from agent.graph import get_agent_graph
from agent.llm_factory import get_chat_model
from backend.routers import health, query, transcribe
from backend.services.transcription import get_whisper_model
from database.chroma_client import get_chroma_store
from database.embedding_factory import get_embedding_model


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm the embedding model, Chroma client, LLM client, Whisper model, and compiled graph
    # once at startup — each is an lru_cache'd singleton, so per-request calls just reuse these.
    get_embedding_model()
    get_chroma_store()
    get_chat_model()
    get_whisper_model()
    get_agent_graph()
    yield


app = FastAPI(title="NeuroRAG", description="AI Research Assistant for Alzheimer's disease literature", lifespan=lifespan)

app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(query.router, prefix="/api/v1", tags=["query"])
app.include_router(transcribe.router, prefix="/api/v1", tags=["transcribe"])
