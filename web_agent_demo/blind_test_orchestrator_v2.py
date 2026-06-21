"""
blind_test_orchestrator_v2.py
=============================

R1 robustness/honesty revision of blind_test_orchestrator.py.  The ORIGINAL
file (web_agent_demo/blind_test_orchestrator.py) is left byte-untouched; this
is a separate, drop-in module that server_v3.py imports instead.

WHAT CHANGED vs blind_test_orchestrator.py (real Demo-defect fixes, by item):

  [1 HIGH/regression] promoted_strategy_card() / selfcheck no longer assume a
      promoted strategy exists.  The card always carries a "status" key (even
      when available=False), and the selfcheck tolerates available:False instead
      of KeyError-ing on entry['status'].  When EVO has restored the real
      promoted=gen01_M1_003 (current state) it still hits and passes; if the
      registry is ever empty the Demo degrades gracefully to a neutral card.

  [2 HIGH] The Memory/cache switch is now HONEST.  solver_v2 already deleted all
      per-seed caches and the solve chain contains no hardcoded answers, so the
      switch does NOT change behaviour.  We say so plainly and, when it is ON,
      we emit a VERIFIABLE trace line proving "0 memory entries were consulted
      this run" (we never look memory up).  We do NOT claim "强制实时搜索"
      (forces real-time search), which falsely implied a behaviour switch.

  [3 HIGH] Empty / garbled / NaN / out-of-range input no longer shows a green
      CERTIFIED OPTIMAL badge.  We route the certificate through
      optimality_bound_r1 (N/A gatekeeping: cov=0/0 => applicable=False,
      certified_optimal=False, never a green badge; NaN/Inf rows rejected and
      out-of-range willingness clamped at parse time, with the parse-notes
      surfaced in the trajectory).

  [4 MEDIUM] The fallback solver_v2 path now ALSO runs in a spawned subprocess
      with a hard wall-clock timeout (it used to run in-process and could block
      the SSE stream ~20s).  Both the primary solve and the fallback emit
      0.5-1s "solving…" heartbeat progress events so the SSE stream never goes
      dead during a long solve.

  [5 MEDIUM] The Planner "selected strategy chain" is now labelled HONESTLY as a
      MIRROR-READ of the solver's internal size/regime classifier (narration,
      not a causal switch that changes what solver_v2 does).  The perception
      regime thresholds are unified to use ONE statistic consistently (mean
      willingness everywhere instead of mixing p50 + single-mean).

  [7 LOW] The 'rider-rich' perception branch is now REACHABLE (threshold lowered
      from d>=2.2 — unreachable, max regime density is ~2.08 — to d>=2.05), and
      the dropdown labels now advertise the EXPECTED perception regime so the
      dropdown vocabulary and the perception vocabulary use ONE shared naming.

(Defects 6 — SSE BrokenPipe / post-header 500 / traceback leakage — are server
concerns and are fixed in server_v3.py, which imports THIS module.)

NON-DESTRUCTIVE: this module only reads / re-uses project helpers (solver_v3,
optimality_bound_r1, multistakeholder_r1, the stress-test generator, the
evolution registry).  It never edits any solver.
"""
from __future__ import annotations

import json
import multiprocessing as mp
import statistics
import time
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Re-used project capabilities (read-only).  R1 modules import per the brief.
from autosolver import optimality_bound_r1 as optimality_bound
from autosolver.competition_audit import parse_competition_rows
from autosolver.multistakeholder_r1 import (
    Weights,
    evaluate_stakeholders,
    fairness_scorecard,
    pareto_front,
    pareto_efficient,
)
from tools.agent_trace_demo import parse_candidates, summarize_solution
from tools.generalization_stress_test import REGIME_BANK, generate_case

SOLVER_V3_PATH = ROOT / "solver_v3.py"
SOLVER_V2_PATH = ROOT / "solver_v2.py"
REGISTRY_PATH = ROOT / "autosolver_agent" / "evolution_state" / "strategy_registry.json"
GENERATED_BLIND_DIR = ROOT / "web_agent_demo" / "blind_cases"
PROMOTED_STRATEGY_ID = "gen01_M1_003"

# Item 7: the dropdown label now states the EXPECTED perception regime (the
# vocabulary used by size_decoupled_perception below), so the generator
# dropdown and the perception output share ONE naming.  The "→ expects" suffix
# is the regime string the size-decoupled classifier should emit on a typical
# fresh instance of this spec.
BLIND_REGIME_LABELS: dict[str, str] = {
    "large": "Large dense 40任务/80骑手 → 预期 balanced",
    "scarce": "Scarce couriers 30任务/18骑手 → 预期 scarce",
    "scarce_tight": "Scarce tight 40任务/22骑手 → 预期 scarce",
    "low_willing": "Low willingness acceptance≈0.05-0.25 → 预期 low-willingness",
    "high_noise": "High noise 信号极不均匀 → 预期 balanced",
    "bundle_heavy": "Bundle heavy 大量2/3任务组合 → 预期 bundle-heavy",
    "medium": "Medium dense 24任务/50骑手 → 预期 rider-rich",
    "small": "Small dense 12任务/25骑手 → 预期 rider-rich",
    "tiny": "Tiny explainable 6任务/10骑手 → 预期 tiny",
}


