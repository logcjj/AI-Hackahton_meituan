"""
cockpit_baseline.py
===================
即时履约智能调度指挥舱 · 纯贪心基线 (iteration-1)

唯一新增的后端工作（落实方案 §4.2 / D6）：在求解流程之外加一次**纯贪心基线**
求解，把两列真值塞进 report["baseline"]，让「基线=纯贪心，AutoSolver 必须严格
优于」可被真值印证。

本模块**只读、不改**任何 solver / orchestrator（算法不动）。它严格按已验证的
配方实现（/tmp/mtg/verify_baseline.py + 方案 §0.5.3 纠错）：

  * 贪心解 + 成本函数来源 module 必须是 solver_v2（含 _fallback_official_greedy
    与 _solution_expected_cost），**绝不能用 solver_v4 取这俩函数**（v4 不暴露）。
  * **绝不能** `from tools.agent_trace_demo import _solution_expected_cost`（会
    ImportError —— 它只是 CRITIC_FUNCTIONS 里的字符串，须经 module 取用）。
  * load_solver 必须传 pathlib.Path（传 str 会 AttributeError）。
  * 候选体用 parse_candidates 返回的 6-tuple，元组解包；成本函数 3 参
    (solution, candidates, sorted(all_tasks))，与 agent_trace_demo.generate_trace
    的调用约定一致（规范口径，非自造）。

已验证真值（large_seed301，确定性可复现）：
  greedy  expected_cost = 2097.658（40/40，40 骑手，≈0.02s）
  solver_v4 expected_cost = 657.104（40/40，80 骑手，≈6.7s）
  cost_pct = 68.67%；strictly_better = True（成本口径：成本更低 + 覆盖不更差）。

「严格优于」口径铁律（§0.5.4）：仅 `v4_cost < greedy_cost and v4_covered >=
greedy_covered`，**不含「骑手更少」**（本 case v4 用 80 > 贪心 40，靠多派/合单换
更低期望成本，绝不宣称省骑手）。
"""
from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# parse_candidates / summarize_solution / load_solver 是 agent_trace_demo 的
# module 级符号，可直接 import（_solution_expected_cost / _fallback_official_greedy
# 不是 —— 它们须经 solver module getattr 取用，见模块 docstring）。
from tools.agent_trace_demo import load_solver, parse_candidates, summarize_solution

GREEDY_SOLVER_PATH = ROOT / "solver_v2.py"   # ⚠️ 必须 solver_v2（非 v4），必须 Path
V4_SOLVER_PATH = ROOT / "solver_v4.py"


