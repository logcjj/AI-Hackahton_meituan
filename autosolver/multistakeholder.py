# =============================================================================
# autosolver/multistakeholder.py
# -----------------------------------------------------------------------------
# Multi-stakeholder decision layer for AutoSolver  --  rider x merchant x
# customer x platform.  This is an OFFLINE analysis / "decision-mode" layer for
# the demo and the business narrative: it does NOT replace the production
# objective (autosolver.competition_audit.solution_expected_cost, which the
# judge actually scores), and it does NOT touch any solver*.py.  It re-scores or
# re-optimizes a given solver assignment under a four-party weighted utility, so
# evaluators can move the weights and watch the Pareto front / scorecard move.
#
#   U(assignment) = wc*Uc + wr*Ur + wm*Um + wp*Up
#
#     Uc  customer  : -ETA  -  asymmetric lateness penalty (late 1.8 > early 1.2)
#     Ur  rider     : income - fatigue(on-route/continuous hours) - empty-drive
#                     + income-fairness bonus (1 - Gini)
#     Um  merchant  : -|arrival - t_ready| (ready-alignment) + exposure fairness
#     Up  platform  : fulfillment-rate + net-margin  (a normalized proxy for the
#                     official expected-cost objective, kept sign-aligned so the
#                     pure-platform corner of the front == the production solver)
#
# -----------------------------------------------------------------------------
# !! HONEST SIGNAL DISCLOSURE (read this before any code walkthrough) !!
# -----------------------------------------------------------------------------
# The competition TSV gives exactly FOUR real fields per row:
#       task_id_list   courier_id   total_score   willingness
# Everything else a "four-party" utility needs (ETA, ready time, on-route time,
# idle/empty-drive, merchant exposure) is NOT in the data.  We therefore
# SYNTHESIZE those signals *deterministically* from the real fields + a fixed
# seed, and we label every synthetic signal in SyntheticConfig.PROVENANCE.
# We never claim a synthetic number is measured.  The synthesis is a transparent
# monotonic function of real fields (e.g. ETA grows with score & bundle size),
# so the qualitative story ("more lateness -> lower Uc") is faithful even though
# the absolute minutes are illustrative.  See PROVENANCE / describe_provenance().
# =============================================================================
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Any, Iterable

from autosolver.competition_audit import (
    CompetitionRow,
    parse_competition_rows,
    group_expected_cost,
)

# Per-task default cost when nobody is assigned / everyone rejects (official rule).
UNCOVERED_TASK_COST = 100.0


