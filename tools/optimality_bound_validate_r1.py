#!/usr/bin/env python3
"""
optimality_bound_validate_r1.py
===============================

R1 validation harness for autosolver/optimality_bound_r1.py
(based on tools/optimality_bound_validate.py). Reproducibility fixes:

  * imports the R1 certificate module (optimality_bound_r1), exercising the
    [HIGH-1] L2 precondition handling and [HIGH-2] robustness paths;
  * fresh-instance seeds are DETERMINISTIC: seed = base + k + crc32(regime)
    (zlib.crc32 -- stable across processes / Python builds) instead of the old
    abs(hash(regime)) which depends on PYTHONHASHSEED;
  * PYTHONHASHSEED is forced to 0 (re-exec if needed) so any residual set
    ordering is pinned, making the per-regime gap numbers reproducible for
    docs/optimality_bound_report.md S4.

For the official sample cases AND a bank of FRESH random instances (reusing the
exact generator from tools/generalization_stress_test.py), this script:

  1. runs solver_v2.py to get OUR solution (the UB),
  2. computes the certified lower bound LB (concave + assignment-transport),
  3. checks the certificate is VALID:  LB <= UB + tol  and  gap in [0, 1],
  4. aggregates per-regime gap statistics,
  5. cross-checks a brute-force exact OPT on TINY instances so we can confirm
     LB <= OPT <= UB really holds (not just LB <= UB).

It writes nothing by itself; the numbers feed docs/optimality_bound_report.md.
Pure stdlib. Run:  python3 tools/optimality_bound_validate_r1.py [--per-regime N]
"""
from __future__ import annotations

import argparse
import importlib.util
import itertools
import os
import sys
import time
import zlib

# R1: pin PYTHONHASHSEED for reproducible set-ordering. If unset/non-zero,
# re-exec this process once with PYTHONHASHSEED=0 so the numbers are stable.
if os.environ.get("PYTHONHASHSEED") != "0":
    os.environ["PYTHONHASHSEED"] = "0"
    os.execv(sys.executable, [sys.executable] + sys.argv)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from autosolver import optimality_bound_r1 as ob  # noqa: E402  (R1 module)


def _regime_seed(base: int, k: int, regime: str) -> int:
    """Deterministic per-regime seed: base + k + crc32(regime). zlib.crc32 is
    stable across processes and Python builds (unlike the old hash())."""
    return base + k + (zlib.crc32(regime.encode("utf-8")) % 9000)

# reuse the FRESH-instance generator + regime bank from the stress harness
_gst_path = os.path.join(ROOT, "tools", "generalization_stress_test.py")
_spec = importlib.util.spec_from_file_location("gst", _gst_path)
gst = importlib.util.module_from_spec(_spec)
sys.modules["gst"] = gst  # register so @dataclass can resolve the module
_spec.loader.exec_module(gst)


