from __future__ import annotations

import time

from autosolver.fast_evaluator import fast_evaluate
from autosolver.lns import improve as lns_improve
from autosolver.objective import better, objective
from autosolver.solve_trace import SolveTrace


def solve(instance, candidates, baseline, remaining_time=1.0, debug=False):
    trace = SolveTrace()
    deadline = time.monotonic() + max(0.0, remaining_time)
    baseline_eval = fast_evaluate(baseline, instance)
    best = list(baseline or [])
    best_eval = baseline_eval
    trace.add('controller_start', candidates=len(candidates), baseline_objective=objective(baseline_eval, instance))

    if time.monotonic() < deadline and remaining_time > 0.05:
        lns_budget = max(0.01, min(remaining_time * 0.8, deadline - time.monotonic()))
        candidate_solution = lns_improve(instance, candidates, best, time_budget=lns_budget, trace=trace)
        candidate_eval = fast_evaluate(candidate_solution, instance)
        if better(candidate_eval, best_eval, instance):
            best = candidate_solution
            best_eval = candidate_eval
            trace.add('controller_accept_lns', objective=objective(best_eval, instance))
        else:
            trace.add('controller_keep_baseline', objective=objective(best_eval, instance))

    trace.add('controller_done', final_objective=objective(best_eval, instance), final_expected_accepts=best_eval.expected_accepts)
    return best, trace.to_dict()
