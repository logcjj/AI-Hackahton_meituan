# =============================================================================
# solver_v6.py  --  solver_v4 with a TIGHTENED wall-clock ceiling (timing margin)
# -----------------------------------------------------------------------------
# Identical algorithm / public contract / no-regression structure as solver_v4.py.
# The ONLY change vs solver_v4.py is the timing safety budget, per the R5 perf
# audit (tools/perf_audit_v4.py): v4's worst observed wall time was 9.09s on a
# scarce instance (only 0.91s under the 10s judge cap, and 0.09s OVER its own
# nominal 9.0s soft deadline because operators overrun their time slice under
# GC/scheduling jitter). v6 pulls the global ceiling 9.0 -> 8.6s and tightens the
# two generic-tail operator gates (so the true wall stays < ~8.75s even under
# jitter), restoring a clean ~1.4s buffer below 10s.
#
# WHY 8.6s (and NOT 8.3-8.5s): solver_v2's own base search self-limits on ITS OWN
# monotonic clock to ~8.7-8.85s; cutting the wrapper to 8.3-8.5s clips that base
# search mid-flight and causes real cost regressions (+10..+54 on genuinely hard
# scarce instances). 8.6s is the measured "knee": worst wall ~8.58s with near-zero
# quality loss (7/8 hard scarce instances cost-identical to the 9.0s setting).
# The no-regression guarantee below is UNAFFECTED: the final pick is still an
# exact-cost argmin with `base` always in the pool, so v6_exact <= its v3 base on
# every instance; a tighter budget only means *less extra polish*, never a worse
# answer than base.
# -----------------------------------------------------------------------------
# (original solver_v4 header preserved below)
# solver_v4.py  --  solver_v3 + leftover-budget targeted polish for scarce / low
# -----------------------------------------------------------------------------
# Same public contract as solver.py / solver_v2.py / solver_v3.py:
#       solve(input_text: str) -> list[(task_id_list_str, [courier_id, ...]), ...]
# Single file, stdlib only, <=10s/case. NEVER calls an LLM / generates code.
#
# WHY v4 CAN NEVER REGRESS vs v3 (structural no-regression guarantee)
#   1. v4 first runs the FULL solver_v3 pipeline (which itself already runs the
#      full solver_v2 pipeline and takes argmin over { v2 answer } u { trusted
#      evolved candidates }). That answer is `base`.
#   2. v4 then spends ONLY the wall-clock time still left under a hard 9.6s
#      global deadline running EXTRA targeted neighbourhood-search polish, and
#      every accepted move is gated by a strict improvement on the EXACT
#      canonical objective (solver_v2._solution_expected_cost, byte-identical to
#      competition_audit.solution_expected_cost). v4 returns argmin-by-exact-cost
#      over { base } u { polished variants }.
#   Because the final pick is argmin on the exact cost and `base` is always in
#   the pool, v4's exact cost is <= v3's exact cost on EVERY instance. The extra
#   passes can only ever *replace* base when provably cheaper, never make it
#   worse. If there is no leftover budget, v4 == v3 (returns base unchanged).
#
# WHAT THE EXTRA POLISH TARGETS (the R2 weak regimes: scarce / low_willingness)
#   v3's scarce / low final pick goes through robust tie-break selectors
#   (_pick_low_robust_best can return a solution up to +25 above the exact-cost
#   minimum when it is more robust across cost models). v4 therefore (a) re-takes
#   a pure exact-cost argmin of the candidates v3 already produced is NOT possible
#   from outside, so instead it (b) drives additional EXACT-cost-monotone search
#   from `base`:
#       - extra deep window LNS (more windows, larger top-rider pools, max_k up to 5)
#       - scarce bundle-insertion repair with more windows
#       - pairwise + triple column exchange with more pairs/triples
#       - reassign / rebalance / shift-couriers / eject-extra local search
#       - a fresh elite-column-recombine seeded from `base`
#   All of these are reused verbatim from solver_v2 (so they are already audited
#   and time-guarded), wrapped here in a strict exact-cost acceptance loop with a
#   conservative per-call sub-deadline so they cannot threaten the 10s budget.
# =============================================================================
from __future__ import annotations

import importlib.util
import time
from pathlib import Path
from types import ModuleType

_ROOT = Path(__file__).resolve().parent

# Hard global wall-clock ceiling for the WHOLE solve() (v3 + extra polish).
# v2 self-limits to ~8.7-8.85s; we keep a safety margin under the 10s judge cap.
# R5 perf-audit fix: tightened 9.0 -> 8.6s. Worst observed wall time drops from
# 8.98-9.09s (v4) to ~8.58s, restoring a ~1.4s buffer below the 10s cap, with
# 7/8 hard scarce instances cost-identical to the 9.0s setting.
_GLOBAL_DEADLINE_S = 8.6

