"""
Per-stage timing for the request pipeline.

The agent has four stages with very different cost profiles — classification is
regex work, retrieval is an embedding plus two searches, generation is a network
call to an LLM. Without per-stage numbers there is no way to know which one to
optimise, so every stage is timed and the breakdown travels with the response.
"""

import time
from contextlib import contextmanager
from typing import Dict, Iterator, List

from loguru import logger


class StageTimer:
    """Collects elapsed milliseconds per named stage for a single request."""

    def __init__(self) -> None:
        self._timings: Dict[str, float] = {}
        self._start = time.perf_counter()

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        started = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000
            # A stage can run more than once per request (retrieval during a
            # comparison, for example); accumulate rather than overwrite.
            self._timings[name] = round(self._timings.get(name, 0.0) + elapsed_ms, 1)

    def record(self, name: str, elapsed_ms: float) -> None:
        self._timings[name] = round(self._timings.get(name, 0.0) + elapsed_ms, 1)

    @property
    def total_ms(self) -> float:
        return round((time.perf_counter() - self._start) * 1000, 1)

    def as_dict(self) -> Dict[str, float]:
        out = dict(self._timings)
        out["total"] = self.total_ms
        return out

    def log(self, intent: str = "") -> None:
        parts = " ".join(f"{k}={v}ms" for k, v in sorted(self._timings.items()))
        logger.info(f"timings intent={intent or 'n/a'} {parts} total={self.total_ms}ms")


def percentile(values: List[float], pct: float) -> float:
    """Nearest-rank percentile. Small sample sizes here, so no interpolation."""
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = max(0, min(len(ordered) - 1, int(round(pct / 100 * len(ordered) + 0.5)) - 1))
    return round(ordered[idx], 1)
