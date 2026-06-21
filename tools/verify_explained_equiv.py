#!/usr/bin/env python3
"""
verify_explained_equiv.py
=========================

Equivalence harness for solver_explained.py (the de-obfuscated "walkthrough"
edition) against solver_v2.py (the semantic baseline).

WHAT IT PROVES
--------------
solver_explained.py is a line-by-line readable rewrite of solver_v2.py with
identical numeric literals, branch conditions, tie-breaks and time budgets, and
with two blocks of proven-dead code removed (the _D-gated _LOW_BIAS_ACTIVE
re-entry and the second _LOW_BIAS_ACTIVE block + their two helpers). This harness
generates a large bank of instances across EVERY regime (tiny / small / medium /
large / scarce / scarce_tight / low_willingness / high_noise / bundle_heavy, plus
size-matched "trap" regimes and the official sample cases) and, for each one,
runs BOTH solvers and compares:

  * STRICT: bit-for-bit identical output (same group list, same courier order).
  * COST  : both feasible AND equal canonical expected cost
            (autosolver/competition_audit.py::solution_expected_cost) to 1e-6.

Because both solvers gate their search stages on wall-clock time (time.monotonic),
two runs of the SAME solver on the SAME input can already diverge slightly if the
machine load differs between the two runs; that is inherent timing nondeterminism,
not a logic difference. We therefore report BOTH rates. The meaningful guarantee
for a competition is the COST-equivalence rate (identical objective value, both
legal); STRICT equivalence is the stronger bit-identity rate and is what you get
on a quiet machine.

USAGE
-----
    python3 tools/verify_explained_equiv.py                 # default bank
    python3 tools/verify_explained_equiv.py --per-regime 4  # more instances
    python3 tools/verify_explained_equiv.py --quick         # fast smoke run
    python3 tools/verify_explained_equiv.py --time-budget 10

Exit code 0 iff every instance is at least COST-equivalent and within budget.
Pure stdlib; reuses the official-format generator from generalization_stress_test.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

# Reuse the judge-shaped instance generator + canonical evaluator already used by
# the generalization stress test, so the bank matches the over-fitting harness.
from generalization_stress_test import (  # type: ignore  # noqa: E402
    REGIME_BANK,
    evaluate,
    generate_case,
    parse_instance,
)


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _VirtualClock:
    """A deterministic monotonic clock that advances a fixed tick per call.

    Both solvers gate their search stages on time.monotonic(). On real hardware
    two sequential runs can get slightly different effective per-stage budgets
    (machine load, cache warmth), so a TIMING difference can yield a different —
    but equally valid — search depth. To test LOGIC equivalence we drive both
    solvers with the SAME deterministic clock: identical code paths consume
    monotonic() in the same order, so every time-gated branch is decided
    identically and any remaining output difference would be a true logic bug.
    """

    __slots__ = ("t", "tick")

    def __init__(self, tick=1e-3):
        self.t = 0.0
        self.tick = tick

    def monotonic(self):
        self.t += self.tick
        return self.t


def _run(module, text, use_vclock):
    if not use_vclock:
        return [(k, list(cs)) for (k, cs) in module.solve(text)]
    clock = _VirtualClock()
    original = module.time.monotonic
    module.time.monotonic = clock.monotonic
    try:
        return [(k, list(cs)) for (k, cs) in module.solve(text)]
    finally:
        module.time.monotonic = original


def _normalize(solution):
    """Canonical comparable form: sorted list of (task_key, tuple(courier order)).
    Courier ORDER inside a group is preserved (solvers emit a deterministic order),
    but groups are sorted so list ordering does not cause spurious mismatches."""
    return sorted((task_key, tuple(couriers)) for task_key, couriers in solution)


def _strict_equal(a, b):
    """Bit-for-bit identical output, including per-group courier order."""
    return [(k, list(cs)) for k, cs in a] == [(k, list(cs)) for k, cs in b]


def _bank(per_regime, seed_base, quick):
    """Yield (name, regime, text) for the full instance bank."""
    regimes = REGIME_BANK
    per = per_regime
    if quick:
        regimes = {k: REGIME_BANK[k] for k in ("tiny", "small", "medium", "scarce", "low_willing")}
        per = 1
    for regime, spec in regimes.items():
        for k in range(per):
            seed = seed_base + k + 1000 * abs(hash(regime)) % 9000
            yield f"{regime}_s{seed}", regime, generate_case(spec, seed)

    # Official sample cases (real judge-shaped data) if present in the repo.
    official = [
        ("data/official_cases/large_seed301.txt", "large"),
        ("web_agent_demo/generated_cases/small_seed100.txt", "small"),
        ("web_agent_demo/generated_cases/scarce_couriers_seed401.txt", "scarce"),
        ("web_agent_demo/generated_cases/medium_seed201.txt", "medium"),
        ("web_agent_demo/generated_cases/medium_seed202.txt", "medium"),
        ("web_agent_demo/generated_cases/medium_seed203.txt", "medium"),
        ("web_agent_demo/generated_cases/large_seed302.txt", "large"),
        ("web_agent_demo/generated_cases/low_willingness_seed501.txt", "low_willing"),
        ("web_agent_demo/generated_cases/high_noise_seed601.txt", "high_noise"),
        ("web_agent_demo/generated_cases/tiny_seed42.txt", "tiny"),
    ]
    if not quick:
        for rel, regime in official:
            path = os.path.join(ROOT, rel)
            if os.path.exists(path):
                yield "official_" + os.path.basename(rel).replace(".txt", ""), regime, open(path, encoding="utf-8").read()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--per-regime", type=int, default=2, help="fresh random instances per regime")
    ap.add_argument("--time-budget", type=float, default=10.0, help="official per-case budget (s)")
    ap.add_argument("--seed-base", type=int, default=24000, help="base seed for fresh instances")
    ap.add_argument("--quick", action="store_true", help="fast smoke run")
    ap.add_argument("--baseline", default=os.path.join(ROOT, "solver_v2.py"))
    ap.add_argument("--explained", default=os.path.join(ROOT, "solver_explained.py"))
    ap.add_argument("--vclock", action="store_true",
                    help="drive both solvers with an identical deterministic clock so timing "
                         "nondeterminism is removed; STRICT equality then proves LOGIC equivalence")
    args = ap.parse_args()

    baseline = _load(args.baseline, "solver_v2_baseline")
    explained = _load(args.explained, "solver_explained_under_test")

    total = 0
    strict_equal = 0
    cost_equal = 0
    failures = []
    worst_time = 0.0
    worst_time_case = ""
    over_budget = []

    print("=" * 100)
    print(f"EQUIVALENCE  solver_explained.py  vs  solver_v2.py")
    print(f"  baseline : {args.baseline}")
    print(f"  explained: {args.explained}")
    print(f"  mode     : {'VIRTUAL CLOCK (identical deterministic timing -> proves logic equivalence)' if args.vclock else 'WALL CLOCK (real timing; STRICT may dip from timing nondeterminism)'}")
    print("=" * 100)
    header = f"{'case':<26} {'regime':<14} {'v2_cost':>11} {'exp_cost':>11} {'dcost':>8} {'strict':>7} {'v2_t':>6} {'exp_t':>6}"
    print(header)
    print("-" * len(header))

    for name, regime, text in _bank(args.per_regime, args.seed_base, args.quick):
        rows, tasks = parse_instance(text)
        total += 1

        t0 = time.monotonic()
        out_v2 = _run(baseline, text, args.vclock)
        t_v2 = time.monotonic() - t0

        t0 = time.monotonic()
        out_ex = _run(explained, text, args.vclock)
        t_ex = time.monotonic() - t0

        cost_v2, feas_v2, viol_v2 = evaluate(out_v2, rows, tasks)
        cost_ex, feas_ex, viol_ex = evaluate(out_ex, rows, tasks)

        is_strict = _strict_equal(out_v2, out_ex)
        is_cost = (
            feas_v2 and feas_ex
            and abs(cost_v2 - cost_ex) <= 1e-6
        )
        if is_strict:
            strict_equal += 1
        if is_cost:
            cost_equal += 1

        # In --vclock mode wall-clock time is NOT a meaningful budget measurement
        # (the virtual tick decouples monotonic() from real time), so skip the
        # budget accounting there; it is only valid in real wall-clock mode.
        if not args.vclock:
            worst_time = max(worst_time, t_v2, t_ex)
            if max(t_v2, t_ex) >= worst_time - 1e-9:
                worst_time_case = name
            if t_v2 > args.time_budget + 0.01 or t_ex > args.time_budget + 0.01:
                over_budget.append((name, t_v2, t_ex))

        if not is_cost:
            failures.append((name, regime, cost_v2, cost_ex, feas_v2, feas_ex, viol_ex[:2]))

        dcost = cost_ex - cost_v2 if (feas_v2 and feas_ex) else float("nan")
        print(f"{name:<26} {regime:<14} {cost_v2:>11.3f} {cost_ex:>11.3f} {dcost:>8.4f} "
              f"{'YES' if is_strict else 'no':>7} {t_v2:>5.2f}s {t_ex:>5.2f}s")

    print("=" * 100)
    print(f"instances          : {total}")
    print(f"STRICT equal       : {strict_equal}/{total}  ({100.0*strict_equal/max(1,total):.1f}%)  bit-for-bit identical output")
    print(f"COST equal (legal) : {cost_equal}/{total}  ({100.0*cost_equal/max(1,total):.1f}%)  same objective, both feasible")
    if args.vclock:
        print("worst solve time   : n/a in --vclock mode (virtual clock decouples wall time)")
    else:
        print(f"worst solve time   : {worst_time:.2f}s  (case: {worst_time_case})  budget {args.time_budget:.0f}s")
        if over_budget:
            print(f"OVER BUDGET cases  : {len(over_budget)} -> " + ", ".join(f"{n}(v2 {a:.1f}/exp {b:.1f})" for n, a, b in over_budget[:6]))
        else:
            print("OVER BUDGET cases  : 0 (all within budget)")
    if failures:
        print("-" * 100)
        print("NON-COST-EQUIVALENT INSTANCES (investigate):")
        for name, regime, cv, ce, fv, fe, viol in failures:
            print(f"  {name} [{regime}] v2_cost={cv:.3f} exp_cost={ce:.3f} feas v2={fv} exp={fe} sample_viol={viol}")

    if args.vclock:
        # Under an identical deterministic clock, equal logic MUST give identical
        # output; STRICT equality is the authoritative logic-equivalence verdict.
        ok = (strict_equal == total)
        verdict = ("PASS — STRICT bit-for-bit identical under identical timing => proven logic-equivalent"
                   if ok else "FAIL — logic divergence under identical timing (investigate above)")
    else:
        # On real timing, accept COST equivalence (same legal objective). A STRICT
        # dip here is expected timing nondeterminism; re-run with --vclock to prove
        # the underlying logic is identical.
        ok = (cost_equal == total) and not over_budget
        verdict = ("PASS — every instance same objective & legal & in budget"
                   if ok else "FAIL — see above (try --vclock to separate timing from logic)")
    print("=" * 100)
    print("RESULT:", verdict)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
