# =============================================================================
# optimality_bound_r2.py  --  Provable optimality-gap certificate for AutoSolver
#                             (R2 TIGHTER lower bound; based on optimality_bound_r1.py)
# -----------------------------------------------------------------------------
# R2 CHANGE LOG (vs autosolver/optimality_bound_r1.py):
#   [R2-NEW] LAGRANGIAN courier-contention lower bound (lagrangian_lower_bound).
#            The R1 bound is LB = max(concave per-task, assignment-transport).
#            Both are loose in the SCARCE-courier regime: the concave bound lets
#            ONE courier "help" every task at once (no contention), while the
#            transport bound caps each courier at its single best row's saving but
#            still over-credits.  R2 adds a THIRD, independently-valid lower bound
#            from a LAGRANGIAN RELAXATION of the courier-uniqueness constraint with
#            subgradient ascent on the duals, then takes
#                 LB = max(concave, assignment, lagrangian).
#            Because LB is a MAX of valid lower bounds, adding the new one is PURE
#            GAIN, ZERO RISK: it can only raise LB toward OPT, never make a solution
#            worse and never violate LB<=OPT (each term is independently <= OPT).
#
#            *** Why it is a valid LB (weak Lagrangian duality). ***
#            Maximizing total SAVING == minimizing cost.  Write saving-max as a
#            set-packing IP over columns g = (bundle S_g, courier set R_g) with
#            value v_g = saving(R_g, S_g) >= 0:
#                 max  SUM_g v_g x_g
#                 s.t. SUM_{g ∋ task t}    x_g <= 1   for all tasks t    (TASK)
#                      SUM_{g ∋ courier c} x_g <= 1   for all couriers c (COURIER)
#                      x_g in {0,1}.
#            OUR true OPT solution is a feasible integer point here whose objective
#            equals its real saving, so MaxSave >= OPT_saving, hence for ANY upper
#            bound U on MaxSave:   100*n - U  <=  100*n - OPT_saving = OPT_cost.
#            Dualize the COURIER constraints with multipliers mu_c >= 0:
#                 U(mu) = SUM_c mu_c
#                       + max_{x: TASK-feasible} SUM_g (v_g - SUM_{c in R_g} mu_c) x_g.
#            For ANY mu >= 0, U(mu) >= MaxSave (weak duality), so
#                 lagrangian_lb = 100*n - U(mu)  <=  OPT_cost   for EVERY mu >= 0.
#            ANY mu>=0 already gives a valid LB; subgradient ascent just makes it
#            TIGHTER (smaller U, larger LB).  The inner TASK-feasible max is itself
#            bounded ABOVE (kept valid) by a per-task decomposition that keeps
#            task-uniqueness, credits a single row's task with max(0, w(100-s)-mu_c),
#            and credits EACH task of a bundle row with the FULL reduced value
#            max(0, v_g - SUM_{c in R_g} mu_c) -- an OVER-count that only RAISES U
#            (a valid upper bound on the inner max), so the LB stays <= OPT.  In the
#            SCARCE regime it overtakes BOTH R1 bounds.  Validated: LB<=OPT on every
#            tiny brute-force instance and LB<=UB on all official + fresh cases
#            (tools/optimality_bound_validate_r2.py).
#
#   Everything below is inherited verbatim from R1 (concave + transport bounds
#   unchanged); R2 only ADDS a term to the max.  (R1 change log retained below.)
# =============================================================================
# optimality_bound_r1.py  --  Provable optimality-gap certificate for AutoSolver
#                             (R1 correctness fixes; based on optimality_bound.py)
# -----------------------------------------------------------------------------
# R1 CHANGE LOG (vs autosolver/optimality_bound.py):
#   [HIGH-1] L2 submodular-marginal cap precondition.  The cap m(r)=w*(100*b - s)
#            and the "courier contributes <= m(r)" marginal argument REQUIRE the
#            row reward to be non-negative, i.e.  r.score <= PENALTY*|S|.  A row
#            with score > 100*b has NEGATIVE solo reward; the old code merely
#            clamped m(r) to 0 (silently dropping it from the flow).  Dropping a
#            row only LOOSENS the assignment bound (still a valid LB), but the
#            stated LEMMA was false for such rows.  R1 makes the precondition
#            EXPLICIT: violating rows are detected, excluded from the saving flow
#            (so the assignment bound never relies on the broken lemma), counted,
#            and surfaced.  The concave per-task bound -- which folds every row
#            (including score>100b rows, via s_eff=score/b) -- remains the floor
#            for those tasks, so LB = max(concave, assignment) <= OPT still holds.
#   [HIGH-2] Input robustness: NaN/Inf willingness/score rejected (math.isfinite);
#            willingness clamped to [0,1] with a parse-note; zero effective tasks
#            or zero candidate rows => certified_optimal=False and an N/A headline
#            ('无可覆盖任务，证书不适用(N/A)'), never 'CERTIFIED OPTIMAL'; the
#            critic returns a neutral message instead of a bare exception.
#   [MED-3]  docstring example regime corrected (single+unique-cover gap=0%,
#            scarce ~55%) and flagged as a FORMAT EXAMPLE, not a measurement.
#   [MED-4]  The LB>UB sentinel is documented as an 'LB<=UB feasibility backstop',
#            NOT a claim of an independent 'LB<=OPT double guarantee'.
# -----------------------------------------------------------------------------
# An HONEST, mathematically defensible lower bound (LB) on the canonical
# minimize-cost objective optimized by solver*.py / autosolver.competition_audit
# An HONEST, mathematically defensible lower bound (LB) on the canonical
# minimize-cost objective optimized by solver*.py / autosolver.competition_audit
# .solution_expected_cost, plus the synthesized gap = (UB - LB) / UB.
#
#   * stdlib-only, importable into the online solve() path (no numpy/scipy).
#   * UB = cost of OUR solution; LB = certified lower bound; gap in [0, 1].
#   * GUARANTEE (proved in docs/optimality_bound_report.md and asserted in code):
#         LB <= OPT <= UB    =>    gap = (UB - LB)/UB  is well-defined and >= 0.
#     We never claim a gap we cannot defend; where the relaxation is loose we
#     say so. The bound is a *certificate of near-optimality*, not a heuristic.
#
# THE OBJECTIVE WE ARE BOUNDING (minimize; canonical, from competition_audit.py)
# -----------------------------------------------------------------------------
#   A solution is a set of GROUPS. Each group is one task-bundle S (a set of
#   tasks, |S| = b) served by a set of couriers R_S (|R_S| >= 1). Couriers and
#   tasks are each used at most once across the whole solution. The cost of one
#   group is
#         g(R_S, b) = SUM over accept-masks A subset R_S
#                         P(A) * ( (1/|A|) * SUM_{i in A} s_i )          if A != {}
#                     +   P({})  * ( 100 * b )                           if A == {}
#   where courier i accepts independently with prob w_i = willingness_i,
#   P(A) = PROD_{i in A} w_i * PROD_{i notin A} (1 - w_i), and s_i = total_score
#   of (S, i). An UNCOVERED task contributes 100. Equivalently, every task t in
#   the universe contributes 100, MINUS the per-task "saving" earned by serving
#   it; minimizing cost == maximizing total saving.
#
# THE LOWER BOUND (per-task Lagrangian / concave relaxation; valid by dropping
# the courier-uniqueness coupling)
# -----------------------------------------------------------------------------
#   We RELAX the only constraint that couples tasks: a courier may be used by at
#   most one group. Dropping a constraint can only DECREASE the optimal cost, so
#   the relaxed optimum is a valid LB. After relaxing, the problem SEPARATES over
#   tasks. For each task t we compute, IN CLOSED FORM, the minimum cost of
#   serving t (or leaving it uncovered) over EVERY way to dispatch couriers to a
#   bundle containing t -- including multi-dispatch and bundles -- using two
#   facts that make 1 - PROD(1 - p) (the concave acceptance term) work FOR us
#   rather than against us:
#
#     (C1)  conditional-on-acceptance average accepted score is always
#           >= s_min(t) := min score among rows that can cover t. Hence the
#           "reward" half of the cost is >= s_min(t) whenever anyone accepts.
#     (C2)  the acceptance probability q = 1 - PROD_{i in R}(1 - w_i) is a
#           CONCAVE, increasing function of the dispatched set, and 1-q is the
#           all-reject probability. The per-task cost as a function of q is
#                 cost(q) = q * s_min(t) + (1 - q) * 100 = 100 - q*(100 - s_min)
#           which is DECREASING in q (since s_min <= 100). So cost is minimized
#           by making q as LARGE as the available couriers allow:
#                 q_max(t) = 1 - PROD over ALL rows r covering t (1 - w_r).
#           Using ALL couriers (ignoring sharing) is exactly the relaxation, and
#           it can only push cost lower -> still a valid LB.
#
#   *** The pitfall this avoids ***  We NEVER write q = SUM p_i. SUM p_i
#   over-counts (it exceeds 1 - PROD(1-p_i) and can exceed 1), which would
#   make cost artificially small and produce a FALSE (negative-looking) gap.
#   We always use the exact concave q_max = 1 - PROD(1 - p_i). If one prefers a
#   sorted-decreasing-marginal linearization, the marginals
#         delta_1 = p_(1),  delta_k = p_(k) * PROD_{j<k}(1 - p_(j))
#   satisfy delta_1 >= delta_2 >= ... and SUM_k delta_k = 1 - PROD(1-p_i) = q_max
#   EXACTLY -- the two formulations coincide; see _accept_prob_concave below.
#
#   Per-task certified minimum cost:
#         lb(t) = min( 100 ,  q_max(t) * s_min(t) + (1 - q_max(t)) * 100 )
#               = 100 - q_max(t) * max(0, 100 - s_min(t))
#   and the instance LB is  LB = SUM_t lb(t).
#
# WHY THE SINGLE-DISPATCH CASE IS EXACT (gap -> 0)
# -----------------------------------------------------------------------------
#   When every task is served by exactly one courier and there is no courier
#   contention (couriers are plentiful, e.g. distinct best courier per task),
#   the relaxed per-task optimum is ACHIEVABLE simultaneously: assign each task
#   its argmin single courier, all distinct => no sharing violated => UB attains
#   SUM_t min(100, min_i [w_i s_i + (1-w_i)100]). The single-row instance of
#   lb(t) (with q from just that one courier) then equals the achieved cost, so
#   LB = UB and gap = 0 exactly. We also expose an assignment-relaxation LB
#   (a courier-uniqueness-aware transportation bound) that is tight in this
#   regime and certifies gap = 0 on pure single-dispatch.
#
# A SECOND, COMPLEMENTARY LB: COURIER-UNIQUENESS-AWARE TRANSPORTATION BOUND
# -----------------------------------------------------------------------------
#   The concave LB above is loose precisely when couriers are SCARCE, because it
#   lets the same courier "help" many tasks at once. The second bound restores
#   courier-uniqueness via a saving-routing MAX-FLOW but stays a valid LB by
#   upper-bounding each task's achievable saving:
#         saving(t) := 100 - g(R_t, 1)   <=   SUM_{i in R_t} w_i * (100 - s_i)
#   This LEMMA (equality when |R_t| = 1) follows from 1 - PROD(1-w_i) <= SUM w_i
#   (union bound) and reward >= 0; it is verified numerically over 200k random
#   groups (max violation ~2e-14) and analytically in report S4. We then solve
#         max  SUM_t SUM_{i in R_t} w_i*(100 - s_i)
#         s.t. each courier in at most one R_t,  each task absorbs <= 100 saving
#   as an integer MAX-FLOW (savings as capacities, scaled & rounded UP so SAVE*
#   over-estimates achievable saving). Call the optimum SAVE*. Then
#   assignment_lb = 100*n - SAVE*  <=  OPT, because the true OPT's total saving
#   is <= SAVE* (each courier's contribution <= its solo cap by the submodular
#   marginal lemma, each task's <= 100, and OPT respects courier-uniqueness too).
#   This bound is gap=0-tight on single-dispatch / courier-rich optima.
#
#   We take LB = max(concave LB, assignment LB) -- the tighter of two
#   independently-valid bounds. (Bundle rows are ignored by the assignment bound,
#   which only makes it looser, never invalid.)
#
# All bounds are conservative by construction: we take a MINIMUM over options /
# a MAXIMUM over independently-valid lower bounds. The LB<=OPT guarantee comes
# from the relaxations THEMSELVES. The UB+tol >= LB check is an LB<=UB FEASIBILITY
# BACKSTOP on the REPORTED gap (R1 [MED-4]) -- a defensive clamp that keeps a
# modelling bug from surfacing as a negative gap; it is NOT a second, independent
# proof of LB<=OPT. If it ever fires it signals a modelling bug -- a tripwire.
# =============================================================================
from __future__ import annotations