# --------------------------------------------------------------------------- #
# 1. Fresh, judge-unseen case generation                                       #
# --------------------------------------------------------------------------- #
def list_blind_regimes() -> list[dict[str, str]]:
    return [
        {"id": rid, "label": BLIND_REGIME_LABELS.get(rid, rid)}
        for rid in BLIND_REGIME_LABELS
        if rid in REGIME_BANK
    ]


def generate_blind_case(regime: str, seed: int | None = None) -> dict[str, Any]:
    """Render a brand-new instance the judge has never seen.

    Uses tools/generalization_stress_test.generate_case with a seed >= 10000,
    disjoint from every official seed (42/100/201/202/203/301/302/401/501/601).
    """
    if regime not in REGIME_BANK:
        raise ValueError(f"unknown regime: {regime}")
    spec = REGIME_BANK[regime]
    if seed is None:
        # time-derived fresh seed, always >= 10000 and disjoint from official.
        seed = 10000 + (int(time.time() * 1000) % 9_000_000)
    text = generate_case(spec, seed)
    rows = text.strip().splitlines()
    row_count = max(0, len(rows) - 1)
    GENERATED_BLIND_DIR.mkdir(parents=True, exist_ok=True)
    out_path = GENERATED_BLIND_DIR / f"blind_{regime}_s{seed}.txt"
    out_path.write_text(text, encoding="utf-8")
    return {
        "regime": regime,
        "label": BLIND_REGIME_LABELS.get(regime, regime),
        "seed": seed,
        "rows": row_count,
        "tasks": spec.tasks,
        "couriers": spec.couriers,
        "path": str(out_path),
        "text": text,
        "note": (
            f"全新随机实例 seed={seed} (>=10000, 与官方 seed 不相交)，"
            "评委此前从未见过；求解链路无任何硬编码缓存可命中。"
        ),
    }


# --------------------------------------------------------------------------- #
# 2. Size-decoupled perception (replaces ==30 / ==60 magic constants)          #
# --------------------------------------------------------------------------- #
def _willingness_quantiles(willingnesses: list[float]) -> dict[str, float]:
    if not willingnesses:
        return {"p10": 0.0, "p25": 0.0, "p50": 0.0, "p75": 0.0, "p90": 0.0, "mean": 0.0}
    s = sorted(willingnesses)

    def q(p: float) -> float:
        if len(s) == 1:
            return s[0]
        idx = p * (len(s) - 1)
        lo = int(idx)
        hi = min(lo + 1, len(s) - 1)
        frac = idx - lo
        return s[lo] * (1 - frac) + s[hi] * frac

    return {
        "p10": round(q(0.10), 4),
        "p25": round(q(0.25), 4),
        "p50": round(q(0.50), 4),
        "p75": round(q(0.75), 4),
        "p90": round(q(0.90), 4),
        "mean": round(statistics.fmean(s), 4),
    }


