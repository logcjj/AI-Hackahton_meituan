#!/usr/bin/env python3
"""
tune_r3.py — R3 self-evolution tuning harness.

Goal: find a TUNED polish configuration that, run as an EXTRA argmin candidate
inside the leftover budget, strictly improves on HELD-OUT instances without
exceeding the time budget. TRAIN seeds drive the search; disjoint HELD-OUT +
official samples validate. Pure exact-cost argmin keeps no-regression.

This harness DOES NOT modify any solver; it imports solver_v2 operators directly
and re-implements v4's _extra_polish with a tunable config, measuring the
*tuned-only* candidate's contribution against v4's base on each instance.
"""
from __future__ import annotations
import importlib.util, sys, time, json, argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import generalization_stress_test as g  # generator + canonical evaluate


def load(fn, al):
    spec = importlib.util.spec_from_file_location(al, str(ROOT / fn))
    m = importlib.util.module_from_spec(spec)
    sys.modules[al] = m
    spec.loader.exec_module(m)
    return m


V2 = load("solver_v2.py", "solver_v2_for_v3")   # same alias v3/v4 use
V3 = load("solver_v3.py", "solver_v3_for_v4")
V4 = load("solver_v4.py", "v4_tune")

_parse = V4._parse_candidates
_detect = V4._detect_regime
cost_fn = V2._solution_expected_cost
cov_fn = V2._solution_covered_count

GLOBAL_DEADLINE_S = 9.0  # identical hard ceiling to v4


def tuned_polish(base, base_cost, candidates, all_tasks, deadline, regime_flags, cfg):
    """A parameterized re-run of v4's scarce/low polish, seeded from base.
    Returns (best, best_cost, n_improved_ops). best_cost <= base_cost."""
    is_scarce, is_low, is_low_cr = regime_flags
    best, best_cost = base, base_cost
    now = time.monotonic
    improved = 0

    # Tuned polish keeps a 0.25s cushion under the hard deadline so worst-case
    # wall time stays ~<=8.75s even with scheduler jitter.
    tdl = deadline - 0.25

    def slice_to(s):
        return min(tdl, now() + s)

    def try_replace(cand, require_cover=False):
        nonlocal best, best_cost, improved
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
            improved += 1

    if is_low or is_low_cr:
        if now() < tdl - 0.9:
            try_replace(V2._low_deep_window_repair_solution(best, candidates, all_tasks, slice_to(cfg["low_deep_s"])))
        if now() < tdl - 0.6:
            try_replace(V2._low_late_acceptance_repair_solution(best, candidates, all_tasks, slice_to(cfg["low_late_s"])))
        if now() < tdl - 0.5:
            try_replace(V2._low_worst_window_repair_solution(best, candidates, all_tasks, slice_to(cfg["low_worst_s"])))

    if is_scarce:
        if now() < tdl - 1.0:
            cand = V2._scarce_bundle_insertion_repair_solution(
                best, candidates, all_tasks, slice_to(cfg["scarce_ins_s"]),
                max_windows=cfg["scarce_windows"], max_window_tasks=cfg["scarce_win_tasks"])
            try_replace(cand)
        if now() < tdl - 0.6:
            cand = V2._column_alns_repair_solution(
                best, candidates, all_tasks, slice_to(cfg["alns_s"]), mode="scarce",
                max_window_tasks=cfg["alns_win_tasks"], top_riders_per_task_key=cfg["alns_top"],
                option_limit=cfg["alns_opt"], max_k=cfg["alns_k"])
            try_replace(cand)
        if now() < tdl - 0.45:
            cand = V2._pairwise_column_exchange_solution(
                best, candidates, all_tasks, slice_to(cfg["pair_s"]),
                top_riders_per_task_key=cfg["pair_top"], max_k=cfg["pair_k"], option_limit=cfg["pair_opt"],
                max_window_tasks=cfg["pair_win_tasks"], max_pairs=cfg["pair_pairs"])
            try_replace(cand, require_cover=True)
        if now() < tdl - 0.4:
            cand = V2._triple_column_exchange_solution(
                best, candidates, all_tasks, slice_to(cfg["triple_s"]),
                top_riders_per_task_key=cfg["triple_top"], max_k=cfg["triple_k"], option_limit=cfg["triple_opt"],
                max_window_tasks=cfg["triple_win_tasks"], max_triples=cfg["triple_triples"])
            try_replace(cand, require_cover=True)

    # generic tail
    if now() < tdl - 0.35:
        try_replace(V2._reassign_mixed_solution(best, candidates, all_tasks, slice_to(0.3)))
    if now() < tdl - 0.25:
        try_replace(V2._local_improve_mixed_solution(best, candidates, all_tasks, slice_to(0.22), include_pair_rewire=True))

    # ITERATED hill-climb: while budget remains, re-apply the cheap exact-monotone
    # operators from the (possibly improved) running best. Re-seeding from an
    # improved point can unlock moves a single pass misses. Stops on no-improve.
    rounds = 0
    while now() < tdl - 0.35 and rounds < cfg.get("iter_rounds", 0):
        before = best_cost
        try_replace(V2._reassign_mixed_solution(best, candidates, all_tasks, slice_to(0.35)))
        if now() < tdl - 0.3:
            try_replace(V2._local_improve_mixed_solution(best, candidates, all_tasks, slice_to(0.3), include_pair_rewire=True))
        if is_scarce and now() < tdl - 0.5:
            cand = V2._pairwise_column_exchange_solution(
                best, candidates, all_tasks, slice_to(cfg["pair_s"]),
                top_riders_per_task_key=cfg["pair_top"], max_k=cfg["pair_k"], option_limit=cfg["pair_opt"],
                max_window_tasks=cfg["pair_win_tasks"], max_pairs=cfg["pair_pairs"])
            try_replace(cand, require_cover=True)
        rounds += 1
        if best_cost >= before - 1e-9:
            break

    return best, best_cost, improved


