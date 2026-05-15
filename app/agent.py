"""
Agent — main orchestration layer.

Flow per request:
  1. Guardrail classify(messages)
  2. Route to handler: clarify / recommend / refine / compare / refuse
  3. Retrieve (if needed)
  4. LLM call (grounded)
  5. Extract + validate recommendations
  6. Return ChatResponse
"""

import re
from typing import List, Dict, Optional
from loguru import logger

from app.schemas import ChatResponse, Recommendation
from app.guardrails import classify, is_end_of_conversation
from app.retriever import retrieve, retrieve_for_comparison
from app.prompts import (
    clarification_prompt,
    recommendation_prompt,
    refinement_prompt,
    comparison_prompt,
    OFF_TOPIC_REFUSAL,
    INJECTION_REFUSAL,
    MAX_TURNS_REPLY,
)
from app.validator import validate_recommendations, extract_recommendations_from_llm_reply
from app.llm_client import call_llm

# Hard cap from assignment spec: max 8 messages (user + assistant combined)
MAX_MESSAGES = 8


# ──────────────────────────────────────────────────────────────────
# Comparison name extraction
# ──────────────────────────────────────────────────────────────────

KNOWN_ASSESSMENT_NAMES = [
    "OPQ32r", "OPQ32", "OPQ",
    "MQ", "Motivational Questionnaire",
    "RemoteWorkQ",
    "Verify Numerical Reasoning", "Verify Verbal Reasoning",
    "Verify Inductive Reasoning", "Verify Deductive Reasoning",
    "Verify Mechanical Comprehension", "Verify Spatial Reasoning",
    "Verify Reading Comprehension", "Verify G+",
    "Global Skills Assessment", "GSA",
    "Leadership Report",
    "Automata", "Automata Pro", "Automata — Fix the Code",
    "Contact Center Simulation", "Financial Services Simulation",
    "Graduate 8.0", "Technology Professional 8.0",
    "Administrative Professional 8.0",
    "Java 8", "Core Java", "Python", "SQL", "JavaScript", "C#",
    "Microsoft Excel",
    "Data Analysis",
    "Dependability and Safety Instrument",
    "Workplace Personality Inventory II",
    "Customer Contact Styles Questionnaire",
    "Situational Judgement Test",
    "Entry Level Sales 7.1",
    "Numerical Reasoning", "Verbal Reasoning",
]


def extract_comparison_names(text: str) -> List[str]:
    """Extract assessment names from a comparison query."""
    found = []
    text_lower = text.lower()
    for name in KNOWN_ASSESSMENT_NAMES:
        if name.lower() in text_lower:
            found.append(name)
    # Deduplicate by normalizing OPQ variants
    if "OPQ32r" in found and "OPQ32" in found:
        found = [n for n in found if n != "OPQ"]
    return list(dict.fromkeys(found))  # preserve order, deduplicate


# ──────────────────────────────────────────────────────────────────
# Query builder from conversation
# ──────────────────────────────────────────────────────────────────

def build_retrieval_query(messages: List[Dict]) -> str:
    """Build a condensed search query from conversation history."""
    user_msgs = [m["content"] for m in messages if m.get("role") == "user"]
    if len(user_msgs) <= 2:
        return " ".join(user_msgs)
    # Use last 3 user messages for recency bias
    return " ".join(user_msgs[-3:])


# ──────────────────────────────────────────────────────────────────
# Handlers
# ──────────────────────────────────────────────────────────────────

def handle_clarify(messages: List[Dict], signals: Dict) -> ChatResponse:
    prompt = clarification_prompt(messages, signals)
    reply = call_llm(prompt, max_tokens=200)
    return ChatResponse(
        reply=reply,
        recommendations=[],
        end_of_conversation=False,
    )


def handle_recommend(messages: List[Dict]) -> ChatResponse:
    query = build_retrieval_query(messages)
    retrieved = retrieve(query, messages=messages, top_k=10)
    logger.info(f"Retrieved {len(retrieved)} docs for recommendation.")

    if not retrieved:
        return ChatResponse(
            reply="I couldn't find matching assessments in the SHL catalog for your requirements. Could you provide more details about the role and skills you need to assess?",
            recommendations=[],
            end_of_conversation=False,
        )

    prompt = recommendation_prompt(messages, retrieved)
    reply = call_llm(prompt, max_tokens=500)

    recs_raw = extract_recommendations_from_llm_reply(reply, retrieved)
    recs_valid, errors = validate_recommendations(recs_raw)

    if errors:
        logger.warning(f"Validation errors: {errors}")

    recs = [Recommendation(**r) for r in recs_valid]

    # Mark end of conversation if we committed to a shortlist
    eoc = len(recs) >= 1

    return ChatResponse(
        reply=reply,
        recommendations=recs,
        end_of_conversation=eoc,
    )


