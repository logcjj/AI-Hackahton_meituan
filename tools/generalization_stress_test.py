#!/usr/bin/env python3
"""
generalization_stress_test.py
=============================

Generalization / over-fitting stress harness for the AutoSolver命题四 solver.

What it does
------------
1. Programmatically generates a large bank of FRESH random instances in the
   exact official input format (TSV: ``task_id_list  courier_id  total_score
   willingness``), spanning many regimes:
       - large            (40 tasks / 80 couriers, dense)
       - scarce couriers  (few couriers per task -> reuse pressure)
       - low willingness  (acceptance prob ~0.05-0.25)
       - high noise       (very uneven score/willingness)
       - bundle heavy     (many 2- and 3-task bundles)
       - small / medium   (general dense)
   Each regime is parameterized by size and distribution and uses BRAND-NEW
   seeds (10000+), disjoint from the known official seeds (42/100/201/202/203/
   301/302/401/501/601).

2. Also evaluates the KNOWN official-named seeds (the ones the original solver
   memorizes) so the hardcode contribution can be isolated.

3. For every instance it runs BOTH solver.py (original) and solver_v2.py
   (generalization-hardened), under a hard per-case wall-clock guard, and
   scores each output with the canonical objective
   (autosolver.competition_audit.solution_expected_cost — lower is better),
   checking feasibility (the same rules as autosolver.validator) and the 10s
   budget.

4. Emits a per-instance + per-regime comparison table and writes a Markdown
   report to docs/generalization_report.md.

Objective (canonical, MINIMIZE)
-------------------------------
    cost(solution) = sum over groups  E[ avg accepted total_score | accept-mask ]
                   + 100 * (number of uncovered tasks)
where, within a group, courier i accepts independently with prob willingness_i,
and an all-reject group contributes 100 * (#tasks in the group).
This is exactly what both solvers optimize internally (``_solution_expected_cost``)
and matches autosolver/competition_audit.py::solution_expected_cost.

Usage
-----
    python3 tools/generalization_stress_test.py                 # default bank
    python3 tools/generalization_stress_test.py --per-regime 6  # more instances
    python3 tools/generalization_stress_test.py --time-budget 10
    python3 tools/generalization_stress_test.py --quick         # tiny smoke run

No third-party dependencies. Pure stdlib + the repo's own modules.
"""
from __future__ import annotations

import argparse
import importlib.util
import math
import multiprocessing as mp
import os
import random
import sys
import time
from dataclasses import dataclass, field

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# --------------------------------------------------------------------------- #
# Instance generation (fresh, judge-shaped, parameterized)                    #
# --------------------------------------------------------------------------- #
HEADER = "task_id_list\tcourier_id\ttotal_score\twillingness"


