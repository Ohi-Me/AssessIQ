"""
Scores retrieval against the labelled set in evals/retrieval_set.json.

Only the retriever is evaluated. Generation is excluded deliberately: it is
non-deterministic and needs API keys, which would make the numbers unrepeatable
and stop this running in CI. Everything measured here is deterministic, so a
regression shows up as a number moving rather than as someone noticing a bad
result by eye.

Run:     python scripts/evaluate.py
CI gate: python scripts/evaluate.py --min-recall-at-5 0.75
"""

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.catalog_loader import load_catalog   # noqa: E402
from app.retriever import ensure_indexes, retrieve   # noqa: E402

EVAL_PATH = Path(__file__).parent.parent / "evals" / "retrieval_set.json"


def recall_at_k(ranked: List[str], relevant: set, k: int) -> float:
    if not relevant:
        return 0.0
    return len(set(ranked[:k]) & relevant) / len(relevant)


def precision_at_k(ranked: List[str], relevant: set, k: int) -> float:
    if k == 0:
        return 0.0
    return len(set(ranked[:k]) & relevant) / k


def reciprocal_rank(ranked: List[str], relevant: set) -> float:
    for i, name in enumerate(ranked, start=1):
        if name in relevant:
            return 1.0 / i
    return 0.0


def ndcg_at_k(ranked: List[str], relevant: set, k: int) -> float:
    """Binary-relevance nDCG."""
    dcg = sum(
        1.0 / math.log2(i + 1)
        for i, name in enumerate(ranked[:k], start=1)
        if name in relevant
    )
    ideal = sum(1.0 / math.log2(i + 1) for i in range(1, min(len(relevant), k) + 1))
    return dcg / ideal if ideal else 0.0


def evaluate(verbose: bool = True) -> Dict[str, float]:
    catalog = load_catalog()
    ensure_indexes(catalog)

    catalog_names = {a["name"] for a in catalog}
    data = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
    cases = data["queries"]

    # A label naming an assessment that no longer exists would silently deflate
    # every score, so fail loudly instead.
    for case in cases:
        unknown = set(case["relevant"]) - catalog_names
        if unknown:
            raise SystemExit(f"Unknown assessment(s) in eval set: {sorted(unknown)}")

    r5, r10, p5, mrr, ndcg = [], [], [], [], []

    for case in cases:
        query = case["query"]
        relevant = set(case["relevant"])
        results = retrieve(query, messages=[{"role": "user", "content": query}], top_k=10)
        ranked = [r["name"] for r in results]

        case_r5 = recall_at_k(ranked, relevant, 5)
        r5.append(case_r5)
        r10.append(recall_at_k(ranked, relevant, 10))
        p5.append(precision_at_k(ranked, relevant, 5))
        mrr.append(reciprocal_rank(ranked, relevant))
        ndcg.append(ndcg_at_k(ranked, relevant, 10))

        if verbose:
            missed = relevant - set(ranked[:5])
            flag = "   " if case_r5 >= 0.5 else " ! "
            print(f"{flag}R@5={case_r5:.2f}  {query}")
            if missed:
                print(f"        missed in top 5: {', '.join(sorted(missed))}")

    metrics = {
        "queries": len(cases),
        "recall@5": round(sum(r5) / len(r5), 4),
        "recall@10": round(sum(r10) / len(r10), 4),
        "precision@5": round(sum(p5) / len(p5), 4),
        "mrr": round(sum(mrr) / len(mrr), 4),
        "ndcg@10": round(sum(ndcg) / len(ndcg), 4),
    }

    if verbose:
        print("\n" + "-" * 46)
        for key, value in metrics.items():
            print(f"  {key:<14} {value}")
        print("-" * 46)

    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-recall-at-5", type=float, default=None,
                        help="Exit non-zero if mean Recall@5 falls below this.")
    parser.add_argument("--json", action="store_true", help="Emit metrics as JSON only.")
    args = parser.parse_args()

    metrics = evaluate(verbose=not args.json)

    if args.json:
        print(json.dumps(metrics, indent=2))

    if args.min_recall_at_5 is not None and metrics["recall@5"] < args.min_recall_at_5:
        print(
            f"\nFAIL: recall@5 {metrics['recall@5']} below threshold "
            f"{args.min_recall_at_5}",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