# Audit hook: the most recent solve()'s internal v3 base answer + its exact cost.
# Used only by the no-regression test harness; never affects the returned answer.
_LAST_BASE = None
_LAST_BASE_COST = None


def _load_module(filename: str, alias: str) -> ModuleType:
    import sys

    if alias in sys.modules:
        return sys.modules[alias]
    spec = importlib.util.spec_from_file_location(alias, str(_ROOT / filename))
    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    spec.loader.exec_module(module)
    return module


def _parse_candidates(input_text):
    """Reproduce solver_v2's parse exactly: rows are
    (task_key, task_ids_tuple, courier_id, score, willingness, row_index)."""
    lines = input_text.strip().splitlines()
    start = 1 if lines and lines[0].startswith("task_id_list") else 0
    candidates = []
    all_tasks = set()
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


def _detect_regime(candidates, all_tasks):
    """Mirror solver_v2.solve's classifier vars relevant to scarce / low. Returns
    (is_scarce, is_low, is_low_courier_rich). These pick the extra-polish recipe;
    a misclassification can only waste a little leftover time, never regress (the
    exact-cost argmin keeps `base`)."""
    if not candidates:
        return False, False, False
    singles = [r for r in candidates if len(r[1]) == 1]
    courier_count = len({r[2] for r in candidates})
    n_tasks = len(all_tasks)
    avg_will = sum(r[4] for r in candidates) / len(candidates)
    avg_single_will = (sum(r[4] for r in singles) / len(singles)) if singles else avg_will
    is_scarce = courier_count <= n_tasks  # G
    is_low = avg_will < 0.27  # F
    is_low_courier_rich = (
        is_low and not is_scarce and courier_count >= n_tasks * 3 // 2
        and courier_count >= 24 and avg_single_will < 0.25
    )  # J
    return is_scarce, is_low, is_low_courier_rich