def size_decoupled_perception(
    candidates: list[tuple[str, tuple[str, ...], str, float, float, int]],
    all_tasks: set[str],
) -> dict[str, Any]:
    """Scale-free regime classification.

    Instead of `task_count == 30 and courier_count == 60` style magic constants,
    classify with SIZE-INVARIANT features:
      * density ratio  d = couriers / tasks   (capacity per task; <1 => scarce)
      * willingness MEAN (item 5: ONE statistic used consistently everywhere)
      * bundle fraction f_b                     (combinatorial coupling)
    These ratios hold the same meaning at 6 tasks or 400 tasks, so the demo
    generalizes to a judge's arbitrary-size blind case.

    Item 5 (threshold unification): every willingness gate below uses the SAME
    statistic — the overall MEAN willingness `w_mean` — instead of the previous
    mix of p50 and single-only mean.  Item 7 (rider-rich reachability): the
    rider-rich density threshold is 2.05 (max regime density ≈2.083, so it is
    reachable from the dropdown), not the old unreachable 2.2.
    """
    n_tasks = len(all_tasks)
    couriers = {row[2] for row in candidates}
    n_couriers = len(couriers)
    n_rows = len(candidates)
    willing = [row[4] for row in candidates]
    quant = _willingness_quantiles(willing)
    w_mean = quant["mean"]  # item 5: the single shared willingness statistic
    singles = [row for row in candidates if len(row[1]) == 1]
    bundles = [row for row in candidates if len(row[1]) > 1]
    bundle_fraction = round(len(bundles) / n_rows, 4) if n_rows else 0.0
    single_w = [row[4] for row in singles]
    single_mean = round(statistics.fmean(single_w), 4) if single_w else w_mean

    density_ratio = round(n_couriers / n_tasks, 4) if n_tasks else 0.0
    rows_per_task = round(n_rows / n_tasks, 3) if n_tasks else 0.0

    # ---- size-free decision rules (all thresholds are ratios/quantiles) ------
    rules: list[str] = []
    if n_tasks == 0:
        regime = "empty"
        rules.append("无候选行 → 无法判定 regime（证书将判 N/A）")
    else:
        # Scarcity: capacity per task <= 1 means couriers are a binding resource.
        scarce = density_ratio <= 1.0
        # Low willingness: detected purely by the shared MEAN willingness
        # statistic (item 5), not by exact instance dimensions.
        low_willing = (w_mean < 0.27 and not scarce)
        if scarce:
            regime = "scarce"
            rules.append(f"密度比 d=couriers/tasks={density_ratio} ≤ 1.0 → 骑手是瓶颈资源 → scarce")
        elif low_willing:
            regime = "low-willingness"
            rules.append(
                f"意愿均值 w_mean={w_mean} < 0.27 (密度比 d={density_ratio} 充足) → low-willingness"
            )
        elif n_tasks <= 8:
            regime = "tiny"
            rules.append(f"任务数 {n_tasks} ≤ 8 → tiny (可解释小样例)")
        elif bundle_fraction >= 0.35:
            regime = "bundle-heavy"
            rules.append(f"bundle 比例 f_b={bundle_fraction} ≥ 0.35 → 组合耦合强 → bundle-heavy")
        elif density_ratio >= 2.05:
            regime = "rider-rich"
            rules.append(f"密度比 d={density_ratio} ≥ 2.05 → 骑手充裕 → rider-rich")
        else:
            regime = "balanced"
            rules.append(f"密度比 d={density_ratio} 适中、意愿均值 {w_mean} 正常、bundle 比例 {bundle_fraction} → balanced")

    return {
        "regime": regime,
        "tasks": n_tasks,
        "couriers": n_couriers,
        "rows": n_rows,
        "density_ratio": density_ratio,
        "rows_per_task": rows_per_task,
        "bundle_fraction": bundle_fraction,
        "willingness": quant,
        "willingness_mean": w_mean,
        "single_mean_willingness": single_mean,
        "has_bundles": bool(bundles),
        "rules": rules,
        "feature_vector": {
            "d_couriers_per_task": density_ratio,
            "willingness_mean": w_mean,
            "willingness_p50": quant["p50"],
            "bundle_fraction": bundle_fraction,
        },
    }


def _planner_strategy_for_regime(regime: str) -> dict[str, str]:
    """Map the size-free regime to a NARRATED solve chain + the WHY.

    Item 5 (honesty): this is a MIRROR-READ of how the solver internally would
    classify the instance — it is *narration / interpretation*, NOT a causal
    switch.  solver_v3.solve() runs its own full anytime chain regardless of
    what string we print here; this panel does not steer the solver.
    """
    table = {
        "scarce": {
            "chain": "列搜索(K2/Bundle) + 最小费用流 (MCF) 重组",
            "why": "骑手稀缺(d≤1) → 骑手复用是硬约束，优先 bundle 覆盖 + 流模型重排，允许少量未覆盖以降期望成本。",
        },
        "low-willingness": {
            "chain": "低意愿全局列搜索 + 风险感知排序",
            "why": "意愿均值低 → 单派接受率低，构造全局候选列、用 willingness 抵御 100/任务的全拒惩罚。",
        },
        "bundle-heavy": {
            "chain": "Pair/Bundle 匹配 + 局部改进链",
            "why": "bundle 比例高 → 组合耦合强，优先二/三元组匹配挖掘组合收益。",
        },
        "rider-rich": {
            "chain": "贪心基线 + 多派 + LNS 局部搜索",
            "why": "骑手充裕(d≥2.05) → 覆盖不是瓶颈，集中算力做质量上的局部改进。",
        },
        "tiny": {
            "chain": "全枚举/列搜索",
            "why": "样例极小 → 可近似穷举核心选择，直接逼近最优。",
        },
        "balanced": {
            "chain": "多策略组合搜索 + anytime LNS",
            "why": "规模/意愿/bundle 均适中 → 跑完整 anytime 求解链做综合搜索与局部改进。",
        },
        "empty": {
            "chain": "（无候选行，跳过求解）",
            "why": "实例为空 / 无可解析候选行 → 不进入求解，证书将判 N/A。",
        },
    }
    return table.get(regime, table["balanced"])