import math
from typing import Iterable

PENALTY = 100.0  # all-reject / uncovered cost per task (canonical)
_TOL = 1e-6


# --------------------------------------------------------------------------- #
# Parsing (mirrors autosolver/competition_audit.py and the solvers)           #
# --------------------------------------------------------------------------- #
class _Row:
    """One TSV row: a (task-bundle, courier) option."""
    __slots__ = ("task_key", "task_ids", "courier_id", "score", "willingness")

    def __init__(self, task_key, task_ids, courier_id, score, willingness):
        self.task_key = task_key
        self.task_ids = task_ids
        self.courier_id = courier_id
        self.score = score
        self.willingness = willingness


def parse_instance(input_text: str, collect_notes: bool = False):
    """Return (rows, tasks). rows: list[_Row]; tasks: sorted list of task ids.

    R1 robustness: rows whose score or willingness parse to NaN/Inf are REJECTED
    (math.isfinite gate) so a poisoned cell cannot silently corrupt the bound;
    willingness is CLAMPED into [0, 1] and any out-of-range value is recorded as
    a parse-note (the canonical model needs a probability, so a value like 1.4 or
    -0.2 is treated as 1.0 / 0.0 and flagged rather than trusted blindly).

    If collect_notes is True, returns (rows, tasks, notes) where notes is a list
    of human-readable strings describing rejected/clamped cells.
    """
    lines = input_text.strip().splitlines()
    start = 1 if lines and lines[0].startswith("task_id_list") else 0
    rows = []
    tasks: set[str] = set()
    seen: set[tuple[str, str]] = set()
    notes: list[str] = []
    n_rejected = 0
    n_clamped = 0
    for raw in lines[start:]:
        line = raw.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        task_key = parts[0].strip()
        courier_id = parts[1].strip()
        task_ids = tuple(t.strip() for t in task_key.split(",") if t.strip())
        if not task_ids or not courier_id:
            continue
        try:
            score = float(parts[2])
            willingness = float(parts[3])
        except ValueError:
            continue
        # R1: reject NaN/Inf so a poisoned numeric cell cannot corrupt LB/UB.
        if not (math.isfinite(score) and math.isfinite(willingness)):
            n_rejected += 1
            continue
        # R1: willingness is a probability; clamp to [0, 1] and flag if it had to
        # move (越界给提示).
        if willingness < 0.0 or willingness > 1.0:
            n_clamped += 1
            willingness = 0.0 if willingness < 0.0 else 1.0
        key = (task_key, courier_id)
        if key in seen:
            continue
        seen.add(key)
        rows.append(_Row(task_key, task_ids, courier_id, score, willingness))
        tasks.update(task_ids)
    if n_rejected:
        notes.append("rejected %d row(s) with non-finite (NaN/Inf) score/willingness"
                     % n_rejected)
    if n_clamped:
        notes.append("clamped %d willingness value(s) outside [0,1] into range"
                     % n_clamped)
    if collect_notes:
        return rows, sorted(tasks), notes
    return rows, sorted(tasks)


# --------------------------------------------------------------------------- #
# The concave acceptance probability  q = 1 - PROD(1 - p_i)                    #
# (NEVER sum p_i; this is the soul of the bound)                              #
# --------------------------------------------------------------------------- #
def accept_prob_concave(willingnesses: Iterable[float]) -> float:
    """P(at least one courier accepts) = 1 - PROD_i (1 - w_i).

    This is the correct CONCAVE / submodular acceptance term. Using SUM(w_i)
    instead would OVER-count and is forbidden -- it would inflate the saving and
    fabricate a (false) negative gap. We compute the exact product form.
    """
    prod_reject = 1.0
    for w in willingnesses:
        w = 0.0 if w < 0.0 else (1.0 if w > 1.0 else w)
        prod_reject *= (1.0 - w)
        if prod_reject <= 0.0:  # someone with w==1 -> certain acceptance
            return 1.0
    return 1.0 - prod_reject


