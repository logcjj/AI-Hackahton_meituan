#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import time
from collections import Counter
from pathlib import Path
from types import ModuleType
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "official_cases"

STRATEGY_FUNCTIONS = {
    "_solve_tiny_column_search",
    "_solve_single_task_multidispatch",
    "_solve_disjoint_then_multidispatch",
    "_solve_pair_potential_matching",
    "_solve_sparse_cover",
    "_solve_low_column_search",
    "_solve_low_global_column_search",
    "_random_single_start_solution",
    "_fallback_official_greedy",
    "_solve_scarce_k2_column_search",
    "_solve_scarce_bundle_mcf_enum",
    "_solve_scarce_bundle_group_mcf_enum",
    "_solve_scarce_elite_column_recombine",
}

IMPROVER_FUNCTIONS = {
    "_local_improve_mixed_solution",
    "_improve_pair_rewires",
    "_improve_single_pair_merges",
    "_improve_covered_bundle_merges",
    "_reassign_mixed_solution",
    "_reassign_single_solution",
    "_rebalance_single_solution",
    "_low_worst_window_repair_solution",
    "_low_deep_window_repair_solution",
    "_low_late_acceptance_repair_solution",
    "_shift_couriers_between_groups",
    "_normal_worst_related_repair_solution",
    "_repair_worst_window_solution",
    "_column_alns_repair_solution",
}

MEMORY_FUNCTIONS = {
    "_scarce_seed401_cached_solution",
    "_small_seed100_cached_solution",
    "_medium_output_upgrade",
    "_high_output_upgrade",
    "_large302_output_upgrade",
}

CRITIC_FUNCTIONS = {
    "_solution_expected_cost",
    "_solution_expected_cost_by_model",
}


def load_solver(path: Path) -> ModuleType:
    raw = path.read_bytes()
    module_name = "trace_solver_" + hashlib.sha1(raw).hexdigest()[:12]
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load solver from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "solve"):
        raise AttributeError(f"{path} has no solve(input_text) function")
    return module


def parse_candidates(text: str) -> tuple[list[tuple[str, tuple[str, ...], str, float, float, int]], set[str]]:
    lines = text.strip().splitlines()
    start = 1 if lines and lines[0].startswith("task_id_list") else 0
    candidates: list[tuple[str, tuple[str, ...], str, float, float, int]] = []
    all_tasks: set[str] = set()
    for row_index, raw in enumerate(lines[start:]):
        parts = raw.strip().split("\t")
        if len(parts) < 4:
            continue
        task_key, courier_id, score_text, willingness_text = parts[:4]
        task_ids = tuple(item.strip() for item in task_key.split(",") if item.strip())
        if not task_ids or not courier_id.strip():
            continue
        try:
            score = float(score_text)
            willingness = float(willingness_text)
        except ValueError:
            continue
        candidates.append((task_key.strip(), task_ids, courier_id.strip(), score, willingness, row_index))
        all_tasks.update(task_ids)
    return candidates, all_tasks


def infer_regime(candidates: list[tuple[str, tuple[str, ...], str, float, float, int]], all_tasks: set[str]) -> str:
    if not candidates:
        return "empty"
    task_count = len(all_tasks)
    courier_count = len({row[2] for row in candidates})
    avg_w = sum(row[4] for row in candidates) / len(candidates)
    singles = [row for row in candidates if len(row[1]) == 1]
    avg_single_w = sum(row[4] for row in singles) / len(singles) if singles else avg_w
    scarce = courier_count <= task_count
    low_willingness = avg_w < 0.27 and not scarce and task_count == 30 and courier_count >= 50 and avg_single_w < 0.25
    if task_count <= 8:
        return "tiny"
    if low_willingness:
        return "low-willingness"
    if scarce:
        return "scarce"
    if task_count <= 15:
        return "small"
    if task_count >= 40:
        return "large"
    return "medium"


def summarize_solution(
    solution: list[tuple[str, list[str]]],
    candidates: list[tuple[str, tuple[str, ...], str, float, float, int]],
    all_tasks: set[str],
    proxy_score: float,
) -> dict[str, Any]:
    rows = {(row[0], row[2]): row for row in candidates}
    used_couriers: set[str] = set()
    covered_tasks: set[str] = set()
    invalid_reasons: list[str] = []
    riders_per_group = Counter()
    tasks_per_group = Counter()
    for task_key, couriers in solution:
        group_rows = []
        for courier_id in couriers:
            row = rows.get((task_key, courier_id))
            if row is None:
                invalid_reasons.append(f"missing row {task_key}/{courier_id}")
                continue
            if courier_id in used_couriers:
                invalid_reasons.append(f"duplicate courier {courier_id}")
            used_couriers.add(courier_id)
            group_rows.append(row)
        if not group_rows:
            invalid_reasons.append(f"empty or invalid group {task_key}")
            continue
        group_tasks = group_rows[0][1]
        riders_per_group[len(group_rows)] += 1
        tasks_per_group[len(group_tasks)] += 1
        for task_id in group_tasks:
            if task_id in covered_tasks:
                invalid_reasons.append(f"duplicate task {task_id}")
            covered_tasks.add(task_id)
    return {
        "groups": len(solution),
        "used_couriers": len(used_couriers),
        "covered_tasks": len(covered_tasks),
        "total_tasks": len(all_tasks),
        "uncovered_tasks": sorted(all_tasks - covered_tasks),
        "valid": not invalid_reasons and math.isfinite(proxy_score),
        "invalid_reasons": invalid_reasons,
        "proxy_score": proxy_score,
        "riders_per_group": dict(sorted(riders_per_group.items())),
        "tasks_per_group": dict(sorted(tasks_per_group.items())),
    }


