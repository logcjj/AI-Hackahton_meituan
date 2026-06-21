# =============================================================================
# solver_explained.py  --  Walkthrough / review edition of the AutoSolver engine
# -----------------------------------------------------------------------------
# This file is a DE-OBFUSCATED, semantically-equivalent rewrite of solver_v2.py
# (the generalization-hardened engine derived from the 706.197 submission).
#
# Public contract (identical to solver.py / solver_v2.py / solver_v3.py):
#       solve(input_text: str) -> list[(task_id_list_str, [courier_id, ...]), ...]
# Single file, stdlib only, <=10s/case.
#
# WHY THIS FILE EXISTS
# --------------------
# solver.py and solver_v2.py are written in an intentionally compressed style
# (single-letter names, many statements per line, module-level constant aliases
# like _A=None / _B=True). That is hard to read in a code walkthrough. This file
# spells everything out: meaningful variable names, one statement per line,
# docstrings, and inline commentary on each algorithmic strategy.
#
# EQUIVALENCE GUARANTEE (test-gated, not just claimed)
# ----------------------------------------------------
# Every numeric literal, comparison, tie-break key, time budget and branch
# condition below is copied verbatim from solver_v2.py. The accompanying harness
#       tools/verify_explained_equiv.py
# generates a large bank of instances across every regime (tiny / small / medium
# / large / scarce / low-willingness / high-noise / bundle-heavy, plus the
# official sample cases) and asserts that
#       solver_v2.solve(text) == solver_explained.solve(text)
# bit-for-bit (identical group list and courier order). Run it with:
#       python3 tools/verify_explained_equiv.py
#
# DEAD CODE REMOVED IN THIS EDITION (proven inert; see README/report)
# -------------------------------------------------------------------
#   * The `_LOW_BIAS_ACTIVE` re-entry guard. In solver.py/solver_v2.py the line
#         if _D and J and not _LOW_BIAS_ACTIVE: ...
#     is gated on the module constant _D, which is hard-wired to False. The body
#     (a recursive call into _bias_low_input_text) therefore NEVER runs, and as a
#     consequence the flag _LOW_BIAS_ACTIVE is never set to True. That in turn
#     makes a SECOND block dead:
#         if J and _LOW_BIAS_ACTIVE and ...: ...   # _LOW_BIAS_ACTIVE always False
#     Both blocks, plus the helpers they alone called (_bias_low_input_text and
#     _bias_scores_for_willingness), are removed here. The equivalence harness
#     confirms output is unchanged.
#
# THE OBJECTIVE (canonical, MINIMIZE) -- identical to
# autosolver/competition_audit.py::solution_expected_cost
# -------------------------------------------------------
#   cost(solution) = sum over groups  E[ avg accepted total_score | accept-mask ]
#                  + 100 * (number of uncovered tasks)
# Within a group each courier accepts independently with probability willingness;
# an all-reject group costs 100 * (#tasks in that group). Lower is better. This
# is implemented below as group_expected_cost / solution_expected_cost.
#
# DATA MODEL
# ----------
# A parsed input row ("candidate") is a 6-tuple, indexed exactly as in v2:
#       candidate[0] = task_key       : str   ("T1" or "T1,T2,T3" -- the raw column)
#       candidate[1] = task_ids       : tuple of str (the task ids in the bundle)
#       candidate[2] = courier_id     : str
#       candidate[3] = total_score    : float (lower is better)
#       candidate[4] = willingness    : float in (0,1] (accept probability)
#       candidate[5] = row_index      : int   (stable tie-break / input order)
# A "solution" is a list of (task_key, [courier_id, ...]) pairs.
# A "selected" dict maps task_key -> [candidate-row, ...] (the working form used
# by all local-search operators); _format_selected serializes it back.
# =============================================================================

import itertools
import random
import time

# Module-level memoization for group_expected_cost (rebuilt per solve() call).
_GROUP_COST_CACHE = {}
_GROUP_COST_CACHE_LIMIT = 250000

# Precomputed popcount for one byte, used by _popcount on arbitrary-width masks.
_POPCOUNT_TABLE = [bin(byte).count("1") for byte in range(256)]

# Regime/cost-model string tags (kept as named constants for readability).
_MODE_GAIN = "gain"      # set-cover scoring: prefer largest absolute saving
_MODE_COVER = "cover"    # set-cover scoring: prefer covering more tasks
_MODE_RATIO = "ratio"    # set-cover scoring: prefer best saving-per-score ratio
_MODE_SCARCE = "scarce"  # repair/pick mode tag for the scarce-courier regime
_MODEL_MIN_SCORE = "min_score"          # robustness model: best riders accept first
_MODEL_MAX_WILLINGNESS = "max_willingness"  # robustness model: eager riders accept first

_UNCOVERED_PENALTY = 100.0  # cost of leaving one task uncovered

# A solve() call self-limits to ~8.7s (bumped to ~8.85s in the dense regime),
# well inside the official 10s budget.
_DEFAULT_BUDGET_S = 8.7
_DENSE_BUDGET_S = 8.85


def solve(input_text):
    """Solve one competition instance.

    The pipeline is a multi-stage portfolio + Large-Neighbourhood-Search refiner:

      1. PARSE the TSV into candidate rows and the set of all task ids.
      2. CLASSIFY the instance into a regime (scarce / low-willingness / dense)
         from cheap structural features, and pick a time budget.
      3. BUILD a portfolio of starting solutions with several constructive
         heuristics (per-task expected-cost greedy multidispatch, disjoint
         set-cover in gain/cover/ratio modes, exact column branch&bound, min-cost
         -flow bundle enumeration, elite column recombination, sparse beam).
      4. PICK the cheapest feasible incumbent (regime-aware tie-breaks).
      5. REFINE the incumbent with a long sequence of LNS / local-search operators
         (reassign via min-cost flow, bundle-insertion repair, pair/triple column
         exchange, worst-window / worst-related / late-acceptance repair, courier
         shifting), each gated on a strict cost improvement and the time budget.

    Returns a list of (task_key, [courier_id, ...]) groups.
    """
    global _GROUP_COST_CACHE
    _GROUP_COST_CACHE = {}

    start_time = time.monotonic()
    deadline = start_time + _DEFAULT_BUDGET_S

    # ---- 1. PARSE -----------------------------------------------------------
    lines = input_text.strip().splitlines()
    header_offset = 1 if lines and lines[0].startswith("task_id_list") else 0
    candidates = []
    all_tasks = set()
    for row_index, raw_line in enumerate(lines[header_offset:]):
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        task_key, courier_id, score_text, willingness_text = parts[:4]
        task_key = task_key.strip()
        courier_id = courier_id.strip()
        task_ids = tuple(t.strip() for t in task_key.split(",") if t.strip())
        if not task_ids or not courier_id:
            continue
        try:
            total_score = float(score_text)
            willingness = float(willingness_text)
        except ValueError:
            continue
        candidates.append((task_key, task_ids, courier_id, total_score, willingness, row_index))
        for task_id in task_ids:
            all_tasks.add(task_id)
    if not candidates:
        return []

    # ---- 2. CLASSIFY --------------------------------------------------------
    portfolio = []                                   # collected candidate solutions
    singles = [c for c in candidates if len(c[1]) == 1]   # single-task rows only
    courier_count = len({c[2] for c in candidates})
    task_count = len(all_tasks)
    avg_willingness = sum(c[4] for c in candidates) / len(candidates)
    avg_single_willingness = (
        sum(c[4] for c in singles) / len(singles) if singles else avg_willingness
    )
    # is_scarce: couriers do NOT comfortably exceed tasks -> heavy courier reuse.
    is_scarce = courier_count <= task_count
    # is_low: globally low acceptance probability -> "low willingness" regime.
    is_low = avg_willingness < 0.27
    # is_low_courier_rich: low willingness AND couriers comfortably exceed tasks.
    #   solver.py pinned this to the exact L==30 of the official low_willingness
    #   seed; solver_v2 widened it to ANY courier-rich low-willingness instance,
    #   which is the structural property the low-willingness pipeline is tuned for.
    is_low_courier_rich = (
        is_low
        and not is_scarce
        and courier_count >= task_count * 3 // 2
        and courier_count >= 24
        and avg_single_willingness < 0.25
    )
    # [removed dead code] The original here had:
    #     if _D and is_low_courier_rich and not _LOW_BIAS_ACTIVE:
    #         _LOW_BIAS_ACTIVE = True
    #         try: return solve(_bias_low_input_text(input_text, .3))
    #         finally: _LOW_BIAS_ACTIVE = False
    # _D is the constant False, so this never executed and _LOW_BIAS_ACTIVE was
    # never set True. Removed; see module docstring.

    # singles_cover_all: every task has at least one single-task row AND couriers
    # are plentiful -> the pure single-task multidispatch start is viable.
    singles_cover_all = (
        courier_count >= len(all_tasks) * 3 // 2
        and _singles_cover_all_tasks(singles, all_tasks)
    )
    has_bundles = any(len(c[1]) >= 2 for c in candidates)        # any 2+ task row
    has_triple_bundles = any(len(c[1]) > 2 for c in candidates)  # any 3+ task row
    # is_dense_scarce: scarce instance that is either small or low-willingness;
    # earns the larger time budget and the "hard scarce" pick/polish path.
    is_dense_scarce = is_scarce and (len(candidates) < 1500 or avg_willingness < 0.4)

    # [removed dead code] per-seed cached-solution short-circuits
    # (_scarce_seed401_cached_solution, _small_seed100_cached_solution) lived here
    # in solver.py and were already neutralized to None-returning stubs in v2.
    # They are simply absent in this edition.

    if is_dense_scarce:
        deadline = start_time + _DENSE_BUDGET_S

    # ---- 3. BUILD the portfolio of starting solutions -----------------------
    # 3a. Tiny instances: exact column branch&bound is affordable.
    if task_count <= 8 and time.monotonic() < deadline - 0.35:
        tiny_solution = _solve_tiny_column_search(
            candidates, all_tasks, min(deadline, time.monotonic() + 0.65)
        )
        if tiny_solution:
            portfolio.append(tiny_solution)

    # 3b. Single-task multidispatch start (+ regime-specific polishing).
    if singles:
        single_solution = _solve_single_task_multidispatch(singles, all_tasks)
        if is_scarce:
            local_deadline = min(deadline, time.monotonic() + 1.2)
            single_solution = _reassign_single_solution(single_solution, singles, all_tasks, local_deadline)
            single_solution = _rebalance_single_solution(single_solution, singles, all_tasks, local_deadline)
            single_solution = _reassign_single_solution(single_solution, singles, all_tasks, local_deadline)
        else:
            if not is_low:
                repair_deadline = (
                    min(deadline, time.monotonic() + 5.5)
                    if singles_cover_all
                    else min(deadline, time.monotonic() + 1.0)
                )
                single_solution = _destroy_repair_single_solution(single_solution, singles, all_tasks, repair_deadline)
            single_solution = _reassign_single_solution(single_solution, singles, all_tasks, deadline)
            single_solution = _rebalance_single_solution(single_solution, singles, all_tasks, deadline)
            single_solution = _reassign_single_solution(single_solution, singles, all_tasks, deadline)
        portfolio.append(single_solution)

        if singles_cover_all and time.monotonic() < deadline - 1.9:
            random_start = _random_single_start_solution(singles, all_tasks, deadline)
            if random_start:
                portfolio.append(random_start)
        if singles_cover_all and has_bundles and not is_low and time.monotonic() < deadline - 1.35:
            pair_match = _solve_pair_potential_matching(
                candidates, all_tasks, min(deadline, time.monotonic() + 1.1), lookahead=5, flexible_initial=True
            )
            if pair_match:
                portfolio.append(pair_match)
        if singles_cover_all and has_bundles and not is_low and time.monotonic() < deadline - 1.35:
            pair_match2 = _solve_pair_potential_matching(
                candidates, all_tasks, min(deadline, time.monotonic() + 1.1), lookahead=5, flexible_initial=False
            )
            if pair_match2:
                portfolio.append(pair_match2)

    # 3c. Low-willingness regime: score-scaled restarts. Multiplying scores by a
    # factor < 1 reshapes the greedy ordering toward configurations that pay off
    # under low acceptance, without changing feasibility. We keep the scaled
    # instances in `scaled_instances` to re-evaluate the incumbent against them
    # later (a cheap robustness check).
    scaled_instances = []
    if is_low and time.monotonic() < deadline - 0.8:
        if is_low_courier_rich and time.monotonic() < deadline - 1.2:
            low_global = _solve_low_global_column_search(
                candidates, all_tasks, min(deadline, time.monotonic() + 0.75)
            )
            if low_global:
                portfolio.append(low_global)
        scale_factors = (0.25, 1.0 / 3.0, 0.5) if is_low_courier_rich else (1.0 / 3.0,)
        for factor in scale_factors:
            if time.monotonic() >= deadline - 0.55:
                break
            scaled = _scale_scores(candidates, factor)
            scaled_instances.append(scaled)
            scaled_singles = [c for c in scaled if len(c[1]) == 1]
            if scaled_singles:
                portfolio.append(_solve_single_task_multidispatch(scaled_singles, all_tasks))
            for mode in (_MODE_GAIN, _MODE_COVER, _MODE_RATIO):
                if time.monotonic() < deadline - 0.35:
                    portfolio.append(_solve_disjoint_then_multidispatch(scaled, all_tasks, mode=mode, deadline=deadline))
            if time.monotonic() < deadline - 0.45:
                scaled_pair = _solve_pair_potential_matching(scaled, all_tasks, deadline, lookahead=6, flexible_initial=True)
                if scaled_pair:
                    portfolio.append(scaled_pair)
            if is_low_courier_rich and factor >= 1.0 / 3.0 and time.monotonic() < deadline - 0.65:
                low_col = _solve_low_column_search(
                    scaled_singles if scaled_singles else singles, all_tasks, min(deadline, time.monotonic() + 0.45)
                )
                if low_col:
                    portfolio.append(low_col)
        # [removed dead code] The original guarded a willingness-biased restart on
        #     if is_low_courier_rich and _LOW_BIAS_ACTIVE and ...:
        # but _LOW_BIAS_ACTIVE is permanently False (its only writer is the dead
        # _D-gated block above), so this branch never ran. Removed, along with its
        # sole helper _bias_scores_for_willingness.

    # 3d. Disjoint set-cover + bundle/column constructions for non-trivial
    # coverage. Runs whenever couriers are NOT abundant, or the instance is low
    # willingness, or it has 3-task bundles to exploit.
    if not singles_cover_all or is_low or has_triple_bundles:
        cover_modes = (_MODE_GAIN, _MODE_COVER) if is_low else (_MODE_RATIO, _MODE_GAIN, _MODE_COVER)
        for mode in cover_modes:
            if time.monotonic() < deadline - 0.35:
                portfolio.append(_solve_disjoint_then_multidispatch(candidates, all_tasks, mode=mode, deadline=deadline))
        if time.monotonic() < deadline - 0.55:
            pair_match = _solve_pair_potential_matching(
                candidates, all_tasks, deadline, lookahead=5 if is_low else 4, flexible_initial=is_low
            )
            if pair_match:
                portfolio.append(pair_match)
        if time.monotonic() < deadline - 0.25:
            portfolio.append(_solve_sparse_cover(candidates, all_tasks, deadline))
        if is_scarce and time.monotonic() < deadline - 1.0:
            k2_column = _solve_scarce_k2_column_search(candidates, all_tasks, min(deadline, time.monotonic() + 0.65))
            if k2_column:
                portfolio.append(k2_column)
            if is_scarce and time.monotonic() < deadline - 1.0:
                bundle_mcf = _solve_scarce_bundle_mcf_enum(candidates, all_tasks, min(deadline, time.monotonic() + 0.85))
                if bundle_mcf:
                    if is_dense_scarce and time.monotonic() < deadline - 1.2:
                        repaired = _scarce_bundle_insertion_repair_solution(
                            bundle_mcf, candidates, all_tasks, min(deadline, time.monotonic() + 0.3),
                            max_windows=42, max_window_tasks=14,
                        )
                        if _solution_expected_cost(repaired, candidates, all_tasks) < _solution_expected_cost(bundle_mcf, candidates, all_tasks) - 1e-09:
                            bundle_mcf = _drop_unprofitable_groups(repaired, candidates, all_tasks)
                    portfolio.append(bundle_mcf)
        if is_scarce and time.monotonic() < deadline - 2.1:
            recombined = _solve_scarce_elite_column_recombine(
                candidates, all_tasks, portfolio, min(deadline, time.monotonic() + 3.0)
            )
            if recombined:
                portfolio.append(recombined)
        if is_scarce and time.monotonic() < deadline - 1.0:
            group_mcf = _solve_scarce_bundle_group_mcf_enum(candidates, all_tasks, min(deadline, time.monotonic() + 0.75))
            if group_mcf:
                if time.monotonic() < deadline - 1.35:
                    group_mcf = _scarce_polish_candidate(group_mcf, candidates, all_tasks, min(deadline, time.monotonic() + 1.2))
                portfolio.append(group_mcf)
        best_coverage = max((_solution_covered_count(s, candidates) for s in portfolio if s), default=0)
        if is_scarce and best_coverage < len(all_tasks) - 1 and time.monotonic() < deadline - 0.9:
            beam = _sparse_beam_search(candidates, all_tasks, min(deadline, time.monotonic() + 1.0), coverage_first=True)
            if beam:
                portfolio.append(beam)

    # Always include the official greedy as a safe feasibility fallback.
    portfolio.append(_fallback_official_greedy(candidates))

    # ---- 4. PICK the incumbent (regime-aware) -------------------------------
    if is_dense_scarce:
        incumbent = _pick_hard_scarce_best(portfolio, candidates, all_tasks)
        incumbent = _drop_unprofitable_groups(incumbent, candidates, all_tasks)
    elif is_scarce:
        incumbent = _pick_scarce_best(portfolio, candidates, all_tasks)
        incumbent = _drop_unprofitable_groups(incumbent, candidates, all_tasks)
    elif is_low_courier_rich:
        incumbent = _pick_low_robust_best(portfolio, candidates, all_tasks)
    else:
        incumbent = min((s for s in portfolio if s), key=lambda s: _solution_expected_cost(s, candidates, all_tasks))

    # ---- 5. REFINE the incumbent --------------------------------------------
    if time.monotonic() < deadline - 0.18:
        incumbent = _local_improve_mixed_solution(incumbent, candidates, all_tasks, deadline, include_pair_rewire=is_scarce)

    # 5a. Scarce-regime deep refinement chain.
    if is_scarce and time.monotonic() < deadline - 0.3:
        incumbent = _reassign_mixed_solution(incumbent, candidates, all_tasks, deadline)
        incumbent = _drop_unprofitable_groups(incumbent, candidates, all_tasks)
        if time.monotonic() < deadline - 0.18:
            incumbent = _local_improve_mixed_solution(incumbent, candidates, all_tasks, deadline, include_pair_rewire=True)
            incumbent = _drop_unprofitable_groups(incumbent, candidates, all_tasks)
        if time.monotonic() < deadline - 0.85:
            incumbent = _column_alns_repair_solution(
                incumbent, candidates, all_tasks, min(deadline, time.monotonic() + 0.75),
                mode=_MODE_SCARCE, max_window_tasks=12, top_riders_per_task_key=8, option_limit=55, max_k=4,
            )
            incumbent = _drop_unprofitable_groups(incumbent, candidates, all_tasks)
        if time.monotonic() < deadline - 0.45:
            repaired = _scarce_bundle_insertion_repair_solution(
                incumbent, candidates, all_tasks, min(deadline, time.monotonic() + 0.34),
                max_windows=34, max_window_tasks=14,
            )
            if _solution_expected_cost(repaired, candidates, all_tasks) < _solution_expected_cost(incumbent, candidates, all_tasks) - 1e-09:
                incumbent = _drop_unprofitable_groups(repaired, candidates, all_tasks)
        if time.monotonic() < deadline - 0.35:
            exchanged = _pairwise_column_exchange_solution(
                incumbent, candidates, all_tasks, min(deadline, time.monotonic() + 0.3),
                top_riders_per_task_key=8, max_k=4, option_limit=55, max_window_tasks=10, max_pairs=28,
            )
            if _solution_covered_count(exchanged, candidates) >= _solution_covered_count(incumbent, candidates) and _solution_expected_cost(exchanged, candidates, all_tasks) < _solution_expected_cost(incumbent, candidates, all_tasks) - 1e-09:
                incumbent = exchanged
                incumbent = _drop_unprofitable_groups(incumbent, candidates, all_tasks)
        if time.monotonic() < deadline - 0.32:
            exchanged = _triple_column_exchange_solution(
                incumbent, candidates, all_tasks, min(deadline, time.monotonic() + 0.27),
                top_riders_per_task_key=8, max_k=4, option_limit=60, max_window_tasks=12, max_triples=16,
            )
            if _solution_covered_count(exchanged, candidates) >= _solution_covered_count(incumbent, candidates) and _solution_expected_cost(exchanged, candidates, all_tasks) < _solution_expected_cost(incumbent, candidates, all_tasks) - 1e-09:
                incumbent = exchanged
                incumbent = _drop_unprofitable_groups(incumbent, candidates, all_tasks)
        if time.monotonic() < deadline - 0.24:
            ejected = _scarce_eject_extra_to_uncovered(incumbent, candidates, all_tasks, min(deadline, time.monotonic() + 0.18))
            if _solution_expected_cost(ejected, candidates, all_tasks) < _solution_expected_cost(incumbent, candidates, all_tasks) - 1e-09:
                incumbent = ejected
                incumbent = _drop_unprofitable_groups(incumbent, candidates, all_tasks)
        if time.monotonic() < deadline - 0.22:
            shifted = _shift_couriers_between_groups(incumbent, candidates, all_tasks, min(deadline, time.monotonic() + 0.18), max_moves=18)
            if _solution_expected_cost(shifted, candidates, all_tasks) < _solution_expected_cost(incumbent, candidates, all_tasks) - 1e-09:
                incumbent = _drop_unprofitable_groups(shifted, candidates, all_tasks)

    # 5b. Low-willingness reassignment.
    if is_low and time.monotonic() < deadline - 0.34:
        reassigned = _reassign_mixed_solution(incumbent, candidates, all_tasks, min(deadline, time.monotonic() + 0.14))
        if _solution_expected_cost(reassigned, candidates, all_tasks) < _solution_expected_cost(incumbent, candidates, all_tasks) - 1e-09:
            incumbent = reassigned

    # 5c. Low-willingness robustness re-pick against the score-scaled instances.
    if is_low and scaled_instances and time.monotonic() < deadline - 0.18:
        for scaled in scaled_instances:
            if time.monotonic() >= deadline - 0.18:
                break
            candidate = min((s for s in portfolio if s), key=lambda s: _solution_expected_cost(s, scaled, all_tasks))
            candidate = _local_improve_mixed_solution(candidate, scaled, all_tasks, deadline, include_pair_rewire=True)
            if _solution_expected_cost(candidate, candidates, all_tasks) < _solution_expected_cost(incumbent, candidates, all_tasks) - 1e-09:
                incumbent = candidate

    if is_low_courier_rich and time.monotonic() < deadline - 0.78:
        incumbent = _low_worst_window_repair_solution(incumbent, candidates, all_tasks, min(deadline, time.monotonic() + 0.62))
    if is_low and time.monotonic() < deadline - 0.35:
        incumbent = _pairwise_column_exchange_solution(
            incumbent, candidates, all_tasks, min(deadline, time.monotonic() + 0.3),
            top_riders_per_task_key=8, max_k=4, option_limit=55, max_window_tasks=10, max_pairs=28,
        )
    if is_low and time.monotonic() < deadline - 0.32:
        incumbent = _triple_column_exchange_solution(
            incumbent, candidates, all_tasks, min(deadline, time.monotonic() + 0.27),
            top_riders_per_task_key=8, max_k=4, option_limit=60, max_window_tasks=12, max_triples=16,
        )
    if is_low and time.monotonic() < deadline - 0.32:
        incumbent = _shift_couriers_between_groups(incumbent, candidates, all_tasks, min(deadline, time.monotonic() + 0.26), max_moves=30)

    # 5d. Medium dense regime (9..35 tasks, courier-rich, not low): window repair.
    if 9 <= task_count <= 35 and not is_scarce and not is_low and time.monotonic() < deadline - 0.55:
        incumbent = _repair_worst_window_solution(incumbent, candidates, all_tasks, min(deadline, time.monotonic() + 0.75))
    if 9 <= task_count <= 35 and not is_scarce and not is_low and time.monotonic() < deadline - 0.75:
        incumbent = _column_alns_repair_solution(
            incumbent, candidates, all_tasks, min(deadline, time.monotonic() + 0.62),
            mode="normal", max_window_tasks=10, top_riders_per_task_key=8, option_limit=55, max_k=3,
        )
        if time.monotonic() < deadline - 0.35:
            incumbent = _pairwise_column_exchange_solution(
                incumbent, candidates, all_tasks, min(deadline, time.monotonic() + 0.3),
                top_riders_per_task_key=8, max_k=4, option_limit=55, max_window_tasks=10, max_pairs=32,
            )
        if time.monotonic() < deadline - 0.32:
            incumbent = _triple_column_exchange_solution(
                incumbent, candidates, all_tasks, min(deadline, time.monotonic() + 0.27),
                top_riders_per_task_key=8, max_k=4, option_limit=60, max_window_tasks=12, max_triples=16,
            )

    if time.monotonic() < deadline - 0.22:
        reassigned = _reassign_mixed_solution(incumbent, candidates, all_tasks, min(deadline, time.monotonic() + 0.35))
        if _solution_expected_cost(reassigned, candidates, all_tasks) < _solution_expected_cost(incumbent, candidates, all_tasks) - 1e-09:
            incumbent = reassigned

    # [removed dead code] solver.py had two L==30/d==60 and L==40/d==80
    # 'output_upgrade' early-returns here that swapped in a memorized table; v2
    # already neutralized them and fell through to the generic polish below.

    incumbent = _normal_medium_polish_solution(incumbent, candidates, all_tasks, deadline, task_count, courier_count, is_scarce, is_low)

    if is_dense_scarce and time.monotonic() < deadline - 3.05:
        repaired = _scarce_bundle_insertion_repair_solution(
            incumbent, candidates, all_tasks, min(deadline, time.monotonic() + 2.8), max_windows=60, max_window_tasks=14
        )
        if _solution_expected_cost(repaired, candidates, all_tasks) < _solution_expected_cost(incumbent, candidates, all_tasks) - 1e-09:
            incumbent = _drop_unprofitable_groups(repaired, candidates, all_tasks)
            if time.monotonic() < deadline - 0.2:
                reassigned = _reassign_mixed_solution(incumbent, candidates, all_tasks, min(deadline, time.monotonic() + 0.18))
                if _solution_expected_cost(reassigned, candidates, all_tasks) < _solution_expected_cost(incumbent, candidates, all_tasks) - 1e-09:
                    incumbent = reassigned
    if is_dense_scarce and time.monotonic() < deadline - 1.35:
        recombined = _solve_scarce_elite_column_recombine(candidates, all_tasks, [incumbent], min(deadline, time.monotonic() + 0.85))
        if recombined:
            recombined = _scarce_polish_candidate(recombined, candidates, all_tasks, min(deadline, time.monotonic() + 0.55))
            if _solution_expected_cost(recombined, candidates, all_tasks) < _solution_expected_cost(incumbent, candidates, all_tasks) - 1e-09:
                incumbent = _drop_unprofitable_groups(recombined, candidates, all_tasks)
    if is_scarce and time.monotonic() < deadline - 0.24:
        incumbent = _shift_couriers_between_groups(incumbent, candidates, all_tasks, min(deadline, time.monotonic() + 0.18), max_moves=18)

    if is_low_courier_rich and time.monotonic() < deadline - 1.35:
        incumbent = _low_deep_window_repair_solution(incumbent, candidates, all_tasks, min(deadline, time.monotonic() + 1.2))
    if is_low_courier_rich and time.monotonic() < deadline - 0.95:
        incumbent = _low_late_acceptance_repair_solution(incumbent, candidates, all_tasks, min(deadline, time.monotonic() + 0.85))
    if is_low_courier_rich and time.monotonic() < deadline - 0.32:
        incumbent = _shift_couriers_between_groups(incumbent, candidates, all_tasks, min(deadline, time.monotonic() + 0.24), max_moves=30)

    if 9 <= task_count <= 35 and not is_scarce and not is_low and time.monotonic() < deadline - 0.85:
        incumbent = _normal_worst_related_repair_solution(incumbent, candidates, all_tasks, min(deadline, time.monotonic() + 0.45))
    if 9 <= task_count <= 35 and not is_scarce and not is_low and time.monotonic() < deadline - 0.95:
        incumbent = _normal_worst_related_repair_solution(incumbent, candidates, all_tasks, min(deadline, time.monotonic() + 0.75))
    return incumbent