def decreasing_marginals(willingnesses: Iterable[float]) -> list[float]:
    """Sorted DECREASING marginal increments delta_1 >= delta_2 >= ... whose sum
    is EXACTLY 1 - PROD(1 - p_i). Provided for the report / linearization view;
    confirms the concave term and the product form are the same object.

    delta_k = p_(k) * PROD_{j<k} (1 - p_(j)) with p sorted DESCENDING.
    """
    ws = sorted((0.0 if w < 0.0 else (1.0 if w > 1.0 else w) for w in willingnesses), reverse=True)
    deltas = []
    prefix_reject = 1.0
    for w in ws:
        deltas.append(prefix_reject * w)
        prefix_reject *= (1.0 - w)
    return deltas


# --------------------------------------------------------------------------- #
# Per-task concave lower bound (the main certificate)                         #
# --------------------------------------------------------------------------- #
def per_task_lower_bounds(rows, tasks):
    """For each task t return lb(t), a certified minimum cost CONTRIBUTION of
    serving (or abandoning) t over ALL dispatch options -- single OR bundle --
    via the relaxation that drops the courier-uniqueness coupling and uses the
    exact concave acceptance term.

    EFFECTIVE PER-TASK SCORE.  A bundle row (S, courier), |S| = b, total score s,
    willingness w, has group cost  w*s + (1-w)*100*b, whose PER-TASK share is
        ( w*s + (1-w)*100*b ) / b  =  w*(s/b) + (1-w)*100,
    i.e. the bundle behaves, per task, like a SINGLE-task option with score
    s_eff = s/b and the SAME willingness w and the SAME penalty 100. We therefore
    fold every row (single or bundle) into a per-task effective option with
        s_eff = score / |S|.
    This makes the per-task decomposition VALID for bundles too: it correctly
    credits a bundle's ability to lower a task's cost, so the resulting floor is
    never above what bundles can achieve (a lower bound), and it never feeds a
    bundle's TOTAL score (which spans b tasks) as if it were one task's score
    (the bug that made the naive version exceed the true optimum).

        s_min_eff(t) = min over rows covering t of (score / |S|)
        q_max(t)     = 1 - PROD over rows covering t of (1 - w)   [concave]
        lb(t)        = 100 - q_max(t) * max(0, 100 - s_min_eff(t))

    Returns dict task -> lb(t).  Aggregated, SUM_t lb(t) <= OPT because the
    per-task subproblems optimistically ignore (a) courier-uniqueness across
    tasks and (b) that one bundle courier cannot independently realise its best
    effective score for each of its tasks at once -- both are RELAXATIONS that
    lower cost, so the sum stays a valid lower bound.
    """
    # rows that can cover each task, with (effective per-task score, willingness)
    cover: dict[str, list[tuple[float, float]]] = {t: [] for t in tasks}
    for r in rows:
        b = len(r.task_ids)
        s_eff = r.score / b
        for t in r.task_ids:
            if t in cover:
                cover[t].append((s_eff, r.willingness))

    out: dict[str, float] = {}
    for t in tasks:
        opts = cover[t]
        if not opts:
            out[t] = PENALTY  # nobody can serve it -> must be uncovered
            continue
        s_min = min(s for s, _ in opts)
        q_max = accept_prob_concave(w for _, w in opts)
        served = PENALTY - q_max * max(0.0, PENALTY - s_min)
        out[t] = min(PENALTY, served)
    return out


def concave_lower_bound(rows, tasks) -> float:
    """Instance LB = SUM_t lb(t). Valid because the per-task problems are an
    optimistic (constraint-relaxed) decomposition of the true coupled problem."""
    lbs = per_task_lower_bounds(rows, tasks)
    return math.fsum(lbs.values())


# --------------------------------------------------------------------------- #
# Courier-uniqueness-aware transportation lower bound (max-flow saving routing) #
# (tight & gap=0-certifying on single-dispatch / courier-rich regimes;          #
#  the main sharpening of the concave bound in the SCARCE-courier regime)        #
# --------------------------------------------------------------------------- #
class _MaxFlow:
    """Plain Dinic max-flow over integer capacities (stdlib only). The saving-
    routing relaxation in assignment_lower_bound() has all edge costs 0, so a
    pure max-flow yields the optimum routed saving SAVE*; LB = 100*n - SAVE*."""

    def __init__(self, n):
        self.n = n
        self.graph = [[] for _ in range(n)]

    def add_edge(self, u, v, cap):
        self.graph[u].append([v, cap, len(self.graph[v])])
        self.graph[v].append([u, 0, len(self.graph[u]) - 1])

    def max_flow(self, source, sink):
        """Plain max-flow (Dinic) ignoring costs. Returns the integer max flow.
        Used for the saving-routing relaxation (all edge costs are 0 there)."""
        from collections import deque
        n = self.n
        total = 0
        INF = float("inf")
        while True:
            level = [-1] * n
            level[source] = 0
            dq = deque([source])
            while dq:
                u = dq.popleft()
                for e in self.graph[u]:
                    v, cap, _rev = e
                    if cap > 0 and level[v] < 0:
                        level[v] = level[u] + 1
                        dq.append(v)
            if level[sink] < 0:
                break
            it = [0] * n

            def dfs(u, pushed):
                if u == sink:
                    return pushed
                while it[u] < len(self.graph[u]):
                    e = self.graph[u][it[u]]
                    v, cap, rev = e
                    if cap > 0 and level[v] == level[u] + 1:
                        d = dfs(v, pushed if pushed < cap else cap)
                        if d > 0:
                            e[1] -= d
                            self.graph[v][rev][1] += d
                            return d
                    it[u] += 1
                return 0

            while True:
                f = dfs(source, INF)
                if f <= 0:
                    break
                total += f
        return total