# --------------------------------------------------------------------------- #
# 3. Sandboxed solve: hard per-instance timeout + heartbeat progress events     #
# --------------------------------------------------------------------------- #
def _solve_worker(solver_path: str, text: str, q) -> None:
    import importlib.util

    try:
        spec = importlib.util.spec_from_file_location("blind_solver_under_test", solver_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        t0 = time.monotonic()
        out = mod.solve(text)
        dt = time.monotonic() - t0
        norm = [(k, list(cs)) for (k, cs) in out]
        q.put(("ok", norm, dt))
    except Exception:  # pragma: no cover - defensive
        import traceback

        q.put(("err", traceback.format_exc(), 0.0))


def _solve_context():
    """Return a robust multiprocessing context.

    Item 4 robustness: prefer 'fork' where available (macOS/Linux).  'fork' does
    NOT re-import the parent's __main__, so the subprocess solve works even when
    run_blind_solve is imported and called outside an `if __name__ == "__main__"`
    guard — unlike 'spawn', which re-executes __main__ and breaks for callers
    whose __main__ has import-time side effects (e.g. binding a server port).
    solver_v2/solver_v3 are import-clean, so 'fork' is safe (the original solver.py
    hardcoded-path side effect — the reason 'spawn' was used — is not on this path).
    Falls back to 'spawn' if 'fork' is unavailable (e.g. Windows).
    """
    try:
        return mp.get_context("fork")
    except (ValueError, RuntimeError):  # pragma: no cover - platform-dependent
        return mp.get_context("spawn")


def solve_with_timeout(
    text: str,
    solver_path: Path,
    hard_timeout_s: float,
    heartbeat: Callable[[float], None] | None = None,
    heartbeat_interval_s: float = 0.7,
) -> dict[str, Any]:
    """Run solver_path.solve(text) in a spawned process with a hard wall guard.

    Item 4: instead of one blocking p.join(hard_timeout_s) (which freezes the
    SSE stream for the whole solve), we poll the worker in short slices and call
    `heartbeat(elapsed)` between slices so the client keeps seeing progress.  If
    the worker overruns hard_timeout_s it is terminated and we report
    status='timeout' instead of hanging the demo.
    """
    ctx = _solve_context()
    q = ctx.Queue()
    p = ctx.Process(target=_solve_worker, args=(str(solver_path), text, q))
    t0 = time.monotonic()
    p.start()
    # Poll loop with heartbeats (item 4: no SSE dead-zone).
    while True:
        p.join(heartbeat_interval_s)
        elapsed = time.monotonic() - t0
        if not p.is_alive():
            break
        if elapsed >= hard_timeout_s:
            p.terminate()
            p.join()
            return {"status": "timeout", "solution": None, "solve_time": elapsed}
        if heartbeat is not None:
            try:
                heartbeat(round(elapsed, 2))
            except Exception:
                pass  # never let a dead client kill the solve
    try:
        status, payload, dt = q.get_nowait()
    except Exception:
        return {"status": "crash", "solution": None, "solve_time": time.monotonic() - t0}
    if status == "err":
        return {"status": "error", "solution": None, "solve_time": dt, "trace": payload}
    return {"status": "ok", "solution": payload, "solve_time": dt}


# --------------------------------------------------------------------------- #
# 4. The promoted self-evolved strategy card (REAL, from the registry)         #
# --------------------------------------------------------------------------- #
def _neutral_card(strategy_id: str, reason: str) -> dict[str, Any]:
    """Item 1: a card that ALWAYS carries 'status' even when nothing is promoted,
    so neither the front-end nor the selfcheck KeyErrors on entry['status']."""
    return {
        "available": False,
        "strategy_id": strategy_id,
        "status": "none",  # <-- always present; was the missing key (item 1)
        "operator": None,
        "generation": None,
        "parent": None,
        "target_regime": None,
        "thought": "",
        "rank_body": "",
        "safety_passed": None,
        "safety_reason": "",
        "heldout_mean": None,
        "baseline_heldout_mean": None,
        "train_mean": None,
        "last_decision": None,
        "last_reason": reason,
        "improvement_vs_baseline": None,
        "code": "",
        "file": "",
        "error": reason,
    }


def promoted_strategy_card(strategy_id: str = PROMOTED_STRATEGY_ID) -> dict[str, Any]:
    """Read the REAL promoted strategy (thought + code) from the registry.

    Item 1: degrades gracefully to a neutral card (available=False, status='none')
    if the registry file is missing, unreadable, or lacks the strategy — it never
    raises and the returned dict ALWAYS has a 'status' key.
    """
    try:
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        return _neutral_card(strategy_id, f"registry 不可读: {type(exc).__name__}")
    entry = registry.get(strategy_id)
    if entry is None:
        # Fall back to ANY promoted strategy if the pinned id is absent.
        promoted = [(sid, e) for sid, e in registry.items() if e.get("status") == "promoted"]
        if promoted:
            strategy_id, entry = promoted[0]
        else:
            return _neutral_card(strategy_id, "registry 中无 promoted 策略 (N/A)")
    code = ""
    fpath = entry.get("file", "")
    if fpath and Path(fpath).exists():
        try:
            code = Path(fpath).read_text(encoding="utf-8")
        except Exception:
            code = ""
    delta = None
    try:
        delta = round(float(entry["baseline_heldout_mean"]) - float(entry["heldout_mean"]), 4)
    except Exception:
        delta = None
    return {
        "available": True,
        "strategy_id": strategy_id,
        "status": entry.get("status", "none"),
        "operator": entry.get("operator"),
        "generation": entry.get("generation"),
        "parent": entry.get("parent"),
        "target_regime": entry.get("target_regime"),
        "thought": entry.get("thought", ""),
        "rank_body": entry.get("rank_body", ""),
        "safety_passed": entry.get("safety_passed"),
        "safety_reason": entry.get("safety_reason"),
        "heldout_mean": entry.get("heldout_mean"),
        "baseline_heldout_mean": entry.get("baseline_heldout_mean"),
        "train_mean": entry.get("train_mean"),
        "last_decision": entry.get("last_decision"),
        "last_reason": entry.get("last_reason"),
        "improvement_vs_baseline": delta,
        "code": code,
        "file": fpath,
    }


def evolution_registry_summary() -> dict[str, Any]:
    try:
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "total_strategies": 0,
            "promoted": [],
            "accepted_or_better": [],
            "registry_path": str(REGISTRY_PATH),
            "error": f"{type(exc).__name__}",
        }
    promoted = [sid for sid, e in registry.items() if e.get("status") == "promoted"]
    accepted = [
        sid
        for sid, e in registry.items()
        if e.get("status") in {"accepted", "candidate", "trusted", "promoted"}
    ]
    return {
        "total_strategies": len(registry),
        "promoted": promoted,
        "accepted_or_better": accepted,
        "registry_path": str(REGISTRY_PATH),
    }


