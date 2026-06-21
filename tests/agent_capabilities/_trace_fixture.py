from __future__ import annotations

from functools import lru_cache
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "official_cases"
LARGE_CASE = DATA / "large_seed301.txt"


@lru_cache(maxsize=1)
def large_trace():
    from tools.agent_trace_demo import generate_trace

    return generate_trace(LARGE_CASE, ROOT / "solver.py")