def _load_solver(path):
    spec = importlib.util.spec_from_file_location("solver_v_cert", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------- #
# Brute-force EXACT optimum for TINY instances (<= ~5 tasks) -- the ground
# truth used to confirm LB <= OPT <= UB, not merely LB <= UB.
# --------------------------------------------------------------------------- #
def brute_force_optimum(rows, tasks):
    """Exhaustive TRUE optimum of the canonical objective, INCLUDING bundles, for
    small instances. Enumerates every assignment of a (disjoint-courier) group to
    each candidate bundle and every task-set partition, minimising expected cost.
    Returns None if the instance is too large to enumerate exactly.

    Model: a 'column' is (task_set S, courier subset R) with cost g(R, |S|). A
    feasible solution is a collection of columns whose task-sets partition (a
    subset of) the universe (uncovered tasks pay 100 each) and whose courier
    subsets are pairwise disjoint. We DP over task subsets with a courier-usage
    branch; tractable for <= 6 tasks and modest courier counts.
    """
    task_list = sorted(tasks)
    n = len(task_list)
    if n > 6:
        return None
    tindex = {t: i for i, t in enumerate(task_list)}
    couriers = sorted({r.courier_id for r in rows})
    if len(couriers) > 16:
        return None
    cindex = {c: i for i, c in enumerate(couriers)}

    # group rows by exact task-set (as a task bitmask); each task-set has a list
    # of (courier, score, willingness)
    by_set = {}
    for r in rows:
        if any(t not in tindex for t in r.task_ids):
            continue
        m = 0
        for t in r.task_ids:
            m |= 1 << tindex[t]
        by_set.setdefault(m, []).append((r.courier_id, r.score, r.willingness))

    # enumerate, per task-set, ALL non-empty courier subsets EXACTLY (no pruning,
    # so the result is the TRUE optimum). Bail out (return None) if any task-set
    # has too many couriers to enumerate exhaustively, so we never report an
    # inexact "optimum".
    set_options = {}
    for m, opts in by_set.items():
        if len(opts) > 13:
            return None  # would require pruning -> not exact; skip this instance
        b = bin(m).count("1")
        best_by_cmask = {}
        k = len(opts)
        for mask in range(1, 1 << k):  # non-empty courier subsets
            grp = [opts[i] for i in range(k) if mask & (1 << i)]
            cmask = 0
            ok = True
            for cid, _, _ in grp:
                bit = 1 << cindex[cid]
                if cmask & bit:
                    ok = False
                    break
                cmask |= bit
            if not ok:
                continue
            cost = ob._group_expected_cost([(s, w) for _, s, w in grp], b)
            if cmask not in best_by_cmask or cost < best_by_cmask[cmask]:
                best_by_cmask[cmask] = cost
        set_options[m] = sorted(best_by_cmask.items(), key=lambda x: x[1])

    full = (1 << n) - 1
    candidate_sets = list(set_options.keys())

    from functools import lru_cache

    # DP over remaining task mask; for each, either leave the lowest task
    # uncovered (cost 100) or cover it with some set-option that fits.
    memo = {}

    def solve(remaining, used_couriers):
        if remaining == 0:
            return 0.0
        key = (remaining, used_couriers)
        if key in memo:
            return memo[key]
        # pick lowest remaining task
        low = (remaining & -remaining).bit_length() - 1
        # option A: leave it uncovered
        best = 100.0 + solve(remaining & ~(1 << low), used_couriers)
        # option B: cover via a set that contains 'low' and is subset of remaining
        for m in candidate_sets:
            if not (m >> low) & 1:
                continue
            if m & ~remaining:
                continue
            for cmask, cost in set_options[m]:
                if cmask & used_couriers:
                    continue
                val = cost + solve(remaining & ~m, used_couriers | cmask)
                if val < best:
                    best = val
        memo[key] = best
        return best

    return solve(full, 0)


def evaluate_case(name, regime, text, solver):
    rows, tasks = ob.parse_instance(text)
    sol = solver.solve(text)
    cert = ob.certify(sol, rows=rows, tasks=tasks)
    valid = (not (cert.upper_bound == cert.upper_bound and  # not nan
                  cert.lower_bound > cert.upper_bound + 1e-6)) and cert.gap >= -1e-12
    opt = brute_force_optimum(rows, tasks)
    opt_ok = True
    if opt is not None and cert.lower_bound > opt + 1e-6:
        opt_ok = False  # LB exceeded the TRUE optimum -> bound invalid!
    return {
        "name": name, "regime": regime,
        "n_tasks": cert.n_tasks, "n_couriers": cert.n_couriers,
        "ub": cert.upper_bound, "lb": cert.lower_bound, "gap": cert.gap,
        "concave": cert.concave_lb, "assign": cert.assignment_lb,
        "binding": cert.binding_bound, "valid": valid,
        "opt": opt, "opt_ok": opt_ok,
        "exact_regime": cert.exact_regime, "certified_optimal": cert.certified_optimal,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-regime", type=int, default=3)
    ap.add_argument("--seed-base", type=int, default=20000)
    args = ap.parse_args()

    solver = _load_solver(os.path.join(ROOT, "solver_v2.py"))
    results = []

    # official named samples
    official = [
        ("tiny_seed42", "tiny"), ("small_seed100", "small"),
        ("scarce_couriers_seed401", "scarce"), ("medium_seed201", "medium"),
        ("medium_seed202", "medium"), ("medium_seed203", "medium"),
        ("low_willingness_seed501", "low_willing"),
        ("high_noise_seed601", "high_noise"), ("large_seed302", "large"),
    ]
    print("=" * 100)
    print("OFFICIAL NAMED CASES")
    print("=" * 100)
    for fname, regime in official:
        p = os.path.join(ROOT, "web_agent_demo", "generated_cases", fname + ".txt")
        if not os.path.exists(p):
            continue
        text = open(p, encoding="utf-8").read()
        r = evaluate_case(fname, regime, text, solver)
        results.append(("official", r))
        _print_row(r)

    # fresh random instances per regime
    print("=" * 100)
    print("FRESH RANDOM INSTANCES (generator from generalization_stress_test.py)")
    print("=" * 100)
    fresh = []
    for regime, spec in gst.REGIME_BANK.items():
        for k in range(args.per_regime):
            seed = _regime_seed(args.seed_base, k, regime)  # R1: deterministic
            text = gst.generate_case(spec, seed)
            r = evaluate_case(f"{regime}_s{seed}", regime, text, solver)
            fresh.append(r)
            results.append(("fresh", r))
            _print_row(r)

    # also a batch of TINY instances for brute-force OPT cross-check
    print("=" * 100)
    print("TINY BRUTE-FORCE CROSS-CHECK (LB <= OPT <= UB)")
    print("=" * 100)
    tiny_spec = gst.REGIME_BANK["tiny"]
    bf_checked = 0
    bf_ok = 0
    for k in range(20):
        text = gst.generate_case(tiny_spec, 30000 + k)
        r = evaluate_case(f"tinybf_{k}", "tiny", text, solver)
        if r["opt"] is not None:
            bf_checked += 1
            ok = (r["lb"] <= r["opt"] + 1e-6) and (r["opt"] <= r["ub"] + 1e-6)
            bf_ok += int(ok)
            print(f"  {r['name']:14s} LB={r['lb']:8.3f} OPT={r['opt']:8.3f} UB={r['ub']:8.3f} "
                  f"LB<=OPT={'Y' if r['lb']<=r['opt']+1e-6 else 'N'} "
                  f"OPT<=UB={'Y' if r['opt']<=r['ub']+1e-6 else 'N'}")

    # summary
    print("=" * 100)
    allr = [r for _, r in results]
    invalid = [r for r in allr if not r["valid"]]
    opt_viol = [r for r in allr if r["opt"] is not None and not r["opt_ok"]]
    print(f"TOTAL cases: {len(allr)}  | invalid certificates (LB>UB or neg gap): {len(invalid)}")
    print(f"Brute-force OPT cross-checks: {bf_ok}/{bf_checked} satisfied LB<=OPT<=UB")
    if opt_viol:
        print("!!! LB EXCEEDED TRUE OPT on:", [r["name"] for r in opt_viol])
    # per-regime gap means (fresh only)
    agg = {}
    for r in fresh:
        agg.setdefault(r["regime"], []).append(r)
    print("\nPER-REGIME GAP (fresh random):")
    print(f"{'regime':<16}{'n':>4}{'mean gap%':>11}{'min gap%':>10}{'max gap%':>10}")
    for regime in sorted(agg):
        rs = agg[regime]
        gaps = [100 * x["gap"] for x in rs]
        print(f"{regime:<16}{len(rs):>4}{sum(gaps)/len(gaps):>11.2f}{min(gaps):>10.2f}{max(gaps):>10.2f}")
    return 0 if not invalid and not opt_viol else 1


def _print_row(r):
    tag = "OK" if r["valid"] else "INVALID!!"
    opt_s = f" OPT={r['opt']:.2f}" if r["opt"] is not None else ""
    print(f"{r['name']:26s} {r['regime']:12s} n={r['n_tasks']:3d} c={r['n_couriers']:3d} "
          f"UB={r['ub']:9.2f} LB={r['lb']:8.2f} gap={100*r['gap']:5.1f}% "
          f"conc={r['concave']:7.1f} asg={r['assign']:7.1f}{opt_s} {tag}")


if __name__ == "__main__":
    raise SystemExit(main())
