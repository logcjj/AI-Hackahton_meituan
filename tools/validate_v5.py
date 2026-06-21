#!/usr/bin/env python3
"""validate_v5.py — direct v5-vs-v4 no-regression + timing + contribution audit.

Runs solver_v4.solve and solver_v5.solve on the SAME bank of fresh HELD-OUT
instances + the 9 official samples, and checks the structural guarantee
(v5_cost <= v4_cost on EVERY instance), feasibility, the <=10s budget, and how
often the evolved (tuned) pass actually became the argmin (= contributed)."""
from __future__ import annotations
import importlib.util, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import generalization_stress_test as g


def load(fn, al):
    sp = importlib.util.spec_from_file_location(al, str(ROOT / fn))
    m = importlib.util.module_from_spec(sp); sys.modules[al] = m; sp.loader.exec_module(m); return m


V4 = load("solver_v4.py", "v4_val")
V5 = load("solver_v5.py", "v5_val")


def cost_feas(text, sol):
    rows, tasks = g.parse_instance(text)
    return g.evaluate(sol, rows, tasks)[:2]


def run(text, name):
    t0 = time.monotonic(); s4 = V4.solve(text); t4 = time.monotonic() - t0
    c4, f4 = cost_feas(text, s4)
    t0 = time.monotonic(); s5 = V5.solve(text); t5 = time.monotonic() - t0
    c5, f5 = cost_feas(text, s5)
    fired = getattr(V5, "_LAST_TUNED_FIRED", False)
    regress = c5 > c4 + 1e-6
    return dict(name=name, c4=c4, c5=c5, f4=f4, f5=f5, t4=t4, t5=t5,
                fired=fired, regress=regress, improved=c5 < c4 - 1e-9)


def bank():
    items = []
    for ri, reg in enumerate(g.REGIME_BANK):
        for k in range(3):
            seed = 40000 + ri * 100 + k
            items.append((f"{reg}#{seed}", g.generate_case(g.REGIME_BANK[reg], seed)))
    off = [
        "tiny_seed42", "small_seed100", "medium_seed201", "medium_seed202",
        "medium_seed203", "large_seed302", "scarce_couriers_seed401",
        "low_willingness_seed501", "high_noise_seed601",
    ]
    for stem in off:
        p = ROOT / "web_agent_demo" / "generated_cases" / f"{stem}.txt"
        if p.exists():
            items.append((f"OFF:{stem}", p.read_text()))
    return items


def main():
    res = [run(text, name) for name, text in bank()]
    n = len(res)
    regress = [r for r in res if r["regress"]]
    infeas = [r for r in res if not r["f5"]]
    fired = [r for r in res if r["fired"]]
    improved = [r for r in res if r["improved"]]
    over = [r for r in res if r["t5"] > 9.0]
    over10 = [r for r in res if r["t5"] > 10.0]
    max_t5 = max(r["t5"] for r in res)
    mean_c4 = sum(r["c4"] for r in res) / n
    mean_c5 = sum(r["c5"] for r in res) / n
    print(f"n={n}")
    print(f"REGRESSIONS (v5>v4): {len(regress)}   <-- MUST be 0")
    for r in regress:
        print(f"   !! {r['name']} c4={r['c4']:.3f} c5={r['c5']:.3f}")
    print(f"infeasible v5: {len(infeas)}   <-- MUST be 0")
    print(f"v5 improved over v4 (tuned became argmin): {len(improved)}/{n}")
    for r in improved:
        print(f"   WIN {r['name']:<26} c4={r['c4']:.3f} -> c5={r['c5']:.3f} (-{r['c4']-r['c5']:.3f}) t5={r['t5']:.2f}s")
    print(f"tuned-pass-fired-flag set: {len(fired)}/{n}")
    print(f"mean v4={mean_c4:.4f}  mean v5={mean_c5:.4f}  delta={mean_c5-mean_c4:+.4f} "
          f"({100*(mean_c5-mean_c4)/mean_c4:+.4f}%)")
    print(f"max v5 wall time: {max_t5:.3f}s   over9s={len(over)} over10s={len(over10)}")
    ok = not regress and not infeas and not over10
    print("VERDICT:", "PASS (no regression, feasible, <=10s)" if ok else "FAIL")


if __name__ == "__main__":
    main()
