from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from autosolver import accurate_evaluator, adapter, controller, formatter, validator
from autosolver.candidate_gen import generate_candidates
from autosolver.column_solver import solve_columns
from autosolver.competition import solve as solve_competition
from autosolver.fallback import FallbackChain
from autosolver.fast_evaluator import fast_evaluate
from autosolver.greedy import greedy_marginal
from autosolver.objective import better
from autosolver.strategies import choose_strategy


def solve(raw_input, time_budget=10.0, debug=False):
    if isinstance(raw_input, str):
        return solve_competition(raw_input, time_budget=time_budget)
    overall_deadline = time.monotonic() + time_budget * 0.95
    fallback = FallbackChain()
    instance = None
    try:
        instance = adapter.adapt(raw_input)
    except Exception:
        return _emergency_raw_output(raw_input)

    try:
        candidates = generate_candidates(instance, time_budget=min(1.0, max(0.05, time_budget * 0.15)))
        strategy = choose_strategy(instance, time_budget=time_budget)
        if strategy == 'column_then_lns':
            baseline = solve_columns(candidates, instance, time_budget=min(1.0, max(0.05, time_budget * 0.20)))
        else:
            baseline = greedy_marginal(candidates, instance, time_budget=min(0.5, max(0.05, time_budget * 0.10)))
        if not baseline or validator.validate(formatter.format_solution(baseline, instance), instance):
            baseline = fallback.fallback_1_top_p(instance)
        improved, trace = controller.solve(
            instance,
            candidates,
            baseline,
            remaining_time=max(0.0, overall_deadline - time.monotonic() - 0.2),
            debug=debug,
        )
        final = improved if better(fast_evaluate(improved, instance), fast_evaluate(baseline, instance), instance) else baseline
        if time.monotonic() < overall_deadline - 0.05:
            accurate = accurate_evaluator.accurate_evaluate(final, instance, n_simulations=500)
            if not accurate.feasible:
                final = baseline
        violations = validator.validate(formatter.format_solution(final, instance), instance)
        if violations:
            final = fallback.fallback_2_greedy(instance)
        output = formatter.format_solution(final, instance, mode='debug' if debug else 'submit')
        if debug:
            output.setdefault('debug', {})['strategy'] = strategy
            output.setdefault('debug', {})['trace'] = trace
        return output
    except Exception:
        try:
            solution = fallback.fallback_2_greedy(instance)
        except Exception:
            try:
                solution = fallback.fallback_1_top_p(instance)
            except Exception:
                solution = fallback.fallback_0_reject_all(instance)
        return formatter.format_solution(solution, instance, mode='submit')


def _emergency_raw_output(raw_input):
    return {'assignments': [], 'rejected': [raw.get('order_id') or raw.get('id') for raw in raw_input.get('orders', [])]}


def _read_json(path: str | None):
    text = Path(path).read_text(encoding='utf-8') if path else sys.stdin.read()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _read_input(path: str | None):
    if path:
        return _read_json(path)
    return _read_json(None)


def _write_json(data, path: str | None) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if path:
        Path(path).write_text(text + '\n', encoding='utf-8')
    else:
        print(text)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Run AutoSolver on a JSON instance or competition TSV candidate file.')
    parser.add_argument('--input', '-i', help='input JSON/TSV path; defaults to stdin')
    parser.add_argument('--output', '-o', help='output JSON path; defaults to stdout')
    parser.add_argument('--time-budget', '-t', type=float, default=10.0)
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args(argv)
    raw_input = _read_input(args.input)
    output = solve(raw_input, time_budget=args.time_budget, debug=args.debug)
    _write_json(output, args.output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
