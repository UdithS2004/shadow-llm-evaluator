"""Async-safe metrics collection for shadow-mode LLM comparisons."""

import asyncio
from typing import Any


class MetricsStore:
    """Tracks comparison results and candidate failures."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self.total_comparisons = 0
        self.matches = 0
        self.mismatches = 0
        self.candidate_failures = 0

    async def record_match(self) -> None:
        async with self._lock:
            self.total_comparisons += 1
            self.matches += 1

    async def record_mismatch(self) -> None:
        async with self._lock:
            self.total_comparisons += 1
            self.mismatches += 1

    async def record_candidate_failure(self) -> None:
        async with self._lock:
            self.candidate_failures += 1

    async def snapshot(self) -> dict[str, Any]:
        async with self._lock:
            if self.total_comparisons == 0:
                match_rate = 100.0
            else:
                match_rate = self.matches / self.total_comparisons * 100

            return {
                "total_comparisons": self.total_comparisons,
                "matches": self.matches,
                "mismatches": self.mismatches,
                "candidate_failures": self.candidate_failures,
                "match_rate_percent": round(match_rate, 2),
            }

    async def reset(self) -> None:
        async with self._lock:
            self.total_comparisons = 0
            self.matches = 0
            self.mismatches = 0
            self.candidate_failures = 0


metrics = MetricsStore()