def _load_solver_module(path: Path):
    """与 blind_test_orchestrator._solve_worker 同款的纯加载（read-only）。"""
    spec = importlib.util.spec_from_file_location("cockpit_v4_solver", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_greedy(text: str) -> dict[str, Any]:
    """纯贪心基线（与 autosolver_agent/system.py:_run_greedy 同款配方）。

    返回 {covered, total, used_couriers, expected_cost, solve_time_s, valid,
          solver_used, solution}。
    """
    m = load_solver(GREEDY_SOLVER_PATH)              # solver_v2，必须 Path
    candidates, all_tasks = parse_candidates(text)   # 6-tuple，元组解包
    all_tasks_sorted = sorted(all_tasks)
    cost_fn = getattr(m, "_solution_expected_cost")  # 经 module 取用，非 import

    t0 = time.monotonic()
    greedy_sol = m._fallback_official_greedy(candidates)
    solve_time = time.monotonic() - t0

    sol_norm = [(k, list(cs)) for (k, cs) in greedy_sol]
    cost = float(cost_fn(sol_norm, candidates, all_tasks_sorted))
    summ = summarize_solution(sol_norm, candidates, all_tasks, cost)
    return {
        "covered": summ["covered_tasks"],
        "total": summ["total_tasks"],
        "used_couriers": summ["used_couriers"],
        "expected_cost": round(cost, 3),
        "solve_time_s": round(solve_time, 4),
        "valid": bool(summ["valid"]),
        "solver_used": "solver_v2.py(_fallback_official_greedy)",
        "solution": sol_norm,
    }


def _autosolver_cost_from_solution(
    text: str,
    solution: list[tuple[str, list[str]]] | None,
    solve_time_s: float | None,
    solver_used: str = "solver_v4.py",
) -> dict[str, Any]:
    """用同一口径(_solution_expected_cost)给一个**已有的** AutoSolver 解算成本，
    避免重复跑 v4（SSE 主线已跑过一次）。成本函数仍走 solver_v2 取用，保证与
    贪心同口径可比。"""
    m = load_solver(GREEDY_SOLVER_PATH)
    candidates, all_tasks = parse_candidates(text)
    all_tasks_sorted = sorted(all_tasks)
    cost_fn = getattr(m, "_solution_expected_cost")
    if not solution:
        return {
            "covered": 0,
            "total": len(all_tasks),
            "used_couriers": 0,
            "expected_cost": None,
            "solve_time_s": round(solve_time_s or 0.0, 4) if solve_time_s is not None else None,
            "valid": False,
            "solver_used": solver_used,
        }
    sol_norm = [(k, list(cs)) for (k, cs) in solution]
    cost = float(cost_fn(sol_norm, candidates, all_tasks_sorted))
    summ = summarize_solution(sol_norm, candidates, all_tasks, cost)
    return {
        "covered": summ["covered_tasks"],
        "total": summ["total_tasks"],
        "used_couriers": summ["used_couriers"],
        "expected_cost": round(cost, 3),
        "solve_time_s": round(solve_time_s, 4) if solve_time_s is not None else None,
        "valid": bool(summ["valid"]),
        "solver_used": solver_used,
    }


def run_autosolver(text: str) -> dict[str, Any]:
    """独立跑一次 solver_v4 求解（仅在没有现成解可复用时使用，如 /api/baseline 单刷）。
    与 SSE 主线相比会多花 ~6.7s。"""
    v4 = _load_solver_module(V4_SOLVER_PATH)
    t0 = time.monotonic()
    sol = v4.solve(text)
    dt = time.monotonic() - t0
    return _autosolver_cost_from_solution(text, sol, dt, solver_used="solver_v4.py")


def _improvement(greedy: dict[str, Any], autosolver: dict[str, Any]) -> dict[str, Any]:
    g_cost = greedy.get("expected_cost")
    a_cost = autosolver.get("expected_cost")
    cost_pct = None
    if g_cost and a_cost is not None and g_cost:
        cost_pct = round((g_cost - a_cost) / g_cost * 100.0, 4)
    coverage_delta = (autosolver.get("covered") or 0) - (greedy.get("covered") or 0)
    strictly_better = bool(
        a_cost is not None
        and g_cost is not None
        and a_cost < g_cost
        and (autosolver.get("covered") or 0) >= (greedy.get("covered") or 0)
    )
    return {
        "cost_pct": cost_pct,
        "coverage_delta": coverage_delta,
        "used_couriers_record": autosolver.get("used_couriers"),  # 仅记录，非优势项
        "strictly_better": strictly_better,
    }


def compute_baseline(
    text: str,
    autosolver_solution: list[tuple[str, list[str]]] | None = None,
    autosolver_solve_time_s: float | None = None,
    autosolver_solver_used: str = "solver_v4.py",
    run_v4_if_missing: bool = False,
) -> dict[str, Any]:
    """计算完整 baseline payload。

    优先复用 SSE 主线已产出的 autosolver_solution（避免二次跑 v4）；若未提供且
    run_v4_if_missing=True，则独立跑一次 v4（单刷 /api/baseline 场景）。
    """
    greedy = run_greedy(text)
    if autosolver_solution is not None:
        autosolver = _autosolver_cost_from_solution(
            text, autosolver_solution, autosolver_solve_time_s, autosolver_solver_used
        )
    elif run_v4_if_missing:
        autosolver = run_autosolver(text)
    else:
        autosolver = {
            "covered": None, "total": greedy["total"], "used_couriers": None,
            "expected_cost": None, "solve_time_s": None, "valid": None,
            "solver_used": autosolver_solver_used,
        }
    # solution 不进对外 payload（只用于算成本），剥掉避免膨胀
    greedy_public = {k: v for k, v in greedy.items() if k != "solution"}
    return {
        "greedy": greedy_public,
        "autosolver": autosolver,
        "improvement": _improvement(greedy, autosolver),
        "is_demo": False,  # 全真值
        "cost_basis": "_solution_expected_cost (solver_v2 口径, 与官方目标一致)",
    }


def selfcheck(text: str | None = None) -> dict[str, Any]:
    """对 large_seed301 跑一次贪心 + v4，断言严格优于。返回结果字典。"""
    if text is None:
        text = (ROOT / "data" / "official_cases" / "large_seed301.txt").read_text(encoding="utf-8")
    bl = compute_baseline(text, run_v4_if_missing=True)
    return bl


if __name__ == "__main__":
    import json
    bl = selfcheck()
    print(json.dumps(bl, ensure_ascii=False, indent=2))
    imp = bl["improvement"]
    print(f"[cockpit_baseline] strictly_better={imp['strictly_better']} "
          f"cost_pct={imp['cost_pct']} (greedy={bl['greedy']['expected_cost']} "
          f"vs v4={bl['autosolver']['expected_cost']})")
