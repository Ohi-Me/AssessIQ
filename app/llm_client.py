"""
LLM client — Groq primary, Gemini fallback.
Both free tier. Groq is faster (< 3s), Gemini is fallback.
"""

import os
import asyncio
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

def call_llm(prompt: str, max_tokens: int = 600) -> str:
    """Call LLM with Groq primary, Gemini fallback."""

    # Try Groq first
    result = _call_groq(prompt, max_tokens)

    if result:
        return result

    # Fallback to Gemini
    logger.info("Falling back to Gemini...")

    result = _call_gemini(prompt, max_tokens)

    if result:
        return result

    # Hard fallback
    logger.error("All LLM providers failed!")

    return "I'm having trouble processing your request right now. Please try again in a moment."


async def call_llm_async(prompt: str, max_tokens: int = 600) -> str:
    """Async wrapper for call_llm."""

    loop = asyncio.get_event_loop()

    return await loop.run_in_executor(
        None,
        call_llm,
        prompt,
        max_tokens
    )
