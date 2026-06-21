# =============================================================================
# solver_v3.py  --  solver_v2 + trusted self-evolved ranking candidates
# -----------------------------------------------------------------------------
# Same public contract as solver.py / solver_v2.py:
#       solve(input_text: str) -> list[(task_id_list_str, [courier_id, ...]), ...]
# Single-purpose, stdlib only, <=10s/case. The ONLINE path here NEVER calls an
# LLM and NEVER generates code — it only *consumes* heuristics that were already
# discovered, AST-audited, and held-out-validated by the OFFLINE evolution loop
# (autosolver_agent/llm_evolution.py via autosolver/offline/reevo_runner_v2.py).
#
# WHAT solver_v3 ADDS vs solver_v2 (and WHY it can never regress)
#   1. It runs the full solver_v2 pipeline unchanged to produce the production
#      answer `base` (the strong multi-stage LNS/MCF/column-search solver).
#   2. It ALSO loads any *trusted, promoted* evolved ranking heuristics from
#         autosolver/offline/evolved/manifest.json
#      Each such strategy is a tiny stdlib-only module exposing the frozen
#      interface  propose(candidates, all_tasks, deadline, helpers). Before it is
#      ever executed online it is re-checked against the SAME AST safety gate used
#      offline (no os/sys/socket/subprocess, no open/exec/eval/compile, no
#      unbounded `while`, exact propose signature). A strategy that fails the gate
#      is silently skipped — the online path degrades to pure solver_v2.
#   3. Each trusted strategy's output is scored with the EXACT canonical objective
#      (_solution_expected_cost, identical to competition_audit.solution_expected_cost)
#      and added to the candidate pool. solver_v3 returns argmin over
#      { solver_v2 answer } ∪ { trusted evolved candidates }.
#
#   Because the final pick is argmin on the exact cost, solver_v3's cost is
#   <= solver_v2's cost on every instance: the evolved candidates can only ever
#   *replace* the base answer when they are provably cheaper, never make it worse.
#   If the manifest is missing/empty (no promoted strategy yet) solver_v3 == v2.
#
# Time safety: the evolved candidates are O(rows log rows) greedy passes guarded
#   by a hard internal sub-deadline (~0.6s total), so they cannot threaten the
#   10s budget; solver_v2 already self-limits to ~8.7s.
# =============================================================================
from __future__ import annotations

import ast
import importlib.util
import inspect
import json
import time
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Optional

_ROOT = Path(__file__).resolve().parent
_MANIFEST = _ROOT / "autosolver" / "offline" / "evolved" / "manifest.json"

# ---- Frozen AST safety gate (mirrors autosolver_agent.evolution, duplicated
# here so the ONLINE solver stays a single self-contained stdlib file with no
# dependency on the offline package). Same allow/block lists. ----------------
_ALLOWED_IMPORTS = {"collections", "heapq", "itertools", "math", "random", "time"}
_BLOCKED_CALLS = {"compile", "eval", "exec", "globals", "locals", "open", "__import__"}
_BLOCKED_ATTR_ROOTS = {"os", "pathlib", "socket", "subprocess", "sys"}
_REQUIRED_SIG = ["candidates", "all_tasks", "deadline", "helpers"]

# Hard wall on time spent running ALL evolved candidates combined.
_EVOLVED_TIME_BUDGET_S = 0.6


def _unsafe_reason(tree: ast.AST) -> Optional[str]:
    for node in ast.walk(tree):
        if isinstance(node, ast.While):
            return "unsafe loop: while"
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom) and node.module == "__future__":
                continue
            names = [alias.name.split(".", 1)[0] for alias in getattr(node, "names", [])]
            if isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module.split(".", 1)[0])
            for name in names:
                if name not in _ALLOWED_IMPORTS:
                    return f"unsafe import: {name}"
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in _BLOCKED_CALLS:
                return f"unsafe call: {func.id}"
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id in _BLOCKED_ATTR_ROOTS:
                return f"unsafe attribute call: {func.value.id}.{func.attr}"
    return None


def _load_trusted_propose(path: Path) -> Optional[Callable]:
    """Re-audit (AST gate + signature) and sandbox-import a trusted evolved
    strategy. Returns its propose() or None if anything is off — the online path
    must never trust a file blindly, even one we wrote ourselves offline."""
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        if _unsafe_reason(tree) is not None:
            return None
        spec = importlib.util.spec_from_file_location(f"solver_v3_evolved_{path.stem}", str(path))
        if spec is None or spec.loader is None:
            return None
        module: ModuleType = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        propose = getattr(module, "propose", None)
        if not callable(propose):
            return None
        if list(inspect.signature(propose).parameters) != _REQUIRED_SIG:
            return None
        return propose
    except Exception:
        return None