# =============================================================================
# THE OBJECTIVE FUNCTION  (canonical expected cost)
# -----------------------------------------------------------------------------
# These mirror autosolver/competition_audit.py exactly and are what every search
# and tie-break below optimizes. They are the most-cited functions in a review,
# so they are written out in full.
# =============================================================================
def _group_expected_cost(rows, task_count, extra=None):
    """Expected cost of ONE dispatch group (a task_key handed to >=0 couriers).

    Model: each courier i in the group independently accepts with probability
    willingness_i. Conditioned on the accept-mask, the realized cost is the
    AVERAGE total_score over the couriers who accepted; if NONE accept, the
    group costs ``100 * task_count`` (the uncovered penalty for its tasks).
    The returned value is the expectation over all 2^n accept-masks.

    ``extra`` optionally appends one more candidate row to ``rows`` (used by the
    greedy "what if I add this courier" probes without building a new list).
    Results are memoized in _GROUP_COST_CACHE keyed by (task_count, sorted rows).
    """
    if extra is not None:
        rows = list(rows) + [extra]
    if not rows:
        return _UNCOVERED_PENALTY * task_count
    rows = list(rows)
    cache_key = (task_count, tuple(sorted((r[5], r[3], r[4]) for r in rows)))
    cached = _GROUP_COST_CACHE.get(cache_key)
    if cached is not None:
        return cached
    group_size = len(rows)
    if group_size > 12:
        # Too many couriers for a 2^n enumeration; use the ordering-independent DP.
        expected = _group_expected_cost_dp(rows, task_count)
    else:
        expected = 0.0
        for accept_mask in range(1 << group_size):
            probability = 1.0
            accepted_score = 0.0
            accepted_count = 0
            for index, row in enumerate(rows):
                if accept_mask >> index & 1:
                    probability *= row[4]               # willingness
                    accepted_score += row[3]            # total_score
                    accepted_count += 1
                else:
                    probability *= 1.0 - row[4]
            if accepted_count:
                expected += probability * (accepted_score / accepted_count)
            else:
                expected += probability * (_UNCOVERED_PENALTY * task_count)
    if len(_GROUP_COST_CACHE) < _GROUP_COST_CACHE_LIMIT:
        _GROUP_COST_CACHE[cache_key] = expected
    return expected


def _group_expected_cost_dp(rows, task_count):
    """O(n^2) dynamic program for E[avg accepted score] when a group is too large
    for the 2^n enumeration (n > 12). Exact and ordering-independent.

    Idea: E[avg] = sum_j score_j * P(j accepts) * E[1/(#accepted) | j accepts].
    For each "pivot" courier j that accepts, convolve the accept distribution of
    all OTHER couriers into a polynomial (dist[k] = P(exactly k others accept)),
    then weight 1/(k+1) by dist[k]. The all-reject mass pays the uncovered penalty.
    """
    prob_all_reject = 1.0
    for row in rows:
        prob_all_reject *= 1.0 - row[4]
    total = prob_all_reject * (_UNCOVERED_PENALTY * task_count)
    for pivot_index, pivot in enumerate(rows):
        pivot_willingness = pivot[4]
        if pivot_willingness <= 0.0:
            continue
        # distribution of the count of OTHER couriers that accept
        dist = [1.0]
        for other_index, other in enumerate(rows):
            if other_index == pivot_index:
                continue
            other_will = other[4]
            new_dist = [0.0] * (len(dist) + 1)
            for k, mass in enumerate(dist):
                new_dist[k] += mass * (1.0 - other_will)
                new_dist[k + 1] += mass * other_will
            dist = new_dist
        expected_inv_count = 0.0
        for accepted_others, mass in enumerate(dist):
            expected_inv_count += mass / (accepted_others + 1)
        total += pivot[3] * pivot_willingness * expected_inv_count
    return total


def _single_expected_cost(cand):
    """Expected cost of dispatching a single-task row to ONE courier:
    willingness*score if accepted, else (1-willingness)*100."""
    return cand[4] * cand[3] + (1.0 - cand[4]) * 100.0


def _solution_expected_cost(result, candidates, all_tasks):
    """Total canonical cost of a full solution (the production objective).

    Sums _group_expected_cost over every group and adds 100 per uncovered task.
    Returns +inf if the solution is INFEASIBLE: an unknown (task_key, courier)
    pair, a courier used in two groups, or a task covered twice.
    """
    row_map = {(c[0], c[2]): c for c in candidates}
    covered_tasks = set()
    used_couriers = set()
    total = 0.0
    for task_key, courier_ids in result:
        group_rows = []
        for courier_id in courier_ids:
            row = row_map.get((task_key, courier_id))
            if row is None or courier_id in used_couriers:
                return float("inf")
            used_couriers.add(courier_id)
            group_rows.append(row)
        if not group_rows:
            return float("inf")
        for task_id in group_rows[0][1]:
            if task_id in covered_tasks:
                return float("inf")
            covered_tasks.add(task_id)
        total += _group_expected_cost(group_rows, len(group_rows[0][1]))
    total += _UNCOVERED_PENALTY * (len(all_tasks) - len(covered_tasks))
    return total


def _group_expected_cost_by_model(rows, task_count, model):
    """Expected cost under a worst/eager-case acceptance ORDERING model, used to
    estimate solution robustness in the low-willingness pick.

    'avg_subset' -> the canonical averaging model (delegates to the real cost).
    'min_score'  -> couriers attempt in best-score-first order; cost is the
                    score of the first acceptor (or 100*task_count if all reject).
    'max_willingness' -> couriers attempt eager-first (highest willingness first).
    """
    if model == "avg_subset":
        return _group_expected_cost(rows, task_count)
    remaining_prob = 1.0
    expected = 0.0
    if model == _MODEL_MIN_SCORE:
        ordered = sorted(rows, key=lambda c: (c[3], -c[4], c[5]))
    elif model == _MODEL_MAX_WILLINGNESS:
        ordered = sorted(rows, key=lambda c: (-c[4], c[3], c[5]))
    else:
        raise ValueError("unknown cost model")
    for row in ordered:
        expected += remaining_prob * row[4] * row[3]
        remaining_prob *= 1.0 - row[4]
    expected += remaining_prob * 100.0 * task_count
    return expected


def _solution_expected_cost_by_model(result, candidates, all_tasks, model):
    """Total solution cost under a robustness ordering model (see above). Returns
    +inf on the same infeasibility conditions as _solution_expected_cost."""
    row_map = {(c[0], c[2]): c for c in candidates}
    covered_tasks = set()
    used_couriers = set()
    total = 0.0
    for task_key, courier_ids in result:
        group_rows = []
        for courier_id in courier_ids:
            row = row_map.get((task_key, courier_id))
            if row is None or courier_id in used_couriers:
                return float("inf")
            used_couriers.add(courier_id)
            group_rows.append(row)
        if not group_rows:
            return float("inf")
        for task_id in group_rows[0][1]:
            if task_id in covered_tasks:
                return float("inf")
            covered_tasks.add(task_id)
        total += _group_expected_cost_by_model(group_rows, len(group_rows[0][1]), model)
    total += 100.0 * (len(all_tasks) - len(covered_tasks))
    return total


def _solution_covered_count(result, candidates):
    """Number of distinct tasks covered by a solution, or -1 if the solution is
    structurally invalid (unknown pair, courier reuse, or task covered twice)."""
    row_map = {(c[0], c[2]): c for c in candidates}
    covered_tasks = set()
    used_couriers = set()
    for task_key, courier_ids in result:
        group_rows = []
        for courier_id in courier_ids:
            row = row_map.get((task_key, courier_id))
            if row is None or courier_id in used_couriers:
                return -1
            used_couriers.add(courier_id)
            group_rows.append(row)
        if not group_rows:
            return -1
        for task_id in group_rows[0][1]:
            if task_id in covered_tasks:
                return -1
            covered_tasks.add(task_id)
    return len(covered_tasks)


def _popcount(value):
    """Number of set bits in an arbitrary-width integer mask (byte-table based)."""
    count = 0
    while value:
        count += _POPCOUNT_TABLE[value & 255]
        value >>= 8
    return count


# =============================================================================
# PARSE/FORMAT + SMALL STRUCTURAL HELPERS
# =============================================================================
def _singles_cover_all_tasks(singles, all_tasks):
    """True iff every task id has at least one single-task candidate row."""
    covered = {c[1][0] for c in singles}
    return all(task in covered for task in all_tasks)


def _scale_scores(candidates, factor):
    """Return a copy of candidates with every total_score multiplied by ``factor``
    (a low-willingness restart trick; willingness and ids are untouched)."""
    return [(k, ids, cid, score * factor, will, idx) for (k, ids, cid, score, will, idx) in candidates]


def _canonical_candidates(candidates):
    """Deduplicate rows by (task_key, courier_id), keeping the last occurrence,
    then sort by stable row_index. Gives constructions a deterministic input."""
    by_pair = {}
    for c in candidates:
        by_pair[(c[0], c[2])] = c
    return sorted(by_pair.values(), key=lambda c: c[5])


def _format_selected(selected):
    """Serialize a working ``selected`` dict (task_key -> [rows]) into the public
    solution format. Groups are emitted in task_ids order; within a group couriers
    are ordered by (score, -willingness, row_index)."""
    result = []
    for task_key in sorted(selected, key=lambda k: selected[k][0][1]):
        ordered_rows = sorted(selected[task_key], key=lambda c: (c[3], -c[4], c[5]))
        result.append((task_key, [r[2] for r in ordered_rows]))
    return result


def _result_to_selected(result, row_map):
    """Inverse of _format_selected: rebuild the working dict (task_key -> [rows])
    from a public solution, resolving each courier via ``row_map``. Drops groups
    whose rows cannot be resolved."""
    selected = {}
    for task_key, courier_ids in result:
        rows = []
        for courier_id in courier_ids:
            row = row_map.get((task_key, courier_id))
            if row is not None:
                rows.append(row)
        if rows:
            selected[task_key] = rows
    return selected


def _selected_couriers_except(selected, excluded_keys):
    """Set of courier ids used by all groups EXCEPT those whose key is excluded."""
    return {row[2] for (key, rows) in selected.items() if key not in excluded_keys for row in rows}


def _selected_cost(selected, all_tasks):
    """Canonical cost of a ``selected`` dict (singles-flavoured: every group is one
    task). Sum of group costs + 100 per uncovered task."""
    covered = 0
    total = 0.0
    for rows in selected.values():
        if not rows:
            continue
        group_task_count = len(rows[0][1])
        covered += group_task_count
        total += _group_expected_cost(rows, group_task_count)
    total += 100.0 * (len(all_tasks) - covered)
    return total


