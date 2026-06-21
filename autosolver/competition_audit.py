from __future__ import annotations

import importlib.util
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Iterable


@dataclass(frozen=True)
class CompetitionRow:
    task_key: str
    task_ids: tuple[str, ...]
    courier_id: str
    total_score: float
    willingness: float
    row_index: int


def parse_competition_rows(input_text: str) -> tuple[dict[tuple[str, str], CompetitionRow], set[str]]:
    lines = input_text.strip().splitlines()
    start = 1 if lines and lines[0].startswith("task_id_list") else 0
    rows: dict[tuple[str, str], CompetitionRow] = {}
    tasks: set[str] = set()
    for row_index, raw_line in enumerate(lines[start:]):
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        task_key, courier_id, score_text, willingness_text = parts[:4]
        task_key = task_key.strip()
        courier_id = courier_id.strip()
        task_ids = tuple(task.strip() for task in task_key.split(",") if task.strip())
        if not task_ids or not courier_id:
            continue
        row = CompetitionRow(
            task_key=task_key,
            task_ids=task_ids,
            courier_id=courier_id,
            total_score=float(score_text),
            willingness=float(willingness_text),
            row_index=row_index,
        )
        rows[(task_key, courier_id)] = row
        tasks.update(task_ids)
    return rows, tasks


def group_expected_cost(group_rows: Iterable[CompetitionRow], task_count: int) -> float:
    rows = list(group_rows)
    if not rows:
        return 100.0 * task_count
    expected = 0.0
    for mask in range(1 << len(rows)):
        probability = 1.0
        accepted_score = 0.0
        accepted_count = 0
        for index, row in enumerate(rows):
            if mask & (1 << index):
                probability *= row.willingness
                accepted_score += row.total_score
                accepted_count += 1
            else:
                probability *= 1.0 - row.willingness
        if accepted_count:
            expected += probability * (accepted_score / accepted_count)
        else:
            expected += probability * (100.0 * task_count)
    return expected


def solution_expected_cost(solution, rows: dict[tuple[str, str], CompetitionRow], all_tasks: set[str]) -> float:
    used_couriers: set[str] = set()
    covered_tasks: set[str] = set()
    total = 0.0
    for task_key, couriers in solution:
        group_rows = []
        for courier_id in couriers:
            row = rows.get((task_key, courier_id))
            if row is None or courier_id in used_couriers:
                return float("inf")
            used_couriers.add(courier_id)
            group_rows.append(row)
        if not group_rows:
            return float("inf")
        for task_id in group_rows[0].task_ids:
            if task_id in covered_tasks:
                return float("inf")
            covered_tasks.add(task_id)
        total += group_expected_cost(group_rows, len(group_rows[0].task_ids))
    total += 100.0 * (len(all_tasks) - len(covered_tasks))
    return total


def result_signature(solution) -> tuple[tuple[str, tuple[str, ...]], ...]:
    return tuple(sorted((task_key, tuple(sorted(couriers))) for task_key, couriers in solution))


def result_metrics(solution, rows: dict[tuple[str, str], CompetitionRow], all_tasks: set[str]) -> dict:
    used_couriers: set[str] = set()
    covered_tasks: set[str] = set()
    tasks_per_group = Counter()
    riders_per_group = Counter()
    invalid_reasons = []
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
        group_tasks = group_rows[0].task_ids
        tasks_per_group[len(group_tasks)] += 1
        riders_per_group[len(group_rows)] += 1
        for task_id in group_tasks:
            if task_id in covered_tasks:
                invalid_reasons.append(f"duplicate task {task_id}")
            covered_tasks.add(task_id)
    expected_cost = solution_expected_cost(solution, rows, all_tasks)
    return {
        "valid": not invalid_reasons and expected_cost != float("inf"),
        "invalid_reasons": invalid_reasons,
        "expected_cost": expected_cost,
        "covered_tasks": len(covered_tasks),
        "uncovered_tasks": len(all_tasks - covered_tasks),
        "groups": len(solution),
        "used_couriers": len(used_couriers),
        "tasks_per_group": dict(sorted(tasks_per_group.items())),
        "riders_per_group": dict(sorted(riders_per_group.items())),
        "signature": result_signature(solution),
    }


def load_solver_module(path: str | Path) -> ModuleType:
    solver_path = Path(path)
    module_name = f"competition_audit_solver_{abs(hash(str(solver_path.resolve())))}"
    spec = importlib.util.spec_from_file_location(module_name, solver_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load solver from {solver_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "solve"):
        raise AttributeError(f"{solver_path} has no solve(input_text) function")
    return module


def summarize_solver(path: str | Path, input_text: str) -> dict:
    rows, tasks = parse_competition_rows(input_text)
    module = load_solver_module(path)
    solution = module.solve(input_text)
    metrics = result_metrics(solution, rows, tasks)
    metrics["path"] = str(path)
    return metrics


def compare_solver_outputs(baseline_path: str | Path, candidate_path: str | Path, input_text: str) -> dict:
    baseline = summarize_solver(baseline_path, input_text)
    candidate = summarize_solver(candidate_path, input_text)
    return {
        "baseline": baseline,
        "candidate": candidate,
        "same_signature": baseline["signature"] == candidate["signature"],
        "delta_expected_cost": candidate["expected_cost"] - baseline["expected_cost"],
        "delta_covered_tasks": candidate["covered_tasks"] - baseline["covered_tasks"],
    }


def json_ready(value):
    if isinstance(value, tuple):
        return [json_ready(item) for item in value]
    if isinstance(value, list):
        return [json_ready(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    return value


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Compare two AutoSolver solver.py-style files on one TSV input.")
    parser.add_argument("baseline")
    parser.add_argument("candidate")
    parser.add_argument("input_file")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    input_text = Path(args.input_file).read_text(encoding="utf-8")
    comparison = compare_solver_outputs(args.baseline, args.candidate, input_text)
    payload = json.dumps(json_ready(comparison), ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