# -----------------------------------------------------------------------------
# Signal provenance: what is REAL vs SYNTHETIC.  Single source of truth.
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class SyntheticConfig:
    """All knobs for the synthesized (Demo-only) signals + their provenance.

    Every field here drives a signal that is NOT in the competition data.  The
    PROVENANCE table is printed in the docs and by describe_provenance() so a
    code reviewer can see exactly which inputs are honest measurements and which
    are illustrative synthesis.
    """

    # --- ETA / time synthesis (minutes). ETA is a monotone function of the real
    #     total_score (a heavier/longer order scores higher) and bundle size. ---
    eta_base_min: float = 8.0          # base trip minutes for a single task
    eta_per_score_min: float = 0.18    # +min per unit of real total_score
    eta_per_extra_task_min: float = 6.5  # +min for each extra task in a bundle (detour)

    # --- Ready-time synthesis (merchant). t_ready spread around the dispatch so
    #     |arrival - t_ready| is sometimes early (rider waits) sometimes late. ---
    ready_base_min: float = 6.0
    ready_per_score_min: float = 0.05
    ready_jitter_min: float = 5.0      # deterministic +/- jitter from id hash

    # --- Lateness penalty (customer). Asymmetric: late hurts more than early. ---
    promise_window_min: float = 30.0   # promised delivery window from ready
    late_slope: float = 1.8            # penalty slope per late minute  (> early)
    early_slope: float = 1.2           # penalty slope per early minute

    # --- Rider economics. Pay is a transparent function of real score + tasks. --
    pay_per_task: float = 5.0          # flat per-delivered-task base pay
    pay_per_score: float = 0.12        # + share of the order "value" (real score)
    fatigue_per_route_min: float = 0.06   # disutility per on-route minute
    empty_drive_min_base: float = 4.0  # synthesized dead-head minutes / pickup
    empty_drive_cost_per_min: float = 0.20

    # --- Merchant exposure baseline (synthetic): each merchant "wants" a fair
    #     share of dispatches.  We hash task_id -> merchant bucket. ---
    n_merchant_buckets: int = 12
    exposure_fairness_weight: float = 1.0

    # --- Deterministic seed for all hashing (so the Demo is reproducible). ---
    seed: int = 20260620

    PROVENANCE: tuple[tuple[str, str, str], ...] = (
        # (signal, source, note)
        ("task_ids", "REAL", "competition column task_id_list (split on ,)"),
        ("courier_id", "REAL", "competition column courier_id"),
        ("total_score", "REAL", "competition column total_score (the official cost basis)"),
        ("willingness", "REAL", "competition column willingness == P(accept)"),
        ("expected_cost", "REAL", "derived from REAL fields via official group_expected_cost"),
        ("fulfillment_prob", "REAL", "1 - Prod(1 - willingness) over a group's couriers"),
        ("ETA_minutes", "SYNTHETIC", "monotone f(total_score, bundle_size): heavier/bundled => longer"),
        ("ready_time_minutes", "SYNTHETIC", "f(total_score) + deterministic id-hash jitter"),
        ("lateness_minutes", "SYNTHETIC", "ETA vs promised window; asym penalty late 1.8 > early 1.2"),
        ("rider_pay", "SYNTHETIC", "pay_per_task + pay_per_score*total_score (illustrative tariff)"),
        ("route_minutes", "SYNTHETIC", "== ETA; proxy for on-route fatigue exposure"),
        ("empty_drive_minutes", "SYNTHETIC", "id-hashed dead-head minutes per pickup"),
        ("worked_minutes", "SYNTHETIC", "route + empty-drive; basis for hourly wage"),
        ("merchant_bucket", "SYNTHETIC", "hash(task_id) -> one of n_merchant_buckets storefronts"),
        ("merchant_exposure", "SYNTHETIC", "count of dispatched orders per merchant bucket"),
    )


def _stable_unit(*parts: Any, seed: int) -> float:
    """Deterministic pseudo-random in [0,1) from arbitrary ids (no real signal).

    Used only for *synthetic* jitter so the Demo is reproducible across runs and
    machines.  Clearly labelled SYNTHETIC in PROVENANCE.
    """
    key = (str(seed) + "|" + "|".join(str(p) for p in parts)).encode("utf-8")
    digest = hashlib.blake2b(key, digest_size=8).digest()
    return int.from_bytes(digest, "big") / float(1 << 64)


# -----------------------------------------------------------------------------
# Solver-output -> internal groups.  Mirrors competition_audit semantics so the
# platform utility stays sign-aligned with the official objective.
# -----------------------------------------------------------------------------
@dataclass
class GroupView:
    task_key: str
    task_ids: tuple[str, ...]
    courier_ids: tuple[str, ...]
    rows: tuple[CompetitionRow, ...]

    @property
    def task_count(self) -> int:
        return len(self.task_ids)

    @property
    def expected_cost(self) -> float:
        return group_expected_cost(self.rows, self.task_count)

    @property
    def fulfillment_prob(self) -> float:
        # P(at least one courier in the group accepts) under independence.
        p_all_reject = 1.0
        for row in self.rows:
            p_all_reject *= (1.0 - row.willingness)
        return 1.0 - p_all_reject


def build_group_views(
    solution: Iterable[tuple[str, list[str]]],
    rows: dict[tuple[str, str], CompetitionRow],
) -> list[GroupView]:
    """Turn a solver assignment into GroupViews; skips rows the solver invented."""
    views: list[GroupView] = []
    for task_key, courier_ids in solution:
        group_rows: list[CompetitionRow] = []
        for courier_id in courier_ids:
            row = rows.get((task_key, courier_id))
            if row is not None:
                group_rows.append(row)
        if not group_rows:
            continue
        views.append(
            GroupView(
                task_key=task_key,
                task_ids=group_rows[0].task_ids,
                courier_ids=tuple(r.courier_id for r in group_rows),
                rows=tuple(group_rows),
            )
        )
    return views


