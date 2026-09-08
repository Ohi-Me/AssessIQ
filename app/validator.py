"""
Response validator — enforces schema correctness and catalog-only URLs.
This is the last layer before returning to client.
"""

import re
from typing import List, Dict, Optional, Tuple
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

    catalog_names = {item.get("name", "").strip().lower() for item in get_catalog()}
    valid = []

    for i, rec in enumerate(recommendations):
        if not isinstance(rec, dict):
            errors.append(f"Item {i} is not a dict.")
            continue

        # Required fields
        name = rec.get("name", "").strip()
        url = (rec.get("url") or "").strip()
        test_type = rec.get("test_type", "").strip()

        if not name:
            errors.append(f"Item {i}: missing name.")
            continue

        # The assessment must exist in the catalog. This is the guarantee that
        # nothing invented reaches the client — it replaces the old check that
        # the URL belonged to one specific vendor's domain.
        if name.lower() not in catalog_names:
            errors.append(f"Item {i} ({name}): not in catalog — skipping.")
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


def _normalize(text: str) -> str:
    """Lowercase, unify dash variants and collapse whitespace, so a name still
    matches when the model writes 'Automata - Fix the Code'."""
    text = text.lower().replace("—", "-").replace("–", "-")
    return re.sub(r"\s+", " ", text)


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

    # Whole-name matching only. Word-level matching cannot work on this catalog:
    # many names end in "(New)", so "C# (New)" reduces to the single token
    # "(new)" and matched any reply that mentioned Python (New) — which is how a
    # C# test ended up recommended for a data engineer. "Java 8 (New)" likewise
    # matched on "java" borrowed from "Core Java". The prompt tells the model to
    # use exact names, and it does.
    reply_norm = _normalize(reply)

    matched = []
    for doc in retrieved_docs:
        name = doc.get("name", "")
        if name and _normalize(name) in reply_norm:
            matched.append(doc)

    # Drop names wholly contained in another match, so "Numerical Reasoning"
    # doesn't ride along when the model named "Verify Numerical Reasoning".
    names_norm = [_normalize(d.get("name", "")) for d in matched]
    scored = []
    for doc, this_name in zip(matched, names_norm):
        if any(this_name != other and this_name in other for other in names_norm):
            continue
        scored.append((doc, 2))

    # Present in relevance order, so displayed scores read as a ranking.
    scored.sort(key=lambda x: -(x[0].get("_score") or 0))

    reason_map = {
        "Core Java": "Evaluates Java fundamentals, OOP, collections, and backend programming skills.",
        "Java 8 (New)": "Assesses modern Java 8 concepts relevant for backend development.",
        "Verbal Reasoning": "Measures communication, comprehension, and reasoning ability.",
        "Verify Verbal Reasoning": "Measures workplace verbal reasoning and communication skills.",
        "OPQ32r": "Evaluates workplace personality traits, teamwork, and communication style.",
        "OPQ32": "Measures behavioral and personality characteristics relevant for teamwork.",
        "Global Skills Assessment (GSA)": "Provides broad evaluation of workplace and professional skills.",
    }

    def _reason_for(doc: Dict) -> Optional[str]:
        """Hand-written reason where we have one, else the catalog's own first
        sentence — better than shipping a recommendation with a blank reason."""
        mapped = reason_map.get(doc.get("name", ""))
        if mapped:
            return mapped
        desc = (doc.get("description") or "").strip()
        if not desc:
            return None
        first = desc.split(". ")[0].strip().rstrip(".")
        return f"{first}." if first else None

    for doc, match_score in scored:
        name = doc.get("name", "")
        if name in seen_names:
            continue
        seen_names.add(name)
        rec = {
            "name": name,
            "url": doc.get("url", ""),
            "test_type": doc.get("test_type", "A"),
            "reason": _reason_for(doc),
        }
        # Attach relevance score from retriever if available
        if doc.get("_score") is not None:
            rec["score"] = doc["_score"]
        recommendations.append(rec)
        if len(recommendations) >= 10:
            break

    # Deliberately no fallback to "just show the top retrieved docs". When the
    # agent asks a clarifying question it names no assessment, and attaching a
    # shortlist anyway produced replies that asked for more detail while
    # displaying recommendations underneath. It also broke the guarantee that
    # nothing is recommended unless the agent actually recommended it.
    if not recommendations:
        logger.info("Reply named no assessment — returning no recommendations.")

    return recommendations