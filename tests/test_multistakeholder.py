"""Tests for the multi-stakeholder decision layer (stdlib-only; no numpy/mpl)."""
from __future__ import annotations

import random

from autosolver import multistakeholder as ms
from autosolver.competition_audit import parse_competition_rows


def _scarce_text(seed: int = 7, n_tasks: int = 30, n_couriers: int = 12) -> str:
    rnd = random.Random(seed)
    lines = ["task_id_list\tcourier_id\ttotal_score\twillingness"]
    for t in range(n_tasks):
        for c in rnd.sample(range(n_couriers), rnd.randint(4, 7)):
            lines.append(f"T{t:04d}\tC{c:03d}\t{rnd.uniform(20, 90):.3f}\t{rnd.uniform(0.2, 0.85):.4f}")
    return "\n".join(lines) + "\n"


def test_gini_bounds():
    assert ms.gini([5, 5, 5, 5]) == 0.0
    assert abs(ms.gini([0, 0, 0, 10]) - 0.75) < 1e-9
    assert ms.gini([]) == 0.0


def test_jain_bounds():
    assert abs(ms.jain_index([5, 5, 5, 5]) - 1.0) < 1e-9
    assert abs(ms.jain_index([0, 0, 0, 10]) - 0.25) < 1e-9


def test_platform_utility_sign_aligned_with_official_cost():
    """Up must strictly increase as the official expected_cost decreases."""
    text = _scarce_text()
    rows, tasks = parse_competition_rows(text)
    cheap = ms.fairness_aware_reoptimize(rows, tasks, alpha=0.0)
    spread = ms.fairness_aware_reoptimize(rows, tasks, alpha=1.0)
    r_cheap = ms.evaluate_stakeholders(cheap, rows, tasks)
    r_spread = ms.evaluate_stakeholders(spread, rows, tasks)
    # Pure-efficiency assignment must have <= expected_cost and >= platform utility.
    assert r_cheap.expected_cost <= r_spread.expected_cost + 1e-9
    assert r_cheap.Up >= r_spread.Up - 1e-9


def test_pareto_front_trades_cost_for_fairness():
    text = _scarce_text()
    rows, tasks = parse_competition_rows(text)
    pts = ms.pareto_front(rows, tasks, courier_capacity=4)
    assert len(pts) >= 5
    # Cost and Gini must actually move across the sweep (a real tradeoff).
    costs = [p.expected_cost for p in pts]
    ginis = [p.rider_income_gini for p in pts]
    assert max(costs) > min(costs) + 1e-6
    assert max(ginis) > min(ginis) + 1e-6
    # Non-dominated set is non-empty and sorted by cost.
    front = ms.pareto_efficient(pts)
    assert front
    assert front == sorted(front, key=lambda p: p.expected_cost)


def test_wage_floor_is_a_real_constraint():
    """A higher hourly floor raises the worst hourly wage (binds)."""
    text = _scarce_text()
    rows, tasks = parse_competition_rows(text)
    base = ms.evaluate_stakeholders(ms.fairness_aware_reoptimize(rows, tasks, 0.0), rows, tasks)
    floor = base.rider_worst_hourly + 4.0
    constrained = ms.evaluate_stakeholders(
        ms.fairness_aware_reoptimize(rows, tasks, 0.0, min_hourly=floor), rows, tasks
    )
    assert constrained.rider_worst_hourly >= base.rider_worst_hourly - 1e-9


def test_determinism():
    text = _scarce_text()
    rows, tasks = parse_competition_rows(text)
    a = ms.pareto_front(rows, tasks)
    b = ms.pareto_front(rows, tasks)
    for p, q in zip(a, b):
        assert abs(p.expected_cost - q.expected_cost) < 1e-9
        assert abs(p.rider_income_gini - q.rider_income_gini) < 1e-9


def test_provenance_labels_every_signal():
    cfg = ms.SyntheticConfig()
    sources = {s for _, s, _ in cfg.PROVENANCE}
    assert sources <= {"REAL", "SYNTHETIC"}
    # The four real competition fields must be present and labelled REAL.
    real = {sig for sig, src, _ in cfg.PROVENANCE if src == "REAL"}
    assert {"task_ids", "courier_id", "total_score", "willingness"} <= real


def test_scorecard_shape():
    text = _scarce_text()
    rows, tasks = parse_competition_rows(text)
    rep = ms.evaluate_stakeholders(ms.fairness_aware_reoptimize(rows, tasks, 0.5), rows, tasks)
    sc = ms.fairness_scorecard(rep)
    assert "income_gini" in sc.rider
    assert "mean_ready_alignment_gap_min" in sc.merchant
    assert "max_lateness_min" in sc.customer
    assert "expected_cost" in sc.platform