def _task_adjacency(candidates):
    """Build task->{co-bundled tasks} adjacency from every 2+ task bundle row.
    Used to grow "related" repair windows around a seed task."""
    adjacency = {}
    for (key, task_ids, cid, score, will, idx) in candidates:
        if len(task_ids) < 2:
            continue
        for task_a in task_ids:
            neighbours = adjacency.setdefault(task_a, set())
            for task_b in task_ids:
                if task_b != task_a:
                    neighbours.add(task_b)
    return adjacency


def _selected_group_tasks_containing(selected, task_id):
    """The task-id set of the group (if any) that currently covers ``task_id``."""
    for rows in selected.values():
        if rows and task_id in rows[0][1]:
            return set(rows[0][1])
    return set()


# =============================================================================
# CONSTRUCTIVE HEURISTIC: per-task expected-cost greedy MULTIDISPATCH
# -----------------------------------------------------------------------------
# Assign couriers to single tasks one at a time, always taking the (task,courier)
# move with the largest marginal DROP in that task's expected group cost. Adding a
# second/third courier to a task is allowed (multidispatch) when it lowers the
# group's expected cost. Any task still uncovered afterwards is force-assigned its
# cheapest available single courier.
# =============================================================================
def _solve_single_task_multidispatch(singles, all_tasks):
    group_rows = {task: [] for task in all_tasks}      # task -> chosen rows
    group_cost = {task: 100.0 for task in all_tasks}   # task -> current group cost
    used_couriers = set()
    while True:
        best_move = None
        best_delta = 0.0
        best_new_cost = 0.0
        for cand in singles:
            _key, task_ids, courier_id, _score, _will, _idx = cand
            if courier_id in used_couriers:
                continue
            task = task_ids[0]
            current = group_cost.get(task, 100.0)
            new_cost = _group_expected_cost(group_rows.get(task, []), 1, extra=cand)
            delta = new_cost - current
            if delta < best_delta - 1e-12:
                best_delta = delta
                best_new_cost = new_cost
                best_move = cand
        if best_move is None:
            break
        task = best_move[1][0]
        group_rows[task].append(best_move)
        group_cost[task] = best_new_cost
        used_couriers.add(best_move[2])
    # Force-cover any task left empty with its cheapest still-free single courier.
    for task in sorted(all_tasks):
        if group_rows.get(task):
            continue
        options = [c for c in singles if c[1][0] == task and c[2] not in used_couriers]
        if not options:
            continue
        chosen = min(options, key=lambda c: _single_expected_cost(c))
        group_rows[task].append(chosen)
        used_couriers.add(chosen[2])
    output = []
    for task in sorted(group_rows):
        rows = group_rows[task]
        if not rows:
            continue
        rows = sorted(rows, key=lambda c: (c[3], -c[4], c[5]))
        output.append((task, [r[2] for r in rows]))
    return output


# =============================================================================
# EXACT COLUMN / SET-PACKING SEARCH via branch & bound  (_search_column_window)
# -----------------------------------------------------------------------------
# This is the exact solver used on small task windows. It enumerates promising
# "columns" (a column = one task_key handed to a small courier subset, with
# NEGATIVE reduced cost, i.e. it beats leaving those tasks uncovered), then does a
# branch & bound over a disjoint PACKING of columns that minimizes total reduced
# cost. Tasks are bit-indexed (task_mask) and couriers are bit-indexed
# (courier_mask) so disjointness and the admissible bound are O(1) bit ops.
#
# Bound: g[t] = best (most negative) reduced cost of any column covering task t.
# A partial packing's optimistic completion adds g[t] for each not-yet-decided
# task t; if that lower bound can't beat the incumbent, prune.
# =============================================================================
def _solve_tiny_column_search(candidates, all_tasks, deadline):
    """Exact column search for tiny instances (<=8 tasks)."""
    return _search_column_window(candidates, all_tasks, deadline, top_riders_per_task_key=10, max_k=4, option_limit=80)


def _solve_low_column_search(singles, all_tasks, deadline):
    """Column search over single-task rows for the low-willingness regime."""
    if not singles:
        return []
    return _search_column_window(singles, all_tasks, deadline, top_riders_per_task_key=10, max_k=3, option_limit=28)


def _solve_low_global_column_search(candidates, all_tasks, deadline):
    """Column search over all rows for the courier-rich low-willingness regime."""
    if not candidates:
        return []
    return _search_column_window(candidates, all_tasks, deadline, top_riders_per_task_key=8, max_k=4, option_limit=28)


def _solve_scarce_k2_column_search(candidates, all_tasks, deadline):
    """Column search restricted to <=2 couriers per column for the scarce regime."""
    if not candidates:
        return []
    return _search_column_window(candidates, all_tasks, deadline, top_riders_per_task_key=10, max_k=2, option_limit=60)


def _search_column_window(candidates, all_tasks, deadline, top_riders_per_task_key, max_k, option_limit):
    del all_tasks  # task set is recomputed locally from the candidate rows
    candidates = _canonical_candidates(candidates)
    task_order = sorted({t for c in candidates for t in c[1]})
    task_bit = {t: i for i, t in enumerate(task_order)}
    courier_bit = {cid: i for i, cid in enumerate(sorted({c[2] for c in candidates}))}

    # Group rows by their task_key (only keys whose tasks are all in this window).
    rows_by_key = {}
    for cand in candidates:
        if all(t in task_bit for t in cand[1]):
            rows_by_key.setdefault(cand[0], []).append(cand)

    # Enumerate negative-reduced-cost columns: (reduced, cost, task_mask, courier_mask, rows)
    columns = []
    for key_rows in rows_by_key.values():
        if time.monotonic() > deadline - 0.05:
            break
        key_rows = sorted(key_rows, key=lambda c: (_group_expected_cost([c], len(c[1])), -c[4], c[5]))[:top_riders_per_task_key]
        if not key_rows:
            continue
        task_mask = 0
        for task_id in key_rows[0][1]:
            task_mask |= 1 << task_bit[task_id]
        bundle_task_count = len(key_rows[0][1])
        for subset_size in range(1, min(max_k, len(key_rows)) + 1):
            for subset in itertools.combinations(key_rows, subset_size):
                courier_mask = 0
                clash = False
                for row in subset:
                    bit = 1 << courier_bit[row[2]]
                    if courier_mask & bit:
                        clash = True
                        break
                    courier_mask |= bit
                if clash:
                    continue
                group_cost = _group_expected_cost(subset, bundle_task_count)
                reduced = group_cost - 100.0 * bundle_task_count
                if reduced < -1e-09:
                    columns.append((reduced, group_cost, task_mask, courier_mask, subset))
    if not columns:
        return []

    task_count = len(task_order)
    full_task_mask = (1 << task_count) - 1
    # columns_covering[t] = list of columns whose task_mask includes task bit t
    columns_covering = [[] for _ in range(task_count)]
    for col in columns:
        col_task_mask = col[2]
        for t in range(task_count):
            if col_task_mask >> t & 1:
                columns_covering[t].append(col)

    # Greedy seed packing (sorted by reduced-per-task then reduced) to warm the
    # incumbent; if it ends up non-negative it is discarded (incumbent stays 0).
    best_packing = []
    best_reduced = 0.0
    used_task_mask = 0
    used_courier_mask = 0
    for col in sorted(columns, key=lambda c: (c[0] / max(1, _popcount(c[2])), c[0])):
        if col[2] & used_task_mask or col[3] & used_courier_mask:
            continue
        used_task_mask |= col[2]
        used_courier_mask |= col[3]
        best_packing.append(col)
        best_reduced += col[0]
    if best_reduced > 0.0:
        best_packing = []
        best_reduced = 0.0

    for col_list in columns_covering:
        col_list.sort(key=lambda c: (c[0], len(c[4]), c[4][0][0], tuple(r[2] for r in c[4])))
    # min_reduced_for_task[t] = most negative reduced cost available to cover t
    min_reduced_for_task = [min(0.0, min((c[0] for c in col_list), default=0.0)) for col_list in columns_covering]

    current_packing = []  # the B&B stack (closure-shared with the recursion)

    def lower_bound(decided_task_mask, current_reduced):
        bound = current_reduced
        remaining = full_task_mask & ~decided_task_mask
        while remaining:
            lowest = remaining & -remaining
            t = lowest.bit_length() - 1
            bound += min_reduced_for_task[t]
            remaining ^= lowest
        return bound

    def pick_branch_task(decided_task_mask, courier_mask):
        # Choose the still-undecided task with the FEWEST feasible columns (most
        # constrained variable). Returns (task_index or None, its column options).
        remaining = full_task_mask & ~decided_task_mask
        chosen_task = None
        chosen_options = []
        while remaining:
            lowest = remaining & -remaining
            t = lowest.bit_length() - 1
            options = [c for c in columns_covering[t] if not c[2] & decided_task_mask and not c[3] & courier_mask]
            if chosen_task is None or len(options) < len(chosen_options):
                chosen_task = t
                chosen_options = options
                if not options:
                    break
            remaining ^= lowest
        return chosen_task, chosen_options

    def branch(decided_task_mask, courier_mask, current_reduced):
        nonlocal best_packing, best_reduced
        if time.monotonic() > deadline - 0.02:
            return
        if lower_bound(decided_task_mask, current_reduced) >= best_reduced - 1e-09:
            return
        if decided_task_mask == full_task_mask:
            if current_reduced < best_reduced - 1e-09:
                best_reduced = current_reduced
                best_packing = list(current_packing)
            return
        branch_task, options = pick_branch_task(decided_task_mask, courier_mask)
        if branch_task is None:
            if current_reduced < best_reduced - 1e-09:
                best_reduced = current_reduced
                best_packing = list(current_packing)
            return
        # Try covering branch_task with each option (bounded by option_limit)...
        for col in options[:option_limit]:
            current_packing.append(col)
            branch(decided_task_mask | col[2], courier_mask | col[3], current_reduced + col[0])
            current_packing.pop()
        # ...or leave branch_task uncovered (mark it decided, no column).
        branch(decided_task_mask | 1 << branch_task, courier_mask, current_reduced)

    branch(0, 0, 0.0)

    output = []
    for col in sorted(best_packing, key=lambda c: (min(r[5] for r in c[4]), c[4][0][0], tuple(r[2] for r in c[4]))):
        ordered = sorted(col[4], key=lambda c: (c[3], -c[4], c[5]))
        output.append((ordered[0][0], [r[2] for r in ordered]))
    return output


# =============================================================================
# TRUE MIN-COST FLOW  (_MinCostFlow) -- SPFA successive shortest augmenting path
# -----------------------------------------------------------------------------
# A textbook successive-shortest-path min-cost-max-flow on a residual graph. Each
# edge is stored as [dest, residual_capacity, cost, index_of_reverse_edge]; the
# reverse edge starts at capacity 0 with negated cost. We repeatedly find a
# shortest (by cost) source->sink path with SPFA (a queue-based Bellman-Ford that
# tolerates the negative residual-edge costs) and push exactly one unit along it.
# Used to OPTIMALLY re-pair the fixed set of dispatch slots to couriers (an
# assignment problem) inside the reassignment operators below.
# =============================================================================
class _MinCostFlow:
    def __init__(self, num_nodes):
        self.graph = [[] for _ in range(num_nodes)]

    def add_edge(self, start, end, capacity, cost):
        forward = [end, capacity, cost, len(self.graph[end])]
        backward = [start, 0, -cost, len(self.graph[start])]
        self.graph[start].append(forward)
        self.graph[end].append(backward)

    def min_cost_flow(self, source, sink, amount):
        """Push up to ``amount`` units of flow source->sink at minimum cost.
        Returns the number of units actually pushed."""
        pushed = 0
        num_nodes = len(self.graph)
        while pushed < amount:
            # SPFA shortest paths by cost from source over residual edges.
            dist = [float("inf")] * num_nodes
            in_queue = [False] * num_nodes
            prev_node = [-1] * num_nodes
            prev_edge = [-1] * num_nodes
            dist[source] = 0.0
            queue = [source]
            in_queue[source] = True
            head = 0
            while head < len(queue):
                node = queue[head]
                head += 1
                in_queue[node] = False
                for edge_index, edge in enumerate(self.graph[node]):
                    dest, residual_cap, edge_cost, _rev = edge
                    if residual_cap <= 0:
                        continue
                    new_dist = dist[node] + edge_cost
                    if new_dist + 1e-12 < dist[dest]:
                        dist[dest] = new_dist
                        prev_node[dest] = node
                        prev_edge[dest] = edge_index
                        if not in_queue[dest]:
                            queue.append(dest)
                            in_queue[dest] = True
            if prev_node[sink] == -1:
                break  # sink unreachable -> no more augmenting paths
            # Augment one unit along the discovered shortest path.
            node = sink
            while node != source:
                forward = self.graph[prev_node[node]][prev_edge[node]]
                backward = self.graph[node][forward[3]]
                forward[1] -= 1
                backward[1] += 1
                node = prev_node[node]
            pushed += 1
        return pushed


# =============================================================================
# REASSIGNMENT OPERATORS (optimal courier<->slot re-pairing via min-cost flow)
# -----------------------------------------------------------------------------
# Given the current grouping (which couriers serve which task_keys), keep the
# group STRUCTURE fixed but re-solve which available courier fills each slot, as a
# min-cost assignment. _reassign_*_once builds the bipartite flow network
# (source -> couriers -> dispatch slots -> sink) and reads the optimal matching
# back from the saturated edges.
# =============================================================================
def _reassign_single_solution(result, singles, all_tasks, deadline):
    """Iterate optimal single-task re-pairing up to 3 times while it improves."""
    row_map = {(c[0], c[2]): c for c in singles}
    selected = _result_to_selected(result, row_map)
    if not selected:
        return result
    best_cost = _selected_cost(selected, all_tasks)
    for _ in range(3):
        if time.monotonic() > deadline - 0.15:
            break
        repaired = _reassign_selected_once(selected, row_map)
        cost = _selected_cost(repaired, all_tasks)
        if cost < best_cost - 1e-09:
            selected = repaired
            best_cost = cost
        else:
            break
    return _format_selected(selected)


def _rebalance_single_solution(result, singles, all_tasks, deadline):
    """Move single-task couriers between tasks one at a time, taking the best
    improving (donor task, receiver task, courier) move each round."""
    row_map = {(c[0], c[2]): c for c in singles}
    row_by_task_courier = {(c[1][0], c[2]): c for c in singles}
    selected = _result_to_selected(result, row_map)
    if not selected:
        return result
    for task in all_tasks:
        selected.setdefault(task, [])
    moves_done = 0
    max_moves = min(12, len(all_tasks))
    while moves_done < max_moves and time.monotonic() < deadline - 0.2:
        best_move = None
        best_delta = 0.0
        for donor_key, donor_rows in selected.items():
            if len(donor_rows) <= 1:
                continue
            donor_base = _group_expected_cost(donor_rows, 1)
            for row in donor_rows:
                courier_id = row[2]
                donor_remaining = [r for r in donor_rows if r != row]
                donor_delta = _group_expected_cost(donor_remaining, 1) - donor_base
                for receiver_key, receiver_rows in selected.items():
                    if receiver_key == donor_key:
                        continue
                    moved_row = row_by_task_courier.get((receiver_key, courier_id))
                    if moved_row is None:
                        continue
                    receiver_base = _group_expected_cost(receiver_rows, 1) if receiver_rows else 100.0
                    receiver_new = _group_expected_cost(receiver_rows, 1, extra=moved_row)
                    delta = donor_delta + receiver_new - receiver_base
                    if delta < best_delta - 1e-12:
                        best_delta = delta
                        best_move = (donor_key, receiver_key, row, moved_row)
        if best_move is None:
            break
        donor_key, receiver_key, row, moved_row = best_move
        selected[donor_key] = [r for r in selected[donor_key] if r != row]
        selected[receiver_key].append(moved_row)
        moves_done += 1
    return _format_selected({k: rows for (k, rows) in selected.items() if rows})


def _reassign_mixed_solution(result, candidates, all_tasks, deadline):
    """Iterate optimal mixed (bundle-aware) re-pairing up to 2 times."""
    row_map = {(c[0], c[2]): c for c in candidates}
    selected = _result_to_selected(result, row_map)
    if not selected:
        return result
    best_cost = _selected_cost(selected, all_tasks)
    for _ in range(2):
        if time.monotonic() > deadline - 0.22:
            break
        repaired = _reassign_mixed_selected_once(selected, row_map)
        cost = _selected_cost(repaired, all_tasks)
        if cost < best_cost - 1e-09:
            selected = repaired
            best_cost = cost
        else:
            break
    return _format_selected(selected)


def _reassign_mixed_selected_once(selected, row_map):
    """One optimal courier->slot re-pairing for a MIXED (bundle) solution.

    Each existing courier slot becomes a flow sink-slot whose cost, given a
    candidate courier, is the expected cost of the courier's group with that one
    slot swapped. A min-cost perfect matching of couriers to slots is read back.
    """
    courier_ids = sorted({row[2] for rows in selected.values() for row in rows})
    slots = []  # (task_key, bundle_task_count, other_rows_in_group)
    for task_key in sorted(selected):
        group = selected[task_key]
        bundle_task_count = len(group[0][1])
        for slot_index, _row in enumerate(group):
            other_rows = [r for (i, r) in enumerate(group) if i != slot_index]
            slots.append((task_key, bundle_task_count, other_rows))
    if not courier_ids or not slots:
        return selected
    source = 0
    courier_node0 = 1
    slot_node0 = courier_node0 + len(courier_ids)
    sink = slot_node0 + len(slots)
    flow = _MinCostFlow(sink + 1)
    edge_lookup = {}
    for i, _cid in enumerate(courier_ids):
        flow.add_edge(source, courier_node0 + i, 1, 0.0)
    for j in range(len(slots)):
        flow.add_edge(slot_node0 + j, sink, 1, 0.0)
    for i, courier_id in enumerate(courier_ids):
        courier_node = courier_node0 + i
        for j, (task_key, bundle_task_count, other_rows) in enumerate(slots):
            if any(r[2] == courier_id for r in other_rows):
                continue  # courier already in that group's other slots
            row = row_map.get((task_key, courier_id))
            if row is None:
                continue
            edge_cost = _group_expected_cost(other_rows + [row], bundle_task_count)
            edge_pos = len(flow.graph[courier_node])
            flow.add_edge(courier_node, slot_node0 + j, 1, edge_cost)
            edge_lookup[(courier_node, edge_pos)] = (j, row)
    if flow.min_cost_flow(source, sink, len(slots)) < len(slots):
        return selected
    rebuilt = {k: [] for k in selected}
    for (courier_node, edge_pos), (slot_index, row) in edge_lookup.items():
        if flow.graph[courier_node][edge_pos][1] == 0:  # edge saturated -> chosen
            task_key = slots[slot_index][0]
            rebuilt[task_key].append(row)
    if any(len(rebuilt.get(k, [])) != len(rows) for (k, rows) in selected.items()):
        return selected
    return rebuilt


