"""Deterministic disk cache for the evaluation sweep.

The evaluation engine is fully seeded: identical (seeds, thresholds) inputs produce
BYTE-IDENTICAL output. The default sweep (20 seeds x 3 thresholds x 2 systems) is
correct but expensive (~minutes) to compute per HTTP request, which makes the
Evaluation UI unusable in a live demo.

This module memoizes the REAL `run_sweep(...)` output for a given (seeds, thresholds)
key to a JSON file on disk. It does NOT fabricate, hardcode, or alter any number —
it stores exactly what the engine produced and returns it on a cache hit. A
`cache` provenance block is attached so the API/UI can disclose that a response was
served from a precomputed real run (with the git commit + timestamp it was computed at).

Non-default queries still compute live (deterministically). Only the known-expensive
default is precomputed.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from typing import Optional

from ariadne.eval.sweep import DEFAULT_SEEDS, run_sweep

# Cache lives under the repo (gitignored via web/.gitignore-style rules or the
# repo .gitignore); it is derived data, safe to delete and regenerate.
_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", ".eval_cache")
DEFAULT_THRESHOLDS = (0.55, 0.70, 0.85)


def _key(seeds: list[int], thresholds: tuple[float, ...]) -> str:
    raw = json.dumps({"seeds": sorted(seeds), "thresholds": sorted(thresholds)}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _cache_path(seeds: list[int], thresholds: tuple[float, ...]) -> str:
    return os.path.join(_CACHE_DIR, f"sweep-{_key(seeds, thresholds)}.json")


def _git_commit() -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=os.path.dirname(_CACHE_DIR),
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
    except Exception:
        return "unknown"


def get_sweep(
    seeds: Optional[list[int]] = None,
    thresholds: tuple[float, ...] = DEFAULT_THRESHOLDS,
    use_cache: bool = True,
) -> dict:
    """Return the real run_sweep output, served from a deterministic disk cache
    when available. On a cache miss it computes live, caches the real result, and
    returns it. Attaches a `cache` provenance block (never alters the numbers)."""
    seed_list = seeds if seeds is not None else DEFAULT_SEEDS
    path = _cache_path(seed_list, thresholds)

    if use_cache and os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        payload["cache"] = {
            "hit": True,
            "computed_at": payload.get("_computed_at"),
            "computed_commit": payload.get("_computed_commit"),
            "note": "served from a deterministic precomputed run (identical to a live sweep for the same seeds/thresholds)",
        }
        return payload

    # cache miss: compute the REAL sweep live (deterministic), then persist it.
    t0 = time.time()
    result = run_sweep(seeds=seed_list, thresholds=thresholds)
    elapsed = round(time.time() - t0, 2)
    result["_computed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime())
    result["_computed_commit"] = _git_commit()
    result["_compute_seconds"] = elapsed

    if use_cache:
        os.makedirs(_CACHE_DIR, exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(result, fh)
        os.replace(tmp, path)

    result["cache"] = {
        "hit": False,
        "computed_at": result["_computed_at"],
        "computed_commit": result["_computed_commit"],
        "compute_seconds": elapsed,
        "note": "computed live (deterministic) this request; subsequent identical requests are cached",
    }
    return result


def precompute_default() -> str:
    """Precompute + cache the default sweep. Returns the cache file path.
    Intended to run once at build/deploy time (or on server startup)."""
    get_sweep(seeds=None, thresholds=DEFAULT_THRESHOLDS, use_cache=True)
    return _cache_path(DEFAULT_SEEDS, DEFAULT_THRESHOLDS)


if __name__ == "__main__":
    p = precompute_default()
    print(f"precomputed default sweep -> {p}")