@dataclass(frozen=True)
class RegimeSpec:
    regime: str
    tasks: int
    couriers: int
    single_density: float          # P(an extra single courier row exists for a task)
    bundle_density: float          # controls how many bundle rows per bundle
    willingness: str               # 'normal' | 'low' | 'noisy' | 'sparse'
    score: str                     # 'normal' | 'bundle' | 'scarce' | 'high_noise' | 'sparse'
    triple_bundles: bool = False


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def generate_case(spec: RegimeSpec, seed: int) -> str:
    """Render one instance to the official TSV format. Self-contained generator
    (deliberately independent of the repo's sample_cases.py so the harness does
    not accidentally reproduce a memorized instance)."""
    rng = random.Random(seed * 1_000_003 + 17)
    tasks = [f"T{i:04d}" for i in range(spec.tasks)]
    couriers = [f"C{i:03d}" for i in range(spec.couriers)]
    rows: dict[tuple[str, str], tuple[str, str, float, float]] = {}

    def willingness(size: int) -> float:
        if spec.willingness == "low":
            return _clamp(rng.uniform(0.04, 0.24) + (0.02 if size > 1 else 0.0), 0.012, 0.965)
        if spec.willingness == "sparse":
            base = rng.uniform(0.03, 0.30)
            return _clamp(base + (0.30 if rng.random() < 0.10 else 0.0), 0.012, 0.965)
        if spec.willingness == "noisy":
            v = rng.uniform(0.04, 0.95) if rng.random() < 0.55 else rng.uniform(0.18, 0.66)
            return _clamp(v, 0.012, 0.965)
        return _clamp(rng.uniform(0.10, 0.85), 0.012, 0.965)

    def score_bias(ti: int, cnum: int) -> float:
        if spec.score == "scarce":
            return -8.0 if (cnum % 3) == (ti % 3) else 5.0
        if spec.score == "high_noise":
            return -12.0 if ((ti + cnum) % 7 == 0) else 6.0
        if spec.score == "sparse":
            return 4.0 if ti % 5 else -6.0
        if spec.score == "bundle":
            return -3.0 if ti % 4 in (1, 2) else 3.0
        return 0.0

    def add(task_ids: tuple[str, ...], courier: str, raw_score: float, size: int) -> None:
        key = ",".join(task_ids)
        rows[(key, courier)] = (
            key, courier,
            round(_clamp(raw_score, 8.0, 100.0), 3),
            round(willingness(size), 4),
        )

    def single_score(ti: int, cnum: int) -> float:
        locality = abs((ti * 7 + 3) % 29 - (cnum * 5) % 29)
        return 22.0 + locality * 1.7 + rng.uniform(0.0, 26.0) + score_bias(ti, cnum)

    # mandatory couriers guarantee every task is coverable by a single
    needed = 2 if spec.willingness == "sparse" else 3
    for ti, t in enumerate(tasks):
        start = (ti * 5 + seed) % spec.couriers
        mandatory = {couriers[(start + o) % spec.couriers] for o in range(min(needed, spec.couriers))}
        for c in mandatory:
            add((t,), c, single_score(ti, int(c[1:])), 1)
        for c in couriers:
            if c in mandatory:
                continue
            if rng.random() < spec.single_density:
                add((t,), c, single_score(ti, int(c[1:])), 1)

    def add_bundle(task_ids: tuple[str, ...], ti: int, scale: float) -> None:
        slots = max(2, int(spec.couriers * spec.bundle_density / max(1, len(task_ids))))
        start = (ti * 7 + seed) % spec.couriers
        cand = [couriers[(start + o * 3) % spec.couriers] for o in range(min(spec.couriers, slots + 4))]
        for c in cand:
            if rng.random() <= spec.bundle_density or c in cand[:2]:
                raw = 18.0 * len(task_ids) * scale + rng.uniform(8.0, 34.0)
                if spec.score in ("bundle", "scarce"):
                    raw -= 7.0 * len(task_ids)
                if spec.score == "high_noise" and rng.random() < 0.35:
                    raw += rng.uniform(-24.0, 30.0)
                add(task_ids, c, raw, len(task_ids))

    # adjacent 2-task bundles
    for ti, t in enumerate(tasks):
        nxt = tasks[(ti + 1) % len(tasks)]
        if t < nxt:
            add_bundle((t, nxt), ti, 1.0)
    # 3-task bundles for bundle-heavy / scarce / large regimes
    if spec.triple_bundles:
        for ti in range(0, len(tasks) - 2, 3):
            add_bundle((tasks[ti], tasks[ti + 1], tasks[ti + 2]), ti, 1.18)

    ordered = sorted(rows.values(), key=lambda r: (int(r[0].split(",")[0][1:]), r[0], r[1]))
    body = "\n".join(f"{k}\t{c}\t{s:.3f}\t{w:.4f}" for k, c, s, w in ordered)
    return f"{HEADER}\n{body}\n"


# Regime bank: brand-new seeds (>=10000), disjoint from official seeds.
REGIME_BANK: dict[str, RegimeSpec] = {
    "large":          RegimeSpec("large", 40, 80, 0.25, 0.28, "normal", "normal", triple_bundles=True),
    "scarce":         RegimeSpec("scarce", 30, 18, 0.42, 0.42, "normal", "scarce", triple_bundles=True),
    "scarce_tight":   RegimeSpec("scarce_tight", 40, 22, 0.40, 0.45, "normal", "scarce", triple_bundles=True),
    "low_willing":    RegimeSpec("low_willing", 30, 60, 0.30, 0.26, "low", "normal"),
    "high_noise":     RegimeSpec("high_noise", 30, 60, 0.34, 0.32, "noisy", "high_noise", triple_bundles=True),
    "bundle_heavy":   RegimeSpec("bundle_heavy", 24, 50, 0.22, 0.50, "normal", "bundle", triple_bundles=True),
    "medium":         RegimeSpec("medium", 24, 50, 0.30, 0.30, "normal", "normal"),
    "small":          RegimeSpec("small", 12, 25, 0.48, 0.26, "normal", "normal"),
    "tiny":           RegimeSpec("tiny", 6, 10, 0.62, 0.34, "normal", "normal"),
    # dimension-matched to the hardcode triggers, but with FRESH content,
    # to prove the original solver's caches do not (and cannot) fire here:
    "trap_small_15_25":  RegimeSpec("trap_small_15_25", 15, 25, 0.48, 0.26, "normal", "normal"),
    "trap_scarce_40_40": RegimeSpec("trap_scarce_40_40", 40, 40, 0.40, 0.45, "normal", "scarce", triple_bundles=True),
    "trap_med_30_60":    RegimeSpec("trap_med_30_60", 30, 60, 0.30, 0.30, "normal", "normal", triple_bundles=True),
    "trap_large_40_80":  RegimeSpec("trap_large_40_80", 40, 80, 0.25, 0.28, "normal", "normal", triple_bundles=True),
}