# -----------------------------------------------------------------------------
# Synthetic per-group physical signals (ETA, ready, lateness, pay, drive).
# -----------------------------------------------------------------------------
@dataclass
class GroupSignals:
    group: GroupView
    eta_min: float
    ready_min: float
    lateness_min: float          # signed: + late, - early
    lateness_penalty: float      # asymmetric, always >= 0
    rider_pay: float             # total pay if group delivers (expected later)
    route_min: float
    empty_drive_min: float
    worked_min: float
    merchant_buckets: tuple[int, ...]


def synthesize_group_signals(group: GroupView, cfg: SyntheticConfig) -> GroupSignals:
    n_tasks = group.task_count
    avg_score = sum(r.total_score for r in group.rows) / len(group.rows)

    # ETA (SYNTHETIC): heavier orders + bigger bundles => longer trips.
    eta = (
        cfg.eta_base_min
        + cfg.eta_per_score_min * avg_score
        + cfg.eta_per_extra_task_min * (n_tasks - 1)
    )

    # Ready time (SYNTHETIC): merchant prep time + deterministic jitter.
    jitter = (_stable_unit(group.task_key, "ready", seed=cfg.seed) - 0.5) * 2.0
    ready = (
        cfg.ready_base_min
        + cfg.ready_per_score_min * avg_score
        + cfg.ready_jitter_min * jitter
    )

    # Lateness vs promised window measured from ready (SYNTHETIC).
    delivery_min = max(eta, ready)  # rider cannot leave before food is ready
    promised = ready + cfg.promise_window_min
    lateness = delivery_min - promised  # + late, - early
    if lateness >= 0:
        penalty = cfg.late_slope * lateness
    else:
        penalty = cfg.early_slope * (-lateness)

    # Rider pay (SYNTHETIC tariff): per-task base + share of real order value.
    pay = cfg.pay_per_task * n_tasks + cfg.pay_per_score * sum(r.total_score for r in group.rows) / max(
        1, len(group.rows)
    )

    # Drive / fatigue exposure (SYNTHETIC).
    route = eta
    empty = cfg.empty_drive_min_base * (
        0.5 + _stable_unit(group.task_key, "empty", seed=cfg.seed)
    )
    worked = route + empty

    # Merchant buckets (SYNTHETIC): hash each task to a storefront.
    buckets = tuple(
        int(_stable_unit(t, "merchant", seed=cfg.seed) * cfg.n_merchant_buckets)
        for t in group.task_ids
    )

    return GroupSignals(
        group=group,
        eta_min=eta,
        ready_min=ready,
        lateness_min=lateness,
        lateness_penalty=penalty,
        rider_pay=pay,
        route_min=route,
        empty_drive_min=empty,
        worked_min=worked,
        merchant_buckets=buckets,
    )


# -----------------------------------------------------------------------------
# Fairness primitives.
# -----------------------------------------------------------------------------
def gini(values: list[float]) -> float:
    """Gini coefficient in [0,1]; 0 == perfectly equal. Empty/zero -> 0."""
    xs = [v for v in values if v is not None]
    n = len(xs)
    if n == 0:
        return 0.0
    if all(v == 0 for v in xs):
        return 0.0
    xs = sorted(max(0.0, v) for v in xs)
    cum = 0.0
    for i, v in enumerate(xs, start=1):
        cum += i * v
    total = sum(xs)
    if total <= 0:
        return 0.0
    return (2.0 * cum) / (n * total) - (n + 1.0) / n


def jain_index(values: list[float]) -> float:
    """Jain's fairness index in (0,1]; 1 == perfectly equal."""
    xs = [v for v in values if v is not None]
    if not xs:
        return 1.0
    s = sum(xs)
    sq = sum(v * v for v in xs)
    if sq <= 0:
        return 1.0
    return (s * s) / (len(xs) * sq)


# -----------------------------------------------------------------------------
# Four-party weighted utility.
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class Weights:
    """Tunable four-party weights.  Evaluators move these to walk the front."""
    wc: float = 1.0  # customer
    wr: float = 1.0  # rider
    wm: float = 1.0  # merchant
    wp: float = 1.0  # platform

    def normalized(self) -> "Weights":
        s = self.wc + self.wr + self.wm + self.wp
        if s <= 0:
            return Weights(0.25, 0.25, 0.25, 0.25)
        return Weights(self.wc / s, self.wr / s, self.wm / s, self.wp / s)