# Default = a BROADER config than v4's existing polish (wider windows / more
# riders / larger option_limit / more pairs+triples) to exploit leftover budget.
DEFAULT_CFG = {
    "low_deep_s": 1.3, "low_late_s": 1.0, "low_worst_s": 0.8,
    "scarce_ins_s": 1.1, "scarce_windows": 110, "scarce_win_tasks": 18,
    "alns_s": 0.9, "alns_win_tasks": 16, "alns_top": 14, "alns_opt": 95, "alns_k": 5,
    "pair_s": 0.6, "pair_top": 14, "pair_k": 5, "pair_opt": 95, "pair_win_tasks": 14, "pair_pairs": 60,
    "triple_s": 0.55, "triple_top": 14, "triple_k": 5, "triple_opt": 100, "triple_win_tasks": 16, "triple_triples": 34,
    "iter_rounds": 0,
}


def run_instance(text, cfg, hard_ceiling=GLOBAL_DEADLINE_S):
    """Run v3 base, then BOTH v4's stock polish and the tuned polish (each from
    the same base, within the SAME remaining budget). Report base/v4/tuned costs
    and wall time. The tuned candidate is only allowed to run if budget remains."""
    candidates, all_tasks = _parse(text)
    start = time.monotonic()
    deadline = start + hard_ceiling
    base = V3.solve(text)
    base_cost = cost_fn(base, candidates, all_tasks)
    flags = _detect(candidates, all_tasks)

    # v4 stock polish (for reference) — re-run from base under remaining budget
    t_after_base = time.monotonic()
    v4_best, v4_cost = base, base_cost
    if t_after_base < deadline - 0.35:
        try:
            v4_best, v4_cost = V4._extra_polish(V2, base, base_cost, candidates, all_tasks,
                                                deadline, *flags)
        except Exception:
            v4_best, v4_cost = base, base_cost

    # tuned polish — must fit in remaining budget AFTER v4 polish (worst case:
    # in production v5 runs base->v4polish->tuned sequentially; emulate that).
    # SAFETY GATE: only run tuned if real leftover budget remains. This keeps
    # max wall time well under 9.0s (tuned never fires on near-deadline cases).
    tuned_best, tuned_cost, n_imp = v4_best, v4_cost, 0
    now = time.monotonic()
    GATE_REMAIN = 1.6   # need >=1.6s of slack to even start tuned
    if now < deadline - GATE_REMAIN:
        try:
            tuned_best, tuned_cost, n_imp = tuned_polish(
                v4_best, v4_cost, candidates, all_tasks, deadline, flags, cfg)
        except Exception:
            tuned_best, tuned_cost, n_imp = v4_best, v4_cost, 0
    elapsed = time.monotonic() - start
    return {
        "base_cost": base_cost, "v4_cost": v4_cost, "tuned_cost": tuned_cost,
        "n_improved": n_imp, "elapsed": elapsed,
        "tuned_beats_v4": tuned_cost < v4_cost - 1e-9,
        "feasible": g.evaluate(tuned_best, *parse_for_eval(text))[1],
    }


