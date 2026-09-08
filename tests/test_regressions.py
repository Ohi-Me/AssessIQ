"""
Regression tests.

Each test here corresponds to a bug that reached the deployed service and was
found by reading output by hand. They are deliberately cheap — no model, no API
keys — so they can gate every push.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.catalog_loader import get_catalog                      # noqa: E402
from app.guardrails import HAS_ROLE_PATTERNS, _matches_any      # noqa: E402
from app.retriever import extract_constraints                   # noqa: E402
from app.validator import (                                     # noqa: E402
    extract_recommendations_from_llm_reply,
    validate_recommendations,
)

CATALOG = get_catalog()
BY_NAME = {a["name"]: a for a in CATALOG}


def doc(name: str, score: float = 0.9) -> dict:
    item = dict(BY_NAME[name])
    item["_score"] = score
    return item


# ── Extraction ────────────────────────────────────────────────────────

def test_clarifying_question_yields_no_recommendations():
    """
    A reply asking which language the intern will use mentioned "Java" and
    "Python" in passing. Half-of-the-words matching turned those mentions into a
    shortlist, so the agent asked for more detail while displaying results.
    """
    reply = (
        "I need a bit more detail. Which primary programming language will the "
        "intern work with (e.g. Java, Python, C#)? Are you evaluating pure "
        "technical ability or general cognitive ability?"
    )
    retrieved = [doc("Java Programming Test"), doc("Python Programming Test"),
                 doc("C# and .NET Test")]
    assert extract_recommendations_from_llm_reply(reply, retrieved) == []


def test_only_named_assessments_are_returned():
    reply = ("I'd suggest the SQL and Database Test for query skills and the "
             "Python Programming Test for scripting.")
    retrieved = [doc("SQL and Database Test"), doc("Python Programming Test"),
                 doc("C# and .NET Test"), doc("Java Programming Test")]
    names = [r["name"] for r in extract_recommendations_from_llm_reply(reply, retrieved)]
    assert names == ["SQL and Database Test", "Python Programming Test"] or set(names) == {
        "SQL and Database Test", "Python Programming Test"}


def test_no_fallback_to_top_documents():
    """
    Nothing named means nothing recommended. The old fallback showed the top
    retrieved documents regardless, which broke the guarantee that the agent
    only recommends what it actually recommended.
    """
    retrieved = [doc("Java Programming Test"), doc("Debugging Simulation")]
    assert extract_recommendations_from_llm_reply("Could you tell me more?", retrieved) == []


def test_recommendations_sorted_by_score():
    """Results were ordered by match quality, so scores rendered out of order."""
    reply = ("Consider the Debugging Simulation, the Java Programming Test and "
             "the Graduate Aptitude Battery.")
    retrieved = [doc("Java Programming Test", 0.62),
                 doc("Graduate Aptitude Battery", 0.91),
                 doc("Debugging Simulation", 0.77)]
    scores = [r["score"] for r in extract_recommendations_from_llm_reply(reply, retrieved)]
    assert scores == sorted(scores, reverse=True)


def test_every_recommendation_has_a_reason():
    """Assessments missing from the hand-written reason map rendered blank."""
    reply = "The Cloud and DevOps Fundamentals Test would fit."
    recs = extract_recommendations_from_llm_reply(reply, [doc("Cloud and DevOps Fundamentals Test")])
    assert recs and all(r["reason"] for r in recs)


# ── Validation ────────────────────────────────────────────────────────

def test_validator_rejects_assessments_outside_the_catalog():
    valid, errors = validate_recommendations(
        [{"name": "Totally Invented Test", "url": "", "test_type": "K"}])
    assert valid == []
    assert errors


def test_validator_accepts_catalog_entries_without_a_url():
    """Entries carry no external URL; requiring one rejected the whole catalog."""
    valid, _ = validate_recommendations(
        [{"name": "Java Programming Test", "url": "", "test_type": "K"}])
    assert len(valid) == 1


# ── Constraint extraction ─────────────────────────────────────────────

@pytest.mark.parametrize("query", [
    "sde intern",
    "hiring a software engineering intern",
    "campus hiring for graduate engineers",
    "swe intern for backend",
])
def test_role_is_detected_for_engineering_titles(query):
    """
    A role is required before the agent will recommend. \\bengineer\\b matched
    neither "engineering" nor "engineers", and SDE/SWE were absent, so these
    queries returned nothing at all.
    """
    assert _matches_any(query, HAS_ROLE_PATTERNS), f"no role detected in {query!r}"


@pytest.mark.parametrize("query,expected", [
    ("Hiring an SDE intern for coding", "programming"),
    ("data engineer intern", "data engineering"),
    ("screening ML interns", "machine learning"),
])
def test_skill_categories_extracted(query, expected):
    assert expected in extract_constraints([{"role": "user", "content": query}])["skills"]


@pytest.mark.parametrize("text", [
    "available for training",
    "please email us",
    "maintain the chair",
])
def test_short_keywords_do_not_match_inside_words(text):
    """"ai" matched inside "available"/"email"/"maintain" as a bare substring."""
    skills = extract_constraints([{"role": "user", "content": text}])["skills"]
    assert "machine learning" not in skills


# ── Test-type coverage ────────────────────────────────────────────────

def test_multiple_requested_types_are_all_represented():
    """
    "mix of aptitude and coding" returned five ability tests and no coding test,
    because one strong cluster took every slot.
    """
    from app import retriever

    ranked = [(i, 1.0 - i * 0.02) for i, a in enumerate(CATALOG)
              if a["test_type"] in {"A", "K", "S"}]
    ranked.sort(key=lambda x: -x[1])
    retriever._catalog_items = CATALOG

    picked = retriever._cover_requested_types(ranked, ["A", "K", "S"], 5)
    types = {CATALOG[i]["test_type"] for i, _ in picked}
    assert len(types) >= 2, f"only {types} represented"


def test_single_requested_type_is_left_alone():
    from app import retriever

    retriever._catalog_items = CATALOG
    ranked = [(i, 1.0 - i * 0.01) for i in range(len(CATALOG))]
    assert retriever._cover_requested_types(ranked, ["A"], 5) == ranked[:5]