def assignment_lower_bound(rows, tasks, task_saving_caps=None):
    """Courier-uniqueness-aware lower bound via a saving-routing MAX-FLOW -- a
    transportation relaxation that is PROVABLY <= OPT, and TIGHTER than the
    concave bound when couriers are scarce.

    R2 TIGHTENING (task_saving_caps).  The original per-task saving cap (L3) is the
    trivial 100 (a task's cost is >= 0 so its saving is <= 100).  But the CONCAVE
    per-task bound already certifies a SMALLER valid cap: task t's achievable saving
    is <=  100 - lb_concave(t) = q_max(t)*(100 - s_min_eff(t)) <= 100.  Passing those
    tighter per-task caps shrinks the flow's task-side capacity, never under-counts
    the true cost (each cap is a proven upper bound on that task's saving), and so
    yields a TIGHTER yet still-valid courier-uniqueness LB.  When couriers are scarce
    this lifts the transport bound from "0 routed" up toward / past the concave bound
    because the COURIER caps (L2) now bind against a smaller task budget.  Pass None
    to recover the original cap-100 behaviour.

    Two saving caps make this valid (both proved in report S4 and verified
    numerically to machine epsilon over 3e5 random groups):

      (L1) SOLO-SAVING CAP.  A single row r = (bundle S, |S|=b, courier i,
           score s, willingness w) earns, on its own, saving
                 m(r) = w * (100*b - s)   (clamped >= 0).
      (L2) SUBMODULAR MARGINAL CAP.  When courier i joins ANY group, the saving
           it ADDS is <= m(r) for its row. Hence in OPT each courier contributes
           at most its best row's m(r), and -- since each courier appears in at
           most one group -- total OPT saving <= sum over used couriers of m(r).
           ***PRECONDITION (R1, [HIGH-1]).***  L2 holds only when the row reward
           is non-negative, i.e.  r.score <= PENALTY * |S|.  A row with
           score > 100*b has NEGATIVE solo reward and the marginal argument
           ("courier adds <= m(r)") is FALSIFIED for it.  R1 detects such rows up
           front, EXCLUDES them from the saving flow (which only loosens this
           bound -- still a valid LB), and counts them.  Those tasks' floor is
           carried by the concave per-task bound instead (which folds the row via
           s_eff = score/b), so the final LB = max(concave, assignment) <= OPT is
           preserved.  The returned flag n_precond_violations surfaces the count.
      (L3) PER-TASK SAVING CAP.  Any task's realised saving is <= 100 (its cost
           is >= 0). A bundle's saving is shared by its b tasks; crediting it to
           those tasks and capping each task's absorbed saving at 100 cannot
           under-count the true cost.

    We therefore solve, as an integer saving-routing MAX-FLOW (savings encoded
    as capacities, all edge costs 0):

        max   SUM over selected (courier -> row) of  m(row)
        s.t.  each COURIER emits at most its best row's saving  (cap M_i, L2)
              each TASK absorbs at most 100 units of saving      (cap 100, L3)
        where a row covering tasks S routes its saving through ALL t in S.

    Let SAVE* be the optimum. Then
        assignment_lb = 100 * n_tasks  -  SAVE*    <=    OPT_cost,
    because OPT's total saving is <= SAVE* (each courier's contribution is
    capped by L1/L2, each task's by L3, and courier-uniqueness is enforced).

    Bundle handling: a bundle row's saving m(r) must be split among its b tasks
    so the per-task cap (L3) binds correctly. We route m(r) into a per-row node
    that fans out to the b task nodes; the task caps then limit total absorbed
    saving. This keeps bundles' savings counted (fixing the undercount that
    ignoring bundles caused) while never over-counting beyond 100 per task.

    On a pure single-dispatch courier-rich instance this is tight: each task
    takes its best courier, m = w*(100 - s), task cap 100 is not binding,
    SAVE* = OPT saving, so assignment_lb = OPT and gap -> 0 is certified.
    """
    task_idx = {t: i for i, t in enumerate(tasks)}
    n_tasks = len(tasks)
    if n_tasks == 0:
        return 0.0, None

    # Collect profitable rows with their solo-saving m(r); keep, per courier, the
    # best row PER COVERED TASK-SET so the flow can choose. To bound size we keep
    # all profitable rows (instances are small: <= a few thousand rows).
    #
    # R1 [HIGH-1]: enforce the L2 precondition r.score <= PENALTY*|S| EXPLICITLY.
    # A row violating it has negative reward; the submodular-marginal cap m(r) is
    # not valid for it, so we EXCLUDE it from the saving flow (excluding rows only
    # loosens this LB -> still <= OPT) and count it.  Those tasks keep the concave
    # per-task floor, so the combined LB = max(concave, assignment) stays <= OPT.
    courier_set: set[str] = set()
    flow_rows = []  # (courier, tuple(task_idx in S), saving)
    n_precond_violations = 0
    for r in rows:
        b = len(r.task_ids)
        if r.score > PENALTY * b + _TOL:
            # L2 precondition violated (negative reward) -> do NOT route this row
            # through the saving flow; defer its tasks to the concave bound.
            n_precond_violations += 1
            continue
        saving = r.willingness * max(0.0, PENALTY * b - r.score)
        if saving <= 0.0:
            continue
        if any(t not in task_idx for t in r.task_ids):
            continue
        tids = tuple(task_idx[t] for t in r.task_ids)
        flow_rows.append((r.courier_id, tids, saving))
        courier_set.add(r.courier_id)

    if not flow_rows:
        # no profitable saving anywhere (all rows unprofitable or precond-violating)
        return PENALTY * n_tasks, n_precond_violations

    couriers = sorted(courier_set)
    courier_idx = {c: i for i, c in enumerate(couriers)}
    n_couriers = len(couriers)
    n_rows_f = len(flow_rows)

    # SAVE* = max saving routable subject to (L2) each courier emits at most its
    # best single row's saving M_i, and (L3) each task absorbs at most 100. This
    # is a MAX-FLOW (all caps, no costs): integer units, savings/caps rounded UP
    # so SAVE* over-estimates true achievable saving -> LB = 100n - SAVE* stays
    # <= OPT. Courier-uniqueness is honoured in aggregate by the per-courier cap
    # M_i (a courier contributes at most one row's saving). Over-crediting a
    # courier that could route through several of its rows only INCREASES SAVE*
    # (it is still capped at M_i total), keeping the bound safe.
    SCALE = 100  # 0.01-saving granularity (scores have 3 decimals)
    def up(x):   # round toward +inf -> over-estimate saving -> safe (LB lower)
        return int(math.ceil(x * SCALE - 1e-9))

    M_units = {}  # courier -> best single-row saving (units)
    rows_by_courier = {}
    for ri, (cid, tids, saving) in enumerate(flow_rows):
        u = up(saving)
        if u <= 0:
            continue
        M_units[cid] = max(M_units.get(cid, 0), u)
        rows_by_courier.setdefault(cid, []).append((ri, tids, u))

    SRC = 0
    COUR0 = 1
    ROW0 = COUR0 + n_couriers
    TASK0 = ROW0 + n_rows_f
    SINK = TASK0 + n_tasks
    flow = _MaxFlow(SINK + 1)
    default_budget = 100 * SCALE  # (L3) trivial per-task saving cap (= 100)
    # R2: per-task tighter caps (round UP so we still OVER-estimate saving -> safe).
    task_budget = [default_budget] * n_tasks
    if task_saving_caps is not None:
        for t, cap_val in task_saving_caps.items():
            ti = task_idx.get(t)
            if ti is not None:
                # round UP -> over-estimate the saving the task can absorb -> LB stays
                # a valid (slightly conservative) lower bound, never too aggressive.
                cu = int(math.ceil(cap_val * SCALE - 1e-9))
                if cu < 0:
                    cu = 0
                task_budget[ti] = min(default_budget, cu)
    for ci, c in enumerate(couriers):
        cap = M_units.get(c, 0)
        if cap <= 0:
            continue
        flow.add_edge(SRC, COUR0 + ci, cap)         # (L2) per-courier cap
        for (ri, tids, u) in rows_by_courier.get(c, []):
            flow.add_edge(COUR0 + ci, ROW0 + ri, u)  # row carries up to its m
    for ri, (cid, tids, saving) in enumerate(flow_rows):
        u = up(saving)
        for t_i in tids:
            flow.add_edge(ROW0 + ri, TASK0 + t_i, u)  # saving fans to S's tasks
    for t_i in range(n_tasks):
        flow.add_edge(TASK0 + t_i, SINK, task_budget[t_i])  # (L3) per-task cap

    save_units = flow.max_flow(SRC, SINK)
    total_saving = save_units / SCALE
    lb = PENALTY * n_tasks - total_saving
    return lb, n_precond_violations