def _extra_polish(v2, base, base_cost, candidates, all_tasks, deadline,
                  is_scarce, is_low, is_low_courier_rich):
    """Drive additional EXACT-cost-monotone neighbourhood search from `base`.
    Returns (best, best_cost) with best_cost <= base_cost guaranteed (we only
    ever accept a strictly-cheaper exact cost; `base` is the fallback)."""
    cost_fn = v2._solution_expected_cost
    cov_fn = v2._solution_covered_count
    best, best_cost = base, base_cost
    now = time.monotonic

    def try_replace(cand, require_cover=False):
        nonlocal best, best_cost
        if not cand:
            return
        try:
            if require_cover and cov_fn(cand, candidates) < cov_fn(best, candidates):
                return
            c = cost_fn(cand, candidates, all_tasks)
        except Exception:
            return
        if c < best_cost - 1e-9:
            best, best_cost = cand, c

    # Budget guard: each operator gets a slice but never past the global deadline.
    def slice_to(seconds):
        return min(deadline, now() + seconds)

    # --- LOW-WILLINGNESS COURIER-RICH: deeper robust window repair, but accepted
    #     only on strict EXACT-cost improvement (stricter than v3's robust pick). -
    if is_low_courier_rich or is_low:
        if now() < deadline - 0.9:
            cand = v2._low_deep_window_repair_solution(best, candidates, all_tasks, slice_to(1.1))
            try_replace(cand)
        if now() < deadline - 0.7:
            cand = v2._low_late_acceptance_repair_solution(best, candidates, all_tasks, slice_to(0.8))
            try_replace(cand)
        if now() < deadline - 0.5:
            cand = v2._low_worst_window_repair_solution(best, candidates, all_tasks, slice_to(0.6))
            try_replace(cand)
        if now() < deadline - 0.3:
            cand = v2._shift_couriers_between_groups(best, candidates, all_tasks, slice_to(0.28), max_moves=40)
            try_replace(cand)

    # --- SCARCE (courier-constrained): more bundle-insertion windows, deeper
    #     column-exchange, eject-extra, elite recombine seeded from base. --------
    if is_scarce:
        # If the v3 base finished with comfortable leftover budget, it may have
        # taken an unlucky fast search path (v3 is intrinsically time-gated and
        # nondeterministic on tight-scarce). Run FRESH global scarce searches
        # (independent of base) and argmin them in -- this both improves the
        # lucky case and rescues an unlucky base, never worsening (exact argmin).
        if now() < deadline - 1.4:
            fresh = v2._solve_scarce_bundle_group_mcf_enum(candidates, all_tasks, slice_to(0.9))
            if fresh:
                fresh = v2._scarce_polish_candidate(fresh, candidates, all_tasks, slice_to(0.45))
                try_replace(fresh)
        if now() < deadline - 1.2:
            fresh2 = v2._solve_scarce_bundle_mcf_enum(candidates, all_tasks, slice_to(0.8))
            try_replace(fresh2)
        if now() < deadline - 1.0:
            cand = v2._scarce_bundle_insertion_repair_solution(
                best, candidates, all_tasks, slice_to(0.9),
                max_windows=80, max_window_tasks=16)
            try_replace(cand)
        if now() < deadline - 0.6:
            cand = v2._column_alns_repair_solution(
                best, candidates, all_tasks, slice_to(0.65), mode="scarce",
                max_window_tasks=14, top_riders_per_task_key=10, option_limit=70, max_k=5)
            try_replace(cand)
        if now() < deadline - 0.45:
            cand = v2._pairwise_column_exchange_solution(
                best, candidates, all_tasks, slice_to(0.4),
                top_riders_per_task_key=10, max_k=5, option_limit=70,
                max_window_tasks=12, max_pairs=40)
            try_replace(cand, require_cover=True)
        if now() < deadline - 0.4:
            cand = v2._triple_column_exchange_solution(
                best, candidates, all_tasks, slice_to(0.35),
                top_riders_per_task_key=10, max_k=5, option_limit=75,
                max_window_tasks=14, max_triples=22)
            try_replace(cand, require_cover=True)
        if now() < deadline - 0.3:
            cand = v2._scarce_eject_extra_to_uncovered(best, candidates, all_tasks, slice_to(0.25))
            try_replace(cand)
        if now() < deadline - 0.25:
            cand = v2._shift_couriers_between_groups(best, candidates, all_tasks, slice_to(0.22), max_moves=30)
            try_replace(cand)
        if now() < deadline - 0.9:
            recomb = v2._solve_scarce_elite_column_recombine(
                candidates, all_tasks, [best], slice_to(0.85))
            if recomb:
                recomb = v2._scarce_polish_candidate(recomb, candidates, all_tasks, slice_to(0.4))
                try_replace(recomb)

    # --- GENERIC EXACT-cost-monotone tail (helps every regime, incl. scarce/low
    #     and the trap_* dimension-matched ones): reassign + a final polish. ----
    # R5 perf-audit hardening: gate the last two generic-tail operators on a
    # wider margin (-0.45) and a smaller slice (0.15) so their inner loops cannot
    # overshoot the tightened ceiling under GC/scheduling jitter. Combined with
    # _GLOBAL_DEADLINE_S=8.6 this bounds the true wall to < ~8.75s.
    if now() < deadline - 0.45:
        cand = v2._reassign_mixed_solution(best, candidates, all_tasks, slice_to(0.15))
        try_replace(cand)
    if now() < deadline - 0.45:
        cand = v2._local_improve_mixed_solution(best, candidates, all_tasks, slice_to(0.15), include_pair_rewire=True)
        try_replace(cand)

    return best, best_cost


def solve(input_text):
    """v3 answer, then leftover-budget exact-cost-monotone polish for scarce/low.
    Returns argmin-by-exact-cost over { v3 answer } u { polished variants }."""
    start = time.monotonic()
    deadline = start + _GLOBAL_DEADLINE_S

    v3 = _load_module("solver_v3.py", "solver_v3_for_v4")
    base = v3.solve(input_text)
    # Expose v3's internal answer + its exact cost for an apples-to-apples
    # no-regression audit (v3 is itself time-nondeterministic, so the rigorous
    # guarantee is v4_final <= THIS base, computed below).

    candidates, all_tasks = _parse_candidates(input_text)
    if not candidates:
        return base

    v2 = _load_module("solver_v2.py", "solver_v2_for_v3")  # same alias v3 uses
    cost_fn = v2._solution_expected_cost
    global _LAST_BASE, _LAST_BASE_COST
    try:
        base_cost = cost_fn(base, candidates, all_tasks)
    except Exception:
        _LAST_BASE, _LAST_BASE_COST = base, None
        return base
    _LAST_BASE, _LAST_BASE_COST = base, base_cost

    # No leftover budget -> v4 == v3.
    if time.monotonic() >= deadline - 0.35:
        return base

    is_scarce, is_low, is_low_cr = _detect_regime(candidates, all_tasks)

    try:
        best, _ = _extra_polish(
            v2, base, base_cost, candidates, all_tasks, deadline,
            is_scarce, is_low, is_low_cr)
    except Exception:
        return base

    # Final safety: never return something worse than base on the exact objective.
    try:
        if cost_fn(best, candidates, all_tasks) <= base_cost + 1e-12:
            return best
    except Exception:
        pass
    return base
