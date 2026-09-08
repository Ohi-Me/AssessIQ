"""
LLM client — Groq primary, Gemini fallback.
Both free tier. Groq is faster (< 3s), Gemini is fallback.
"""

import os
import asyncio
import hashlib
import time
from collections import OrderedDict
from typing import Optional

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# Overridable by env so a provider deprecation can be handled without a deploy.
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


# ──────────────────────────────────────────────────────────────────
# Groq client
# ──────────────────────────────────────────────────────────────────

def _call_groq(prompt: str, max_tokens: int = 600) -> Optional[str]:
    try:
        from groq import Groq

        api_key = os.getenv("GROQ_API_KEY", "")

        if not api_key:
            logger.error("Groq API key missing")
            return None

        client = Groq(api_key=api_key)

        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.3,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.exception(f"Groq failed: {e}")
        return None


# ──────────────────────────────────────────────────────────────────
# Gemini client
# ──────────────────────────────────────────────────────────────────

def _call_gemini(prompt: str, max_tokens: int = 600) -> Optional[str]:
    try:
        import google.generativeai as genai

        api_key = os.getenv("GEMINI_API_KEY", "")

        if not api_key:
            logger.error("Gemini API key missing")
            return None

        genai.configure(api_key=api_key)

        model = genai.GenerativeModel(GEMINI_MODEL)

        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=0.3,
            )
        )

        return response.text.strip()

    except Exception as e:
        logger.exception(f"Gemini failed: {e}")
        return None


# ──────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────

HARD_FALLBACK = (
    "I'm having trouble processing your request right now. Please try again in a moment."
)

# Generation dominates request latency — retrieval is milliseconds, a completion
# is seconds. Identical prompts recur constantly (the demo's starter prompts, a
# reloaded page), so successful completions are memoized. Failures are never
# cached: caching one rate-limited response would pin the error in place.
_CACHE_MAX = 256
_response_cache: "OrderedDict[str, str]" = OrderedDict()
_cache_hits = 0
_cache_misses = 0


def _cache_key(prompt: str, max_tokens: int) -> str:
    return hashlib.sha256(f"{max_tokens}:{prompt}".encode("utf-8")).hexdigest()


def cache_stats() -> dict:
    return {
        "hits": _cache_hits,
        "misses": _cache_misses,
        "size": len(_response_cache),
        "maxsize": _CACHE_MAX,
    }


def clear_cache() -> None:
    global _cache_hits, _cache_misses
    _response_cache.clear()
    _cache_hits = 0
    _cache_misses = 0


def call_llm(prompt: str, max_tokens: int = 600) -> str:
    """Call LLM with Groq primary, Gemini fallback. Successful replies are cached."""
    global _cache_hits, _cache_misses

    key = _cache_key(prompt, max_tokens)
    cached = _response_cache.get(key)
    if cached is not None:
        _response_cache.move_to_end(key)
        _cache_hits += 1
        logger.info("LLM cache hit")
        return cached
    _cache_misses += 1

    # Try Groq first. One retry, because the free tier rate-limits under bursts
    # and a single 429 was enough to show the generic error text to a visitor.
    result = _call_groq(prompt, max_tokens)

    if not result:
        time.sleep(1.5)
        logger.info("Retrying Groq once...")
        result = _call_groq(prompt, max_tokens)

    if result:
        return _remember(key, result)

    # Fallback to Gemini
    logger.info("Falling back to Gemini...")

    result = _call_gemini(prompt, max_tokens)

    if result:
        return _remember(key, result)

    # Hard fallback — deliberately not cached.
    logger.error("All LLM providers failed!")

    return HARD_FALLBACK


def _remember(key: str, reply: str) -> str:
    _response_cache[key] = reply
    _response_cache.move_to_end(key)
    while len(_response_cache) > _CACHE_MAX:
        _response_cache.popitem(last=False)
    return reply


async def call_llm_async(prompt: str, max_tokens: int = 600) -> str:
    """Async wrapper for call_llm."""

    loop = asyncio.get_event_loop()

    return await loop.run_in_executor(
        None,
        call_llm,
        prompt,
        max_tokens
    )
