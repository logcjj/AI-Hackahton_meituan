#!/usr/bin/env python3
"""
optbound_lemma_stress_r1.py
===========================

Randomised stress test of the THREE lemmas that make the assignment-transport
lower bound in autosolver/optimality_bound_r1.py valid. This is the reproducible
engine behind the report's S4 numbers: it actually RUNS L1/L2/L3 over many random
groups and prints the maximum observed violation for each.

The sampling is RESTRICTED to the precondition regime  score <= PENALTY*|S|
(R1 [HIGH-1]): outside that regime L2 is provably false, the code excludes such
rows from the flow, and there is nothing to "verify" there -- so we sample where
the lemma is claimed to hold and confirm it numerically to machine epsilon.

The exact group cost g(R, b) is computed by optimality_bound_r1._group_expected_cost
(the canonical objective), so the lemmas are checked against the SAME cost the
certificate uses.

  L1  SOLO-SAVING IDENTITY.   For a single row r=(b, s, w) with s <= 100*b,
          100*b - g({r}, b)  ==  w*(100*b - s)            (equality, not <=)
      i.e. the solo saving m(r) is EXACT. (violation should be ~0)

  L2  SUBMODULAR MARGINAL CAP.  Adding a courier i (its own row r_i=(b,s_i,w_i),
      s_i <= 100*b) to ANY existing group R serving the same bundle adds saving
          saving(R + i) - saving(R)  <=  w_i*(100*b - s_i)  =  m(r_i)
      where saving(R) = 100*b - g(R, b). (violation should be <= ~1e-12)

  L3  PER-TASK SAVING CAP.  For any group R on a bundle of b tasks,
          0  <=  saving(R)  <=  100*b      (so each of the b tasks absorbs <=100)
      (both sides should hold with violation ~0)

Pure stdlib. Deterministic (fixed seed). Run:
    PYTHONHASHSEED=0 python3 tools/optbound_lemma_stress_r1.py [--trials N] [--seed S]
"""
from __future__ import annotations

import argparse
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from autosolver import optimality_bound_r1 as ob  # noqa: E402

PENALTY = ob.PENALTY


def _saving(group, b):
    """saving(R) = 100*b - g(R, b), using the canonical exact group cost."""
    return PENALTY * b - ob._group_expected_cost(group, b)


def _rand_row(rng, b):
    """A random (score, willingness) row on a b-task bundle, RESTRICTED to the
    precondition regime score <= 100*b (so L2 is claimed to hold)."""
    s = rng.uniform(0.0, PENALTY * b)   # score in [0, 100b] -> precondition holds
    w = rng.uniform(0.0, 1.0)
    return (s, w)


def stress(trials, seed):
    rng = random.Random(seed)
    l1_max = 0.0   # |solo saving - w*(100b - s)|
    l2_max = 0.0   # marginal - m(r_i)  (want <= 0)
    l3_lo_max = 0.0  # max(0, -saving)   (saving should be >= 0)
    l3_hi_max = 0.0  # max(0, saving - 100b)
    n_l1 = n_l2 = n_l3 = 0

    for _ in range(trials):
        b = rng.randint(1, 3)          # single + double + triple bundles
        k = rng.randint(1, 6)          # group size
        group = [_rand_row(rng, b) for _ in range(k)]

        # ---- L1: solo-saving identity on each single row -----------------
        for (s, w) in group:
            m = w * (PENALTY * b - s)
            solo = _saving([(s, w)], b)
            l1_max = max(l1_max, abs(solo - m))
            n_l1 += 1

        # ---- L3: per-bundle saving in [0, 100b] --------------------------
        sv = _saving(group, b)
        l3_lo_max = max(l3_lo_max, max(0.0, -sv))
        l3_hi_max = max(l3_hi_max, max(0.0, sv - PENALTY * b))
        n_l3 += 1

        # ---- L2: submodular marginal cap ---------------------------------
        # add ONE more courier i to the group; its marginal saving must be
        # <= its solo cap m(r_i).
        s_i, w_i = _rand_row(rng, b)
        m_i = w_i * (PENALTY * b - s_i)
        base = _saving(group, b)
        plus = _saving(group + [(s_i, w_i)], b)
        marginal = plus - base
        # violation is how much marginal EXCEEDS the cap (want <= 0)
        l2_max = max(l2_max, marginal - m_i)
        n_l2 += 1

    return {
        "trials": trials, "seed": seed,
        "L1_checks": n_l1, "L1_max_abs_err": l1_max,
        "L2_checks": n_l2, "L2_max_excess_over_cap": l2_max,
        "L3_checks": n_l3, "L3_max_below_zero": l3_lo_max,
        "L3_max_above_100b": l3_hi_max,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=200000)
    ap.add_argument("--seed", type=int, default=12345)
    args = ap.parse_args()

    res = stress(args.trials, args.seed)
    print("=" * 70)
    print("L1/L2/L3 LEMMA STRESS (precondition regime score <= 100*|S|)")
    print("  module: autosolver/optimality_bound_r1.py   seed=%d  trials=%d"
          % (res["seed"], res["trials"]))
    print("=" * 70)
    print("L1 solo-saving identity      checks=%-8d max|err|        = %.3e"
          % (res["L1_checks"], res["L1_max_abs_err"]))
    print("L2 submodular marginal cap   checks=%-8d max(marg - cap) = %.3e"
          % (res["L2_checks"], res["L2_max_excess_over_cap"]))
    print("L3 saving >= 0               checks=%-8d max(-saving)    = %.3e"
          % (res["L3_checks"], res["L3_max_below_zero"]))
    print("L3 saving <= 100*|S|         checks=%-8d max(sv - 100b)  = %.3e"
          % (res["L3_checks"], res["L3_max_above_100b"]))
    print("-" * 70)
    ok = (res["L1_max_abs_err"] < 1e-9 and res["L2_max_excess_over_cap"] < 1e-9
          and res["L3_max_below_zero"] < 1e-9 and res["L3_max_above_100b"] < 1e-9)
    print("ALL LEMMAS HOLD to ~machine epsilon:" , "YES" if ok else "NO -- INVESTIGATE")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