def _load_trusted_strategies() -> list[tuple[str, Callable]]:
    """Read the offline evolution manifest and return [(strategy_id, propose)]
    for every promoted strategy that still passes the safety gate."""
    if not _MANIFEST.exists():
        return []
    try:
        entries = json.loads(_MANIFEST.read_text(encoding="utf-8") or "[]")
    except Exception:
        return []
    out: list[tuple[str, Callable]] = []
    seen: set[str] = set()
    for entry in entries:
        sid = entry.get("strategy_id")
        file = entry.get("file")
        if not sid or not file or sid in seen:
            continue
        path = Path(file)
        if not path.is_absolute():
            path = _ROOT / path
        if not path.exists():
            continue
        propose = _load_trusted_propose(path)
        if propose is not None:
            out.append((sid, propose))
            seen.add(sid)
    return out


# ---- Parse + objective: imported from solver_v2 so cost is byte-identical ---
def _load_solver_v2() -> ModuleType:
    import sys

    name = "solver_v2_for_v3"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, str(_ROOT / "solver_v2.py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _parse_candidates(input_text: str) -> tuple[list[tuple], set[str]]:
    """Reproduce solver_v2's parse exactly: rows are
    (task_key, task_ids_tuple, courier_id, score, willingness, row_index)."""
    lines = input_text.strip().splitlines()
    start = 1 if lines and lines[0].startswith("task_id_list") else 0
    candidates: list[tuple] = []
    all_tasks: set[str] = set()
    for row_index, raw in enumerate(lines[start:]):
        line = raw.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        task_key, courier_id, score_text, will_text = parts[:4]
        task_key = task_key.strip()
        courier_id = courier_id.strip()
        task_ids = tuple(t.strip() for t in task_key.split(",") if t.strip())
        if not task_ids or not courier_id:
            continue
        try:
            score = float(score_text)
            will = float(will_text)
        except ValueError:
            continue
        candidates.append((task_key, task_ids, courier_id, score, will, row_index))
        all_tasks.update(task_ids)
    return candidates, all_tasks


def _normalize(solution: Any) -> Optional[list[tuple[str, list[str]]]]:
    """Validate the shape of an evolved candidate's output before scoring."""
    if not isinstance(solution, list):
        return None
    out: list[tuple[str, list[str]]] = []
    for item in solution:
        if not (isinstance(item, tuple) and len(item) == 2):
            return None
        task_key, couriers = item
        if not isinstance(task_key, str) or not isinstance(couriers, list):
            return None
        if not all(isinstance(c, str) for c in couriers):
            return None
        out.append((task_key, list(couriers)))
    return out


def solve(input_text):
    """solver_v2 answer ∪ trusted evolved candidates, argmin by exact cost."""
    v2 = _load_solver_v2()
    # 1) production answer from the full v2 pipeline (unchanged).
    base = v2.solve(input_text)

    candidates, all_tasks = _parse_candidates(input_text)
    if not candidates:
        return base

    cost_fn = v2._solution_expected_cost
    best = base
    try:
        best_cost = cost_fn(base, candidates, all_tasks)
    except Exception:
        return base

    # 2) trusted evolved candidates as ADDITIONAL options (never replacements
    #    unless strictly cheaper on the exact objective).
    trusted = _load_trusted_strategies()
    if not trusted:
        return base

    helpers = {
        "time_left": lambda target_deadline: max(0.0, target_deadline - time.monotonic()),
        "task_count": len(all_tasks),
        "courier_count": len({r[2] for r in candidates}),
    }
    hard_stop = time.monotonic() + _EVOLVED_TIME_BUDGET_S
    for _sid, propose in trusted:
        if time.monotonic() >= hard_stop:
            break
        sub_deadline = min(hard_stop, time.monotonic() + 0.25)
        try:
            raw = propose(list(candidates), set(all_tasks), sub_deadline, helpers)
        except Exception:
            continue
        sol = _normalize(raw)
        if sol is None:
            continue
        try:
            cost = cost_fn(sol, candidates, all_tasks)
        except Exception:
            continue
        if cost < best_cost - 1e-9:
            best, best_cost = sol, cost

    return best