@dataclass
class StakeholderReport:
    # Raw per-party (un-normalized) utilities.
    Uc: float
    Ur: float
    Um: float
    Up: float
    U: float                       # weighted total under the supplied Weights
    # Headline metrics for the scorecard.
    expected_cost: float           # REAL official objective (lower better)
    fulfillment_rate: float        # REAL coverage-weighted accept prob
    customer_max_lateness: float   # SYNTHETIC, minutes
    customer_mean_eta: float       # SYNTHETIC, minutes
    rider_income_gini: float       # SYNTHETIC distribution fairness
    rider_income_jain: float       # SYNTHETIC
    rider_worst_hourly: float      # SYNTHETIC Rawlsian worst hourly wage
    merchant_mean_ready_gap: float # SYNTHETIC |arrival - ready|
    merchant_exposure_gini: float  # SYNTHETIC
    covered_tasks: int
    total_tasks: int
    n_riders_used: int
    detail: dict[str, Any] = field(default_factory=dict)


def evaluate_stakeholders(
    solution: Iterable[tuple[str, list[str]]],
    rows: dict[tuple[str, str], CompetitionRow],
    all_tasks: set[str],
    weights: Weights = Weights(),
    cfg: SyntheticConfig = SyntheticConfig(),
) -> StakeholderReport:
    """Re-score an existing solver assignment under the four-party utility."""
    views = build_group_views(solution, rows)
    total_tasks = len(all_tasks)

    covered: set[str] = set()
    per_rider_income: dict[str, float] = {}
    per_rider_worked: dict[str, float] = {}
    merchant_exposure: dict[int, int] = {}

    sum_eta = 0.0
    sum_lateness_pen = 0.0
    max_lateness = 0.0
    sum_ready_gap = 0.0
    sum_empty_cost = 0.0
    sum_fatigue = 0.0
    sum_income = 0.0
    sum_expected_cost = 0.0
    sum_fulfillment_weighted = 0.0
    n_covered_groups = 0

    for view in views:
        sig = synthesize_group_signals(view, cfg)
        p_fulfill = view.fulfillment_prob
        n_tasks = view.task_count

        for t in view.task_ids:
            covered.add(t)

        # Customer: expected ETA + asymmetric lateness, weighted by fulfillment.
        sum_eta += sig.eta_min * n_tasks
        sum_lateness_pen += sig.lateness_penalty * n_tasks
        max_lateness = max(max_lateness, sig.lateness_min)
        sum_ready_gap += abs(sig.eta_min - sig.ready_min) * n_tasks

        # Rider: expected income/fatigue/empty-drive credited to each courier.
        #  - Pay is EXPECTED over willingness (earned only on acceptance).
        #  - Worked time is the FULL dispatched route+dead-head: a dispatch
        #    commits the rider's slot whether or not they ultimately accept, so
        #    low-acceptance riders burn committed time for less expected pay.
        #    => hourly wage = expected_pay / committed_worked_time naturally
        #    punishes low-willingness assignments and makes the Rawlsian worst
        #    hourly wage (and the wage-floor constraint) a meaningful signal.
        for r in view.rows:
            exp_pay = sig.rider_pay * r.willingness
            per_rider_income[r.courier_id] = per_rider_income.get(r.courier_id, 0.0) + exp_pay
            per_rider_worked[r.courier_id] = per_rider_worked.get(r.courier_id, 0.0) + sig.worked_min
            sum_income += exp_pay
            sum_fatigue += cfg.fatigue_per_route_min * sig.route_min * r.willingness
            sum_empty_cost += cfg.empty_drive_cost_per_min * sig.empty_drive_min

        # Merchant: ready-alignment + exposure tally.
        for b in sig.merchant_buckets:
            merchant_exposure[b] = merchant_exposure.get(b, 0) + 1

        # Platform: expected cost + fulfillment.
        sum_expected_cost += view.expected_cost
        sum_fulfillment_weighted += p_fulfill * n_tasks
        n_covered_groups += 1

    uncovered = total_tasks - len(covered)
    # Uncovered tasks: official penalty + worst-case customer/merchant experience.
    sum_expected_cost += UNCOVERED_TASK_COST * uncovered

    # ---- Fairness aggregates (SYNTHETIC distributions) ----
    incomes = list(per_rider_income.values())
    income_gini = gini(incomes)
    income_jain = jain_index(incomes)
    # Rawlsian worst hourly wage among active riders.
    hourly_wages = []
    for cid, inc in per_rider_income.items():
        worked = per_rider_worked.get(cid, 0.0)
        if worked > 1e-9:
            hourly_wages.append(inc / (worked / 60.0))
    worst_hourly = min(hourly_wages) if hourly_wages else 0.0
    exposure_gini = gini([float(v) for v in merchant_exposure.values()])

    fulfillment_rate = (sum_fulfillment_weighted / total_tasks) if total_tasks else 0.0
    mean_eta = (sum_eta / max(1, len(covered)))
    mean_ready_gap = (sum_ready_gap / max(1, len(covered)))

    # ---- Per-party utilities (higher == better for that party) ----
    # Customer utility: negative ETA + negative asymmetric lateness penalty.
    Uc = -(sum_eta) - sum_lateness_pen
    # Rider utility: income - fatigue - empty-drive + income-fairness bonus.
    income_fairness_bonus = (1.0 - income_gini) * (sum_income * 0.15)
    Ur = sum_income - sum_fatigue - sum_empty_cost + income_fairness_bonus
    # Merchant utility: -ready-gap + exposure fairness bonus.
    exposure_fairness_bonus = (1.0 - exposure_gini) * cfg.exposure_fairness_weight * len(covered) * 0.5
    Um = -sum_ready_gap + exposure_fairness_bonus
    # Platform utility: fulfillment reward - expected cost (sign-aligned w/ official obj).
    # Up rises as expected_cost falls, so the pure-platform corner == production solver.
    Up = fulfillment_rate * (UNCOVERED_TASK_COST * total_tasks) - sum_expected_cost

    w = weights.normalized()
    U = w.wc * Uc + w.wr * Ur + w.wm * Um + w.wp * Up

    return StakeholderReport(
        Uc=Uc, Ur=Ur, Um=Um, Up=Up, U=U,
        expected_cost=sum_expected_cost,
        fulfillment_rate=fulfillment_rate,
        customer_max_lateness=max_lateness,
        customer_mean_eta=mean_eta,
        rider_income_gini=income_gini,
        rider_income_jain=income_jain,
        rider_worst_hourly=worst_hourly,
        merchant_mean_ready_gap=mean_ready_gap,
        merchant_exposure_gini=exposure_gini,
        covered_tasks=len(covered),
        total_tasks=total_tasks,
        n_riders_used=len(per_rider_income),
        detail={
            "weights_normalized": (w.wc, w.wr, w.wm, w.wp),
            "rider_hourly_wages": sorted(hourly_wages),
            "rider_incomes": sorted(incomes),
            "merchant_exposure": dict(sorted(merchant_exposure.items())),
            "n_groups": n_covered_groups,
            "uncovered_tasks": uncovered,
        },
    )