def _category(name: str) -> str:
    if name in STRATEGY_FUNCTIONS:
        return "strategy"
    if name in IMPROVER_FUNCTIONS:
        return "improver"
    if name in MEMORY_FUNCTIONS:
        return "memory"
    if name in CRITIC_FUNCTIONS:
        return "critic"
    return "other"


def instrument_solver(module: ModuleType, event_limit: int = 400) -> tuple[list[dict[str, Any]], Counter[str], dict[str, Counter[str]]]:
    events: list[dict[str, Any]] = []
    category_counts: Counter[str] = Counter()
    function_counts: dict[str, Counter[str]] = {
        "strategy": Counter(),
        "improver": Counter(),
        "memory": Counter(),
        "critic": Counter(),
    }
    names = STRATEGY_FUNCTIONS | IMPROVER_FUNCTIONS | MEMORY_FUNCTIONS | CRITIC_FUNCTIONS

    def make_wrapper(name: str, func: Callable[..., Any]) -> Callable[..., Any]:
        category = _category(name)

        def wrapped(*args: Any, **kwargs: Any) -> Any:
            start = time.monotonic()
            category_counts[category] += 1
            function_counts.setdefault(category, Counter())[name] += 1
            try:
                result = func(*args, **kwargs)
                ok = True
                return result
            finally:
                elapsed_ms = round((time.monotonic() - start) * 1000.0, 3)
                if len(events) < event_limit and category != "critic":
                    events.append(
                        {
                            "index": len(events),
                            "name": name,
                            "category": category,
                            "elapsed_ms": elapsed_ms,
                            "ok": ok if "ok" in locals() else False,
                        }
                    )

        wrapped.__name__ = getattr(func, "__name__", name)
        return wrapped

    for name in names:
        func = getattr(module, name, None)
        if callable(func):
            setattr(module, name, make_wrapper(name, func))
    return events, category_counts, function_counts


def generate_trace(input_path: str | Path, solver_path: str | Path = ROOT / "solver.py") -> dict[str, Any]:
    input_path = Path(input_path)
    solver_path = Path(solver_path)
    text = input_path.read_text(encoding="utf-8")
    candidates, all_tasks = parse_candidates(text)
    module = load_solver(solver_path)
    original_score = getattr(module, "_solution_expected_cost")
    events, category_counts, function_counts = instrument_solver(module)
    available_strategy_functions = sorted(name for name in STRATEGY_FUNCTIONS if callable(getattr(module, name, None)))
    available_improver_functions = sorted(name for name in IMPROVER_FUNCTIONS if callable(getattr(module, name, None)))
    available_memory_functions = sorted(name for name in MEMORY_FUNCTIONS if callable(getattr(module, name, None)))
    start = time.monotonic()
    solution = module.solve(text)
    wall_time_s = time.monotonic() - start
    proxy_score = float(original_score(solution, candidates, sorted(all_tasks)))
    solution_summary = summarize_solution(solution, candidates, all_tasks, proxy_score)
    features = {
        "tasks": len(all_tasks),
        "couriers": len({row[2] for row in candidates}),
        "rows": len(candidates),
        "avg_willingness": round(sum(row[4] for row in candidates) / len(candidates), 6) if candidates else 0.0,
        "has_bundles": any(len(row[1]) > 1 for row in candidates),
    }
    return {
        "input_path": str(input_path),
        "solver_path": str(solver_path),
        "regime": infer_regime(candidates, all_tasks),
        "features": features,
        "wall_time_s": round(wall_time_s, 6),
        "solution": solution_summary,
        "summary": {
            "available_strategy_functions": available_strategy_functions,
            "available_improver_functions": available_improver_functions,
            "available_memory_functions": available_memory_functions,
            "strategy_calls": dict(sorted(function_counts["strategy"].items())),
            "improver_calls": dict(sorted(function_counts["improver"].items())),
            "memory_calls": dict(sorted(function_counts["memory"].items())),
            "critic_evaluations": int(category_counts["critic"]),
            "recorded_events": len(events),
        },
        "events": events,
    }


def trace_to_markdown(trace: dict[str, Any]) -> str:
    solution = trace["solution"]
    lines = [
        "# AutoSolver Agent Trace",
        "",
        f"- Input: `{trace['input_path']}`",
        f"- Regime: `{trace['regime']}`",
        f"- Wall time: `{trace['wall_time_s']:.3f}s`",
        f"- Local trace cost (not official): `{solution['proxy_score']:.2f}`",
        f"- Coverage: `{solution['covered_tasks']}/{solution['total_tasks']}`",
        f"- Valid: `{solution['valid']}`",
        "",
        "## Function Calls",
        "",
    ]
    for title, key in (("Strategy", "strategy_calls"), ("Improver", "improver_calls"), ("Memory", "memory_calls")):
        lines.append(f"### {title}")
        calls = trace["summary"][key]
        if not calls:
            lines.append("- None")
        else:
            for name, count in calls.items():
                lines.append(f"- `{name}`: {count}")
        lines.append("")
    lines.extend(["## Timeline", ""])
    for event in trace["events"][:80]:
        lines.append(f"- {event['index']:03d} `{event['category']}` `{event['name']}` {event['elapsed_ms']}ms")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate an external trace for solver.py without modifying it.")
    parser.add_argument("input", nargs="?", default=str(DATA_DIR / "large_seed301.txt"))
    parser.add_argument("--solver", default=str(ROOT / "solver.py"))
    parser.add_argument("--json-output")
    parser.add_argument("--markdown")
    args = parser.parse_args(argv)
    trace = generate_trace(args.input, args.solver)
    payload = json.dumps(trace, ensure_ascii=False, indent=2)
    if args.json_output:
        Path(args.json_output).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    if args.markdown:
        Path(args.markdown).write_text(trace_to_markdown(trace), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
