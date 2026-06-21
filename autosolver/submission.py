from __future__ import annotations

from autosolver.competition import solve as solve_competition
from autosolver.main import solve


def run(raw_input, time_budget=10.0):
    if isinstance(raw_input, str):
        return solve_competition(raw_input, time_budget=time_budget)
    return solve(raw_input, time_budget=time_budget, debug=False)