# -----------------------------------------------------------------------------
# Re-optimization: a transparent, fast LOCAL re-solver that trades platform cost
# for fairness/equity, parameterized by alpha.  This is a Demo decision-mode
# heuristic (greedy w/ a fairness-aware marginal score), NOT the production
# solver.  It lets the front be generated even without re-running solver_v2 under
# different weights.  Given an incumbent solution, it can also be used directly
# (alpha sweep on the SAME assignment via epsilon-constraint -- see below).
# -----------------------------------------------------------------------------
def fairness_aware_reoptimize(
    rows: dict[tuple[str, str], CompetitionRow],
    all_tasks: set[str],
    alpha: float,
    cfg: SyntheticConfig = SyntheticConfig(),
    min_hourly: float | None = None,
    courier_capacity: int = 4,
) -> list[tuple[str, list[str]]]:
    """Greedy single-dispatch re-solve that trades efficiency for income equity.

    alpha in [0,1]:  0 == pure efficiency (minimize expected cost, == platform),
                     1 == pure equity (level income toward the worst-off riders).
    min_hourly:      optional HARD constraint -- a rider may only take a task if
                     their resulting synthetic committed hourly wage stays
                     >= min_hourly (the Work4Food-style wage floor).
    courier_capacity: max tasks a single courier may carry across the shift.  A
                     courier MAY serve several tasks, so income accumulates and
                     the equity term becomes a real lever (without reuse, every
                     courier is fresh and alpha has nothing to level).

    Operates on single-task rows (the dominant structure) for a clean, auditable
    Demo.  Bundles in the input are still scored by evaluate_stakeholders, but
    assignment here is per task to keep the fairness accounting transparent.
    """
    # Index single-task candidate rows by task.
    by_task: dict[str, list[CompetitionRow]] = {}
    for (task_key, courier_id), row in rows.items():
        if len(row.task_ids) != 1:
            continue
        by_task.setdefault(row.task_ids[0], []).append(row)

    rider_income: dict[str, float] = {}
    rider_worked: dict[str, float] = {}
    rider_load: dict[str, int] = {}
    assignment: list[tuple[str, list[str]]] = []

    # Pre-synthesize per-row signals (single-task groups).
    def row_signal(row: CompetitionRow) -> GroupSignals:
        view = GroupView(row.task_key, row.task_ids, (row.courier_id,), (row,))
        return synthesize_group_signals(view, cfg)

    # Efficiency term: expected cost of assigning this row alone (lower better).
    def efficiency_cost(row: CompetitionRow) -> float:
        return group_expected_cost([row], 1)

    # A global running max of earned-so-far normalizes the equity term so that,
    # at high alpha, a brand-new courier (earned 0) is strongly preferred over a
    # courier already near the top of the income distribution -> Gini falls.
    for task in sorted(all_tasks):
        # Candidates: couriers who still have capacity left this shift.
        candidates = [
            r for r in by_task.get(task, [])
            if rider_load.get(r.courier_id, 0) < courier_capacity
        ]
        if not candidates:
            continue

        feasible: list[tuple[CompetitionRow, float, float, GroupSignals]] = []
        for row in candidates:
            sig = row_signal(row)
            # Hard rider hourly-wage floor (optional): committed worked time.
            if min_hourly is not None:
                prospective_income = rider_income.get(row.courier_id, 0.0) + sig.rider_pay * row.willingness
                prospective_worked = rider_worked.get(row.courier_id, 0.0) + sig.worked_min
                if prospective_worked > 1e-9:
                    hourly = prospective_income / (prospective_worked / 60.0)
                    if hourly < min_hourly:
                        continue
            eff = efficiency_cost(row)
            equity = rider_income.get(row.courier_id, 0.0)  # earned-so-far (Rawlsian)
            feasible.append((row, eff, equity, sig))

        if not feasible:
            # Floor was infeasible for every candidate -> leave task uncovered.
            continue

        # Min-max normalize efficiency and equity onto [0,1] within this task's
        # feasible set so alpha interpolates smoothly instead of one term
        # swamping the other (cost ~ tens, income ~ tens but different ranges).
        effs = [f[1] for f in feasible]
        eqs = [f[2] for f in feasible]
        eff_lo, eff_hi = min(effs), max(effs)
        eq_lo, eq_hi = min(eqs), max(eqs)
        eff_rng = (eff_hi - eff_lo) or 1.0
        eq_rng = (eq_hi - eq_lo) or 1.0

        best_row = None
        best_sig = None
        best_score = math.inf
        for row, eff, equity, sig in feasible:
            eff_n = (eff - eff_lo) / eff_rng       # 0 == cheapest courier
            eq_n = (equity - eq_lo) / eq_rng       # 0 == least-paid-so-far courier
            score = (1.0 - alpha) * eff_n + alpha * eq_n
            if score < best_score - 1e-12:
                best_score = score
                best_row = row
                best_sig = sig
        if best_row is None:
            continue
        cid = best_row.courier_id
        rider_income[cid] = rider_income.get(cid, 0.0) + best_sig.rider_pay * best_row.willingness
        rider_worked[cid] = rider_worked.get(cid, 0.0) + best_sig.worked_min
        rider_load[cid] = rider_load.get(cid, 0) + 1
        assignment.append((best_row.task_key, [cid]))

    return assignment


