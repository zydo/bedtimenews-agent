"""FastAPI application for BedtimeNews Agentic RAG service."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import StreamingResponse

from .chat import nonstream_chat, stream_chat
from .models import ChatRequest, ChatResponse
from .settings import settings
from .vector_db import close_connection_pool

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Manage application lifespan."""
    logger.info("Starting up")
    logger.info(
        f"Using models: FAST={settings.fast_model}, GENERATION={settings.generation_model}"
    )
    yield
    logger.info("Shutting down")
    close_connection_pool()


app = FastAPI(lifespan=lifespan)


# ============================================================================
# Chat Endpoint (Agentic RAG)
# ============================================================================
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Intelligent Q&A using the BedtimeNews Agentic RAG system.

    Agentic RAG Pipeline:
    1. Routing: Determines if question needs retrieval or direct answer
    2. Query Rewriting: Optimizes search queries for better retrieval
    3. Retrieval: Multi-query semantic search
    4. Document Grading: Filters relevant documents using LLM
    5. Answer Generation: Synthesizes answer with citations

    Features:
    - Automatic routing (RAG vs direct answer)
    - Multi-query retrieval for better coverage
    - Document relevance grading
    - Proper citations in [doc_id:chunk_index] format
    - Optional streaming support
    - Optional reasoning trace for observability

    Args:
        request: Chat request with question and options

    Returns:
        ChatResponse with answer, citations, and metadata
        OR StreamingResponse (if stream=True)
    """
    logger.debug(f"Chat: '{request.question[:100]}...', stream={request.stream}")

    # Exception is caught and transformed to error message SSE inside stream_chat,
    # no try-catch needed.
    if request.stream:
        return StreamingResponse(
            stream_chat(request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    try:
        return nonstream_chat(request)
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat processing failed: {str(e)}",
        )