# --------------------------------------------------------------------------- #
# Canonical objective + feasibility (mirrors autosolver/competition_audit.py   #
# and autosolver/validator.py)                                                 #
# --------------------------------------------------------------------------- #
def parse_instance(text: str):
    rows: dict[tuple[str, str], tuple[float, float, tuple[str, ...]]] = {}
    tasks: set[str] = set()
    lines = text.strip().splitlines()
    start = 1 if lines and lines[0].startswith("task_id_list") else 0
    for ln in lines[start:]:
        parts = ln.split("\t")
        if len(parts) < 4:
            continue
        key = parts[0].strip()
        courier = parts[1].strip()
        try:
            score = float(parts[2])
            will = float(parts[3])
        except ValueError:
            continue
        tids = tuple(t.strip() for t in key.split(",") if t.strip())
        if not tids or not courier:
            continue
        rows[(key, courier)] = (score, will, tids)
        tasks.update(tids)
    return rows, tasks


def _group_expected_cost(group, task_count: int) -> float:
    n = len(group)
    if n == 0:
        return 100.0 * task_count
    if n > 14:
        # closed-form ordering-independent DP for big groups (rare; keeps it fast)
        prob_all_reject = 1.0
        for s, w in group:
            prob_all_reject *= (1.0 - w)
        total = prob_all_reject * (100.0 * task_count)
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
        exp += prob * (acc / cnt if cnt else 100.0 * task_count)
    return exp


def evaluate(solution, rows, tasks):
    """Return (cost, feasible, violations)."""
    if solution is None:
        return float("inf"), False, ["null solution"]
    used = set()
    covered = set()
    violations = []
    total = 0.0
    for entry in solution:
        try:
            key, couriers = entry
        except Exception:
            return float("inf"), False, [f"bad entry {entry!r}"]
        group = []
        tids = None
        for c in couriers:
            r = rows.get((key, c))
            if r is None:
                violations.append(f"unknown pair {key}/{c}")
                return float("inf"), False, violations
            if c in used:
                violations.append(f"courier reuse {c}")
                return float("inf"), False, violations
            used.add(c)
            group.append((r[0], r[1]))
            tids = r[2]
        if not group or tids is None:
            violations.append(f"empty group {key}")
            return float("inf"), False, violations
        for t in tids:
            if t in covered:
                violations.append(f"duplicate task {t}")
                return float("inf"), False, violations
            covered.add(t)
        total += _group_expected_cost(group, len(tids))
    uncovered = len(tasks) - len(covered)
    total += 100.0 * uncovered
    return total, True, violations