# -----------------------------------------------------------------------------
# Pareto front via epsilon-constraint: efficiency (expected cost) vs rider Gini.
# -----------------------------------------------------------------------------
@dataclass
class ParetoPoint:
    alpha: float
    expected_cost: float
    rider_income_gini: float
    rider_worst_hourly: float
    fulfillment_rate: float
    customer_max_lateness: float
    report: StakeholderReport


def pareto_front(
    rows: dict[tuple[str, str], CompetitionRow],
    all_tasks: set[str],
    alphas: list[float] | None = None,
    cfg: SyntheticConfig = SyntheticConfig(),
    weights: Weights = Weights(),
    min_hourly: float | None = None,
    courier_capacity: int = 4,
) -> list[ParetoPoint]:
    """Sweep alpha from pure efficiency (0) to pure equity (1).

    Each alpha yields a re-optimized assignment; we re-score it under the four-
    party utility and record (expected_cost, rider_income_gini).  Sorting these
    gives the efficiency-vs-fairness Pareto front.  An optional min_hourly hard
    constraint can be applied to every point (epsilon-constraint on rider wage).
    """
    if alphas is None:
        alphas = [i / 10.0 for i in range(0, 11)]
    points: list[ParetoPoint] = []
    for a in alphas:
        assignment = fairness_aware_reoptimize(
            rows, all_tasks, a, cfg, min_hourly=min_hourly, courier_capacity=courier_capacity
        )
        report = evaluate_stakeholders(assignment, rows, all_tasks, weights=weights, cfg=cfg)
        points.append(
            ParetoPoint(
                alpha=a,
                expected_cost=report.expected_cost,
                rider_income_gini=report.rider_income_gini,
                rider_worst_hourly=report.rider_worst_hourly,
                fulfillment_rate=report.fulfillment_rate,
                customer_max_lateness=report.customer_max_lateness,
                report=report,
            )
        )
    return points