def _reassign_selected_once(selected, row_map):
    """One optimal courier->slot re-pairing for a SINGLE-task solution (the
    bundle_task_count is always 1, so slots carry no task-count field)."""
    courier_ids = sorted({row[2] for rows in selected.values() for row in rows})
    slots = []  # (task_key, other_rows_in_group)
    for task_key in sorted(selected):
        group = selected[task_key]
        for slot_index, _row in enumerate(group):
            other_rows = [r for (i, r) in enumerate(group) if i != slot_index]
            slots.append((task_key, other_rows))
    if not courier_ids or not slots:
        return selected
    source = 0
    courier_node0 = 1
    slot_node0 = courier_node0 + len(courier_ids)
    sink = slot_node0 + len(slots)
    flow = _MinCostFlow(sink + 1)
    edge_lookup = {}
    for i, _cid in enumerate(courier_ids):
        flow.add_edge(source, courier_node0 + i, 1, 0.0)
    for j in range(len(slots)):
        flow.add_edge(slot_node0 + j, sink, 1, 0.0)
    for i, courier_id in enumerate(courier_ids):
        courier_node = courier_node0 + i
        for j, (task_key, other_rows) in enumerate(slots):
            if any(r[2] == courier_id for r in other_rows):
                continue
            row = row_map.get((task_key, courier_id))
            if row is None:
                continue
            edge_cost = _group_expected_cost(other_rows + [row], 1)
            edge_pos = len(flow.graph[courier_node])
            flow.add_edge(courier_node, slot_node0 + j, 1, edge_cost)
            edge_lookup[(courier_node, edge_pos)] = (j, row)
    if flow.min_cost_flow(source, sink, len(slots)) < len(slots):
        return selected
    rebuilt = {k: [] for k in selected}
    for (courier_node, edge_pos), (slot_index, row) in edge_lookup.items():
        if flow.graph[courier_node][edge_pos][1] == 0:
            task_key = slots[slot_index][0]
            rebuilt[task_key].append(row)
    if any(len(rebuilt.get(k, [])) != len(rows) for (k, rows) in selected.items()):
        return selected
    return rebuilt


# =============================================================================
# CONSTRUCTIVE: disjoint set-cover greedy + multidispatch top-up
# -----------------------------------------------------------------------------
# Greedily pick disjoint columns (each a task_key + one courier) by a mode-
# dependent score, never reusing a courier or covering a task twice. Then force-
# cover leftovers with the cheapest valid column, and finally call
# _add_extra_dispatches to add profitable extra couriers to existing groups.
# Scoring modes (saving = 100*tasks - group_cost):
#   gain  -> (saving, tasks, saving/score, willingness, -score)   prefer big saving
#   cover -> (tasks, saving/score, saving, willingness, -score)   prefer coverage
#   ratio -> (saving/score, tasks, saving, willingness, -score)   prefer efficiency
# =============================================================================
def _solve_disjoint_then_multidispatch(candidates, all_tasks, mode, deadline=None):
    selected = {}
    covered_tasks = set()
    used_couriers = set()
    while True:
        if deadline is not None and time.monotonic() > deadline - 0.25:
            break
        best_row = None
        best_key = None
        for cand in candidates:
            _key, task_ids, courier_id, score, will, _idx = cand
            if courier_id in used_couriers:
                continue
            if any(t in covered_tasks for t in task_ids):
                continue
            saving = 100.0 * len(task_ids) - _group_expected_cost([cand], len(task_ids))
            if saving <= 1e-12:
                continue
            if mode == _MODE_GAIN:
                sort_key = (saving, len(task_ids), saving / max(score, 1e-09), will, -score)
            elif mode == _MODE_COVER:
                sort_key = (len(task_ids), saving / max(score, 1e-09), saving, will, -score)
            else:
                sort_key = (saving / max(score, 1e-09), len(task_ids), saving, will, -score)
            if best_key is None or sort_key > best_key:
                best_key = sort_key
                best_row = cand
        if best_row is None:
            break
        selected[best_row[0]] = [best_row]
        used_couriers.add(best_row[2])
        for task_id in best_row[1]:
            covered_tasks.add(task_id)
    for task in sorted(all_tasks):
        if task in covered_tasks:
            continue
        options = [c for c in candidates if task in c[1] and c[2] not in used_couriers and not any(t in covered_tasks for t in c[1])]
        if not options:
            continue
        chosen = min(options, key=lambda c: _group_expected_cost([c], len(c[1])))
        selected[chosen[0]] = [chosen]
        used_couriers.add(chosen[2])
        for task_id in chosen[1]:
            covered_tasks.add(task_id)
    _add_extra_dispatches(selected, candidates, used_couriers, deadline)
    return _format_selected(selected)


def _add_extra_dispatches(selected, candidates, used_couriers, deadline=None):
    """Repeatedly add the single most cost-reducing extra courier to an existing
    group (multidispatch), mutating ``selected`` and ``used_couriers`` in place."""
    rows_by_key = {}
    for cand in candidates:
        rows_by_key.setdefault(cand[0], []).append(cand)
    improved = True
    while improved:
        if deadline is not None and time.monotonic() > deadline - 0.2:
            break
        improved = False
        best_move = None
        best_delta = 0.0
        for task_key, group in selected.items():
            bundle_task_count = len(group[0][1])
            base_cost = _group_expected_cost(group, bundle_task_count)
            for cand in rows_by_key.get(task_key, []):
                if cand[2] in used_couriers:
                    continue
                new_cost = _group_expected_cost(group, bundle_task_count, extra=cand)
                delta = new_cost - base_cost
                if delta < best_delta - 1e-12:
                    best_delta = delta
                    best_move = (task_key, cand)
        if best_move is not None:
            task_key, cand = best_move
            selected[task_key].append(cand)
            used_couriers.add(cand[2])
            improved = True


# =============================================================================
# CONSTRUCTIVE: pair-potential bundle matching
# -----------------------------------------------------------------------------
# Rank multi-task bundles by their best achievable saving (via _best_group_rows),
# then greedily claim disjoint bundles, seeding each with one courier. Remaining
# tasks are covered by their cheapest single, then extra dispatches are added.
# =============================================================================
def _solve_pair_potential_matching(candidates, all_tasks, deadline, lookahead=4, flexible_initial=False):
    rows_by_key = {}
    singles = []
    for cand in candidates:
        rows_by_key.setdefault(cand[0], []).append(cand)
        if len(cand[1]) == 1:
            singles.append(cand)
    bundle_options = []
    for key, key_rows in rows_by_key.items():
        if time.monotonic() > deadline - 0.45:
            break
        task_ids = key_rows[0][1]
        if len(task_ids) < 2:
            continue
        limit = max(lookahead, min(8, len(task_ids) + 2))
        best_rows, best_cost = _best_group_rows(key_rows, len(task_ids), limit)
        if not best_rows:
            continue
        saving = 100.0 * len(task_ids) - best_cost
        if saving <= 1e-12:
            continue
        bundle_options.append((saving, -best_cost, key, task_ids, best_rows))
    if not bundle_options:
        return []
    bundle_options.sort(reverse=True)
    selected = {}
    covered_tasks = set()
    used_couriers = set()
    for (_saving, _neg_cost, key, task_ids, best_rows) in bundle_options:
        if any(t in covered_tasks for t in task_ids):
            continue
        if flexible_initial:
            chosen = None
            for row in best_rows:
                if row[2] not in used_couriers:
                    chosen = row
                    break
            if chosen is None:
                continue
        else:
            chosen = best_rows[0]
            if chosen[2] in used_couriers:
                continue
        selected[key] = [chosen]
        used_couriers.add(chosen[2])
        for task_id in task_ids:
            covered_tasks.add(task_id)
        if len(covered_tasks) >= len(all_tasks):
            break
    for task in sorted(all_tasks):
        if task in covered_tasks:
            continue
        options = [c for c in singles if c[1][0] == task and c[2] not in used_couriers]
        if not options:
            continue
        chosen = min(options, key=lambda c: _group_expected_cost([c], 1))
        selected[task] = [chosen]
        used_couriers.add(chosen[2])
        covered_tasks.add(task)
    _add_extra_dispatches(selected, candidates, used_couriers, deadline)
    return _format_selected(selected)


def _best_group_rows(rows, task_count, limit):
    """Greedily build the (up to ``limit``) courier subset for one task_key that
    minimizes expected group cost, adding the most-reducing courier each step.
    Returns (chosen_rows, resulting_cost)."""
    chosen = []
    used = set()
    current_cost = 100.0 * task_count
    while len(chosen) < limit:
        best_row = None
        best_delta = 0.0
        best_new_cost = 0.0
        for row in rows:
            if row[2] in used:
                continue
            new_cost = _group_expected_cost(chosen, task_count, extra=row)
            delta = new_cost - current_cost
            if delta < best_delta - 1e-12:
                best_row = row
                best_delta = delta
                best_new_cost = new_cost
        if best_row is None:
            break
        chosen.append(best_row)
        used.add(best_row[2])
        current_cost = best_new_cost
    return chosen, current_cost


# =============================================================================
# ELITE COLUMN RECOMBINATION + beam set-packing (scarce regime)
# -----------------------------------------------------------------------------
# Collect a pool of high-quality "columns" (one task_key + a courier subset with
# positive saving) from (a) the best seed solutions and (b) per-key greedy/combo
# enumeration, keyed by (task_mask, courier_mask) keeping the cheapest. Prune to a
# bounded elite set, then beam-search a maximum-saving DISJOINT packing of columns.
# =============================================================================
def _solve_scarce_elite_column_recombine(candidates, all_tasks, seed_solutions, deadline):
    task_order = sorted(all_tasks)
    if not task_order:
        return []
    task_bit = {t: i for i, t in enumerate(task_order)}
    courier_bit = {cid: i for i, cid in enumerate(sorted({c[2] for c in candidates}))}
    row_map = {(c[0], c[2]): c for c in candidates}
    columns_by_masks = {}  # (task_mask, courier_mask) -> (saving, cost, t_mask, c_mask, rows, source_rank)

    def add_column(rows, source_rank=0):
        if not rows:
            return
        key = rows[0][0]
        task_ids = rows[0][1]
        if any(r[0] != key or r[1] != task_ids for r in rows):
            return  # not a single coherent task_key
        courier_ids = [r[2] for r in rows]
        if len(courier_ids) != len(set(courier_ids)):
            return  # courier reused within the column
        task_mask = 0
        for task_id in task_ids:
            bit = task_bit.get(task_id)
            if bit is None:
                return
            task_mask |= 1 << bit
        courier_mask = 0
        for courier_id in courier_ids:
            bit = courier_bit.get(courier_id)
            if bit is None:
                return
            bit_value = 1 << bit
            if courier_mask & bit_value:
                return
            courier_mask |= bit_value
        bundle_task_count = len(task_ids)
        cost = _group_expected_cost(rows, bundle_task_count)
        saving = 100.0 * bundle_task_count - cost
        if saving <= 1e-09:
            return
        masks_key = (task_mask, courier_mask)
        record = (saving, cost, task_mask, courier_mask, tuple(rows), source_rank)
        existing = columns_by_masks.get(masks_key)
        if existing is None or cost < existing[1] - 1e-09 or (abs(cost - existing[1]) <= 1e-09 and source_rank > existing[5]):
            columns_by_masks[masks_key] = record

    # (a) columns from the best seed solutions
    scored_seeds = []
    for sol in seed_solutions:
        if not sol:
            continue
        cost = _solution_expected_cost(sol, candidates, all_tasks)
        if cost < float("inf"):
            scored_seeds.append((cost, sol))
    scored_seeds.sort(key=lambda item: item[0])
    for rank, (_cost, sol) in enumerate(scored_seeds[:8]):
        selected = _result_to_selected(sol, row_map)
        source_rank = 8 - rank
        for rows in selected.values():
            add_column(tuple(rows), source_rank=source_rank)

    # (b) per-key greedy / combination columns
    rows_by_key = {}
    for cand in _canonical_candidates(candidates):
        rows_by_key.setdefault(cand[0], []).append(cand)
    for key_rows in rows_by_key.values():
        if time.monotonic() > deadline - 0.18:
            break
        cheapest_by_courier = {}
        for row in key_rows:
            existing = cheapest_by_courier.get(row[2])
            if existing is None or _group_expected_cost([row], len(row[1])) < _group_expected_cost([existing], len(existing[1])) - 1e-12:
                cheapest_by_courier[row[2]] = row
        pool = sorted(cheapest_by_courier.values(), key=lambda c: (_group_expected_cost([c], len(c[1])), -c[4], c[5]))
        if not pool:
            continue
        bundle_task_count = len(pool[0][1])
        pool_limit = 8 if bundle_task_count == 1 else 9
        pool = pool[:pool_limit]
        max_combo = 2 if bundle_task_count == 1 else min(3, len(pool))
        scored_combos = []
        for combo_size in range(1, max_combo + 1):
            for combo in itertools.combinations(pool, combo_size):
                cost = _group_expected_cost(combo, bundle_task_count)
                saving = 100.0 * bundle_task_count - cost
                if saving <= 1e-09:
                    continue
                scored_combos.append((saving, cost, tuple(combo)))
        if not scored_combos:
            continue
        # diversify across 4 different greedy orderings, top-3 each
        sort_keys = (
            lambda item: (item[0] / max(1, len(item[2])), item[0], -item[1]),
            lambda item: (item[0] / max(item[1], 1e-09), item[0], -item[1]),
            lambda item: (item[0], item[0] / max(1, len(item[2])), -item[1]),
            lambda item: (-item[1], item[0]),
        )
        chosen_combos = []
        seen_courier_tuples = set()
        for sort_key in sort_keys:
            for (_saving, _cost, combo) in sorted(scored_combos, key=sort_key, reverse=True)[:3]:
                courier_tuple = tuple(r[2] for r in combo)
                if courier_tuple in seen_courier_tuples:
                    continue
                seen_courier_tuples.add(courier_tuple)
                chosen_combos.append(combo)
        for combo in chosen_combos[:7]:
            add_column(combo, source_rank=0)

    elite_columns = list(columns_by_masks.values())
    if not elite_columns:
        return []
    elite_columns = _scarce_prune_elite_columns(elite_columns, max_columns=1150)
    packing_indices = _scarce_beam_pack_columns(elite_columns, deadline, beam_width=5200)
    if not packing_indices:
        return []
    result = []
    for col_index in packing_indices:
        ordered = sorted(elite_columns[col_index][4], key=lambda c: (c[3], -c[4], c[5]))
        result.append((ordered[0][0], [r[2] for r in ordered]))
    # stable order: by the canonical row_index of the leading (key, first courier)
    result.sort(key=lambda item: row_map.get((item[0], item[1][0]), ("", ("",), "", 0.0, 0.0, 0))[1])
    return result


def _scarce_column_order_key(column):
    """Ranking key for an elite column (used with reverse=True, so higher==better).
    Order: source_rank, saving-per-courier, #tasks, saving-per-cost, saving, -size."""
    saving, cost, task_mask, courier_mask, rows, source_rank = column
    task_pop = _popcount(task_mask)
    courier_pop = _popcount(courier_mask)
    return (source_rank, saving / max(1, courier_pop), task_pop, saving / max(cost, 1e-09), saving, -len(rows))


def _scarce_prune_elite_columns(columns, max_columns):
    """Keep a bounded, diverse elite subset of columns. Below the cap, just sort
    by the order key; above it, round-robin the top of 4 different orderings,
    deduplicating by (task_mask, courier_mask)."""
    if len(columns) <= max_columns:
        return sorted(columns, key=_scarce_column_order_key, reverse=True)
    kept = []
    seen_masks = set()
    sort_keys = (
        lambda c: (c[5], c[0] / max(1, _popcount(c[3])), c[0], _popcount(c[2])),
        lambda c: (_popcount(c[2]), c[0] / max(1, _popcount(c[3])), c[0] / max(c[1], 1e-09)),
        lambda c: (c[0], c[0] / max(c[1], 1e-09), -c[1]),
        lambda c: (c[0] / max(1, _popcount(c[2])), c[0], -_popcount(c[3])),
    )
    per_key = max_columns // len(sort_keys) + 25
    for sort_key in sort_keys:
        for col in sorted(columns, key=sort_key, reverse=True)[:per_key]:
            masks = (col[2], col[3])
            if masks in seen_masks:
                continue
            seen_masks.add(masks)
            kept.append(col)
            if len(kept) >= max_columns:
                break
        if len(kept) >= max_columns:
            break
    return sorted(kept, key=_scarce_column_order_key, reverse=True)


def _scarce_beam_pack_columns(columns, deadline, beam_width):
    """Beam search over disjoint column packings maximizing total saving. State =
    (task_mask, courier_mask) -> (best_saving, column_index_tuple). Returns the
    column-index tuple of the best packing found."""
    states = {(0, 0): (0.0, ())}
    best_saving = 0.0
    best_indices = ()
    for col_index, column in enumerate(columns):
        if time.monotonic() > deadline - 0.05:
            break
        saving, _cost, task_mask, courier_mask, _rows, _source = column
        additions = []
        for (state_task_mask, state_courier_mask), (state_saving, indices) in states.items():
            if state_task_mask & task_mask or state_courier_mask & courier_mask:
                continue
            new_masks = (state_task_mask | task_mask, state_courier_mask | courier_mask)
            new_saving = state_saving + saving
            existing = states.get(new_masks)
            if existing is None or new_saving > existing[0] + 1e-09:
                additions.append((new_masks, (new_saving, indices + (col_index,))))
                if new_saving > best_saving + 1e-09:
                    best_saving = new_saving
                    best_indices = indices + (col_index,)
        for new_masks, payload in additions:
            existing = states.get(new_masks)
            if existing is None or payload[0] > existing[0] + 1e-09:
                states[new_masks] = payload
        if len(states) > beam_width * 2:
            states = dict(sorted(states.items(), key=lambda item: (item[1][0], _popcount(item[0][0]), -_popcount(item[0][1])), reverse=True)[:beam_width])
    if best_indices:
        return best_indices
    _best_masks, (_best_saving, indices) = max(states.items(), key=lambda item: (item[1][0], _popcount(item[0][0]), -_popcount(item[0][1])))
    return indices


# =============================================================================
# LNS / REPAIR-WINDOW INFRASTRUCTURE (ALNS operators)
# -----------------------------------------------------------------------------
# The generic move: pick a "window" of tasks (a small subset), tear out the groups
# touching those tasks, and re-optimize ONLY that window with the exact column
# search (_repair_task_window -> _search_column_window), keeping the rest fixed.
# Windows are chosen by several destroy heuristics: worst groups first ("ranked"),
# bundle-adjacent to a seed ("related"), around an uncovered task ("uncovered"),
# or random walks over the adjacency graph ("random"). The ALNS variants below
# differ only in which destroy operators they cycle and how they accept results.
# =============================================================================
def _selected_repair_groups(selected):
    """For each group emit (cost_per_task, #tasks, task_key, task_ids, rows). Used
    as the ranking input to window selection (worst cost-per-task first)."""
    groups = []
    for task_key, rows in selected.items():
        if rows:
            task_ids = rows[0][1]
            cost = _group_expected_cost(rows, len(task_ids))
            groups.append((cost / max(1, len(task_ids)), len(task_ids), task_key, task_ids, rows))
    return groups


def _ranked_repair_window(ranked_groups, max_window_tasks):
    """Accumulate task ids from the (already ranked) groups until adding the next
    group would exceed ``max_window_tasks``."""
    window = set()
    for (_cost_per_task, _count, _key, task_ids, _rows) in ranked_groups:
        grown = window | set(task_ids)
        if len(grown) > max_window_tasks:
            continue
        window = grown
        if len(window) >= max_window_tasks:
            break
    return window


def _related_repair_window(seed_tasks, selected, adjacency, max_window_tasks):
    """Grow a window outward from ``seed_tasks`` along bundle adjacency, pulling in
    the whole covering group of each neighbour, up to ``max_window_tasks``."""
    window = set(seed_tasks)
    frontier = list(seed_tasks)
    while frontier and len(window) < max_window_tasks:
        current = frontier.pop(0)
        for neighbour in sorted(adjacency.get(current, ())):
            if neighbour in window:
                continue
            group_tasks = _selected_group_tasks_containing(selected, neighbour)
            if not group_tasks:
                group_tasks = {neighbour}
            if len(window | group_tasks) > max_window_tasks:
                continue
            window |= group_tasks
            frontier.extend(sorted(group_tasks - {neighbour}))
            if len(window) >= max_window_tasks:
                break
    return window


