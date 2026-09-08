"""
Response validator — enforces schema correctness and catalog-only URLs.
This is the last layer before returning to client.
"""

import re
from typing import List, Dict, Tuple
from loguru import logger

from app.catalog_loader import get_catalog_urls, get_catalog


def validate_recommendations(recommendations: List[Dict]) -> Tuple[List[Dict], List[str]]:
    """
    Validate recommendation list.
    Returns (valid_recs, error_messages).
    """
    errors = []

    if not isinstance(recommendations, list):
        return [], ["recommendations must be a list"]

    if len(recommendations) > 10:
        errors.append(f"Too many recommendations: {len(recommendations)} > 10. Truncating.")
        recommendations = recommendations[:10]

    catalog_urls = get_catalog_urls()
    valid = []

    for i, rec in enumerate(recommendations):
        if not isinstance(rec, dict):
            errors.append(f"Item {i} is not a dict.")
            continue

        # Required fields
        name = rec.get("name", "").strip()
        url = rec.get("url", "").strip()
        test_type = rec.get("test_type", "").strip()

        if not name:
            errors.append(f"Item {i}: missing name.")
            continue

        if not url:
            errors.append(f"Item {i} ({name}): missing URL.")
            continue

        # URL must be from the catalog
        if url not in catalog_urls:
            # Try to find correct URL from catalog
            correct_url = _find_url_by_name(name)
            if correct_url:
                logger.warning(f"Corrected URL for '{name}': {url} → {correct_url}")
                url = correct_url
            else:
                errors.append(f"Item {i} ({name}): URL not in catalog — skipping.")
                continue

        if not test_type:
            # Try to infer from catalog
            test_type = _get_test_type_by_name(name) or "A"

        validated = {"name": name, "url": url, "test_type": test_type}

        # Pass through optional enrichment fields
        if rec.get("reason"):
            validated["reason"] = str(rec["reason"])[:300]  # truncate safety
        if rec.get("score") is not None:
            validated["score"] = round(float(rec["score"]), 3)

        valid.append(validated)

    return valid, errors


def _find_url_by_name(name: str) -> str | None:
    """Find catalog URL by assessment name (fuzzy)."""
    catalog = get_catalog()
    name_lower = name.lower()
    # Exact match first
    for item in catalog:
        if item["name"].lower() == name_lower:
            return item["url"]
    # Partial match
    for item in catalog:
        if name_lower in item["name"].lower() or item["name"].lower() in name_lower:
            return item["url"]
    return None


def _get_test_type_by_name(name: str) -> str | None:
    catalog = get_catalog()
    name_lower = name.lower()
    for item in catalog:
        if item["name"].lower() == name_lower or name_lower in item["name"].lower():
            return item.get("test_type")
    return None


def extract_recommendations_from_llm_reply(
    reply: str,
    retrieved_docs: List[Dict],
) -> List[Dict]:
    """
    Parse LLM reply to extract which assessments it recommended,
    then build proper recommendation objects from catalog data.

    Strategy:
    1. Find assessment names mentioned in reply
    2. Match to retrieved_docs (catalog items)
    3. Return properly structured recommendations
    """
    recommendations = []
    seen_names = set()

    # Score each retrieved doc by how much its name appears in the reply
    reply_lower = reply.lower()

    scored = []
    for doc in retrieved_docs:
        name = doc.get("name", "")
        name_lower = name.lower()

        # Exact name match
        if name_lower in reply_lower:
            scored.append((doc, 2))
            continue

        # Partial word match (key words of the name)
        words = [w for w in name_lower.split() if len(w) > 3]
        matches = sum(1 for w in words if w in reply_lower)
        if matches >= max(1, len(words) // 2):
            scored.append((doc, 1))

    # Sort by score desc, then by original order
    scored.sort(key=lambda x: -x[1])

    reason_map = {
        "Core Java": "Evaluates Java fundamentals, OOP, collections, and backend programming skills.",
        "Java 8 (New)": "Assesses modern Java 8 concepts relevant for backend development.",
        "Verbal Reasoning": "Measures communication, comprehension, and reasoning ability.",
        "Verify Verbal Reasoning": "Measures workplace verbal reasoning and communication skills.",
        "OPQ32r": "Evaluates workplace personality traits, teamwork, and communication style.",
        "OPQ32": "Measures behavioral and personality characteristics relevant for teamwork.",
        "Global Skills Assessment (GSA)": "Provides broad evaluation of workplace and professional skills.",
    }

    for doc, match_score in scored:
        name = doc.get("name", "")
        if name in seen_names:
            continue
        seen_names.add(name)
        rec = {
            "name": name,
            "url": doc.get("url", ""),
            "test_type": doc.get("test_type", "A"),
            "reason": reason_map.get(name),
        }
        # Attach relevance score from retriever if available
        if doc.get("_score") is not None:
            rec["score"] = doc["_score"]
        recommendations.append(rec)
        if len(recommendations) >= 10:
            break

    # If nothing matched from reply, fall back to top retrieved docs
    if not recommendations and retrieved_docs:
        logger.warning("No recommendations extracted from reply — using top retrieved docs")
        for doc in retrieved_docs[:5]:
            name = doc.get("name", "")
            if name not in seen_names:
                seen_names.add(name)
                rec = {
                    "name": name,
                    "url": doc.get("url", ""),
                    "test_type": doc.get("test_type", "A"),
                    "reason": reason_map.get(name),
                }
                if doc.get("_score") is not None:
                    rec["score"] = doc["_score"]
                recommendations.append(rec)

    return recommendations