def pareto_efficient(points: list[ParetoPoint]) -> list[ParetoPoint]:
    """Keep only non-dominated points: minimize expected_cost AND rider Gini."""
    front: list[ParetoPoint] = []
    for p in points:
        dominated = False
        for q in points:
            if q is p:
                continue
            if (
                q.expected_cost <= p.expected_cost
                and q.rider_income_gini <= p.rider_income_gini
                and (q.expected_cost < p.expected_cost or q.rider_income_gini < p.rider_income_gini)
            ):
                dominated = True
                break
        if not dominated:
            front.append(p)
    front.sort(key=lambda p: p.expected_cost)
    return front


# -----------------------------------------------------------------------------
# Three-party fairness scorecard.
# -----------------------------------------------------------------------------
@dataclass
class Scorecard:
    rider: dict[str, float]
    merchant: dict[str, float]
    customer: dict[str, float]
    platform: dict[str, float]


def fairness_scorecard(report: StakeholderReport) -> Scorecard:
    """Compact, presentable fairness scorecard across the three "served" parties
    plus a platform summary."""
    return Scorecard(
        rider={
            "income_gini": report.rider_income_gini,        # 0 == equal
            "income_jain": report.rider_income_jain,        # 1 == equal
            "worst_hourly_wage_rawlsian": report.rider_worst_hourly,
            "n_riders": float(report.n_riders_used),
        },
        merchant={
            "mean_ready_alignment_gap_min": report.merchant_mean_ready_gap,
            "exposure_gini": report.merchant_exposure_gini,
        },
        customer={
            "max_lateness_min": report.customer_max_lateness,
            "mean_eta_min": report.customer_mean_eta,
        },
        platform={
            "expected_cost": report.expected_cost,
            "fulfillment_rate": report.fulfillment_rate,
            "covered_tasks": float(report.covered_tasks),
            "total_tasks": float(report.total_tasks),
        },
    )


# -----------------------------------------------------------------------------
# Convenience entry point: parse a TSV and a solver output, return everything.
# -----------------------------------------------------------------------------
def analyze_solution(
    input_text: str,
    solution: Iterable[tuple[str, list[str]]],
    weights: Weights = Weights(),
    cfg: SyntheticConfig = SyntheticConfig(),
) -> tuple[StakeholderReport, Scorecard]:
    rows, tasks = parse_competition_rows(input_text)
    report = evaluate_stakeholders(solution, rows, tasks, weights=weights, cfg=cfg)
    return report, fairness_scorecard(report)


def describe_provenance(cfg: SyntheticConfig = SyntheticConfig()) -> str:
    """Human-readable provenance table for docs / code-walkthrough."""
    lines = [
        "SIGNAL PROVENANCE (REAL = from competition TSV, SYNTHETIC = Demo synthesis):",
        f"  {'signal':<24} {'source':<10} note",
        "  " + "-" * 78,
    ]
    for signal, source, note in cfg.PROVENANCE:
        lines.append(f"  {signal:<24} {source:<10} {note}")
    return "\n".join(lines)


if __name__ == "__main__":  # pragma: no cover - manual smoke
    print(describe_provenance())