def _uncovered_repair_window(task_id, selected, adjacency, max_window_tasks):
    """Build a window around an UNCOVERED task: its bundle neighbours' groups
    first (smallest first), then top up with the worst existing groups."""
    window = {task_id}
    neighbour_groups = []
    for neighbour in sorted(adjacency.get(task_id, ())):
        group_tasks = _selected_group_tasks_containing(selected, neighbour) or {neighbour}
        neighbour_groups.append((len(group_tasks), neighbour, group_tasks))
    neighbour_groups.sort()
    for (_size, _neighbour, group_tasks) in neighbour_groups:
        if len(window | group_tasks) > max_window_tasks:
            continue
        window |= group_tasks
        if len(window) >= max_window_tasks:
            break
    if len(window) < max_window_tasks:
        worst_groups = _selected_repair_groups(selected)
        worst_groups.sort(reverse=True)
        for (_cpt, _count, _key, task_ids, _rows) in worst_groups:
            group_tasks = set(task_ids)
            if window & group_tasks:
                continue
            if len(window | group_tasks) > max_window_tasks:
                continue
            window |= group_tasks
            if len(window) >= max_window_tasks:
                break
    return window


def _random_repair_window(seed_tasks, selected, adjacency, max_window_tasks, rng):
    """Random-walk window growth from a seed group along bundle adjacency."""
    window = set(seed_tasks)
    steps = 0
    while len(window) < max_window_tasks and steps < max_window_tasks * 3:
        steps += 1
        pivot = rng.choice(tuple(window))
        neighbours = sorted(adjacency.get(pivot, ()))
        if not neighbours:
            break
        neighbour = neighbours[rng.randrange(len(neighbours))]
        group_tasks = _selected_group_tasks_containing(selected, neighbour) or {neighbour}
        if len(window | group_tasks) <= max_window_tasks:
            window |= group_tasks
    return window


def _repair_task_window(selected, candidates, all_tasks, window_tasks, deadline, top_riders_per_task_key=10, max_k=3, option_limit=70):
    """Freeze the groups OUTSIDE the window, then exactly re-solve the window with
    _search_column_window over only the rows that touch the window's tasks, do not
    reuse a frozen courier, and do not spill onto frozen tasks. Returns the full
    repaired solution, or [] if the window cannot be solved."""
    del all_tasks
    frozen = {}
    for task_key, rows in selected.items():
        if not set(rows[0][1]) & window_tasks:
            frozen[task_key] = rows
    frozen_tasks = {t for rows in frozen.values() for t in rows[0][1]}
    frozen_couriers = {r[2] for rows in frozen.values() for r in rows}
    window_rows = [
        c for c in candidates
        if c[2] not in frozen_couriers and set(c[1]) <= window_tasks and not set(c[1]) & frozen_tasks
    ]
    if not window_rows:
        return []
    repaired_window = _search_column_window(window_rows, window_tasks, deadline, top_riders_per_task_key=top_riders_per_task_key, max_k=max_k, option_limit=option_limit)
    if not repaired_window:
        return []
    return _format_selected(frozen) + repaired_window


def _repair_worst_window_solution(result, candidates, all_tasks, deadline, top_riders_per_task_key=10, max_k=3, option_limit=70):
    """Repair the window of the worst-cost-per-task groups (a couple of offsets and
    window sizes), accepting any strictly cheaper result."""
    row_map = {(c[0], c[2]): c for c in candidates}
    selected = _result_to_selected(result, row_map)
    if not selected:
        return result
    groups = []
    for task_key, rows in selected.items():
        if rows:
            task_ids = rows[0][1]
            cost = _group_expected_cost(rows, len(task_ids))
            groups.append((cost / max(1, len(task_ids)), len(task_ids), task_key, task_ids, rows))
    if not groups:
        return result
    ranked = sorted(groups, reverse=True)
    best = result
    best_cost = _solution_expected_cost(result, candidates, all_tasks)
    seen_windows = set()
    for (window_size, offsets) in ((10, (0, 3, 6)), (14, (0,))):
        for offset in offsets:
            if time.monotonic() > deadline - 0.08:
                return best
            window = _ranked_repair_window(ranked[offset:], window_size)
            if not window:
                continue
            window_key = tuple(sorted(window))
            if window_key in seen_windows:
                continue
            seen_windows.add(window_key)
            repaired = _repair_task_window(selected, candidates, all_tasks, window, min(deadline, time.monotonic() + 0.22), top_riders_per_task_key=top_riders_per_task_key, max_k=max_k, option_limit=option_limit)
            if not repaired:
                continue
            cost = _solution_expected_cost(repaired, candidates, all_tasks)
            if cost < best_cost - 1e-09:
                best = repaired
                best_cost = cost
    return best


def _column_alns_repair_solution(result, candidates, all_tasks, deadline, mode, max_window_tasks, top_riders_per_task_key, option_limit, max_k=3):
    """Adaptive LNS: cycle ranked + related + uncovered + random destroy windows,
    re-solving each window and accepting per ``mode`` (scarce / low / cost-only)."""
    row_map = {(c[0], c[2]): c for c in candidates}
    selected = _result_to_selected(result, row_map)
    if not selected:
        return result
    best = result
    repair_groups = _selected_repair_groups(selected)
    if not repair_groups:
        return result
    ranked = sorted(repair_groups, reverse=True)
    adjacency = _task_adjacency(candidates)
    windows = []
    for offset in (0, 3, 6):
        windows.append(_ranked_repair_window(ranked[offset:], max_window_tasks))
    for (_cpt, _count, _key, task_ids, _rows) in ranked[:6]:
        windows.append(_related_repair_window(task_ids, selected, adjacency, max_window_tasks))
    covered = {t for rows in selected.values() for t in rows[0][1]}
    for uncovered_task in sorted(set(all_tasks) - covered):
        windows.append(_uncovered_repair_window(uncovered_task, selected, adjacency, max_window_tasks))
    rng = random.Random(20260512 + len(all_tasks) * 17 + len(candidates))
    for _ in range(8):
        if not ranked:
            break
        seed_group = ranked[rng.randrange(min(len(ranked), 12))]
        windows.append(_random_repair_window(seed_group[3], selected, adjacency, max_window_tasks, rng))
    seen_windows = set()
    for window in windows:
        if time.monotonic() > deadline - 0.08:
            break
        if not window:
            continue
        window_key = tuple(sorted(window))
        if window_key in seen_windows:
            continue
        seen_windows.add(window_key)
        current_selected = _result_to_selected(best, row_map)
        repaired = _repair_task_window(current_selected, candidates, all_tasks, window, min(deadline, time.monotonic() + 0.18), top_riders_per_task_key=top_riders_per_task_key, max_k=max_k, option_limit=option_limit)
        if not repaired:
            continue
        best = _pick_repair_best(best, repaired, candidates, all_tasks, mode)
    return best


def _low_worst_window_repair_solution(result, candidates, all_tasks, deadline):
    """Low-willingness worst-window repair, accepting via the robustness pick."""
    row_map = {(c[0], c[2]): c for c in candidates}
    selected = _result_to_selected(result, row_map)
    if not selected:
        return result
    repair_groups = _selected_repair_groups(selected)
    if not repair_groups:
        return result
    ranked = sorted(repair_groups, reverse=True)
    best = result
    seen_windows = set()
    for (window_size, offsets) in ((8, range(0, 8)), (10, range(0, 8)), (12, range(0, 8))):
        for offset in offsets:
            if time.monotonic() > deadline - 0.08:
                return best
            window = _ranked_repair_window(ranked[offset:], window_size)
            if not window:
                continue
            window_key = tuple(sorted(window))
            if window_key in seen_windows:
                continue
            seen_windows.add(window_key)
            current_selected = _result_to_selected(best, row_map)
            repaired = _repair_task_window(current_selected, candidates, all_tasks, window, min(deadline, time.monotonic() + 0.22), top_riders_per_task_key=12, max_k=4, option_limit=90)
            if not repaired:
                continue
            best = _pick_low_robust_best([best, repaired], candidates, all_tasks)
    return best


def _low_deep_window_repair_solution(result, candidates, all_tasks, deadline):
    """Deeper low-willingness window repair (more couriers/options per window)."""
    row_map = {(c[0], c[2]): c for c in candidates}
    selected = _result_to_selected(result, row_map)
    if not selected:
        return result
    repair_groups = _selected_repair_groups(selected)
    if not repair_groups:
        return result
    ranked = sorted(repair_groups, reverse=True)
    best = result
    seen_windows = set()
    for window_size in (8, 10, 12):
        for offset in range(10):
            if time.monotonic() > deadline - 0.08:
                return best
            window = _ranked_repair_window(ranked[offset:], window_size)
            if not window:
                continue
            window_key = tuple(sorted(window))
            if window_key in seen_windows:
                continue
            seen_windows.add(window_key)
            current_selected = _result_to_selected(best, row_map)
            repaired = _repair_task_window(current_selected, candidates, all_tasks, window, min(deadline, time.monotonic() + 0.2), top_riders_per_task_key=13, max_k=5, option_limit=110)
            if not repaired:
                continue
            best = _pick_low_robust_best([best, repaired], candidates, all_tasks)
    return best


def _low_late_acceptance_repair_solution(result, candidates, all_tasks, deadline):
    """Late-Acceptance Hill Climbing for the low-willingness regime. Cycles destroy
    operators; accepts a repair if it beats the current cost OR a cost from
    ``history_len`` iterations ago (with a small +4 slack), escaping local minima.
    Returns the robustness-pick of the original vs. the best seen."""
    row_map = {(c[0], c[2]): c for c in candidates}
    adjacency = _task_adjacency(candidates)
    rng = random.Random(70331 + len(candidates))
    current = result
    best_seen = result
    current_cost = _solution_expected_cost(current, candidates, all_tasks)
    best_cost = current_cost
    history = [current_cost] * 10
    iteration = 0
    while time.monotonic() < deadline - 0.12:
        current_selected = _result_to_selected(current, row_map)
        ranked = sorted(_selected_repair_groups(current_selected), reverse=True)
        if not ranked:
            break
        window_size = (8, 10, 12, 14)[iteration % 4]
        operator = iteration % 5
        if operator == 0:
            offset = iteration * 3 % min(14, len(ranked))
            window = _ranked_repair_window(ranked[offset:], window_size)
        elif operator in (1, 2):
            seed_group = ranked[(iteration * 5 + operator) % min(12, len(ranked))]
            window = _related_repair_window(seed_group[3], current_selected, adjacency, window_size)
        elif operator == 3:
            seed_group = ranked[rng.randrange(min(14, len(ranked)))]
            window = _random_repair_window(seed_group[3], current_selected, adjacency, window_size, rng)
        else:
            seed_group = ranked[iteration * 2 % min(10, len(ranked))]
            window = set(seed_group[3])
            for group in ranked:
                grown = window | set(group[3])
                if len(grown) <= window_size:
                    window = grown
                if len(window) >= window_size:
                    break
        if not window:
            iteration += 1
            continue
        repaired = _repair_task_window(current_selected, candidates, all_tasks, window, min(deadline, time.monotonic() + 0.12), top_riders_per_task_key=13, max_k=5, option_limit=110)
        if not repaired:
            iteration += 1
            continue
        repaired_cost = _solution_expected_cost(repaired, candidates, all_tasks)
        history_index = iteration % len(history)
        if repaired_cost < best_cost - 1e-09:
            best_seen = repaired
            best_cost = repaired_cost
        if repaired_cost < current_cost - 1e-09 or repaired_cost <= history[history_index] + 4.0:
            current = repaired
            current_cost = repaired_cost
        history[history_index] = current_cost
        iteration += 1
    return _pick_low_robust_best([result, best_seen], candidates, all_tasks)


def _normal_worst_related_repair_solution(result, candidates, all_tasks, deadline):
    """Medium-dense regime repair: cycle ranked + related windows, accept cheaper."""
    row_map = {(c[0], c[2]): c for c in candidates}
    selected = _result_to_selected(result, row_map)
    if not selected:
        return result
    repair_groups = _selected_repair_groups(selected)
    if not repair_groups:
        return result
    ranked = sorted(repair_groups, reverse=True)
    adjacency = _task_adjacency(candidates)
    windows = []
    for window_size in (8, 10, 12):
        for offset in range(min(8, len(ranked))):
            windows.append(_ranked_repair_window(ranked[offset:], window_size))
    for (_cpt, _count, _key, task_ids, _rows) in ranked[:8]:
        for window_size in (8, 10):
            windows.append(_related_repair_window(task_ids, selected, adjacency, window_size))
    best = result
    seen_windows = set()
    for window in windows:
        if time.monotonic() > deadline - 0.08:
            break
        if not window:
            continue
        window_key = tuple(sorted(window))
        if window_key in seen_windows:
            continue
        seen_windows.add(window_key)
        current_selected = _result_to_selected(best, row_map)
        repaired = _repair_task_window(current_selected, candidates, all_tasks, window, min(deadline, time.monotonic() + 0.16), top_riders_per_task_key=10, max_k=4, option_limit=80)
        if not repaired:
            continue
        if _solution_expected_cost(repaired, candidates, all_tasks) < _solution_expected_cost(best, candidates, all_tasks) - 1e-09:
            best = repaired
    return best


# =============================================================================
# BUNDLE-INSERTION REPAIR + PAIR/TRIPLE COLUMN EXCHANGE + EJECT + COURIER SHIFT
# -----------------------------------------------------------------------------
# More LNS operators. Bundle-insertion repair tries to merge singles into a
# profitable multi-task bundle and re-solves the affected window. Pair/triple
# column exchange tears out 2 (resp. 3) high-cost groups together and re-solves
# their combined window. Eject moves a redundant extra courier off a multidispatch
# group onto an uncovered task. Courier shift relocates one courier between groups.
# Every operator is gated on a strict cost improvement.
# =============================================================================
def _scarce_bundle_insertion_repair_solution(result, candidates, all_tasks, deadline, max_windows, max_window_tasks, use_courier_pressure=False):
    row_map = {(c[0], c[2]): c for c in candidates}
    selected = _result_to_selected(result, row_map)
    if not selected:
        return result
    covered_tasks = {t for rows in selected.values() for t in rows[0][1]}
    task_to_group_key = {}
    for group_key, rows in selected.items():
        for task_id in rows[0][1]:
            task_to_group_key[task_id] = group_key
    courier_pressure = {}
    if use_courier_pressure:
        for rows in selected.values():
            group_tasks = set(rows[0][1])
            for row in rows:
                courier_pressure[row[2]] = group_tasks
    bundle_rows_by_key = {}
    for cand in candidates:
        if len(cand[1]) >= 2:
            bundle_rows_by_key.setdefault(cand[0], []).append(cand)
    if not bundle_rows_by_key:
        return result

    insertion_candidates = []
    for _bundle_key, bundle_rows in bundle_rows_by_key.items():
        if time.monotonic() > deadline - 0.08:
            break
        bundle_tasks = bundle_rows[0][1]
        bundle_task_set = set(bundle_tasks)
        best_group = _best_group_from_pool(
            sorted(bundle_rows, key=lambda c: (_group_expected_cost([c], len(bundle_tasks)), -c[4], c[5]))[:9],
            len(bundle_tasks), min(5, len(bundle_rows)),
        )
        if not best_group:
            continue
        bundle_cost = _group_expected_cost(best_group, len(bundle_tasks))
        bundle_saving = 100.0 * len(bundle_tasks) - bundle_cost
        if bundle_saving <= 1e-09:
            continue
        displaced_keys = {task_to_group_key[t] for t in bundle_tasks if t in task_to_group_key}
        displaced_tasks = set()
        displaced_cost = 0.0
        for key in displaced_keys:
            group = selected.get(key)
            if not group:
                continue
            displaced_tasks.update(group[0][1])
            displaced_cost += _group_expected_cost(group, len(group[0][1]))
        newly_covered = len(bundle_task_set - covered_tasks)
        net_delta = bundle_cost - displaced_cost - 100.0 * newly_covered
        pressure_tasks = set()
        if use_courier_pressure:
            for row in best_group:
                pressure_tasks.update(courier_pressure.get(row[2], ()))
        insertion_candidates.append((newly_covered, -net_delta, bundle_saving / max(1, len(best_group)), len(bundle_tasks), bundle_task_set, pressure_tasks))
    if not insertion_candidates:
        return result

    adjacency = _task_adjacency(candidates)
    insertion_candidates.sort(reverse=True)
    best = result
    best_cost = _solution_expected_cost(best, candidates, all_tasks)
    seen_windows = set()
    windows_done = 0
    for (_newly, _neg_delta, _ratio, _count, bundle_task_set, pressure_tasks) in insertion_candidates:
        if windows_done >= max_windows or time.monotonic() > deadline - 0.06:
            break
        window = set(bundle_task_set) | set(pressure_tasks)
        for task_id in sorted(bundle_task_set):
            group_key = task_to_group_key.get(task_id)
            if group_key is not None and group_key in selected:
                window.update(selected[group_key][0][1])
        if len(window) < max_window_tasks:
            for task_id in sorted(bundle_task_set):
                for neighbour in sorted(adjacency.get(task_id, ())):
                    neighbour_group_tasks = _selected_group_tasks_containing(selected, neighbour) or {neighbour}
                    if len(window | neighbour_group_tasks) > max_window_tasks:
                        continue
                    window |= neighbour_group_tasks
                    if len(window) >= max_window_tasks:
                        break
                if len(window) >= max_window_tasks:
                    break
        if len(window) > max_window_tasks:
            ordered = sorted(window, key=lambda task_id: (task_id not in bundle_task_set, task_id not in pressure_tasks, task_id))
            window = set(ordered[:max_window_tasks])
        window_key = tuple(sorted(window))
        if window_key in seen_windows:
            continue
        seen_windows.add(window_key)
        windows_done += 1
        current_selected = _result_to_selected(best, row_map)
        repaired = _repair_task_window(current_selected, candidates, all_tasks, window, min(deadline, time.monotonic() + 0.12), top_riders_per_task_key=9, max_k=4, option_limit=65)
        if not repaired:
            continue
        if time.monotonic() < deadline - 0.05:
            repaired = _reassign_mixed_solution(repaired, candidates, all_tasks, min(deadline, time.monotonic() + 0.05))
        repaired_cost = _solution_expected_cost(repaired, candidates, all_tasks)
        if repaired_cost < best_cost - 1e-09:
            best = repaired
            best_cost = repaired_cost
    return best


def _pairwise_column_exchange_solution(result, candidates, all_tasks, deadline, top_riders_per_task_key, max_k, option_limit, max_window_tasks, max_pairs):
    row_map = {(c[0], c[2]): c for c in candidates}
    selected = _result_to_selected(result, row_map)
    if not selected:
        return result
    group_entries = []  # (cost_per_task, task_key, task_set)
    for task_key, rows in selected.items():
        if not rows:
            continue
        task_set = set(rows[0][1])
        cost = _group_expected_cost(rows, len(rows[0][1]))
        group_entries.append((cost / max(1, len(task_set)), task_key, task_set))
    if len(group_entries) < 2:
        return result
    group_entries.sort(reverse=True)
    pairs = []
    for i, entry_a in enumerate(group_entries[:10]):
        for entry_b in group_entries[i + 1:i + 12]:
            if len(entry_a[2] | entry_b[2]) <= max_window_tasks:
                pairs.append((entry_a, entry_b))
    for cand in candidates:
        if len(cand[1]) < 2:
            continue
        cand_task_set = set(cand[1])
        touching = [e for e in group_entries[:14] if e[2] & cand_task_set]
        for i, entry_a in enumerate(touching):
            for entry_b in touching[i + 1:]:
                if len(entry_a[2] | entry_b[2]) <= max_window_tasks:
                    pairs.append((entry_a, entry_b))
    best = result
    best_cost = _solution_expected_cost(best, candidates, all_tasks)
    seen_windows = set()
    pairs_done = 0
    for (entry_a, entry_b) in pairs:
        if pairs_done >= max_pairs or time.monotonic() > deadline - 0.04:
            break
        window = entry_a[2] | entry_b[2]
        window_key = tuple(sorted(window))
        if window_key in seen_windows:
            continue
        seen_windows.add(window_key)
        pairs_done += 1
        current_selected = _result_to_selected(best, row_map)
        repaired = _repair_task_window(current_selected, candidates, all_tasks, window, min(deadline, time.monotonic() + 0.1), top_riders_per_task_key=top_riders_per_task_key, max_k=max_k, option_limit=option_limit)
        if not repaired:
            continue
        if time.monotonic() < deadline - 0.05:
            repaired = _reassign_mixed_solution(repaired, candidates, all_tasks, min(deadline, time.monotonic() + 0.06))
        repaired_cost = _solution_expected_cost(repaired, candidates, all_tasks)
        if repaired_cost < best_cost - 1e-09:
            best = repaired
            best_cost = repaired_cost
    return best