# --------------------------------------------------------------------------- #
# Sandboxed solver execution with hard timeout                                 #
# --------------------------------------------------------------------------- #
def _worker(solver_path, text, q):
    try:
        spec = importlib.util.spec_from_file_location("solver_under_test", solver_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        t0 = time.monotonic()
        out = mod.solve(text)
        dt = time.monotonic() - t0
        # normalize to plain lists for pickling
        norm = [(k, list(cs)) for (k, cs) in out]
        q.put(("ok", norm, dt))
    except Exception as exc:  # pragma: no cover - defensive
        import traceback
        q.put(("err", traceback.format_exc(), 0.0))


def run_solver(solver_path, text, hard_timeout):
    """Run solve() in a separate process with a hard wall-clock guard."""
    ctx = mp.get_context("spawn")
    q = ctx.Queue()
    p = ctx.Process(target=_worker, args=(solver_path, text, q))
    t0 = time.monotonic()
    p.start()
    p.join(hard_timeout)
    if p.is_alive():
        p.terminate()
        p.join()
        return {"status": "timeout", "solution": None, "solve_time": time.monotonic() - t0}
    try:
        status, payload, dt = q.get_nowait()
    except Exception:
        return {"status": "crash", "solution": None, "solve_time": time.monotonic() - t0}
    if status == "err":
        return {"status": "error", "solution": None, "solve_time": dt, "trace": payload}
    return {"status": "ok", "solution": payload, "solve_time": dt}


# --------------------------------------------------------------------------- #
# Harness                                                                      #
# --------------------------------------------------------------------------- #
@dataclass
class CaseResult:
    name: str
    regime: str
    tasks: int
    couriers: int
    rows: int
    v1_cost: float = float("inf")
    v2_cost: float = float("inf")
    v1_feasible: bool = False
    v2_feasible: bool = False
    v1_time: float = 0.0
    v2_time: float = 0.0
    v1_status: str = ""
    v2_status: str = ""

    @property
    def delta(self):  # v2 - v1 ; negative => v2 better (lower cost)
        if math.isinf(self.v1_cost) or math.isinf(self.v2_cost):
            return float("nan")
        return self.v2_cost - self.v1_cost

    @property
    def delta_pct(self):
        if math.isinf(self.v1_cost) or self.v1_cost == 0 or math.isinf(self.v2_cost):
            return float("nan")
        return (self.v2_cost - self.v1_cost) / self.v1_cost * 100.0


def run_one(name, regime, text, v1_path, v2_path, hard_timeout, budget):
    rows, tasks = parse_instance(text)
    n_rows = sum(1 for _ in text.strip().splitlines()) - 1
    couriers = len({c for (_, c) in rows})
    res = CaseResult(name=name, regime=regime, tasks=len(tasks), couriers=couriers, rows=n_rows)

    r1 = run_solver(v1_path, text, hard_timeout)
    res.v1_status = r1["status"]
    res.v1_time = r1["solve_time"]
    if r1["status"] == "ok":
        c1, f1, _ = evaluate(r1["solution"], rows, tasks)
        res.v1_cost, res.v1_feasible = c1, f1 and r1["solve_time"] <= budget + 0.5

    r2 = run_solver(v2_path, text, hard_timeout)
    res.v2_status = r2["status"]
    res.v2_time = r2["solve_time"]
    if r2["status"] == "ok":
        c2, f2, _ = evaluate(r2["solution"], rows, tasks)
        res.v2_cost, res.v2_feasible = c2, f2 and r2["solve_time"] <= budget + 0.5
    return res


def fmt_row(r: CaseResult):
    dp = r.delta_pct
    dp_s = f"{dp:+.3f}%" if not math.isnan(dp) else "  n/a "
    return (f"{r.name:<24} {r.regime:<16} {r.tasks:>3}/{r.couriers:<3} "
            f"{r.v1_cost:>11.3f} {r.v2_cost:>11.3f} {dp_s:>9} "
            f"{r.v1_time:>6.2f}s {r.v2_time:>6.2f}s "
            f"{'OK' if r.v1_feasible else 'X':>3}/{'OK' if r.v2_feasible else 'X':<3}")


def write_report(known_results, fresh_results, path, args):
    lines = []
    lines.append("# AutoSolver 泛化压力测试报告 (generalization_report)")
    lines.append("")
    lines.append(f"- 生成时间预算 / case: **{args.time_budget}s** (硬超时 {args.hard_timeout}s)")
    lines.append(f"- 每个 regime 的全新随机实例数: **{args.per_regime}**")
    lines.append("- 目标函数 (越小越好): "
                 "`sum_groups E[平均被接受 score] + 100 * 未覆盖任务数`，"
                 "等价于 `autosolver/competition_audit.py::solution_expected_cost`。")
    lines.append("- v1 = `solver.py` (原版, 含按 seed 硬编码)，v2 = `solver_v2.py` (泛化加固, 移除全部硬编码)。")
    lines.append("- delta% = (v2_cost - v1_cost)/v1_cost，**负数表示 v2 更优**。")
    lines.append("")

    def section(title, results, note):
        lines.append(f"## {title}")
        lines.append("")
        lines.append(note)
        lines.append("")
        lines.append("| case | regime | T/C | v1_cost | v2_cost | delta% | v1_t | v2_t | feas v1/v2 |")
        lines.append("|---|---|---|---:|---:|---:|---:|---:|:--:|")
        for r in results:
            dp = r.delta_pct
            dp_s = f"{dp:+.3f}%" if not math.isnan(dp) else "n/a"
            lines.append(f"| {r.name} | {r.regime} | {r.tasks}/{r.couriers} | "
                         f"{r.v1_cost:.3f} | {r.v2_cost:.3f} | {dp_s} | "
                         f"{r.v1_time:.2f}s | {r.v2_time:.2f}s | "
                         f"{'OK' if r.v1_feasible else 'FAIL'}/{'OK' if r.v2_feasible else 'FAIL'} |")
        lines.append("")

    section("A. 已知官方命名 seed (原版可能命中硬编码的实例)", known_results,
            "这些是仓库内置的官方命名样例。若本地文件与评测机隐藏实例不同, 硬编码不会触发——"
            "此时 v1≈v2 即证明本地分数并不依赖硬编码; 若某行 v1 明显优于 v2 且 v2 可行, 则该差值即"
            "硬编码在该实例上的贡献量。")

    def regime_summary(results):
        agg = {}
        for r in results:
            agg.setdefault(r.regime, []).append(r)
        out = []
        out.append("| regime | n | v1 mean | v2 mean | mean delta% | v2 wins | ties | v2 loses | both feasible |")
        out.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
        gv1 = gv2 = 0.0
        gn = 0
        gw = gt = gl = gf = 0
        for regime, rs in sorted(agg.items()):
            feas = [r for r in rs if r.v1_feasible and r.v2_feasible]
            if not feas:
                out.append(f"| {regime} | {len(rs)} | n/a | n/a | n/a | 0 | 0 | 0 | 0/{len(rs)} |")
                continue
            v1m = sum(r.v1_cost for r in feas) / len(feas)
            v2m = sum(r.v2_cost for r in feas) / len(feas)
            dpm = sum(r.delta_pct for r in feas) / len(feas)
            wins = sum(1 for r in feas if r.v2_cost < r.v1_cost - 1e-6)
            losses = sum(1 for r in feas if r.v2_cost > r.v1_cost + 1e-6)
            ties = len(feas) - wins - losses
            out.append(f"| {regime} | {len(rs)} | {v1m:.2f} | {v2m:.2f} | {dpm:+.3f}% | "
                       f"{wins} | {ties} | {losses} | {len(feas)}/{len(rs)} |")
            gv1 += v1m * len(feas)
            gv2 += v2m * len(feas)
            gn += len(feas)
            gw += wins
            gt += ties
            gl += losses
            gf += len(feas)
        if gn:
            out.append(f"| **ALL** | {gf} | {gv1/gn:.2f} | {gv2/gn:.2f} | "
                       f"{(gv2-gv1)/gv1*100:+.3f}% | {gw} | {gt} | {gl} | — |")
        return out

    lines.append("## B. 全新随机 seed (从未见过的实例) — 逐 regime 汇总")
    lines.append("")
    lines.append("全部使用 >=10000 的全新随机种子, 与官方 seed(42/100/201/202/203/301/302/401/501/601) 不相交。"
                 "硬编码在此**不可能命中**, 因此这组数字衡量的是『真实算法』在新数据上的表现。")
    lines.append("")
    lines.extend(regime_summary(fresh_results))
    lines.append("")
    lines.append("### B.1 全新随机 seed 逐实例明细")
    lines.append("")
    section("", fresh_results, "")

    # conclusions
    feas = [r for r in fresh_results if r.v1_feasible and r.v2_feasible]
    wins = sum(1 for r in feas if r.v2_cost < r.v1_cost - 1e-6)
    losses = sum(1 for r in feas if r.v2_cost > r.v1_cost + 1e-6)
    ties = len(feas) - wins - losses
    v2_infeas = sum(1 for r in fresh_results if not r.v2_feasible)
    v1_infeas = sum(1 for r in fresh_results if not r.v1_feasible)
    over = [r for r in fresh_results if r.v2_time > args.time_budget + 0.01 or r.v1_time > args.time_budget + 0.01]
    lines.append("## C. 结论")
    lines.append("")
    lines.append(f"- 全新随机实例共 **{len(fresh_results)}** 个, 两者均可行 **{len(feas)}** 个。")
    lines.append(f"- 在均可行的实例上: v2 更优 **{wins}**, 持平 **{ties}**, 更差 **{losses}**。")
    if feas:
        mean_dp = sum(r.delta_pct for r in feas) / len(feas)
        lines.append(f"- 平均 delta% = **{mean_dp:+.3f}%** (负=v2更优)。")
    lines.append(f"- 可行性: v1 不可行 {v1_infeas} / v2 不可行 {v2_infeas} (含超时/崩溃)。")
    if over:
        lines.append(f"- ⚠️ 超出 {args.time_budget}s 预算的实例: {len(over)} 个 -> "
                     + ", ".join(f"{r.name}(v1 {r.v1_time:.1f}s/v2 {r.v2_time:.1f}s)" for r in over[:8]))
    else:
        lines.append(f"- 所有实例均在 {args.time_budget}s 预算内完成 (含大规模 large/40-80)。")
    lines.append("")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--per-regime", type=int, default=4, help="fresh random instances per regime")
    ap.add_argument("--time-budget", type=float, default=10.0, help="official per-case budget (s)")
    ap.add_argument("--hard-timeout", type=float, default=20.0, help="hard wall-clock kill (s)")
    ap.add_argument("--seed-base", type=int, default=10000, help="base seed for fresh instances")
    ap.add_argument("--quick", action="store_true", help="tiny smoke run (1 per small regime)")
    ap.add_argument("--report", default=os.path.join(ROOT, "docs", "generalization_report.md"))
    args = ap.parse_args()

    v1_path = os.path.join(ROOT, "solver.py")
    v2_path = os.path.join(ROOT, "solver_v2.py")
    for p in (v1_path, v2_path):
        if not os.path.exists(p):
            print(f"missing solver: {p}", file=sys.stderr)
            sys.exit(2)

    regimes = REGIME_BANK
    per = args.per_regime
    if args.quick:
        regimes = {k: REGIME_BANK[k] for k in ("tiny", "small", "medium", "scarce")}
        per = 1

    # ---- A. known official-named seeds (load repo files if present) ----------
    known_results = []
    known_files = [
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
    if not args.quick:
        print("=" * 118)
        print("A. KNOWN OFFICIAL-NAMED SEEDS  (hardcode may apply on the real judge instance)")
        print("=" * 118)
        for rel, regime in known_files:
            ap_path = os.path.join(ROOT, rel)
            if not os.path.exists(ap_path):
                continue
            text = open(ap_path, encoding="utf-8").read()
            r = run_one(os.path.basename(rel).replace(".txt", ""), regime, text,
                        v1_path, v2_path, args.hard_timeout, args.time_budget)
            known_results.append(r)
            print(fmt_row(r))

    # ---- B. fresh random instances ------------------------------------------
    print("=" * 118)
    print("B. FRESH RANDOM SEEDS  (never-seen; hardcode cannot fire)")
    print("=" * 118)
    fresh_results = []
    for regime, spec in regimes.items():
        for k in range(per):
            seed = args.seed_base + k + 1000 * abs(hash(regime)) % 9000
            name = f"{regime}_s{seed}"
            text = generate_case(spec, seed)
            r = run_one(name, regime, text, v1_path, v2_path, args.hard_timeout, args.time_budget)
            fresh_results.append(r)
            print(fmt_row(r))

    # ---- report --------------------------------------------------------------
    os.makedirs(os.path.dirname(args.report), exist_ok=True)
    write_report(known_results, fresh_results, args.report, args)

    feas = [r for r in fresh_results if r.v1_feasible and r.v2_feasible]
    wins = sum(1 for r in feas if r.v2_cost < r.v1_cost - 1e-6)
    losses = sum(1 for r in feas if r.v2_cost > r.v1_cost + 1e-6)
    print("=" * 118)
    print(f"FRESH: {len(feas)}/{len(fresh_results)} both-feasible | v2 wins {wins} / loses {losses} / ties {len(feas)-wins-losses}")
    if feas:
        print(f"FRESH mean delta% (v2 vs v1, neg=better) = {sum(r.delta_pct for r in feas)/len(feas):+.3f}%")
    print(f"Report written -> {args.report}")


if __name__ == "__main__":
    main()
