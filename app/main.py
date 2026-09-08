"""
AssessIQ — FastAPI Application
GET  /health  → readiness check
POST /chat    → conversational agent
"""

import time
import asyncio
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.schemas import ChatRequest, ChatResponse, HealthResponse, Message
from app.catalog_loader import load_catalog
from app.retriever import ensure_indexes
from app.agent import process_chat


# ──────────────────────────────────────────────────────────────────
# Startup: load catalog + build indexes
# ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AssessIQ...")
    start = time.time()

    # Load catalog
    catalog = load_catalog()
    logger.info(f"Catalog loaded: {len(catalog)} assessments")

    # Build/load retrieval indexes (run in thread to not block event loop)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, ensure_indexes, catalog)

    elapsed = time.time() - start
    logger.info(f"Startup complete in {elapsed:.1f}s")
    yield
    logger.info("Shutting down AssessIQ...")


# ──────────────────────────────────────────────────────────────────
# App
# ──────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AssessIQ",
    description="Conversational agent that recommends talent assessments from a real product catalog",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────────────────────────
# Request timing middleware
# ──────────────────────────────────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = time.time() - start
    logger.info(f"{request.method} {request.url.path} → {response.status_code} ({elapsed:.2f}s)")
    return response


# ──────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health():
    """Readiness check. Returns 200 OK when service is ready."""
    return HealthResponse(status="ok")


@app.get("/stats")
async def stats():
    """Cache counters, for checking hit rates against a running instance."""
    from app.retriever import cache_stats as embedding_cache_stats
    from app.llm_client import cache_stats as llm_cache_stats

    return {
        "embedding_cache": embedding_cache_stats(),
        "llm_cache": llm_cache_stats(),
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main conversational endpoint.
    Accepts full conversation history, returns next agent reply.
    Stateless — no server-side session state.
    """
    messages = [m.model_dump() for m in request.messages]

    # Validate turn count (max 8 turns including user + assistant)
    if len(messages) > 8:
        logger.warning(f"Turn count exceeded: {len(messages)} > 8")
        messages = messages[-8:]  # use last 8 turns

    # Validate message roles
    for msg in messages:
        if msg.get("role") not in ("user", "assistant", "system"):
            raise HTTPException(
                status_code=422,
                detail=f"Invalid message role: {msg.get('role')}"
            )

    # Ensure at least one user message
    user_messages = [m for m in messages if m.get("role") == "user"]
    if not user_messages:
        raise HTTPException(status_code=422, detail="At least one user message required")

    try:
        # Run agent with timeout
        loop = asyncio.get_event_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(None, process_chat, messages),
            timeout=25.0  # 25s to stay under 30s limit
        )
        return response

    except asyncio.TimeoutError:
        logger.error("Agent timed out (>25s)")
        return ChatResponse(
            reply="I'm taking too long to process your request. Please try rephrasing your question.",
            recommendations=[],
            end_of_conversation=False,
        )

    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        return ChatResponse(
            reply="I encountered an error processing your request. Please try again.",
            recommendations=[],
            end_of_conversation=False,
        )


@app.get("/")
async def root():
    return {
        "service": "AssessIQ",
        "version": "1.0.0",
        "endpoints": {
            "health": "GET /health",
            "chat": "POST /chat",
            "docs": "GET /docs",
        }
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