def _triple_column_exchange_solution(result, candidates, all_tasks, deadline, top_riders_per_task_key, max_k, option_limit, max_window_tasks, max_triples):
    row_map = {(c[0], c[2]): c for c in candidates}
    selected = _result_to_selected(result, row_map)
    if not selected:
        return result
    group_entries = []
    for task_key, rows in selected.items():
        if not rows:
            continue
        task_set = set(rows[0][1])
        cost = _group_expected_cost(rows, len(rows[0][1]))
        group_entries.append((cost / max(1, len(task_set)), task_key, task_set))
    if len(group_entries) < 3:
        return result
    group_entries.sort(reverse=True)
    triples = []
    for combo in itertools.combinations(group_entries[:9], 3):
        window = set().union(*(e[2] for e in combo))
        if len(window) <= max_window_tasks:
            triples.append(combo)
    for cand in candidates:
        if len(cand[1]) < 2:
            continue
        cand_task_set = set(cand[1])
        touching = [e for e in group_entries[:12] if e[2] & cand_task_set]
        for combo in itertools.combinations(touching[:6], 3):
            window = set().union(*(e[2] for e in combo))
            if len(window) <= max_window_tasks:
                triples.append(combo)
    best = result
    best_cost = _solution_expected_cost(best, candidates, all_tasks)
    seen_windows = set()
    triples_done = 0
    for combo in triples:
        if triples_done >= max_triples or time.monotonic() > deadline - 0.04:
            break
        window = set().union(*(e[2] for e in combo))
        window_key = tuple(sorted(window))
        if window_key in seen_windows:
            continue
        seen_windows.add(window_key)
        triples_done += 1
        current_selected = _result_to_selected(best, row_map)
        repaired = _repair_task_window(current_selected, candidates, all_tasks, window, min(deadline, time.monotonic() + 0.11), top_riders_per_task_key=top_riders_per_task_key, max_k=max_k, option_limit=option_limit)
        if not repaired:
            continue
        if time.monotonic() < deadline - 0.05:
            repaired = _reassign_mixed_solution(repaired, candidates, all_tasks, min(deadline, time.monotonic() + 0.06))
        repaired_cost = _solution_expected_cost(repaired, candidates, all_tasks)
        if repaired_cost < best_cost - 1e-09:
            best = repaired
            best_cost = repaired_cost
    return best


def _scarce_eject_extra_to_uncovered(result, candidates, all_tasks, deadline):
    """Move a redundant extra courier off a multidispatch group onto an uncovered
    task whenever that lowers total cost (donor loses a courier; the courier's
    single row covers the uncovered task)."""
    row_map = {(c[0], c[2]): c for c in candidates}
    selected = _result_to_selected(result, row_map)
    if not selected:
        return result
    rows_by_courier = {}
    for cand in candidates:
        rows_by_courier.setdefault(cand[2], []).append(cand)
    while time.monotonic() < deadline - 0.04:
        covered = {t for rows in selected.values() for t in rows[0][1]}
        uncovered = set(all_tasks) - covered
        if not uncovered:
            break
        best_move = None
        best_delta = 0.0
        active_keys = set(selected)
        for donor_key, donor_rows in list(selected.items()):
            if time.monotonic() > deadline - 0.04:
                break
            if len(donor_rows) <= 1:
                continue
            bundle_task_count = len(donor_rows[0][1])
            donor_base = _group_expected_cost(donor_rows, bundle_task_count)
            for row in donor_rows:
                donor_remaining = [r for r in donor_rows if r != row]
                if not donor_remaining:
                    continue
                donor_delta = _group_expected_cost(donor_remaining, bundle_task_count) - donor_base
                for cand in rows_by_courier.get(row[2], ()):
                    if cand[0] in active_keys:
                        continue
                    cand_tasks = set(cand[1])
                    if not cand_tasks or not cand_tasks <= uncovered:
                        continue
                    cand_cost = _group_expected_cost([cand], len(cand[1]))
                    delta = donor_delta + cand_cost - 100.0 * len(cand[1])
                    if delta < best_delta - 1e-09:
                        best_delta = delta
                        best_move = (donor_key, row, cand)
        if best_move is None:
            break
        donor_key, row, cand = best_move
        selected[donor_key] = [r for r in selected[donor_key] if r != row]
        selected[cand[0]] = [cand]
    return _format_selected(selected)


def _shift_couriers_between_groups(result, candidates, all_tasks, deadline, max_moves):
    """Relocate one courier at a time from its current group to a different group
    that can also serve it, taking the best improving move; commit only if the
    final solution is strictly cheaper than the input."""
    row_map = {(c[0], c[2]): c for c in candidates}
    selected = _result_to_selected(result, row_map)
    if not selected:
        return result
    rows_by_courier = {}
    for cand in candidates:
        rows_by_courier.setdefault(cand[2], []).append(cand)
    moves_done = 0
    while moves_done < max_moves and time.monotonic() < deadline - 0.04:
        best_move = None
        best_delta = 0.0
        for donor_key, donor_rows in list(selected.items()):
            if time.monotonic() > deadline - 0.04:
                break
            if not donor_rows:
                continue
            donor_task_count = len(donor_rows[0][1])
            donor_base = _group_expected_cost(donor_rows, donor_task_count)
            for row in donor_rows:
                donor_remaining = [r for r in donor_rows if r != row]
                donor_after = _group_expected_cost(donor_remaining, donor_task_count) if donor_remaining else 100.0 * donor_task_count
                donor_delta = donor_after - donor_base
                for moved_row in rows_by_courier.get(row[2], ()):
                    receiver_key = moved_row[0]
                    if receiver_key == donor_key or receiver_key not in selected:
                        continue
                    receiver_rows = selected[receiver_key]
                    if any(r[2] == row[2] for r in receiver_rows):
                        continue
                    receiver_task_count = len(receiver_rows[0][1])
                    receiver_base = _group_expected_cost(receiver_rows, receiver_task_count)
                    receiver_after = _group_expected_cost(receiver_rows, receiver_task_count, extra=moved_row)
                    delta = donor_delta + receiver_after - receiver_base
                    if delta < best_delta - 1e-09:
                        best_delta = delta
                        best_move = (donor_key, row, receiver_key, moved_row)
        if best_move is None:
            break
        donor_key, row, receiver_key, moved_row = best_move
        selected[donor_key] = [r for r in selected[donor_key] if r != row]
        if not selected[donor_key]:
            del selected[donor_key]
        selected[receiver_key].append(moved_row)
        moves_done += 1
    formatted = _format_selected(selected)
    if _solution_expected_cost(formatted, candidates, all_tasks) < _solution_expected_cost(result, candidates, all_tasks) - 1e-09:
        return formatted
    return result


def _scarce_polish_candidate(result, candidates, all_tasks, deadline):
    """A fixed polishing chain for a scarce-regime candidate: local-improve,
    reassign, ALNS column repair, bundle insertion, pair/triple exchange, eject,
    courier shift, final reassign. Each step is gated on a strict improvement."""
    polished = result
    if time.monotonic() < deadline - 0.18:
        polished = _local_improve_mixed_solution(polished, candidates, all_tasks, deadline, include_pair_rewire=True)
    if time.monotonic() < deadline - 0.3:
        polished = _reassign_mixed_solution(polished, candidates, all_tasks, deadline)
        polished = _drop_unprofitable_groups(polished, candidates, all_tasks)
    if time.monotonic() < deadline - 0.18:
        polished = _local_improve_mixed_solution(polished, candidates, all_tasks, deadline, include_pair_rewire=True)
        polished = _drop_unprofitable_groups(polished, candidates, all_tasks)
    if time.monotonic() < deadline - 0.85:
        polished = _column_alns_repair_solution(polished, candidates, all_tasks, min(deadline, time.monotonic() + 0.75), mode=_MODE_SCARCE, max_window_tasks=12, top_riders_per_task_key=8, option_limit=55, max_k=4)
        polished = _drop_unprofitable_groups(polished, candidates, all_tasks)
    if time.monotonic() < deadline - 0.45:
        repaired = _scarce_bundle_insertion_repair_solution(polished, candidates, all_tasks, min(deadline, time.monotonic() + 0.34), max_windows=34, max_window_tasks=14)
        if _solution_expected_cost(repaired, candidates, all_tasks) < _solution_expected_cost(polished, candidates, all_tasks) - 1e-09:
            polished = _drop_unprofitable_groups(repaired, candidates, all_tasks)
    if time.monotonic() < deadline - 0.35:
        exchanged = _pairwise_column_exchange_solution(polished, candidates, all_tasks, min(deadline, time.monotonic() + 0.3), top_riders_per_task_key=8, max_k=4, option_limit=55, max_window_tasks=10, max_pairs=28)
        if _solution_expected_cost(exchanged, candidates, all_tasks) < _solution_expected_cost(polished, candidates, all_tasks) - 1e-09:
            polished = _drop_unprofitable_groups(exchanged, candidates, all_tasks)
    if time.monotonic() < deadline - 0.32:
        exchanged = _triple_column_exchange_solution(polished, candidates, all_tasks, min(deadline, time.monotonic() + 0.27), top_riders_per_task_key=8, max_k=4, option_limit=60, max_window_tasks=12, max_triples=16)
        if _solution_expected_cost(exchanged, candidates, all_tasks) < _solution_expected_cost(polished, candidates, all_tasks) - 1e-09:
            polished = _drop_unprofitable_groups(exchanged, candidates, all_tasks)
    if time.monotonic() < deadline - 0.24:
        ejected = _scarce_eject_extra_to_uncovered(polished, candidates, all_tasks, min(deadline, time.monotonic() + 0.18))
        if _solution_expected_cost(ejected, candidates, all_tasks) < _solution_expected_cost(polished, candidates, all_tasks) - 1e-09:
            polished = _drop_unprofitable_groups(ejected, candidates, all_tasks)
    if time.monotonic() < deadline - 0.22:
        shifted = _shift_couriers_between_groups(polished, candidates, all_tasks, min(deadline, time.monotonic() + 0.18), max_moves=18)
        if _solution_expected_cost(shifted, candidates, all_tasks) < _solution_expected_cost(polished, candidates, all_tasks) - 1e-09:
            polished = _drop_unprofitable_groups(shifted, candidates, all_tasks)
    if time.monotonic() < deadline - 0.22:
        reassigned = _reassign_mixed_solution(polished, candidates, all_tasks, min(deadline, time.monotonic() + 0.35))
        if _solution_expected_cost(reassigned, candidates, all_tasks) < _solution_expected_cost(polished, candidates, all_tasks) - 1e-09:
            polished = reassigned
    return polished


def _pick_repair_best(best, candidate, candidates, all_tasks, mode):
    """Accept a repaired solution over the incumbent according to ``mode``:
    'scarce' uses the scarce pick, 'low' the robustness pick, otherwise strict
    cost-only improvement."""
    if mode == _MODE_SCARCE:
        return _pick_scarce_best([best, candidate], candidates, all_tasks)
    if mode == "low":
        return _pick_low_robust_best([best, candidate], candidates, all_tasks)
    if _solution_expected_cost(candidate, candidates, all_tasks) < _solution_expected_cost(best, candidates, all_tasks) - 1e-09:
        return candidate
    return best


# =============================================================================
# SINGLE-TASK LNS: destroy/repair + randomized greedy reconstruction
# =============================================================================
def _destroy_repair_single_solution(result, singles, all_tasks, deadline):
    """Ruin-and-recreate for single-task solutions: each round, rank rows by how
    little removing them costs, randomly remove a few of the cheapest-to-remove,
    then greedily (with noise) rebuild; accept strictly cheaper rebuilds. Stops on
    the iteration cap, the no-improvement streak cap, or the deadline."""
    row_map = {(c[0], c[2]): c for c in singles}
    selected = _result_to_selected(result, row_map)
    if not selected:
        return result
    best = selected
    rng = random.Random(123)
    iterations = 0
    max_iterations = 900 if len(all_tasks) >= 35 else 350
    max_stall = 100 if len(all_tasks) >= 35 else 60
    stall = 0
    while iterations < max_iterations and stall < max_stall and time.monotonic() < deadline - 0.05:
        iterations += 1
        removal_costs = []
        for _key, rows in best.items():
            base = _group_expected_cost(rows, 1)
            for row in rows:
                remaining = [r for r in rows if r != row]
                after = _group_expected_cost(remaining, 1) if remaining else 100.0
                removal_costs.append((after - base, row[5], row))
        if not removal_costs:
            break
        removal_costs.sort(key=lambda x: (x[0], x[1]))
        removal_pool = [row for (_delta, _idx, row) in removal_costs[:min(40, len(removal_costs))]]
        remove_count = rng.choice([2, 3, 4, 5, 6, 8])
        to_remove = set(rng.sample(removal_pool, min(remove_count, len(removal_pool))))
        partial = {}
        for key, rows in best.items():
            kept = [r for r in rows if r not in to_remove]
            if kept:
                partial[key] = kept
        noise = rng.choice([0.0, 0.1, 0.2, 0.35])
        rebuilt = _greedy_repair_single(partial, singles, all_tasks, random.Random(iterations), noise)
        if _selected_cost(rebuilt, all_tasks) < _selected_cost(best, all_tasks) - 1e-09:
            best = rebuilt
            stall = 0
        else:
            stall += 1
    return _format_selected(best)


def _greedy_repair_single(selected, singles, all_tasks, rng, noise):
    """Greedily assign free single-task couriers to whichever task yields the
    biggest cost reduction (optionally jittered by ``noise`` and chosen from the
    top-3 for diversity), until no improving assignment remains."""
    selected = {k: list(rows) for (k, rows) in selected.items()}
    used_couriers = {row[2] for rows in selected.values() for row in rows}
    group_cost = {k: _group_expected_cost(rows, 1) for (k, rows) in selected.items()}
    for task in all_tasks:
        if task not in selected:
            selected[task] = []
            group_cost[task] = 100.0
    while True:
        moves = []
        for cand in singles:
            key, _ids, courier_id, score, will, idx = cand
            if courier_id in used_couriers:
                continue
            current = group_cost.get(key, 100.0)
            new_cost = _group_expected_cost(selected.get(key, []), 1, extra=cand)
            improvement = current - new_cost
            if improvement <= 1e-12:
                continue
            jittered = improvement
            if noise:
                jittered *= rng.uniform(1.0 - noise, 1.0 + noise)
            moves.append((jittered, improvement, will, -score, -idx, cand, new_cost))
        if not moves:
            break
        moves.sort(reverse=True)
        chosen = moves[rng.randrange(min(3, len(moves)))]
        cand = chosen[5]
        new_cost = chosen[6]
        selected.setdefault(cand[0], []).append(cand)
        group_cost[cand[0]] = new_cost
        used_couriers.add(cand[2])
    return {k: rows for (k, rows) in selected.items() if rows}


def _random_single_start_solution(singles, all_tasks, deadline):
    """A fresh noisy greedy start (then reassign/rebalance), for solution diversity."""
    if time.monotonic() > deadline - 1.8:
        return []
    local_deadline = min(deadline, time.monotonic() + 1.8)
    rebuilt = _greedy_repair_single({}, singles, all_tasks, random.Random(18), 0.5)
    solution = _format_selected(rebuilt)
    solution = _reassign_single_solution(solution, singles, all_tasks, local_deadline)
    solution = _rebalance_single_solution(solution, singles, all_tasks, local_deadline)
    solution = _reassign_single_solution(solution, singles, all_tasks, local_deadline)
    return solution


# =============================================================================
# MIXED LOCAL IMPROVEMENT (several intensification operators)
# =============================================================================
def _local_improve_mixed_solution(result, candidates, all_tasks, deadline, include_pair_rewire=False):
    """Apply intensification operators in rounds until none improves: re-optimize
    each group's couriers (same key), split bundles into singles, merge single
    pairs into bundles (or merge covered bundles), and optionally rewire pairs.
    Commit only if the final solution is strictly cheaper than the input."""
    row_map = {(c[0], c[2]): c for c in candidates}
    selected = _result_to_selected(result, row_map)
    if not selected:
        return result
    rows_by_key = {}
    singles_by_task = {}
    bundles_by_tasks = {}
    for cand in candidates:
        rows_by_key.setdefault(cand[0], []).append(cand)
        if len(cand[1]) == 1:
            singles_by_task.setdefault(cand[1][0], []).append(cand)
        elif len(cand[1]) >= 2:
            bundles_by_tasks.setdefault(tuple(sorted(cand[1])), []).append(cand)
    has_large_bundles = any(len(ids) > 2 for ids in bundles_by_tasks)
    best_cost = _selected_cost(selected, all_tasks)
    rounds = 0
    while rounds < 2 and time.monotonic() < deadline - 0.12:
        rounds += 1
        improved = False
        if _improve_same_key_groups(selected, rows_by_key, all_tasks, deadline):
            cost = _selected_cost(selected, all_tasks)
            if cost < best_cost - 1e-09:
                best_cost = cost
                improved = True
        if time.monotonic() < deadline - 0.12:
            if _improve_bundle_splits(selected, singles_by_task, all_tasks, deadline):
                cost = _selected_cost(selected, all_tasks)
                if cost < best_cost - 1e-09:
                    best_cost = cost
                    improved = True
        if time.monotonic() < deadline - 0.12:
            if has_large_bundles:
                merged = _improve_covered_bundle_merges(selected, bundles_by_tasks, all_tasks, deadline)
            else:
                merged = _improve_single_pair_merges(selected, bundles_by_tasks, all_tasks, deadline)
            if merged:
                cost = _selected_cost(selected, all_tasks)
                if cost < best_cost - 1e-09:
                    best_cost = cost
                    improved = True
        if include_pair_rewire and time.monotonic() < deadline - 0.12:
            if _improve_pair_rewires(selected, bundles_by_tasks, all_tasks, deadline):
                cost = _selected_cost(selected, all_tasks)
                if cost < best_cost - 1e-09:
                    best_cost = cost
                    improved = True
        if not improved:
            break
    formatted = _format_selected(selected)
    if _solution_expected_cost(formatted, candidates, all_tasks) < _solution_expected_cost(result, candidates, all_tasks) - 1e-09:
        return formatted
    return result


def _improve_same_key_groups(selected, by_key, all_tasks, deadline):
    """For each group, try re-choosing its best courier subset (same task_key) from
    all available couriers; replace when strictly cheaper. Mutates ``selected``."""
    improved = False
    for task_key in list(selected):
        if time.monotonic() > deadline - 0.12:
            break
        group = selected.get(task_key)
        if not group:
            continue
        used_elsewhere = _selected_couriers_except(selected, {task_key})
        pool = [c for c in by_key.get(task_key, []) if c[2] not in used_elsewhere]
        if not pool:
            continue
        limit = min(len(pool), max(1, len(group) + 2), 7)
        replacement = _best_group_from_pool(pool, len(group[0][1]), limit)
        if not replacement:
            continue
        current_cost = _group_expected_cost(group, len(group[0][1]))
        new_cost = _group_expected_cost(replacement, len(replacement[0][1]))
        if new_cost < current_cost - 1e-09:
            selected[task_key] = replacement
            improved = True
    return improved