def handle_refine(messages: List[Dict]) -> ChatResponse:
    query = build_retrieval_query(messages)
    retrieved = retrieve(query, messages=messages, top_k=12)
    logger.info(f"Retrieved {len(retrieved)} docs for refinement.")

    prompt = refinement_prompt(messages, retrieved)
    reply = call_llm(prompt, max_tokens=500)

    recs_raw = extract_recommendations_from_llm_reply(reply, retrieved)
    recs_valid, errors = validate_recommendations(recs_raw)

    if errors:
        logger.warning(f"Refinement validation errors: {errors}")

    recs = [Recommendation(**r) for r in recs_valid]

    # Refinement also produces a committed shortlist → end_of_conversation
    eoc = len(recs) >= 1

    return ChatResponse(
        reply=reply,
        recommendations=recs,
        end_of_conversation=eoc,
    )


def handle_compare(messages: List[Dict], last_msg: str) -> ChatResponse:
    names = extract_comparison_names(last_msg)
    logger.info(f"Comparing assessments: {names}")

    comparison_items = retrieve_for_comparison(names) if names else []

    # Fallback to semantic search if name extraction failed
    if not comparison_items:
        query = build_retrieval_query(messages)
        comparison_items = retrieve(query, messages=messages, top_k=4)

    prompt = comparison_prompt(messages, comparison_items)
    reply = call_llm(prompt, max_tokens=600)

    # Comparisons don't produce a shortlist — user can follow up
    return ChatResponse(
        reply=reply,
        recommendations=[],
        end_of_conversation=False,
    )


def handle_off_topic() -> ChatResponse:
    return ChatResponse(
        reply=OFF_TOPIC_REFUSAL,
        recommendations=[],
        end_of_conversation=False,
    )


def handle_injection() -> ChatResponse:
    return ChatResponse(
        reply=INJECTION_REFUSAL,
        recommendations=[],
        end_of_conversation=False,
    )


def handle_max_turns() -> ChatResponse:
    """Called when the conversation hits the 8-message cap."""
    return ChatResponse(
        reply=MAX_TURNS_REPLY,
        recommendations=[],
        end_of_conversation=True,
    )


# ──────────────────────────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────────────────────────

def process_chat(messages: List[Dict]) -> ChatResponse:
    """
    Main agent pipeline.
    Takes full conversation history, returns next response.
    """
    logger.info(f"Processing chat with {len(messages)} messages.")

    # Hard turn cap: assignment spec says max 8 messages total.
    # If we're AT the cap, return graceful close instead of erroring.
    if len(messages) >= MAX_MESSAGES:
        logger.warning(f"Conversation at turn cap ({len(messages)} messages).")
        return handle_max_turns()

    # Classify intent
    classification = classify(messages)
    intent = classification["intent"]
    logger.info(
        f"Intent: {intent} | Score: {classification['context_score']} | "
        f"Turns: {classification['turn_count']} | Signals: {classification['signals']}"
    )

    # Route to handler
    if intent == "injection":
        response = handle_injection()

    elif intent == "off_topic":
        response = handle_off_topic()

    elif intent == "comparison":
        response = handle_compare(messages, classification["last_user_msg"])

    elif intent == "refinement":
        response = handle_refine(messages)

    elif intent == "vague":
        response = handle_clarify(messages, classification["signals"])

    else:  # intent == "ok"
        response = handle_recommend(messages)

    # Secondary end-of-conversation check (thanks/done signals from user)
    # Only override to True, never set to False (handle_recommend already sets True on shortlist)
    if not response.end_of_conversation:
        response.end_of_conversation = is_end_of_conversation(messages, response.reply)

    logger.info(
        f"Response: intent={intent}, recs={len(response.recommendations)}, "
        f"end={response.end_of_conversation}"
    )
    return response
