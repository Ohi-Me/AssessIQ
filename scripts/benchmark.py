"""
Measures retrieval latency, cold vs warm cache.

Generation is excluded on purpose: it is a network call to a third-party API,
so its latency says more about the provider than about this system. What is
measurable here is everything the service itself controls — query expansion,
embedding, BM25 and FAISS search, fusion, metadata boosting and type coverage.

Run:  python scripts/benchmark.py
"""

import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.catalog_loader import load_catalog          # noqa: E402
from app.metrics import percentile                   # noqa: E402
from app.retriever import (                           # noqa: E402
    cache_stats,
    clear_caches,
    ensure_indexes,
    retrieve,
)

QUERIES = [
    "Hiring an SDE intern - need to test coding and problem solving",
    "Screening AI/ML interns for Python and data skills",
    "data engineer intern",
    "Campus hiring for graduate engineers, mix of aptitude and coding",
    "Need a personality test for a sales manager role",
    "Backend developer with SQL and API experience",
    "Graduate scheme, verbal and numerical reasoning",
    "DevOps engineer, cloud and CI/CD",
]

REPEATS = 5


def time_one(query: str) -> float:
    started = time.perf_counter()
    retrieve(query, messages=[{"role": "user", "content": query}], top_k=10)
    return (time.perf_counter() - started) * 1000


def run(label: str, cold: bool) -> list:
    samples = []
    for _ in range(REPEATS):
        for q in QUERIES:
            if cold:
                clear_caches()
            samples.append(time_one(q))
    print(f"\n{label}")
    print(f"  n        {len(samples)}")
    print(f"  mean     {statistics.mean(samples):.1f} ms")
    print(f"  p50      {percentile(samples, 50):.1f} ms")
    print(f"  p95      {percentile(samples, 95):.1f} ms")
    print(f"  min/max  {min(samples):.1f} / {max(samples):.1f} ms")
    return samples


def main() -> None:
    catalog = load_catalog()
    ensure_indexes(catalog)
    print(f"catalog: {len(catalog)} assessments")

    # One untimed pass so model load and lazy imports don't land in the numbers.
    for q in QUERIES:
        time_one(q)

    cold = run("cold cache (embedding recomputed every call)", cold=True)
    clear_caches()
    for q in QUERIES:  # populate
        time_one(q)
    warm = run("warm cache (embedding memoized)", cold=False)

    cold_p50 = percentile(cold, 50)
    warm_p50 = percentile(warm, 50)
    if warm_p50 > 0:
        print(f"\np50 speedup: {cold_p50 / warm_p50:.1f}x  ({cold_p50} ms -> {warm_p50} ms)")
    print(f"embedding cache: {cache_stats()}")


if __name__ == "__main__":
    main()