def _improve_bundle_splits(selected, singles_by_task, all_tasks, deadline):
    """Try replacing a multi-task bundle group with separate single-task groups
    (one per task) when that is strictly cheaper. Mutates ``selected``."""
    improved = False
    for bundle_key in list(selected):
        if time.monotonic() > deadline - 0.12:
            break
        group = selected.get(bundle_key)
        if not group or len(group[0][1]) < 2:
            continue
        bundle_tasks = group[0][1]
        if any(t in selected for t in bundle_tasks):
            continue  # one of the split keys already exists
        used_elsewhere = _selected_couriers_except(selected, {bundle_key})
        split = _best_multi_split_groups(bundle_tasks, singles_by_task, used_elsewhere, max_rows=min(len(group) + len(bundle_tasks), max(7, len(bundle_tasks) * 2)))
        if split is None:
            continue
        bundle_cost = _group_expected_cost(group, len(bundle_tasks))
        split_cost = sum(_group_expected_cost(rows, 1) for rows in split.values())
        if split_cost < bundle_cost - 1e-09:
            del selected[bundle_key]
            for task_key, rows in split.items():
                selected[task_key] = rows
            improved = True
    return improved


def _improve_single_pair_merges(selected, bundles_by_tasks, all_tasks, deadline):
    """Try merging two single-task groups into one 2-task bundle group when a
    cheaper bundle exists for their task pair. Mutates ``selected``."""
    improved = False
    single_keys = [k for (k, rows) in selected.items() if rows and len(rows[0][1]) == 1]
    for i, key_a in enumerate(single_keys):
        if time.monotonic() > deadline - 0.12:
            break
        if key_a not in selected:
            continue
        for key_b in single_keys[i + 1:]:
            if time.monotonic() > deadline - 0.12:
                break
            if key_b not in selected:
                continue
            group_a = selected[key_a]
            group_b = selected[key_b]
            bundle_tasks = tuple(sorted((group_a[0][1][0], group_b[0][1][0])))
            bundle_rows = bundles_by_tasks.get(bundle_tasks)
            if not bundle_rows:
                continue
            used_elsewhere = _selected_couriers_except(selected, {key_a, key_b})
            pool = [c for c in bundle_rows if c[2] not in used_elsewhere]
            if not pool:
                continue
            limit = min(len(pool), len(group_a) + len(group_b) + 2, 7)
            replacement = _best_group_from_pool(pool, 2, limit)
            if not replacement:
                continue
            current_cost = _group_expected_cost(group_a, 1) + _group_expected_cost(group_b, 1)
            new_cost = _group_expected_cost(replacement, 2)
            if new_cost < current_cost - 1e-09:
                del selected[key_a]
                del selected[key_b]
                selected[replacement[0][0]] = replacement
                improved = True
                break
    return improved


def _improve_covered_bundle_merges(selected, bundles_by_tasks, all_tasks, deadline):
    """Repeatedly merge the set of groups that exactly cover a bundle's tasks into
    one cheaper bundle group, taking the best improving merge each round (used when
    3+ task bundles exist). Mutates ``selected``."""
    improved = False
    bundle_items = sorted(bundles_by_tasks.items(), key=lambda item: (-len(item[0]), item[0]))
    while time.monotonic() < deadline - 0.12:
        best_merge = None
        best_delta = 0.0
        task_to_key = {}
        for task_key, rows in selected.items():
            if not rows:
                continue
            for task_id in rows[0][1]:
                task_to_key[task_id] = task_key
        for (bundle_tasks, bundle_rows) in bundle_items:
            if time.monotonic() > deadline - 0.12:
                break
            if len(bundle_tasks) < 2:
                continue
            covering_keys = set()
            incomplete = False
            for task_id in bundle_tasks:
                key = task_to_key.get(task_id)
                if key is None:
                    incomplete = True
                    break
                covering_keys.add(key)
            if incomplete or len(covering_keys) == 1:
                continue
            covered_union = set()
            covered_cost = 0.0
            covered_rider_total = 0
            for key in covering_keys:
                group = selected.get(key)
                if not group:
                    continue
                covered_union.update(group[0][1])
                covered_cost += _group_expected_cost(group, len(group[0][1]))
                covered_rider_total += len(group)
            if covered_union != set(bundle_tasks):
                continue  # the covering groups spill onto other tasks
            used_elsewhere = _selected_couriers_except(selected, covering_keys)
            pool = [c for c in bundle_rows if c[2] not in used_elsewhere]
            if not pool:
                continue
            limit = min(len(pool), max(1, covered_rider_total + 2), max(7, len(bundle_tasks) + 3))
            replacement = _best_group_from_pool(pool, len(bundle_tasks), limit)
            if not replacement:
                continue
            new_cost = _group_expected_cost(replacement, len(bundle_tasks))
            delta = new_cost - covered_cost
            if delta < best_delta - 1e-09:
                best_delta = delta
                best_merge = (covering_keys, replacement)
        if best_merge is None:
            break
        covering_keys, replacement = best_merge
        for key in covering_keys:
            if key in selected:
                del selected[key]
        selected[replacement[0][0]] = replacement
        improved = True
    return improved


def _improve_pair_rewires(selected, bundles_by_tasks, all_tasks, deadline):
    """Swap the task pairing of two 2-task bundle groups (cross their tasks) when
    a cheaper pair of bundles exists for the re-crossed task sets. Mutates
    ``selected``."""
    pair_keys = [k for (k, rows) in selected.items() if rows and len(rows[0][1]) == 2]
    if len(pair_keys) < 2:
        return False
    improved = False
    while time.monotonic() < deadline - 0.12:
        best_move = None
        best_delta = 0.0
        pair_keys = [k for (k, rows) in selected.items() if rows and len(rows[0][1]) == 2]
        for i, key_a in enumerate(pair_keys):
            if time.monotonic() > deadline - 0.12:
                break
            if key_a not in selected:
                continue
            group_a = selected[key_a]
            task_a1, task_a2 = group_a[0][1]
            for key_b in pair_keys[i + 1:]:
                if time.monotonic() > deadline - 0.12:
                    break
                if key_b not in selected:
                    continue
                group_b = selected[key_b]
                task_b1, task_b2 = group_b[0][1]
                if len({task_a1, task_a2, task_b1, task_b2}) < 4:
                    continue
                current_cost = _group_expected_cost(group_a, 2) + _group_expected_cost(group_b, 2)
                used_elsewhere = _selected_couriers_except(selected, {key_a, key_b})
                for (cross_x, cross_y) in (((task_a1, task_b1), (task_a2, task_b2)), ((task_a1, task_b2), (task_a2, task_b1))):
                    bundle_x = tuple(sorted(cross_x))
                    bundle_y = tuple(sorted(cross_y))
                    pool_x = [c for c in bundles_by_tasks.get(bundle_x, []) if c[2] not in used_elsewhere]
                    if not pool_x:
                        continue
                    new_group_x = _best_group_from_pool(pool_x, 2, min(len(group_a) + 1, 6))
                    if not new_group_x:
                        continue
                    used_by_x = {r[2] for r in new_group_x}
                    pool_y = [c for c in bundles_by_tasks.get(bundle_y, []) if c[2] not in used_elsewhere and c[2] not in used_by_x]
                    if not pool_y:
                        continue
                    new_group_y = _best_group_from_pool(pool_y, 2, min(len(group_b) + 1, 6))
                    if not new_group_y:
                        continue
                    new_cost = _group_expected_cost(new_group_x, 2) + _group_expected_cost(new_group_y, 2)
                    delta = new_cost - current_cost
                    if delta < best_delta - 1e-09:
                        best_delta = delta
                        best_move = (key_a, key_b, new_group_x, new_group_y)
        if best_move is None:
            break
        key_a, key_b, new_group_x, new_group_y = best_move
        if key_a in selected:
            del selected[key_a]
        if key_b in selected:
            del selected[key_b]
        selected[new_group_x[0][0]] = new_group_x
        selected[new_group_y[0][0]] = new_group_y
        improved = True
    return improved


def _best_group_from_pool(pool, task_count, limit):
    """Greedily build the (up to ``limit``) courier subset from ``pool`` that
    minimizes the group's expected cost; same as _best_group_rows but returns only
    the rows."""
    chosen = []
    used = set()
    current_cost = 100.0 * task_count
    while len(chosen) < limit:
        best_row = None
        best_new_cost = 0.0
        best_delta = 0.0
        for row in pool:
            if row[2] in used:
                continue
            new_cost = _group_expected_cost(chosen, task_count, extra=row)
            delta = new_cost - current_cost
            if delta < best_delta - 1e-12:
                best_row = row
                best_new_cost = new_cost
                best_delta = delta
        if best_row is None:
            break
        chosen.append(best_row)
        used.add(best_row[2])
        current_cost = best_new_cost
    return chosen


def _best_multi_split_groups(task_ids, singles_by_task, outside_couriers, max_rows):
    """Greedily assign free single couriers to the individual tasks of a bundle,
    minimizing per-task cost. Returns task_key -> rows, or None if any task in the
    bundle cannot be covered."""
    groups = {t: [] for t in task_ids}
    group_cost = {t: 100.0 for t in task_ids}
    used = set(outside_couriers)
    pool = []
    for t in task_ids:
        pool.extend(singles_by_task.get(t, []))
    while sum(len(rows) for rows in groups.values()) < max_rows:
        best_row = None
        best_task = None
        best_new_cost = 0.0
        best_delta = 0.0
        for cand in pool:
            task = cand[1][0]
            if cand[2] in used:
                continue
            new_cost = _group_expected_cost(groups[task], 1, extra=cand)
            delta = new_cost - group_cost[task]
            if delta < best_delta - 1e-12:
                best_row = cand
                best_task = task
                best_new_cost = new_cost
                best_delta = delta
        if best_row is None:
            break
        groups[best_task].append(best_row)
        group_cost[best_task] = best_new_cost
        used.add(best_row[2])
    if any(not groups[t] for t in task_ids):
        return None
    return groups


