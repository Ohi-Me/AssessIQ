"""
Retrieval quality tests.
Validate that retriever finds expected assessments for known queries.
"""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import subprocess
catalog_path = Path(__file__).parent.parent / "data" / "catalog.json"
if not catalog_path.exists():
    subprocess.run([sys.executable, "scripts/scrape_catalog.py", "--use-fallback"])

from app.catalog_loader import load_catalog
from app.retriever import retrieve, ensure_indexes

# Setup
catalog = load_catalog()
ensure_indexes(catalog)


def get_names(results):
    return [r["name"] for r in results]


# ──────────────────────────────────────────────────────────────────
# Recall tests
# ──────────────────────────────────────────────────────────────────

def test_java_developer_retrieval():
    """Java developer query should retrieve Java-related assessments."""
    results = retrieve("mid-level Java developer backend engineer", top_k=10)
    names = get_names(results)
    print(f"\nJava dev results: {names}")
    java_tests = [n for n in names if "java" in n.lower() or "Java" in n]
    assert len(java_tests) >= 1, f"Expected Java tests in results, got: {names}"


def test_personality_retrieval():
    """Personality query should retrieve OPQ and similar."""
    results = retrieve("personality assessment behavior traits", top_k=10)
    names = get_names(results)
    print(f"\nPersonality results: {names}")
    personality = [n for n in names if any(k in n.lower() for k in ["opq", "personality", "motivat"])]
    assert len(personality) >= 1, f"Expected personality tests, got: {names}"


def test_cognitive_retrieval():
    """Cognitive ability query should retrieve Verify tests."""
    results = retrieve("cognitive ability reasoning numerical verbal", top_k=10)
    names = get_names(results)
    print(f"\nCognitive results: {names}")
    cognitive = [n for n in names if any(k in n.lower() for k in ["verify", "reasoning", "numerical", "verbal"])]
    assert len(cognitive) >= 1, f"Expected cognitive tests, got: {names}"


def test_leadership_retrieval():
    """Leadership query should retrieve management assessments."""
    results = retrieve("senior manager leadership executive", top_k=10)
    names = get_names(results)
    print(f"\nLeadership results: {names}")
    leadership = [n for n in names if any(k in n.lower() for k in ["leader", "manager", "opq", "global"])]
    assert len(leadership) >= 1, f"Expected leadership tests, got: {names}"


def test_customer_service_retrieval():
    """Customer service query should retrieve relevant assessments."""
    results = retrieve("customer service representative contact center", top_k=10)
    names = get_names(results)
    print(f"\nCustomer service results: {names}")
    cs_tests = [n for n in names if any(k in n.lower() for k in ["customer", "contact", "service"])]
    assert len(cs_tests) >= 1, f"Expected customer service tests, got: {names}"


def test_python_data_scientist():
    """Python/data science query should retrieve relevant tests."""
    results = retrieve("python data scientist machine learning analytics", top_k=10)
    names = get_names(results)
    print(f"\nPython/DS results: {names}")
    tech = [n for n in names if any(k in n.lower() for k in ["python", "data", "sql"])]
    assert len(tech) >= 1, f"Expected technical tests, got: {names}"


def test_recall_at_10_java_stakeholder():
    """
    Simulate evaluation trace: Java developer with stakeholder communication.
    Expected relevant: Java 8, Core Java, OPQ32r (for stakeholder communication), Verify Numerical.
    """
    query = "mid-level Java developer who works with stakeholders around 4 years experience"
    messages = [{"role": "user", "content": query}]
    results = retrieve(query, messages=messages, top_k=10)
    names = get_names(results)
    print(f"\nJava + stakeholder results: {names}")

    relevant_expected = ["Java 8 (New)", "Core Java", "OPQ32r", "OPQ32"]
    found = [r for r in relevant_expected if any(r.lower() in n.lower() for n in names)]
    recall = len(found) / len(relevant_expected)
    print(f"Recall@10: {recall:.2f} ({len(found)}/{len(relevant_expected)})")
    assert recall >= 0.5, f"Recall too low: {recall:.2f}. Found: {found}"


def test_no_hallucinated_urls():
    """All retrieved items must have real SHL URLs."""
    from app.catalog_loader import get_catalog_urls
    catalog_urls = get_catalog_urls()

    results = retrieve("software developer assessment", top_k=10)
    for item in results:
        assert item["url"] in catalog_urls, f"Non-catalog URL: {item['url']}"
        assert "shl.com" in item["url"]


if __name__ == "__main__":
    print("Running retrieval quality tests...\n")
    tests = [
        test_java_developer_retrieval,
        test_personality_retrieval,
        test_cognitive_retrieval,
        test_leadership_retrieval,
        test_customer_service_retrieval,
        test_python_data_scientist,
        test_recall_at_10_java_stakeholder,
        test_no_hallucinated_urls,
    ]
    for fn in tests:
        try:
            fn()
            print(f"✅ {fn.__name__}")
        except AssertionError as e:
            print(f"❌ {fn.__name__}: {e}")
        except Exception as e:
            print(f"💥 {fn.__name__}: {type(e).__name__}: {e}")