def parse_for_eval(text):
    rows, tasks = g.parse_instance(text)
    return rows, tasks


def build_split(per_regime=3, train_base=30000, held_base=40000):
    regimes = list(g.REGIME_BANK.keys())
    train, held = [], []
    for ri, reg in enumerate(regimes):
        for k in range(per_regime):
            train.append((reg, train_base + ri * 100 + k))
            held.append((reg, held_base + ri * 100 + k))
    return train, held


def eval_split(split, cfg, label):
    rows = []
    for reg, seed in split:
        text = g.generate_case(g.REGIME_BANK[reg], seed)
        r = run_instance(text, cfg)
        r["regime"] = reg; r["seed"] = seed
        rows.append(r)
    n = len(rows)
    n_beats = sum(1 for r in rows if r["tuned_beats_v4"])
    n_infeas = sum(1 for r in rows if not r["feasible"])
    max_t = max(r["elapsed"] for r in rows)
    over = sum(1 for r in rows if r["elapsed"] > GLOBAL_DEADLINE_S)
    mean_v4 = sum(r["v4_cost"] for r in rows) / n
    mean_tuned = sum(r["tuned_cost"] for r in rows) / n
    print(f"[{label}] n={n} tuned_beats_v4={n_beats}/{n} "
          f"mean_v4={mean_v4:.3f} mean_tuned={mean_tuned:.3f} "
          f"delta={mean_tuned-mean_v4:+.3f} max_t={max_t:.2f}s over9s={over} infeas={n_infeas}")
    for r in rows:
        if r["tuned_beats_v4"]:
            print(f"   WIN {r['regime']:<18} seed{r['seed']} v4={r['v4_cost']:.2f}->tuned={r['tuned_cost']:.2f} "
                  f"(-{r['v4_cost']-r['tuned_cost']:.2f}) t={r['elapsed']:.2f}s")
    return rows


OFFICIAL = [
    "web_agent_demo/generated_cases/tiny_seed42.txt",
    "web_agent_demo/generated_cases/small_seed100.txt",
    "web_agent_demo/generated_cases/medium_seed201.txt",
    "web_agent_demo/generated_cases/medium_seed202.txt",
    "web_agent_demo/generated_cases/medium_seed203.txt",
    "web_agent_demo/generated_cases/large_seed302.txt",
    "web_agent_demo/generated_cases/scarce_couriers_seed401.txt",
    "web_agent_demo/generated_cases/low_willingness_seed501.txt",
    "web_agent_demo/generated_cases/high_noise_seed601.txt",
]


def eval_official(cfg, label="OFFICIAL-9"):
    rows = []
    for rel in OFFICIAL:
        p = ROOT / rel
        if not p.exists():
            continue
        text = p.read_text()
        r = run_instance(text, cfg)
        r["regime"] = Path(rel).stem
        r["seed"] = "-"
        rows.append(r)
    n = len(rows)
    n_beats = sum(1 for r in rows if r["tuned_beats_v4"])
    n_infeas = sum(1 for r in rows if not r["feasible"])
    max_t = max(r["elapsed"] for r in rows)
    over = sum(1 for r in rows if r["elapsed"] > GLOBAL_DEADLINE_S)
    print(f"[{label}] n={n} tuned_beats_v4={n_beats}/{n} max_t={max_t:.2f}s over9s={over} infeas={n_infeas}")
    for r in rows:
        flag = "WIN " if r["tuned_beats_v4"] else "    "
        print(f"   {flag}{r['regime']:<30} v4={r['v4_cost']:.2f} tuned={r['tuned_cost']:.2f} t={r['elapsed']:.2f}s")
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-regime", type=int, default=2)
    ap.add_argument("--which", default="both", choices=["train", "held", "both", "official", "all"])
    args = ap.parse_args()
    train, held = build_split(args.per_regime)
    if args.which in ("train", "both", "all"):
        eval_split(train, DEFAULT_CFG, "TRAIN")
    if args.which in ("held", "both", "all"):
        eval_split(held, DEFAULT_CFG, "HELD-OUT")
    if args.which in ("official", "all"):
        eval_official(DEFAULT_CFG)