# =============================================================================
# SCARCE-REGIME MIN-COST-FLOW BUNDLE ENUMERATION
# -----------------------------------------------------------------------------
# Enumerate promising profitable bundle columns, then BFS-expand disjoint
# combinations of them (beam-pruned by an admissible completion bound), and for
# each partial bundle selection COMPLETE the remaining single tasks OPTIMALLY via
# a min-cost flow (couriers -> tasks assignment, with a 100-cost "leave uncovered"
# edge per task). Keep the cheapest complete solution found.
# =============================================================================
def _solve_scarce_bundle_mcf_enum(candidates, all_tasks, deadline):
    task_order = sorted(all_tasks)
    task_bit = {t: i for i, t in enumerate(task_order)}
    singles_by_task = {}
    bundle_columns = []  # (saving, cost, task_mask, courier_id, row)
    for cand in _canonical_candidates(candidates):
        _key, task_ids, courier_id, _score, _will, _idx = cand
        if len(task_ids) == 1:
            singles_by_task.setdefault(task_ids[0], []).append(cand)
            continue
        task_mask = 0
        for task_id in task_ids:
            if task_id not in task_bit:
                task_mask = 0
                break
            task_mask |= 1 << task_bit[task_id]
        if not task_mask:
            continue
        cost = _group_expected_cost([cand], len(task_ids))
        saving = 100.0 * len(task_ids) - cost
        if saving <= 1e-09:
            continue
        bundle_columns.append((saving, cost, task_mask, courier_id, cand))
    if not bundle_columns:
        return []
    bundle_columns.sort(key=lambda item: (_popcount(item[2]), item[0] / max(item[1], 1e-09), item[0], -item[1], -item[4][5]), reverse=True)
    bundle_columns = bundle_columns[:120]

    # BFS over disjoint bundle selections; state = (task_mask, frozenset(couriers), rows)
    frontier = [(0, frozenset(), ())]
    all_states = list(frontier)
    best = _complete_scarce_bundles_with_mcf((), singles_by_task, task_order)
    best_cost = _solution_expected_cost(best, candidates, all_tasks) if best else float("inf")
    max_depth = min(len({c[2] for c in candidates}), len(all_tasks) // 2 + 2)
    for _ in range(max_depth):
        if time.monotonic() > deadline - 0.28:
            break
        next_states = []
        for (task_mask, used_couriers, rows) in frontier:
            for (_saving, _cost, col_task_mask, courier_id, row) in bundle_columns:
                if task_mask & col_task_mask or courier_id in used_couriers:
                    continue
                next_states.append((task_mask | col_task_mask, used_couriers | {courier_id}, rows + (row,)))
                if len(next_states) >= 1800:
                    break
            if len(next_states) >= 1800 or time.monotonic() > deadline - 0.28:
                break
        if not next_states:
            break
        next_states = _prune_scarce_bundle_states(next_states, task_order, singles_by_task, max_states=180)
        all_states.extend(next_states)
        frontier = next_states

    seen = set()
    for (task_mask, used_couriers, rows) in all_states:
        if time.monotonic() > deadline - 0.05:
            break
        state_key = (task_mask, tuple(sorted(used_couriers)))
        if state_key in seen:
            continue
        seen.add(state_key)
        completed = _complete_scarce_bundles_with_mcf(rows, singles_by_task, task_order)
        if not completed:
            continue
        cost = _solution_expected_cost(completed, candidates, all_tasks)
        if cost < best_cost - 1e-09:
            best = completed
            best_cost = cost
    return best


def _solve_scarce_bundle_group_mcf_enum(candidates, all_tasks, deadline):
    """Like _solve_scarce_bundle_mcf_enum but the bundle "columns" can be a small
    multidispatch GROUP (1..3 couriers) per bundle key, not just a single row."""
    task_order = sorted(all_tasks)
    task_bit = {t: i for i, t in enumerate(task_order)}
    singles_by_task = {}
    bundle_rows_by_key = {}
    for cand in _canonical_candidates(candidates):
        if len(cand[1]) == 1:
            singles_by_task.setdefault(cand[1][0], []).append(cand)
        else:
            bundle_rows_by_key.setdefault(cand[0], []).append(cand)
    columns = []  # (saving, cost, task_mask, frozenset(couriers), rows)
    for key_rows in bundle_rows_by_key.values():
        if time.monotonic() > deadline - 0.2:
            break
        task_mask = 0
        valid = True
        for task_id in key_rows[0][1]:
            if task_id not in task_bit:
                valid = False
                break
            task_mask |= 1 << task_bit[task_id]
        if not valid:
            continue
        bundle_task_count = len(key_rows[0][1])
        pool = sorted(key_rows, key=lambda c: (_group_expected_cost([c], bundle_task_count), -c[4], c[5]))[:7]
        key_columns = []
        for combo_size in range(1, min(3, len(pool)) + 1):
            for combo in itertools.combinations(pool, combo_size):
                courier_ids = tuple(sorted(r[2] for r in combo))
                if len(courier_ids) != len(set(courier_ids)):
                    continue
                cost = _group_expected_cost(combo, bundle_task_count)
                saving = 100.0 * bundle_task_count - cost
                if saving <= 1e-09:
                    continue
                key_columns.append((saving, cost, task_mask, frozenset(courier_ids), tuple(combo)))
        key_columns.sort(key=lambda item: (item[0] / max(item[1], 1e-09), item[0], -item[1]), reverse=True)
        columns.extend(key_columns[:3])
    if not columns:
        return []
    columns.sort(key=lambda item: (_popcount(item[2]), item[0] / max(1, len(item[3])), item[0] / max(item[1], 1e-09), item[0]), reverse=True)
    columns = columns[:90]

    frontier = [(0, frozenset(), ())]
    all_states = list(frontier)
    best = _complete_scarce_bundle_groups_with_mcf((), singles_by_task, task_order)
    best_cost = _solution_expected_cost(best, candidates, all_tasks) if best else float("inf")
    max_depth = min(len(all_tasks) // 2 + 2, 18)
    for _ in range(max_depth):
        if time.monotonic() > deadline - 0.22:
            break
        next_states = []
        for (task_mask, used_couriers, groups) in frontier:
            for (_saving, _cost, col_task_mask, col_couriers, group) in columns:
                if task_mask & col_task_mask or used_couriers & col_couriers:
                    continue
                next_states.append((task_mask | col_task_mask, used_couriers | col_couriers, groups + (group,)))
                if len(next_states) >= 1300:
                    break
            if len(next_states) >= 1300 or time.monotonic() > deadline - 0.22:
                break
        if not next_states:
            break
        next_states = _prune_scarce_bundle_group_states(next_states, task_order, singles_by_task, max_states=120)
        all_states.extend(next_states)
        frontier = next_states

    seen = set()
    for (task_mask, used_couriers, groups) in all_states:
        if time.monotonic() > deadline - 0.05:
            break
        state_key = (task_mask, tuple(sorted(used_couriers)))
        if state_key in seen:
            continue
        seen.add(state_key)
        completed = _complete_scarce_bundle_groups_with_mcf(groups, singles_by_task, task_order)
        if not completed:
            continue
        cost = _solution_expected_cost(completed, candidates, all_tasks)
        if cost < best_cost - 1e-09:
            best = completed
            best_cost = cost
    return best


def _prune_scarce_bundle_group_states(states, task_list, singles_by_task, max_states):
    """Beam-prune partial bundle-GROUP states by an admissible cost estimate:
    chosen group cost + cheapest free single per still-uncovered task."""
    task_index = {t: i for i, t in enumerate(task_list)}

    def state_key(state):
        task_mask, used_couriers, groups = state
        chosen_cost = sum(_group_expected_cost(g, len(g[0][1])) for g in groups)
        completion = 0.0
        for task in task_list:
            if task_mask >> task_index[task] & 1:
                continue
            free = [c for c in singles_by_task.get(task, []) if c[2] not in used_couriers]
            if free:
                completion += min(_group_expected_cost([c], 1) for c in free)
            else:
                completion += 100.0
        return (chosen_cost + completion, -_popcount(task_mask), len(used_couriers))

    states.sort(key=state_key)
    return states[:max_states]


def _complete_scarce_bundle_groups_with_mcf(bundle_groups, singles_by_task, task_list):
    """Given fixed bundle GROUPS, optimally cover the remaining single tasks with a
    min-cost flow (each task either gets a free single courier, or pays 100)."""
    covered_tasks = {t for g in bundle_groups for t in g[0][1]}
    used_couriers = {r[2] for g in bundle_groups for r in g}
    remaining_tasks = [t for t in task_list if t not in covered_tasks]
    result = [(g[0][0], [r[2] for r in g]) for g in bundle_groups]
    if not remaining_tasks:
        return result
    free_couriers = sorted({c[2] for t in remaining_tasks for c in singles_by_task.get(t, []) if c[2] not in used_couriers})
    source = 0
    task_node0 = 1
    courier_node0 = task_node0 + len(remaining_tasks)
    sink = courier_node0 + len(free_couriers)
    flow = _MinCostFlow(sink + 1)
    edge_lookup = {}
    for i in range(len(remaining_tasks)):
        flow.add_edge(source, task_node0 + i, 1, 0.0)
        flow.add_edge(task_node0 + i, sink, 1, 100.0)  # "leave uncovered" edge
    for j in range(len(free_couriers)):
        flow.add_edge(courier_node0 + j, sink, 1, 0.0)
    courier_index = {cid: i for i, cid in enumerate(free_couriers)}
    for i, task in enumerate(remaining_tasks):
        task_node = task_node0 + i
        cheapest_by_courier = {}
        for cand in singles_by_task.get(task, []):
            if cand[2] in used_couriers:
                continue
            existing = cheapest_by_courier.get(cand[2])
            if existing is None or _group_expected_cost([cand], 1) < _group_expected_cost([existing], 1) - 1e-12:
                cheapest_by_courier[cand[2]] = cand
        for courier_id, cand in cheapest_by_courier.items():
            courier_node = courier_node0 + courier_index[courier_id]
            edge_pos = len(flow.graph[task_node])
            flow.add_edge(task_node, courier_node, 1, _group_expected_cost([cand], 1))
            edge_lookup[(task_node, edge_pos)] = cand
    if flow.min_cost_flow(source, sink, len(remaining_tasks)) < len(remaining_tasks):
        return result
    for (task_node, edge_pos), cand in edge_lookup.items():
        if flow.graph[task_node][edge_pos][1] == 0:  # saturated -> courier used
            result.append((cand[0], [cand[2]]))
    return result


def _prune_scarce_bundle_states(states, task_list, singles_by_task, max_states):
    """Beam-prune partial single-bundle-row states by the same admissible estimate."""
    task_index = {t: i for i, t in enumerate(task_list)}

    def state_key(state):
        task_mask, used_couriers, rows = state
        chosen_cost = sum(_group_expected_cost([r], len(r[1])) for r in rows)
        completion = 0.0
        for task in task_list:
            if task_mask >> task_index[task] & 1:
                continue
            free = [c for c in singles_by_task.get(task, []) if c[2] not in used_couriers]
            if free:
                completion += min(_group_expected_cost([c], 1) for c in free)
            else:
                completion += 100.0
        return (chosen_cost + completion, -_popcount(task_mask), len(used_couriers), tuple(r[0] for r in rows))

    states.sort(key=state_key)
    return states[:max_states]


def _complete_scarce_bundles_with_mcf(bundle_rows, singles_by_task, task_list):
    """Given fixed single bundle ROWS, optimally cover the remaining single tasks
    with a min-cost flow (same network as the group variant)."""
    covered_tasks = {t for r in bundle_rows for t in r[1]}
    used_couriers = {r[2] for r in bundle_rows}
    remaining_tasks = [t for t in task_list if t not in covered_tasks]
    result = [(r[0], [r[2]]) for r in bundle_rows]
    if not remaining_tasks:
        return result
    free_couriers = sorted({c[2] for t in remaining_tasks for c in singles_by_task.get(t, []) if c[2] not in used_couriers})
    source = 0
    task_node0 = 1
    courier_node0 = task_node0 + len(remaining_tasks)
    sink = courier_node0 + len(free_couriers)
    flow = _MinCostFlow(sink + 1)
    edge_lookup = {}
    for i in range(len(remaining_tasks)):
        flow.add_edge(source, task_node0 + i, 1, 0.0)
        flow.add_edge(task_node0 + i, sink, 1, 100.0)
    for j in range(len(free_couriers)):
        flow.add_edge(courier_node0 + j, sink, 1, 0.0)
    courier_index = {cid: i for i, cid in enumerate(free_couriers)}
    for i, task in enumerate(remaining_tasks):
        task_node = task_node0 + i
        cheapest_by_courier = {}
        for cand in singles_by_task.get(task, []):
            if cand[2] in used_couriers:
                continue
            existing = cheapest_by_courier.get(cand[2])
            if existing is None or _group_expected_cost([cand], 1) < _group_expected_cost([existing], 1) - 1e-12:
                cheapest_by_courier[cand[2]] = cand
        for courier_id, cand in cheapest_by_courier.items():
            courier_node = courier_node0 + courier_index[courier_id]
            edge_pos = len(flow.graph[task_node])
            flow.add_edge(task_node, courier_node, 1, _group_expected_cost([cand], 1))
            edge_lookup[(task_node, edge_pos)] = cand
    if flow.min_cost_flow(source, sink, len(remaining_tasks)) < len(remaining_tasks):
        return result
    for (task_node, edge_pos), cand in edge_lookup.items():
        if flow.graph[task_node][edge_pos][1] == 0:
            result.append((cand[0], [cand[2]]))
    return result


# =============================================================================
# SPARSE SET-COVER (greedy + beam) for coverage-pressured instances
# =============================================================================
def _solve_sparse_cover(candidates, all_tasks, deadline):
    """Best of three greedy set-cover orderings, optionally improved by a beam
    search when the instance is small enough."""
    best = []
    for mode in (_MODE_COVER, _MODE_GAIN, _MODE_RATIO):
        if time.monotonic() > deadline - 0.25:
            break
        greedy = _sparse_greedy(candidates, mode)
        if not best or _simple_result_score(greedy, candidates, all_tasks) < _simple_result_score(best, candidates, all_tasks):
            best = greedy
    beam_affordable = (
        len(all_tasks) <= 60
        and len(candidates) <= 60000
        and len({c[2] for c in candidates}) <= 80
        and time.monotonic() < deadline - 1.0
    )
    if beam_affordable:
        beam = _sparse_beam_search(candidates, all_tasks, deadline)
        if beam and _simple_result_score(beam, candidates, all_tasks) < _simple_result_score(best, candidates, all_tasks):
            best = beam
    return best


def _sparse_beam_search(candidates, all_tasks, deadline, coverage_first=False):
    """Beam search over disjoint columns maximizing total saving (or coverage when
    ``coverage_first``). One column per courier is kept per task_mask; states are a
    dict task_mask -> (best_saving, chosen_rows)."""
    task_order = sorted(all_tasks)
    task_bit = {t: i for i, t in enumerate(task_order)}
    columns_by_courier = {}  # courier_id -> [(task_mask, saving, cost, row)]
    for cand in candidates:
        task_mask = 0
        valid = True
        for task_id in cand[1]:
            if task_id not in task_bit:
                valid = False
                break
            task_mask |= 1 << task_bit[task_id]
        if not valid:
            continue
        cost = _group_expected_cost([cand], len(cand[1]))
        saving = 100.0 * len(cand[1]) - cost
        if saving <= 1e-12:
            continue
        columns_by_courier.setdefault(cand[2], []).append((task_mask, saving, cost, cand))
    if not columns_by_courier:
        return []
    small = len(candidates) <= 10000 and len(columns_by_courier) <= 25
    per_courier_limit = 45 if small else 28
    courier_column_lists = []
    for courier_id, courier_columns in columns_by_courier.items():
        best_by_mask = {}
        for (task_mask, saving, cost, cand) in courier_columns:
            existing = best_by_mask.get(task_mask)
            if existing is None or cost < existing[2] - 1e-12:
                best_by_mask[task_mask] = (task_mask, saving, cost, cand)
        pruned = sorted(best_by_mask.values(), key=lambda r: (_popcount(r[0]), r[1], -r[2]), reverse=True)[:per_courier_limit]
        courier_column_lists.append((courier_id, pruned))
    courier_column_lists.sort(key=lambda item: max((c[1] for c in item[1]), default=0.0), reverse=True)
    states = {0: (0.0, ())}
    beam_width = 12000 if small else 900 if len(courier_column_lists) <= 30 else 520
    for (_courier_id, courier_columns) in courier_column_lists:
        if time.monotonic() > deadline - 0.25:
            break
        next_states = dict(states)
        for (state_mask, (state_saving, chosen_rows)) in states.items():
            for (col_mask, col_saving, _cost, cand) in courier_columns:
                if state_mask & col_mask:
                    continue
                new_mask = state_mask | col_mask
                new_saving = state_saving + col_saving
                existing = next_states.get(new_mask)
                if existing is None or new_saving > existing[0] + 1e-12:
                    next_states[new_mask] = (new_saving, chosen_rows + (cand,))
        if len(next_states) > beam_width:
            if coverage_first:
                trimmed = sorted(next_states.items(), key=lambda item: (_popcount(item[0]), item[1][0]), reverse=True)[:beam_width]
            else:
                trimmed = sorted(next_states.items(), key=lambda item: (item[1][0], _popcount(item[0])), reverse=True)[:beam_width]
            states = dict(trimmed)
        else:
            states = next_states
    if coverage_first:
        _best_mask, (_best_saving, chosen_rows) = max(states.items(), key=lambda item: (_popcount(item[0]), item[1][0]))
    else:
        _best_mask, (_best_saving, chosen_rows) = max(states.items(), key=lambda item: (item[1][0], _popcount(item[0])))
    return [(cand[0], [cand[2]]) for cand in chosen_rows]


def _sparse_greedy(candidates, mode):
    """Plain greedy disjoint set-cover: repeatedly take the best-scoring column
    that adds only NEW tasks and a free courier. Scoring modes as in
    _solve_disjoint_then_multidispatch."""
    covered_tasks = set()
    used_couriers = set()
    result = []
    while True:
        best_row = None
        best_key = None
        for cand in candidates:
            _key, task_ids, courier_id, score, will, _idx = cand
            if courier_id in used_couriers:
                continue
            new_tasks = [t for t in task_ids if t not in covered_tasks]
            if len(new_tasks) != len(task_ids):
                continue  # overlaps an already-covered task
            task_count = len(task_ids)
            saving = 100.0 * task_count - _group_expected_cost([cand], task_count)
            if saving <= 1e-12:
                continue
            if mode == _MODE_COVER:
                sort_key = (task_count, saving / max(score, 1e-09), saving, will, -score)
            elif mode == _MODE_GAIN:
                sort_key = (saving, task_count, saving / max(score, 1e-09), will, -score)
            else:
                sort_key = (saving / max(score, 1e-09), task_count, saving, will, -score)
            if best_key is None or sort_key > best_key:
                best_key = sort_key
                best_row = cand
        if best_row is None:
            break
        result.append((best_row[0], [best_row[2]]))
        used_couriers.add(best_row[2])
        for task_id in best_row[1]:
            covered_tasks.add(task_id)
    return result


def _simple_result_score(result, candidates, all_tasks):
    return _solution_expected_cost(result, candidates, all_tasks)


# =============================================================================
# SOLUTION PICKERS (regime-aware incumbent selection) + drop helpers
# =============================================================================
def _pick_low_robust_best(solutions, candidates, all_tasks):
    """Pick a low-willingness incumbent that balances the canonical cost against
    two worst/eager-case acceptance models. Blend = .45*avg + .45*min_score +
    .1*max_willingness, plus a .15 penalty on the worst regret vs the cheapest
    solution. Falls back to the plain-cheapest if the robust pick is >25 worse."""
    feasible = [s for s in solutions if s]
    if not feasible:
        return []
    cheapest = min(feasible, key=lambda s: _solution_expected_cost(s, candidates, all_tasks))
    cheapest_cost = _solution_expected_cost(cheapest, candidates, all_tasks)

    def robust_key(solution):
        avg_cost = _solution_expected_cost(solution, candidates, all_tasks)
        min_score_cost = _solution_expected_cost_by_model(solution, candidates, all_tasks, _MODEL_MIN_SCORE)
        max_will_cost = _solution_expected_cost_by_model(solution, candidates, all_tasks, _MODEL_MAX_WILLINGNESS)
        blend = 0.45 * avg_cost + 0.45 * min_score_cost + 0.1 * max_will_cost
        worst_regret = max(avg_cost - cheapest_cost, min_score_cost - cheapest_cost, max_will_cost - cheapest_cost)
        return (blend + 0.15 * max(0.0, worst_regret), max(avg_cost, min_score_cost, max_will_cost), avg_cost)

    robust = min(feasible, key=robust_key)
    robust_cost = _solution_expected_cost(robust, candidates, all_tasks)
    if robust_cost <= cheapest_cost + 25.0:
        return robust
    return cheapest


def _pick_hard_scarce_best(solutions, candidates, all_tasks):
    """For the dense-scarce regime, consider the 4 cheapest solutions plus their
    riskiest-group-dropped variants, and pick by a "shadow cost" that penalizes
    courier-heavy and bundle-heavy structure (proxy for acceptance fragility)."""
    feasible = [s for s in solutions if s]
    if not feasible:
        return []
    cheapest_four = sorted(feasible, key=lambda s: _solution_expected_cost(s, candidates, all_tasks))[:4]
    variants = []
    for sol in cheapest_four:
        variants.append(sol)
        drop1 = _drop_riskiest_groups(sol, candidates, 1)
        if drop1:
            variants.append(drop1)
        drop2 = _drop_riskiest_groups(sol, candidates, 2)
        if drop2:
            variants.append(drop2)
    return min(variants, key=lambda s: (_hard_scarce_shadow_cost(s, candidates, all_tasks), _solution_expected_cost(s, candidates, all_tasks)))


def _pick_scarce_best(solutions, candidates, all_tasks):
    """Plain cheapest feasible solution (scarce regime)."""
    feasible = [s for s in solutions if s]
    if not feasible:
        return []
    return min(feasible, key=lambda s: _solution_expected_cost(s, candidates, all_tasks))


def _drop_riskiest_groups(result, candidates, drop_groups):
    """Return the solution with the ``drop_groups`` groups of largest reduced cost
    removed (the ones whose saving over the uncovered penalty is smallest)."""
    if drop_groups <= 0 or len(result) <= drop_groups:
        return result
    row_map = {(c[0], c[2]): c for c in candidates}
    scored = []
    for group_index, (task_key, courier_ids) in enumerate(result):
        rows = [row_map.get((task_key, cid)) for cid in courier_ids]
        rows = [r for r in rows if r is not None]
        if not rows:
            continue
        task_count = len(rows[0][1])
        cost = _group_expected_cost(rows, task_count)
        scored.append((cost - 100.0 * task_count, cost / max(1, task_count), group_index))
    drop_indices = {idx for (_reduced, _cpt, idx) in sorted(scored, reverse=True)[:drop_groups]}
    return [group for (i, group) in enumerate(result) if i not in drop_indices]


def _hard_scarce_shadow_cost(result, candidates, all_tasks):
    """A robustness "shadow cost": canonical group cost + 60 per uncovered task +
    14 per extra courier beyond 2 in a group + 1 per bundle group + 0.2 per
    courier. Used only to rank scarce candidates (penalizes fragile structure)."""
    row_map = {(c[0], c[2]): c for c in candidates}
    covered_tasks = set()
    used_couriers = set()
    total_cost = 0.0
    extra_couriers = 0
    total_couriers = 0
    bundle_groups = 0
    for (task_key, courier_ids) in result:
        rows = []
        for courier_id in courier_ids:
            row = row_map.get((task_key, courier_id))
            if row is None or courier_id in used_couriers:
                return float("inf")
            used_couriers.add(courier_id)
            rows.append(row)
        if not rows:
            return float("inf")
        for task_id in rows[0][1]:
            if task_id in covered_tasks:
                return float("inf")
            covered_tasks.add(task_id)
        total_cost += _group_expected_cost(rows, len(rows[0][1]))
        extra_couriers += max(0.0, len(rows) - 2)
        total_couriers += len(rows)
        bundle_groups += len(rows[0][1]) >= 2
    return total_cost + 60.0 * (len(all_tasks) - len(covered_tasks)) + 14.0 * extra_couriers + bundle_groups + total_couriers / 5.0


def _drop_unprofitable_groups(result, candidates, all_tasks):
    """Remove any group whose expected cost is NOT cheaper than leaving its tasks
    uncovered (i.e. it does not actually save anything). Keep the change only if it
    lowers the canonical solution cost."""
    row_map = {(c[0], c[2]): c for c in candidates}
    kept = []
    for (task_key, courier_ids) in result:
        rows = [row_map.get((task_key, cid)) for cid in courier_ids]
        rows = [r for r in rows if r is not None]
        if not rows:
            continue
        task_count = len(rows[0][1])
        if _group_expected_cost(rows, task_count) < 100.0 * task_count - 1e-09:
            kept.append((task_key, list(courier_ids)))
    if _solution_expected_cost(kept, candidates, all_tasks) < _solution_expected_cost(result, candidates, all_tasks) - 1e-09:
        return kept
    return result


# =============================================================================
# GENERIC MEDIUM/LARGE POLISH + OFFICIAL GREEDY FALLBACK
# =============================================================================
def _normal_medium_polish_solution(result, candidates, all_tasks, deadline, task_count, courier_count, is_scarce, is_low):
    """Generic LNS polish for the dense medium/large regimes (the ones solver.py
    used to short-circuit with a memorized table): reassign + bundle-insertion +
    pairwise/triple exchange + ALNS column repair + final reassign, each gated on a
    strict improvement and the budget. A no-op for the scarce/low regimes (they
    have dedicated tails) and when no improving move exists."""
    if result is None:
        return result
    if is_scarce or is_low:
        return result

    def cost(solution):
        return _solution_expected_cost(solution, candidates, all_tasks)

    best = cost(result)
    # 1) drop unprofitable + reassign within current grouping
    if time.monotonic() < deadline - 0.4:
        reassigned = _reassign_mixed_solution(result, candidates, all_tasks, min(deadline, time.monotonic() + 0.5))
        reassigned = _drop_unprofitable_groups(reassigned, candidates, all_tasks)
        c = cost(reassigned)
        if c < best - 1e-09:
            result = reassigned
            best = c
    # 2) bundle insertion repair
    if time.monotonic() < deadline - 0.6:
        repaired = _scarce_bundle_insertion_repair_solution(result, candidates, all_tasks, min(deadline, time.monotonic() + 0.6), max_windows=48, max_window_tasks=14)
        c = cost(repaired)
        if c < best - 1e-09:
            result = _drop_unprofitable_groups(repaired, candidates, all_tasks)
            best = cost(result)
    # 3) pairwise then triple column exchange
    if time.monotonic() < deadline - 0.5:
        exchanged = _pairwise_column_exchange_solution(result, candidates, all_tasks, min(deadline, time.monotonic() + 0.45), top_riders_per_task_key=8, max_k=4, option_limit=60, max_window_tasks=10, max_pairs=34)
        c = cost(exchanged)
        if c < best - 1e-09:
            result = _drop_unprofitable_groups(exchanged, candidates, all_tasks)
            best = cost(result)
    if time.monotonic() < deadline - 0.5:
        exchanged = _triple_column_exchange_solution(result, candidates, all_tasks, min(deadline, time.monotonic() + 0.42), top_riders_per_task_key=8, max_k=4, option_limit=66, max_window_tasks=12, max_triples=20)
        c = cost(exchanged)
        if c < best - 1e-09:
            result = _drop_unprofitable_groups(exchanged, candidates, all_tasks)
            best = cost(result)
    # 4) ALNS column repair on worst windows
    if time.monotonic() < deadline - 0.7:
        repaired = _column_alns_repair_solution(result, candidates, all_tasks, min(deadline, time.monotonic() + 0.7), mode="normal", max_window_tasks=11, top_riders_per_task_key=8, option_limit=60, max_k=4)
        c = cost(repaired)
        if c < best - 1e-09:
            result = _drop_unprofitable_groups(repaired, candidates, all_tasks)
            best = cost(result)
    # 5) final reassignment sweep
    if time.monotonic() < deadline - 0.3:
        reassigned = _reassign_mixed_solution(result, candidates, all_tasks, min(deadline, time.monotonic() + 0.3))
        c = cost(reassigned)
        if c < best - 1e-09:
            result = reassigned
            best = c
    return result


def _fallback_official_greedy(candidates):
    """The simplest feasible baseline: sort rows by score ascending and greedily
    take any (task_key, courier) that uses a free courier and only new tasks. Used
    as a safety net so the portfolio always contains a valid solution."""
    ordered = sorted(candidates, key=lambda c: c[3])
    used_couriers = set()
    covered_tasks = set()
    result = []
    for (task_key, task_ids, courier_id, _score, _will, _idx) in ordered:
        if courier_id in used_couriers:
            continue
        if any(t in covered_tasks for t in task_ids):
            continue
        used_couriers.add(courier_id)
        for task_id in task_ids:
            covered_tasks.add(task_id)
        result.append((task_key, [courier_id]))
    return result
