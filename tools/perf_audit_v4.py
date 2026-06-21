#!/usr/bin/env python3
"""Performance audit harness for solver_v4 / solver_v5.

Times solve() wall-clock on the HARDEST instances, multiple trials each, IN
THE SAME PROCESS (so module import / cache warmup is amortized exactly like the
judge would NOT necessarily do -- we also report a cold first-run number).

Hard instances:
  - official large_seed301.txt (40 tasks)
  - generated large / scarce_tight / trap_scarce_40_40 / trap_large_40_80
    (the largest + courier-constrained regimes) across several fresh seeds.

Reports per (solver,instance): cold time, warm min/median/max over N trials,
proxy cost, coverage, and the global worst wall time.
"""
import importlib.util, os, statistics, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tools.generalization_stress_test as G  # generator + regime bank


def load_solver(name):
    path = ROOT / name
    spec = importlib.util.spec_from_file_location(f"perf_{name.replace('.','_')}", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def proxy(mod, out, cands, all_tasks):
    try:
        c = mod._solution_expected_cost(out, cands, all_tasks)
    except Exception:
        # v4/v5 don't export _solution_expected_cost; use the generator's evaluate
        rows, tasks = G.parse_instance(_CUR_TEXT)
        c, _, _ = G.evaluate([(k, list(cs)) for k, cs in out], rows, tasks)
    return c


_CUR_TEXT = ""


def build_instances(seeds):
    """Return list of (label, text)."""
    inst = []
    official = ROOT / "data" / "official_cases" / "large_seed301.txt"
    inst.append(("official_large_seed301", official.read_text()))
    hard_regimes = ["large", "scarce_tight", "trap_scarce_40_40", "trap_large_40_80"]
    for regime in hard_regimes:
        spec = G.REGIME_BANK[regime]
        for s in seeds:
            inst.append((f"{regime}_s{s}", G.generate_case(spec, s)))
    return inst


def parse_for_proxy(text):
    cands, all_tasks = [], set()
    lines = text.strip().splitlines()
    start = 1 if lines and lines[0].startswith("task_id_list") else 0
    for ri, raw in enumerate(lines[start:]):
        parts = raw.strip().split("\t")
        if len(parts) < 4:
            continue
        key, cid, st, wt = parts[:4]
        tids = tuple(t.strip() for t in key.split(",") if t.strip())
        try:
            sc, wl = float(st), float(wt)
        except ValueError:
            continue
        cands.append((key, tids, cid.strip(), sc, wl, ri))
        all_tasks.update(tids)
    return cands, all_tasks


def main():
    global _CUR_TEXT
    solvers = sys.argv[1].split(",") if len(sys.argv) > 1 else ["solver_v4.py"]
    n_trials = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    seeds = [20001, 20002, 20003] if len(sys.argv) <= 3 else [int(x) for x in sys.argv[3].split(",")]

    instances = build_instances(seeds)
    print(f"# perf audit | solvers={solvers} | trials={n_trials} | seeds={seeds}")
    print(f"# instances: {len(instances)}")

    global_worst = {}
    for sname in solvers:
        mod = load_solver(sname)
        print("=" * 100)
        print(f"SOLVER {sname}")
        print("=" * 100)
        worst = 0.0
        worst_lbl = ""
        for label, text in instances:
            _CUR_TEXT = text
            cands, all_tasks = parse_for_proxy(text)
            times = []
            last_out = None
            for i in range(n_trials):
                t0 = time.monotonic()
                out = mod.solve(text)
                dt = time.monotonic() - t0
                times.append(dt)
                last_out = out
            cold = times[0]
            warm = times[1:] if len(times) > 1 else times
            tmin, tmed, tmax = min(times), statistics.median(times), max(times)
            # coverage
            lut = {(c[0], c[2]): c for c in cands}
            covered = set()
            for key, couriers in last_out:
                for cid in couriers:
                    r = lut.get((key, cid))
                    if r:
                        covered.update(r[1]); break
            pc = proxy(mod, last_out, cands, all_tasks)
            if tmax > worst:
                worst, worst_lbl = tmax, label
            flag = ""
            if tmax >= 9.5:
                flag = "  <<< >=9.5s TAIL"
            elif tmax >= 9.0:
                flag = "  << >=9.0s"
            print(f"  {label:<28} cold={cold:5.2f}s  min={tmin:5.2f}s med={tmed:5.2f}s "
                  f"max={tmax:5.2f}s  proxy={pc:9.2f} cov={len(covered)}/{len(all_tasks)}{flag}")
            print(f"      all_times={['%.2f'%t for t in times]}")
        global_worst[sname] = (worst, worst_lbl)
        print(f"  -> WORST wall time for {sname}: {worst:.2f}s on {worst_lbl}")

    print("=" * 100)
    for sname, (w, lbl) in global_worst.items():
        margin = 10.0 - w
        print(f"GLOBAL WORST {sname}: {w:.2f}s on {lbl} | budget margin to 10s = {margin:.2f}s")


if __name__ == "__main__":
    main()