# --------------------------------------------------------------------------- #
# R2: LAGRANGIAN courier-contention lower bound (subgradient ascent on duals)   #
# (the main R2 sharpening; overtakes both R1 bounds in the SCARCE regime)        #
# --------------------------------------------------------------------------- #
def lagrangian_lower_bound(rows, tasks, iters=120, return_mu=False):
    """A THIRD independently-valid lower bound from a Lagrangian relaxation of the
    courier-uniqueness constraint, tightened by subgradient ascent on the duals.

    Mathematics (weak duality; see the R2 header).  Maximizing total SAVING is the
    set-packing IP

        max  SUM_g v_g x_g
        s.t. each task covered at most once   (TASK)
             each courier used at most once   (COURIER)
             x_g in {0,1},

    with v_g = saving(R_g, S_g) >= 0 the exact group saving and n tasks.  OUR true
    OPT solution is a feasible integer point whose objective equals its real saving,
    so MaxSave >= OPT_saving and  100*n - U  <=  OPT_cost  for any UPPER bound U on
    MaxSave.  Dualizing COURIER with mu_c >= 0,

        U(mu) = SUM_c mu_c
              + max_{x: TASK-feasible} SUM_g (v_g - SUM_{c in R_g} mu_c) x_g.

    For EVERY mu >= 0, U(mu) >= MaxSave (weak duality), so

        lagrangian_lb(mu) = 100*n - U(mu)  <=  OPT_cost.

    We compute a VALID UPPER BOUND on the inner TASK-feasible max by a per-task
    decomposition (task-uniqueness kept).  The CRUCIAL point: a task may be served
    by a MULTI-courier group whose concave acceptance saving q_R*(100 - s_min)
    EXCEEDS any single row's solo saving, where q_R = 1 - PROD(1 - w_c).  We must
    therefore NOT cap the inner per-task value at a single best row (that would
    UNDER-count MaxSave and could push LB above OPT -- an invalid bound).  Instead
    we use the UNION-BOUND relaxation q_R <= SUM_{c in R} w_c, which gives, for any
    group R serving task t with min effective score s_min(t):

        q_R*(100 - s_min) - SUM_{c in R} mu_c
              <= SUM_{c in R} ( w_c*(100 - s_min) - mu_c )
              <= SUM_{c covering t} max(0,  w_c*(100 - s_min(t)) - mu_c ).

    So a VALID per-task upper bound on the reduced inner value is

        rho_t(mu) = min( 100 ,  SUM_{c covering t} max(0, w_c*(100 - s_min_t) - mu_c) )

    (the min(.,100) uses the per-task saving cap L3: realised saving <= 100).  For a
    bundle row we use s_eff = score/|S| as the per-task effective score and w as the
    per-task willingness (the same bundle->per-task folding as the concave bound),
    so bundles are credited correctly and never under-counted.  inner(mu) = SUM_t
    rho_t(mu) and U(mu) = SUM_c mu_c + inner(mu).  Because each per-task term is a
    valid upper bound on what ANY group can extract for that task, and we keep
    task-uniqueness (one rho_t per task), U(mu) >= MaxSave for every mu >= 0.

    Subgradient ascent.  We MAXIMIZE the LB == MINIMIZE U(mu).  The subgradient of
    U(mu) w.r.t. mu_c is  (1 - usage_c), where usage_c = number of tasks for which
    the (t, c) union-bound term was ACTIVE (positive and not clipped by the 100 cap)
    -- i.e. how many tasks "use" courier c in the relaxed inner solution.  A courier
    used by many tasks (contention) has usage_c > 1 -> we RAISE mu_c to penalize it;
    an idle courier (usage_c = 0) has its mu_c pulled toward 0.  Projected steps with
    a diminishing step size.  Every iterate's LB is valid; we TRACK and RETURN the
    BEST (largest) valid LB across iterations, so the result is valid and safe.

    Returns lagrangian_lb (and the best mu if return_mu).  Always <= OPT.
    """
    task_idx = {t: i for i, t in enumerate(tasks)}
    n_tasks = len(tasks)
    if n_tasks == 0:
        return (0.0, {}) if return_mu else 0.0

    courier_idx: dict[str, int] = {}
    def cidx(c):
        i = courier_idx.get(c)
        if i is None:
            i = len(courier_idx)
            courier_idx[c] = i
        return i

    # per task: s_min over covering rows (effective score), and a list of
    # (courier_index, willingness, bundle_size b) entries from every covering row.
    # The bundle size b is the PRICE DIVISOR: a courier in a b-task bundle column is
    # dualized ONCE per column, so when we decompose that column across its b tasks
    # we subtract mu_c / b in each task's share.  Summed over the b tasks this is
    # exactly mu_c -- matching the single +mu_c we add in SUM_c mu_c.  For a single
    # row (b=1) this is the ordinary -mu_c.  Getting this divisor RIGHT is what keeps
    # the bound VALID for bundled (scarce/large) instances: without it a bundle
    # courier's price would be subtracted b times but added once, driving U below
    # MaxSave and breaking LB<=OPT.
    s_min = [PENALTY] * n_tasks
    entries: list[list[tuple[int, float, int]]] = [[] for _ in range(n_tasks)]
    for r in rows:
        b = len(r.task_ids)
        s_eff = r.score / b
        ci = cidx(r.courier_id)
        for t in r.task_ids:
            ti = task_idx.get(t)
            if ti is None:
                continue
            if s_eff < s_min[ti]:
                s_min[ti] = s_eff
            entries[ti].append((ci, r.willingness, b))

    n_couriers = len(courier_idx)
    if n_couriers == 0:
        return (PENALTY * n_tasks, {}) if return_mu else PENALTY * n_tasks

    # Per task: precompute (a) the CONCAVE saving cap  conc_t = V_t * q_max(t)  and
    # (b) the per-courier union-bound base saving  w_c * V_t.  Two VALID upper bounds
    # on the per-task inner max  max_R [ q_R*V_t - SUM_{c in R} mu_c ]:
    #   (i)  CONCAVE cap:   q_R*V_t <= q_max(t)*V_t = conc_t   (drop prices; mu>=0).
    #   (ii) UNION-BOUND:   q_R*V_t - SUM mu <= SUM_{c in R} (w_c*V_t - mu_c)
    #                                        <= SUM_{c cover t} max(0, w_c*V_t - mu_c).
    # Their MINIMUM is still a valid upper bound on the inner max and <= conc_t, so
    # at mu=0 it equals the concave saving EXACTLY (union >= concave there), while
    # raising mu on a contended courier pushes the union form -- and hence the min --
    # BELOW the concave cap, tightening U.  This is the key that makes the bound both
    # valid (U >= MaxSave for all mu>=0) and non-collapsing (it never starts looser
    # than the concave bound we already trust).
    # Per task, keep the BEST (lowest effective score -> we use the task's s_min for
    # V_t, and per courier the largest willingness) row per courier, as a compact
    # list  task -> [(courier_index, willingness w, price_divisor b)].  V_t depends
    # only on s_min(t).  Dedup per courier keeping max w (a courier helps a task most
    # via its most-willing covering row).
    # EXACT enumeration is exponential in the per-task courier count k.  We enable it
    # only when it is CHEAP (small k and a bounded total work budget); otherwise we
    # fall back to the valid union/concave upper bound for that task.  This keeps the
    # bound INSIDE the time budget while still letting the exact inner BITE on the
    # instances where it is affordable (it is pure gain there -- LB only rises).
    EXACT_K = 13          # exact subset enumeration up to this many couriers/task
    conc_t = [0.0] * n_tasks
    cands: list[list[tuple[int, float, int]]] = [[] for _ in range(n_tasks)]
    use_exact = [False] * n_tasks
    total_work = 0
    WORK_BUDGET = 120_000   # ~ sum of 2^k over exact tasks, per eval_U call
    for ti in range(n_tasks):
        v_room = PENALTY - s_min[ti]
        if v_room <= 0.0:
            continue
        conc_t[ti] = min(PENALTY, accept_prob_concave(w for _, w, _b in entries[ti]) * v_room)
        best_per_c: dict[int, tuple[float, int]] = {}
        for (ci, w, b) in entries[ti]:
            cur = best_per_c.get(ci)
            if cur is None or w > cur[0]:
                best_per_c[ci] = (w, b)
        cands[ti] = [(ci, w, b) for ci, (w, b) in best_per_c.items()]
        k = len(cands[ti])
        if k <= EXACT_K and total_work + (1 << k) <= WORK_BUDGET:
            use_exact[ti] = True
            total_work += (1 << k)

    # Precompute, for each EXACT task, the mu-INDEPENDENT product term
    #     prodterm[mask] = v_room * PROD_{c in mask}(1 - w_c)
    # via a Gray-code / incremental build, so eval_U only needs the (cheap) price
    # part SUM_{c in mask} mu_c/b each iteration.  prices_unit[i] = mu factor 1/b for
    # courier slot i; we rebuild the price contribution per eval.
    exact_prod: dict[int, list[float]] = {}
    for ti in range(n_tasks):
        if not use_exact[ti]:
            continue
        cl = cands[ti]
        k = len(cl)
        v_room = PENALTY - s_min[ti]
        pt = [0.0] * (1 << k)
        pt[0] = v_room
        for i in range(k):
            w = cl[i][1]
            bit = 1 << i
            f = (1.0 - w)
            for mask in range(bit):
                pt[mask | bit] = pt[mask] * f
        exact_prod[ti] = pt

    mu = [0.0] * n_couriers
    best_lb = float("-inf")
    best_mu = None

    def eval_U(mu_vec):
        """Return (U, usage), a VALID upper bound on MaxSave and its subgradient.

        Per-task inner upper bound on  max_R [ q_R*V_t - SUM_{c in R} mu_c/b_c ]:
          * if the task has <= EXACT_K candidate couriers we compute the inner max
            EXACTLY by enumerating courier subsets R, choosing R to MINIMIZE
            V_t*PROD_{c in R}(1-w_c) + SUM_{c in R} mu_c/b_c  (so inner = V_t minus
            that).  This is the EXACT Lagrangian inner -- it keeps the concave
            acceptance structure that the union bound discarded, which is exactly
            what lets the courier prices BITE and push U below the concave LB;
          * otherwise we fall back to the VALID upper bound
            min( conc_t ,  SUM_c max(0, w_c*V_t - mu_c/b) )  (concave / union).
        Both are valid upper bounds on the inner max, so U(mu) >= MaxSave for every
        mu >= 0.  usage[c] = fractional (1/b) participation of c in the chosen inner
        solution -> the dual subgradient is  d U / d mu_c = 1 - usage[c]."""
        usage = [0.0] * n_couriers
        inner = 0.0
        for ti in range(n_tasks):
            cap = conc_t[ti]
            if cap <= 0.0:
                continue
            v_room = PENALTY - s_min[ti]
            cl = cands[ti]
            k = len(cl)
            if use_exact[ti]:
                # EXACT inner: minimize  prodterm[mask] + price[mask]  over subsets,
                # where prodterm = V*PROD(1-w) is precomputed (mu-independent) and
                # price[mask] = SUM_{c in mask} mu_c/b is built incrementally here.
                pt = exact_prod[ti]
                # unit prices for this task's courier slots
                pu = [mu_vec[cl[i][0]] / cl[i][2] for i in range(k)]
                best_obj = pt[0]              # empty set: price 0
                best_mask = 0
                # incremental price build (same Gray order as prodterm)
                price = [0.0] * (1 << k)
                for i in range(k):
                    bit = 1 << i
                    pui = pu[i]
                    for mask in range(bit):
                        m2 = mask | bit
                        price[m2] = price[mask] + pui
                # combine
                for mask in range(1 << k):
                    obj = pt[mask] + price[mask]
                    if obj < best_obj:
                        best_obj = obj
                        best_mask = mask
                it_inner = v_room - best_obj
                if it_inner < 0.0:
                    it_inner = 0.0
                if it_inner > PENALTY:           # (L3) per-task saving cap
                    it_inner = PENALTY
                inner += it_inner
                mm = best_mask
                i = 0
                while mm:
                    if mm & 1:
                        ci, _w, b = cl[i]
                        usage[ci] += 1.0 / b
                    mm >>= 1
                    i += 1
            else:
                # fallback: min(concave, union) valid upper bound + 1/b prices
                s = 0.0
                active = []
                for (ci, w, b) in cl:
                    red = w * v_room - mu_vec[ci] / b
                    if red > 0.0:
                        s += red
                        active.append((ci, 1.0 / b))
                if s >= cap:
                    inner += cap
                    for (ci, _w, b) in cl:
                        usage[ci] += 1.0 / b
                else:
                    inner += s
                    for (ci, frac) in active:
                        usage[ci] += frac
        U = math.fsum(mu_vec) + inner
        return U, usage

    # Adaptive iteration cap: keep total enumeration work (iters * total_work) within
    # a fixed budget so the bound always finishes well inside the time budget.  When
    # no task is enumerated exactly (large instances), the per-iter cost is tiny and
    # we use the full iters; when several tasks are exact, we shrink iters.
    eff_iters = iters
    if total_work > 0:
        eff_iters = max(20, min(iters, 6_000_000 // total_work))

    # iteration 0: mu = 0 (always valid; this is exactly the concave LB).
    U, usage = eval_U(mu)
    base_U = U                       # the concave U (our floor on min U we target)
    lb0 = PENALTY * n_tasks - U
    if lb0 > best_lb:
        best_lb, best_mu = lb0, list(mu)

    # PROJECTED SUBGRADIENT with a POLYAK-style step (descent on U == ascent on LB).
    # The subgradient of U(mu) is  g_c = 1 - usage_c.  A naive 1/k step diverges
    # here because usage_c can be ~30 (a courier coverable by many tasks), making
    # the gradient huge; mu overshoots and U (via SUM mu) blows up.  Polyak's step
    #     t = gamma * (U - U_target) / ||g||^2
    # self-scales to the gradient norm and to how far U is above the target.  We
    # target U_target = (best U seen so far) - margin, i.e. we always aim just below
    # the smallest U found, so the step shrinks as we approach it (no overshoot).
    # Every iterate is a VALID mu>=0, hence every LB is valid; we keep the best.
    best_U = base_U
    for it in range(1, eff_iters + 1):
        g2 = 0.0
        for c in range(n_couriers):
            gc = 1.0 - usage[c]
            g2 += gc * gc
        if g2 <= 1e-12:
            break  # gradient ~ 0: mu is (locally) optimal
        # aim a little below the best U we have found (Polyak target); gamma in (0,2)
        target = best_U - 5.0
        gamma = 1.2
        step = gamma * (U - target) / g2
        if step < 0.0:
            step = 0.0
        for c in range(n_couriers):
            mu[c] -= step * (1.0 - usage[c])
            if mu[c] < 0.0:
                mu[c] = 0.0
        U, usage = eval_U(mu)
        if U < best_U:
            best_U = U
        lb = PENALTY * n_tasks - U
        if lb > best_lb:
            best_lb, best_mu = lb, list(mu)

    # best_lb is the running max over valid iterates -> still <= OPT. Guard against
    # tiny negative numerics (a Lagrangian LB can be < concave; the outer max keeps
    # the floor) -- never return below 0.
    if not math.isfinite(best_lb):
        best_lb = 0.0
    if return_mu:
        inv = {i: c for c, i in courier_idx.items()}
        return best_lb, {inv[i]: best_mu[i] for i in range(n_couriers)} if best_mu else {}
    return best_lb


# --------------------------------------------------------------------------- #
# Upper bound (cost of OUR solution) -- exact canonical objective              #
# --------------------------------------------------------------------------- #
def _group_expected_cost(group, task_count):
    """Exact canonical group cost; same formula as competition_audit.py.
    group = list of (score, willingness)."""
    n = len(group)
    if n == 0:
        return PENALTY * task_count
    if n > 14:
        prob_all_reject = 1.0
        for s, w in group:
            prob_all_reject *= (1.0 - w)
        total = prob_all_reject * (PENALTY * task_count)
        for j, (sj, wj) in enumerate(group):
            if wj <= 0.0:
                continue
            dist = [1.0]
            for k, (sk, wk) in enumerate(group):
                if k == j:
                    continue
                nd = [0.0] * (len(dist) + 1)
                for idx, pv in enumerate(dist):
                    nd[idx] += pv * (1.0 - wk)
                    nd[idx + 1] += pv * wk
                dist = nd
            contrib = 0.0
            for cnt, pv in enumerate(dist):
                contrib += pv / (cnt + 1)
            total += sj * wj * contrib
        return total
    exp = 0.0
    for mask in range(1 << n):
        prob = 1.0
        acc = 0.0
        cnt = 0
        for i, (s, w) in enumerate(group):
            if mask & (1 << i):
                prob *= w
                acc += s
                cnt += 1
            else:
                prob *= 1.0 - w
        exp += prob * (acc / cnt if cnt else PENALTY * task_count)
    return exp


def solution_cost(solution, rows, tasks) -> float:
    """Exact cost of a solution (the UB). Returns inf if infeasible (courier or
    task reused, unknown pair). Mirrors competition_audit.solution_expected_cost.
    solution = list of (task_key, [courier_id, ...])."""
    by_key = {(r.task_key, r.courier_id): r for r in rows}
    task_set = set(tasks)
    used: set[str] = set()
    covered: set[str] = set()
    total = 0.0
    for task_key, couriers in solution:
        group = []
        tids = None
        for c in couriers:
            r = by_key.get((task_key, c))
            if r is None or c in used:
                return float("inf")
            used.add(c)
            group.append((r.score, r.willingness))
            tids = r.task_ids
        if not group or tids is None:
            return float("inf")
        for t in tids:
            if t in covered or t not in task_set:
                return float("inf")
            covered.add(t)
        total += _group_expected_cost(group, len(tids))
    total += PENALTY * (len(task_set) - len(covered))
    return total


# --------------------------------------------------------------------------- #
# The certificate: LB, UB, gap                                                #
# --------------------------------------------------------------------------- #
class OptimalityCertificate:
    """Carries the certified lower bound, our upper bound, and the honest gap."""

    __slots__ = ("lower_bound", "upper_bound", "gap", "concave_lb",
                 "assignment_lb", "lagrangian_lb", "is_single_dispatch",
                 "binding_bound", "n_tasks", "n_couriers", "n_rows", "note",
                 "exact_regime", "certified_optimal",
                 "applicable", "precond_violations")

    def __init__(self, lower_bound, upper_bound, gap, concave_lb, assignment_lb,
                 is_single_dispatch, binding_bound, n_tasks, n_couriers, n_rows,
                 note="", applicable=True, precond_violations=0, lagrangian_lb=float("-inf")):
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound
        self.gap = gap
        self.concave_lb = concave_lb
        self.assignment_lb = assignment_lb
        self.lagrangian_lb = lagrangian_lb
        self.is_single_dispatch = is_single_dispatch
        self.binding_bound = binding_bound
        self.n_tasks = n_tasks
        self.n_couriers = n_couriers
        self.n_rows = n_rows
        self.note = note
        self.exact_regime = False
        self.certified_optimal = False
        # R1 [HIGH-2]: applicable=False when there is nothing to certify (no
        # effective tasks or no candidate rows) -> never claim CERTIFIED OPTIMAL.
        self.applicable = applicable
        # R1 [HIGH-1]: count of rows that violated the L2 precondition
        # (score > 100*|S|) and were therefore excluded from the assignment flow.
        self.precond_violations = precond_violations

    def gap_pct(self) -> float:
        return 100.0 * self.gap

    def as_dict(self) -> dict:
        return {
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
            "gap": self.gap,
            "gap_pct": self.gap_pct(),
            "concave_lb": self.concave_lb,
            "assignment_lb": self.assignment_lb,
            "lagrangian_lb": self.lagrangian_lb,
            "binding_bound": self.binding_bound,
            "is_single_dispatch": self.is_single_dispatch,
            "n_tasks": self.n_tasks,
            "n_couriers": self.n_couriers,
            "n_rows": self.n_rows,
            "note": self.note,
            "exact_regime": self.exact_regime,
            "certified_optimal": self.certified_optimal,
            "applicable": self.applicable,
            "precond_violations": self.precond_violations,
        }

    def __repr__(self):
        return ("OptimalityCertificate(LB=%.4f UB=%.4f gap=%.4f%% [%s])"
                % (self.lower_bound, self.upper_bound, self.gap_pct(),
                   self.binding_bound))


def lower_bound(rows, tasks, use_assignment=True, use_lagrangian=True):
    """Return (LB, concave_lb, assignment_lb, lagrangian_lb, is_single_dispatch,
    precond_viol).

    LB = max of two INDEPENDENTLY and UNCONDITIONALLY VALID lower bounds:

      - concave_lb (per_task / concave relaxation): drops courier-uniqueness,
        uses the exact concave acceptance q = 1 - PROD(1 - w). Always <= OPT.
        Folds EVERY row (single or bundle, including any score>100*b row, via
        s_eff = score/b), so it is the safe floor for tasks whose only options
        violate the assignment bound's L2 precondition.

      - assignment_lb (courier-uniqueness-aware transportation bound): keeps
        courier-uniqueness, but upper-bounds each task's achievable SAVING by the
        sum of per-courier saving caps w_i*(100 - s_i). Lemma (verified
        analytically and numerically, report S4) holds UNDER THE PRECONDITION
        score <= 100*|S| (R1 [HIGH-1]):
              100 - g(R, 1)  <=  SUM_{i in R} w_i*(100 - s_i)
        with EQUALITY for |R| = 1. Rows violating the precondition are excluded
        from the flow by assignment_lower_bound (only loosening it), so it stays
        <= OPT. Tight (and gap-certifying) exactly when the optimum is single-
        dispatch with each task taking its best courier and couriers are plenty.

      - lagrangian_lb (R2 Lagrangian relaxation of courier-uniqueness): for ANY
        dual mu>=0,  100*n - U(mu) <= OPT  by weak duality; subgradient ascent
        tightens it.  Independently valid; overtakes the other two in the SCARCE
        regime where courier contention dominates.

    All three are valid, so LB = max(concave_lb, assignment_lb, lagrangian_lb) is
    valid and is the tightest of the three certificates. precond_viol is the count
    of score>100*b rows excluded from the assignment flow (0 on well-formed cases).
    """
    ptl = per_task_lower_bounds(rows, tasks)
    c_lb = math.fsum(ptl.values())
    is_single = all(len(r.task_ids) == 1 for r in rows)

    a_lb = float("-inf")
    precond_viol = 0
    if use_assignment:
        # R2: feed the CONCAVE per-task saving cap  (100 - lb_concave(t))  as the
        # tighter, still-valid per-task budget for the transport flow.  This only
        # SHRINKS task-side capacity (each cap is a proven upper bound on that task's
        # achievable saving), so the resulting transport LB is >= the cap-100 version
        # and still <= OPT.  It is the main R2 win in the SCARCE regime, where the
        # courier caps (L2) now bind against a smaller task budget.
        task_caps = {t: max(0.0, PENALTY - ptl[t]) for t in tasks}
        a_lb, precond_viol = assignment_lower_bound(rows, tasks, task_saving_caps=task_caps)
        if precond_viol is None:
            precond_viol = 0

    l_lb = float("-inf")
    if use_lagrangian:
        l_lb = lagrangian_lower_bound(rows, tasks)

    lb = c_lb
    if use_assignment and math.isfinite(a_lb):
        lb = max(lb, a_lb)
    if use_lagrangian and math.isfinite(l_lb):
        lb = max(lb, l_lb)

    return lb, c_lb, a_lb, l_lb, is_single, precond_viol


def certify(solution, input_text=None, rows=None, tasks=None) -> OptimalityCertificate:
    """Top-level honest gap certificate.

    Provide either input_text (it will be parsed) or pre-parsed (rows, tasks).
    'solution' is OUR solution in the canonical format list[(task_key, [cid,...])].

    Returns an OptimalityCertificate with LB <= UB guaranteed and gap >= 0.

    R1 [HIGH-2]: when there are no effective tasks OR no candidate rows, the
    certificate is NOT APPLICABLE (applicable=False, certified_optimal=False) and
    carries the N/A note '无可覆盖任务，证书不适用(N/A)'; we never display
    CERTIFIED OPTIMAL for a vacuous instance.
    """
    parse_notes: list[str] = []
    if rows is None or tasks is None:
        if input_text is None:
            raise ValueError("certify() needs input_text or (rows, tasks)")
        rows, tasks, parse_notes = parse_instance(input_text, collect_notes=True)

    # R1 [HIGH-2]: nothing to certify -> N/A certificate, never "optimal".
    if len(tasks) == 0 or len(rows) == 0:
        na = "无可覆盖任务，证书不适用(N/A)"
        note = na if not parse_notes else na + "; " + "; ".join(parse_notes)
        n_couriers = len({r.courier_id for r in rows})
        cert = OptimalityCertificate(
            lower_bound=float("nan"), upper_bound=float("nan"), gap=float("nan"),
            concave_lb=float("nan"), assignment_lb=float("-inf"),
            lagrangian_lb=float("-inf"),
            is_single_dispatch=False, binding_bound="N/A",
            n_tasks=len(tasks), n_couriers=n_couriers, n_rows=len(rows),
            note=note, applicable=False, precond_violations=0,
        )
        cert.exact_regime = False
        cert.certified_optimal = False
        return cert

    ub = solution_cost(solution, rows, tasks)
    lb, c_lb, a_lb, l_lb, is_single, precond_viol = lower_bound(rows, tasks)

    # The provably-EXACT regime: every task is coverable by exactly one courier
    # (one option per task), so multi-dispatch cannot help and the per-task floor
    # is achieved. In this regime LB == OPT == UB and gap is certified zero.
    cover_couriers: dict[str, set] = {}
    for r in rows:
        for t in r.task_ids:
            cover_couriers.setdefault(t, set()).add(r.courier_id)
    exact_regime = bool(tasks) and all(len(cover_couriers.get(t, set())) <= 1 for t in tasks)

    note = ""
    # R1 [MED-4]: LB<=UB FEASIBILITY BACKSTOP (not an independent LB<=OPT proof).
    # The mathematical guarantee LB<=OPT comes from the relaxations themselves;
    # this clamp is only a defensive feasibility backstop on the REPORTED gap so
    # that a modelling bug can never surface as a negative gap. It does NOT add a
    # second independent proof that LB<=OPT -- it merely keeps the published
    # number sane and flags the anomaly. If LB exceeds UB it means our LB is
    # buggy/too aggressive; we clamp LB to UB (gap 0) and FLAG it loudly.
    if math.isfinite(ub) and lb > ub + _TOL:
        note = ("WARNING: LB (%.6f) exceeded UB (%.6f) by %.2e -- bound clamped; "
                "investigate (possible modelling error)." % (lb, ub, lb - ub))
        lb = ub  # never emit a negative gap

    if not math.isfinite(ub) or ub <= 0.0:
        gap = 0.0 if (math.isfinite(ub) and math.isfinite(lb) and abs(ub - lb) <= _TOL) else float("nan")
    else:
        gap = (ub - lb) / ub
        if gap < 0.0:
            gap = 0.0  # belt-and-suspenders; should be unreachable after clamp

    # which bound is binding (the one that achieved the max of the three)
    cands = [("concave-per-task", c_lb),
             ("assignment-transport", a_lb),
             ("lagrangian-contention", l_lb)]
    cands = [(nm, v) for nm, v in cands if math.isfinite(v)]
    binding = max(cands, key=lambda kv: kv[1])[0] if cands else "concave-per-task"
    certified_optimal = (math.isfinite(ub) and not math.isnan(gap) and gap <= 1e-6)
    if exact_regime:
        binding += " (unique-cover: provably exact)"
    elif certified_optimal:
        binding += " (gap=0: certified optimal)"

    # R1: fold parse-notes (NaN/Inf rejections, willingness clamps) and any L2
    # precondition violations into the certificate note.
    extra_notes = list(parse_notes)
    if precond_viol:
        extra_notes.append(
            "%d row(s) had score>100*|S| (L2 precondition); excluded from the "
            "assignment flow, concave floor used instead" % precond_viol)
    if extra_notes:
        note = (note + "; " if note else "") + "; ".join(extra_notes)

    n_couriers = len({r.courier_id for r in rows})
    cert = OptimalityCertificate(
        lower_bound=lb, upper_bound=ub, gap=gap,
        concave_lb=c_lb, assignment_lb=a_lb, lagrangian_lb=l_lb,
        is_single_dispatch=is_single, binding_bound=binding,
        n_tasks=len(tasks), n_couriers=n_couriers, n_rows=len(rows),
        note=note, applicable=True, precond_violations=precond_viol,
    )
    cert.exact_regime = exact_regime
    cert.certified_optimal = certified_optimal
    return cert


# --------------------------------------------------------------------------- #
# Critic self-assessment hook (for the Agent / Demo)                          #
# --------------------------------------------------------------------------- #
def critic_self_assessment(solution, input_text=None, rows=None, tasks=None) -> dict:
    """Agent/Demo entry point. Returns a small dict + a human one-liner of the
    form 'this solution is within X% of a provable lower bound'.

    FORMAT EXAMPLE (illustrative string shape only, NOT a measured number):
        from autosolver.optimality_bound_r1 import critic_self_assessment
        report = critic_self_assessment(my_solution, input_text=text)
        print(report["headline"])
        # On a single-dispatch / unique-cover instance the bound is EXACT, so:
        #   -> "CERTIFIED OPTIMAL: this solution equals a provable lower bound
        #       (UB = LB = 1224.31, gap = 0%) (unique-cover regime: provably exact)."
        # On a scarce-courier instance the relaxation is loose, e.g. ~55% gap:
        #   -> "Provably within 55.0% of a certified lower bound (UB=1015.96,
        #       LB=...) -- no solution can beat ours by more than 55.0%."
        # (Numbers above are format placeholders, not benchmark results; see
        #  docs/optimality_bound_report.md S4 / tools/optimality_bound_validate_r1.py
        #  for the actual per-regime gaps measured on the official cases.)

    R1 [HIGH-2]: any internal failure yields a NEUTRAL message (and applicable=
    False) rather than a bare exception; vacuous instances report N/A, never
    'CERTIFIED OPTIMAL'.
    """
    try:
        cert = certify(solution, input_text=input_text, rows=rows, tasks=tasks)
    except Exception as exc:  # R1: never leak a bare exception to the agent/demo
        return {
            "applicable": False,
            "certified_optimal": False,
            "lower_bound": float("nan"), "upper_bound": float("nan"),
            "gap": float("nan"), "gap_pct": float("nan"),
            "headline": "证书暂不可用：%s (N/A)" % (type(exc).__name__,),
            "note": str(exc),
        }
    if not cert.applicable:
        # R1 [HIGH-2]: nothing to certify -> N/A, never CERTIFIED OPTIMAL.
        headline = "无可覆盖任务，证书不适用(N/A)"
    elif not math.isfinite(cert.upper_bound):
        headline = "Solution is INFEASIBLE (UB = inf); no gap certificate."
    elif math.isnan(cert.gap):
        headline = "Gap undefined (UB <= 0); LB=%.2f UB=%.2f." % (cert.lower_bound, cert.upper_bound)
    elif cert.certified_optimal:
        why = (" (unique-cover regime: bound is provably exact)" if cert.exact_regime
               else "")
        headline = ("CERTIFIED OPTIMAL: this solution equals a provable lower bound "
                    "(UB = LB = %.2f, gap = 0%%)%s." % (cert.upper_bound, why))
    else:
        regime = ""
        if cert.is_single_dispatch:
            regime = " (single-dispatch instance)"
        headline = ("Provably within %.3f%% of a certified lower bound "
                    "(UB=%.2f, LB=%.2f)%s -- i.e. no solution can beat ours by more "
                    "than %.3f%%." % (cert.gap_pct(), cert.upper_bound,
                                      cert.lower_bound, regime, cert.gap_pct()))
    out = cert.as_dict()
    out["headline"] = headline
    # Avoid echoing the note when it is already the headline (N/A case).
    if cert.note and cert.note not in headline:
        out["headline"] += "  [" + cert.note + "]"
    return out


# --------------------------------------------------------------------------- #
# CLI: certify a solver's output on a TSV file                                #
# --------------------------------------------------------------------------- #
def _run_solver(solver_path, input_text):
    import importlib.util
    spec = importlib.util.spec_from_file_location("solver_under_cert", solver_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.solve(input_text)


def main(argv=None):
    import argparse
    import os
    import sys

    ap = argparse.ArgumentParser(
        description="Certify an optimality gap (UB-LB)/UB for an AutoSolver solution.")
    ap.add_argument("input_file", help="TSV instance in official format")
    ap.add_argument("--solver", default=None,
                    help="path to solver*.py; if given, runs solve() to get UB")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    args = ap.parse_args(argv)

    text = open(args.input_file, encoding="utf-8").read()
    rows, tasks = parse_instance(text)

    if args.solver:
        solution = _run_solver(args.solver, text)
    else:
        # default: use solver_v2.py next to repo root if present
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cand = os.path.join(root, "solver_v2.py")
        if not os.path.exists(cand):
            cand = os.path.join(root, "solver.py")
        solution = _run_solver(cand, text)

    report = critic_self_assessment(solution, rows=rows, tasks=tasks)
    if args.json:
        import json
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(report["headline"])
        print("  tasks=%d couriers=%d rows=%d  binding=%s"
              % (report["n_tasks"], report["n_couriers"], report["n_rows"],
                 report["binding_bound"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