# --------------------------------------------------------------------------- #
# 5. Multi-stakeholder panel (four-party scorecard + Pareto front)             #
# --------------------------------------------------------------------------- #
WEIGHT_PRESETS: dict[str, dict[str, float]] = {
    "balanced": {"wc": 1.0, "wr": 1.0, "wm": 1.0, "wp": 1.0},
    "platform_first": {"wc": 0.6, "wr": 0.6, "wm": 0.6, "wp": 2.5},
    "rider_first": {"wc": 0.8, "wr": 2.5, "wm": 0.6, "wp": 0.8},
    "customer_first": {"wc": 2.5, "wr": 0.8, "wm": 0.8, "wp": 0.8},
}


def stakeholder_panel(
    text: str,
    solution: list[tuple[str, list[str]]],
    preset: str = "balanced",
) -> dict[str, Any]:
    """Four-party scorecard + a small efficiency-vs-fairness Pareto front."""
    rows, tasks = parse_competition_rows(text)
    wcfg = WEIGHT_PRESETS.get(preset, WEIGHT_PRESETS["balanced"])
    weights = Weights(**wcfg)
    report = evaluate_stakeholders(solution, rows, tasks, weights=weights)
    card = fairness_scorecard(report)

    # Small Pareto front: efficiency (cost) vs rider income Gini, 5 alphas.
    alphas = [0.0, 0.25, 0.5, 0.75, 1.0]
    front_raw = pareto_front(rows, tasks, alphas=alphas, weights=weights)
    efficient = {id(p) for p in pareto_efficient(front_raw)}
    front = [
        {
            "alpha": round(p.alpha, 2),
            "expected_cost": round(p.expected_cost, 3),
            "rider_income_gini": round(p.rider_income_gini, 4),
            "rider_worst_hourly": round(p.rider_worst_hourly, 3),
            "fulfillment_rate": round(p.fulfillment_rate, 4),
            "customer_max_lateness": round(p.customer_max_lateness, 3),
            "pareto_efficient": id(p) in efficient,
        }
        for p in front_raw
    ]
    return {
        "preset": preset,
        "weights": wcfg,
        "scorecard": {
            "customer": {k: round(v, 4) for k, v in card.customer.items()},
            "rider": {k: round(v, 4) for k, v in card.rider.items()},
            "merchant": {k: round(v, 4) for k, v in card.merchant.items()},
            "platform": {k: round(v, 4) for k, v in card.platform.items()},
        },
        "utilities": {
            "Uc_customer": round(report.Uc, 3),
            "Ur_rider": round(report.Ur, 3),
            "Um_merchant": round(report.Um, 3),
            "Up_platform": round(report.Up, 3),
            "U_weighted_total": round(report.U, 3),
        },
        "pareto_front": front,
    }


