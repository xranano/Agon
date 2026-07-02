"""On-disk memoization for evaluation-time LLM grading calls.

Grading calls (improvement-rate pairwise comparisons, fidelity scoring, persona-
convergence checks) are deterministic given the same prompt, but re-running
``python -m evaluation.metrics`` during development would otherwise re-spend
money on identical calls every time. This cache keys on a hash of the exact
prompt text and persists to disk so it survives across process runs. Safe to
call concurrently from a thread pool.
"""

from __future__ import annotations

import hashlib
import json
import threading
from typing import Any

from config import RESULTS_DIR

CACHE_PATH = RESULTS_DIR / ".cache" / "eval_llm_cache.json"

_lock = threading.Lock()
_cache: dict[str, Any] | None = None


def _load() -> dict[str, Any]:
    global _cache
    if _cache is None:
        _cache = json.loads(CACHE_PATH.read_text(encoding="utf-8")) if CACHE_PATH.exists() else {}
    return _cache


def cache_key(*parts: str) -> str:
    return hashlib.sha256("||".join(parts).encode("utf-8")).hexdigest()


def get(key: str) -> Any | None:
    with _lock:
        return _load().get(key)


def put(key: str, value: Any) -> None:
    with _lock:
        cache = _load()
        cache[key] = value
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")