# --------------------------------------------------------------------------- #
# 6. The headline orchestration: a streamed blind-test decision trajectory     #
# --------------------------------------------------------------------------- #
def run_blind_solve(
    text: str,
    case_label: str = "blind-case",
    memory_enabled: bool = True,
    weight_preset: str = "balanced",
    hard_timeout_s: float = 11.0,
    observer: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """End-to-end blind-test solve over a brand-new case, with a live trajectory.

    Item 2 (HONEST memory switch): the solve path is solver_v3.solve (= solver_v2
    with NO per-seed cache / NO hardcoded answers + argmin over trusted evolved
    candidates) in BOTH switch positions.  The switch does NOT change behaviour
    — solver_v2 already removed every cache, so there is nothing to "turn off".
    We surface that honestly: when memory is ON we emit a verifiable line stating
    "0 memory entries were consulted this run" (we never perform a memory
    lookup), and we do NOT claim the OFF position "forces real-time search".
    """
    started = time.monotonic()
    events: list[dict[str, Any]] = []

    def emit(event: dict[str, Any]) -> None:
        event = {"time_s": round(time.monotonic() - started, 3), **event}
        events.append(event)
        if observer is not None:
            try:
                observer(event)
            except Exception:
                # Item 6 (defensive): a dead SSE client must not crash the solve.
                pass

    candidates, all_tasks = parse_candidates(text)

    # ---- Input hygiene (item 3): surface parse-notes (NaN/Inf rejected,        #
    # ---- out-of-range willingness clamped) from optimality_bound_r1.           #
    parse_notes: list[str] = []
    try:
        _r, _t, parse_notes = optimality_bound.parse_instance(text, collect_notes=True)
    except Exception:
        parse_notes = []
    if parse_notes:
        emit(
            {
                "type": "input_hygiene",
                "message": "输入清洗：" + "；".join(parse_notes) + "。证书将基于清洗后的合法行计算。",
                "notes": parse_notes,
            }
        )

    # ---- Perception (size-decoupled) ----------------------------------------
    perc = size_decoupled_perception(candidates, all_tasks)
    emit(
        {
            "type": "perception",
            "message": f"尺寸解耦特征判定为 {perc['regime']} 场景（无 ==30/==60 魔法常数，意愿统一用均值口径）。",
            "perception": perc,
        }
    )

    # ---- Memory / cache switch (item 2: HONEST, no behaviour-switch claim) ----
    solver_path = SOLVER_V3_PATH
    if memory_enabled:
        cache_msg = (
            "Memory/缓存：开。可核验证据：本次求解共查询了 0 条记忆条目"
            "（solver_v2 已删除所有 per-seed 缓存，求解链路本就不含硬编码答案，故无记忆可命中）。"
        )
    else:
        cache_msg = (
            "Memory/缓存：关。说明：本开关用于演示『求解不依赖任何记忆』——"
            "开/关两种位置走的是同一条 solver_v3 实时求解链路、字节级相同，"
            "关闭不改变行为，只是显式声明本项目无 per-seed 缓存可关。"
        )
    emit(
        {
            "type": "memory_switch",
            "memory_enabled": memory_enabled,
            "solver": "solver_v3.py",
            "message": cache_msg,
            "memory_entries_consulted": 0,
            "behaviour_changes_with_switch": False,
        }
    )

    # ---- Planner / Trials ----------------------------------------------------
    plan = _planner_strategy_for_regime(perc["regime"])
    emit(
        {
            "type": "planner",
            "message": (
                f"Planner（旁白：以下为对求解器内部规模/regime 分类的镜像解读，"
                f"非改变求解行为的因果开关）选定策略链：{plan['chain']}。"
            ),
            "regime": perc["regime"],
            "chain": plan["chain"],
            "why": plan["why"],
            "is_mirror_read": True,
        }
    )
    emit(
        {
            "type": "trial_start",
            "message": "Trials：在隔离子进程中调用 solver_v3 实时搜索（带硬超时保护 + 心跳进度）。",
            "solver": "solver_v3.py",
            "hard_timeout_s": hard_timeout_s,
        }
    )

    def _heartbeat(elapsed: float) -> None:
        emit(
            {
                "type": "progress",
                "message": f"求解进行中… 已用 {elapsed}s（硬超时 {hard_timeout_s}s 保护）。",
                "elapsed_s": elapsed,
                "phase": "solver_v3",
            }
        )

    solve_result = solve_with_timeout(text, solver_path, hard_timeout_s, heartbeat=_heartbeat)
    solve_status = solve_result["status"]
    solve_time = round(float(solve_result.get("solve_time", 0.0)), 3)

    if solve_status != "ok" or solve_result.get("solution") is None:
        # Item 4: fallback ALSO runs in a spawned subprocess with the hard timeout
        # + heartbeats (it used to run in-process and could block the SSE ~20s).
        emit(
            {
                "type": "controller",
                "message": (
                    f"solver_v3 子进程返回 {solve_status}，Controller 回退到 "
                    f"solver_v2 子进程（同样带硬超时 + 心跳，仍无硬编码）。"
                ),
                "status": solve_status,
            }
        )

        def _heartbeat_fb(elapsed: float) -> None:
            emit(
                {
                    "type": "progress",
                    "message": f"回退求解进行中… 已用 {elapsed}s（solver_v2 子进程，硬超时保护）。",
                    "elapsed_s": elapsed,
                    "phase": "solver_v2_fallback",
                }
            )

        fb = solve_with_timeout(text, SOLVER_V2_PATH, hard_timeout_s, heartbeat=_heartbeat_fb)
        if fb["status"] == "ok" and fb.get("solution") is not None:
            solution = fb["solution"]
            solve_time = round(float(fb.get("solve_time", 0.0)), 3)
            solve_status = "ok-fallback-v2"
        else:
            solution = []
            solve_status = f"failed:{fb['status']}"
    else:
        solution = solve_result["solution"]

    # ---- Critic: optimality gap certificate (item 3: N/A gatekeeping via r1) --
    summary = summarize_solution(solution, candidates, all_tasks, 0.0)
    try:
        cert = optimality_bound.critic_self_assessment(solution, input_text=text)
        headline = cert.get("headline", "")
        gap_pct = cert.get("gap_pct")
        lower_bound = cert.get("lower_bound")
        upper_bound = cert.get("upper_bound")
        binding = cert.get("binding_bound")
        # Item 3: certified_optimal is gated by applicable; never show a green
        # CERTIFIED badge on a vacuous / non-applicable certificate.
        applicable = cert.get("applicable", True)
        certified_optimal = bool(cert.get("certified_optimal")) and bool(applicable)
    except Exception as exc:
        headline = f"证书暂不可用：{type(exc).__name__} (N/A)"
        gap_pct = lower_bound = upper_bound = binding = None
        applicable = False
        certified_optimal = False

    emit(
        {
            "type": "critic",
            "message": f"Critic 最优性证书：{headline}",
            "headline": headline,
            "gap_pct": gap_pct,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "binding_bound": binding,
            "certified_optimal": certified_optimal,
            "applicable": applicable,
            "coverage": f"{summary['covered_tasks']}/{summary['total_tasks']}",
            "valid": bool(summary["valid"]),
        }
    )

    # ---- Controller / Memory: best solution ---------------------------------
    within_budget = solve_time <= 10.5
    emit(
        {
            "type": "controller",
            "message": (
                f"Controller：择优保留当前最优解；用时 {solve_time}s "
                f"{'(10s 预算内)' if within_budget else '(超预算，已被硬超时保护)'}，状态 {solve_status}。"
            ),
            "solve_time_s": solve_time,
            "within_budget": within_budget,
            "status": solve_status,
        }
    )
    emit(
        {
            "type": "memory",
            "message": (
                f"Memory：最优解 {summary['groups']} 组、覆盖 {summary['covered_tasks']}/{summary['total_tasks']}、"
                f"用骑手 {summary['used_couriers']}。"
                + ("（本次未查询/未写入任何记忆条目）" if not memory_enabled else "")
            ),
            "groups": summary["groups"],
            "used_couriers": summary["used_couriers"],
            "covered": f"{summary['covered_tasks']}/{summary['total_tasks']}",
        }
    )

    # ---- Stakeholder panel ---------------------------------------------------
    try:
        panel = stakeholder_panel(text, solution, preset=weight_preset)
    except Exception as exc:
        panel = {"error": f"{type(exc).__name__}: {exc}"}

    wall = round(time.monotonic() - started, 3)
    emit({"type": "final", "message": f"盲测求解完成，总用时 {wall}s。", "wall_time_s": wall})

    return {
        "status": "ok",
        "case_label": case_label,
        "memory_enabled": memory_enabled,
        "solver": "solver_v3.py",
        "live_search_path": True,
        "memory_entries_consulted": 0,
        "perception": perc,
        "planner": {"regime": perc["regime"], "is_mirror_read": True, **plan},
        "solve_status": solve_status,
        "solve_time_s": solve_time,
        "within_budget": within_budget,
        "input_notes": parse_notes,
        "solution_summary": {
            "groups": summary["groups"],
            "used_couriers": summary["used_couriers"],
            "covered_tasks": summary["covered_tasks"],
            "total_tasks": summary["total_tasks"],
            "valid": bool(summary["valid"]),
        },
        "certificate": {
            "headline": headline,
            "gap_pct": gap_pct,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "binding_bound": binding,
            "certified_optimal": certified_optimal,
            "applicable": applicable,
        },
        "stakeholders": panel,
        "evolution": {
            "promoted_card": promoted_strategy_card(),
            "registry_summary": evolution_registry_summary(),
        },
        "wall_time_s": wall,
        "events": events,
        "solution": solution,
    }


# --------------------------------------------------------------------------- #
# Headless self-check (no server): generate -> blind solve -> assert sane       #
# --------------------------------------------------------------------------- #
def _selfcheck(regime: str = "scarce") -> int:
    print(f"[selfcheck] generating fresh blind case (regime={regime}) ...")
    case = generate_blind_case(regime)
    print(f"[selfcheck]   seed={case['seed']} rows={case['rows']} -> {case['path']}")
    print("[selfcheck] running blind solve with memory ON (honest no-op switch) ...")
    events_seen: list[str] = []
    report = run_blind_solve(
        case["text"],
        case_label=case["path"],
        memory_enabled=True,
        observer=lambda e: events_seen.append(e["type"]),
    )
    ok = True
    print(f"[selfcheck]   solve_status   = {report['solve_status']}")
    print(f"[selfcheck]   solve_time_s   = {report['solve_time_s']} (within_budget={report['within_budget']})")
    print(f"[selfcheck]   regime         = {report['perception']['regime']} "
          f"(d={report['perception']['density_ratio']}, w_mean={report['perception']['willingness_mean']})")
    print(f"[selfcheck]   coverage       = {report['solution_summary']['covered_tasks']}/"
          f"{report['solution_summary']['total_tasks']} valid={report['solution_summary']['valid']}")
    print(f"[selfcheck]   certificate    = {report['certificate']['headline'][:100]}")
    print(f"[selfcheck]   gap_pct        = {report['certificate']['gap_pct']}")
    print(f"[selfcheck]   cert.applicable= {report['certificate']['applicable']} "
          f"certified_optimal={report['certificate']['certified_optimal']}")
    # Item 1: card must always carry a 'status' key, even if unavailable.
    card = report["evolution"]["promoted_card"]
    assert "status" in card, "promoted card missing 'status' key (item 1 regression)"
    print(f"[selfcheck]   promoted       = {card['strategy_id']} status={card['status']} "
          f"available={card['available']} (Δheldout={card['improvement_vs_baseline']})")
    print(f"[selfcheck]   stakeholders   = U_total={report['stakeholders'].get('utilities', {}).get('U_weighted_total')} "
          f"pareto_points={len(report['stakeholders'].get('pareto_front', []))}")
    print(f"[selfcheck]   event types    = {events_seen}")
    if report["solve_status"] not in {"ok", "ok-fallback-v2"}:
        print("[selfcheck] FAIL: solve did not succeed"); ok = False
    if not report["within_budget"]:
        print("[selfcheck] WARN: solve exceeded 10s budget")
    # Item 1: tolerate available:False (no KeyError); only require correct id
    # WHEN a strategy is actually promoted.
    if card["available"]:
        if card["status"] != "promoted" or card["strategy_id"] != "gen01_M1_003":
            print("[selfcheck] FAIL: promoted strategy card not gen01_M1_003/promoted"); ok = False
    else:
        print("[selfcheck] NOTE: no promoted strategy available; card degraded gracefully (status='none')")
    if "perception" not in events_seen or "critic" not in events_seen:
        print("[selfcheck] FAIL: trajectory missing perception/critic stages"); ok = False

    # ---- Item 3 hardening: empty + NaN/garbled input must NOT show CERTIFIED --
    print("[selfcheck] N/A gate test: empty input ...")
    empty_rep = run_blind_solve("", case_label="empty", memory_enabled=True)
    if empty_rep["certificate"]["certified_optimal"]:
        print("[selfcheck] FAIL: empty input showed CERTIFIED OPTIMAL"); ok = False
    else:
        print(f"[selfcheck]   empty cert headline = {empty_rep['certificate']['headline'][:80]} "
              f"(certified_optimal={empty_rep['certificate']['certified_optimal']}) OK")

    print("[selfcheck] N/A gate test: NaN/out-of-range willingness input ...")
    bad = ("task_id_list\tcourier_id\ttotal_score\twillingness\n"
           "T0001\tC001\tnan\t0.5\n"
           "T0002\tC002\t30.0\t1.4\n"
           "T0003\tC003\t25.0\t-0.2\n")
    bad_rep = run_blind_solve(bad, case_label="bad-input", memory_enabled=True)
    note_types = [e["type"] for e in bad_rep["events"]]
    if "input_hygiene" not in note_types:
        print("[selfcheck] FAIL: NaN/oob input did not emit input_hygiene note"); ok = False
    else:
        print(f"[selfcheck]   input notes = {bad_rep['input_notes']} OK")

    print(f"[selfcheck] {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Headless self-check for the R1 blind-test orchestrator.")
    ap.add_argument("--regime", default="scarce", choices=list(BLIND_REGIME_LABELS))
    ap.add_argument("--selfcheck", action="store_true", help="run the headless self-check and exit")
    args = ap.parse_args()
    raise SystemExit(_selfcheck(args.regime))
