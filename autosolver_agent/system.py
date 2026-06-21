from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from autosolver_agent.evolution import EvolutionManager, GeneratedStrategy
from tools.agent_trace_demo import infer_regime, load_solver, parse_candidates, summarize_solution


ROOT = Path(__file__).resolve().parents[1]
SOLVER_PATH = ROOT / "solver.py"
EVOLUTION_ROOT = ROOT / "autosolver_agent" / "evolution_state"


AGENT_BLUEPRINT = {
    "name": "AutoSolver Autonomous Strategy Agent",
    "objective": "在 10 秒测试预算内，自主探索多种配送分配策略，用内部 Critic 做接受/拒绝筛选，并输出当前最优合法方案。",
    "capabilities": [
        {
            "id": "perception",
            "title": "场景感知",
            "description": "解析任务、骑手、意愿、bundle 与稀缺度，自动识别 large / scarce / low-willingness 等 regime。",
        },
        {
            "id": "exploration",
            "title": "自主策略探索",
            "description": "不由人工指定单一算法，自动尝试 greedy、multi-dispatch、pair matching、sparse cover、column-style search 和 production solver。",
        },
        {
            "id": "critic",
            "title": "自动评估与筛选",
            "description": "每个候选解都经过同一 Critic 判断；网页只展示接受/拒绝和后续动作。",
        },
        {
            "id": "adaptation",
            "title": "迭代改进循环",
            "description": "根据上一轮接受/拒绝结果和 regime 调整下一轮策略，例如低意愿转向 low column，骑手稀缺转向 scarce bundle。",
        },
        {
            "id": "anytime",
            "title": "限时输出",
            "description": "每个策略都有时间片，接近预算时停止扩展，直接输出当前最优分配方案。",
        },
        {
            "id": "self_evolution",
            "title": "自进化策略生成",
            "description": "生成实验 Python 策略，经过安全检查、限时试跑、Critic 筛选；失败自动回退，成功写入策略记忆。",
        },
    ],
}


REVIEW_ALIGNMENT = {
    "source": {
        "type": "competition_delivery_requirements",
        "note": "Used to keep the demo aligned with final reproduction expectations, not as an official scoring rule.",
    },
    "review_dimensions": {
        "solution_quality": {
            "label": "最终解质量",
            "description": "正式结果以官方评测为准；页面不把本地 Critic 信号包装成官方成绩。",
        },
        "autonomous_iteration": {
            "label": "Agent 自主迭代能力",
            "description": "展示自主策略探索、自动评估筛选、历史驱动迭代和自进化实验闭环。",
        },
        "technical_report": {
            "label": "技术报告与证据",
            "description": "用架构图、运行截图、trace、测试和打包证据解释系统边界。",
        },
    },
    "agent_requirements": [
        {
            "id": "autonomous_strategy_exploration",
            "title": "自主策略探索",
            "description": "Agent 自主提出并尝试 greedy、matching、column-search、flow 和 production solver 等策略。",
            "evidence": "round_start / attempt_start events",
        },
        {
            "id": "automatic_evaluation_filtering",
            "title": "自动评估与筛选",
            "description": "Critic 自动判断候选是否合法、是否更新 best-so-far，并保留拒绝原因。",
            "evidence": "attempt_result / best_update events",
        },
        {
            "id": "iterative_improvement_loop",
            "title": "迭代改进循环",
            "description": "Controller 根据历史实验结果和 case profile 调整下一轮策略方向。",
            "evidence": "adapt / evolution_replay events",
        },
        {
            "id": "current_best_output",
            "title": "当前最优输出",
            "description": "系统持续维护 best-so-far，预算临近时输出当前最优合法方案。",
            "evidence": "best_update / final events",
        },
    ],
    "runtime_boundary": {
        "best_so_far_window_s": "2-5",
        "per_case_budget_s": 10,
        "description": "页面解释 best-so-far 过程；正式求解热路径按每个样例 10 秒边界设计。",
    },
    "non_goals": [
        "不展示本地 cost 为官方成绩",
        "不展示 40/40 为官方结论",
        "网页自进化实验不直接改写正式 solver.py 热路径",
    ],
}


@dataclass(frozen=True)
class StrategyAttempt:
    name: str
    label: str
    reason: str
    runner: Callable[[Any, list, set[str], list, float], list[tuple[str, list[str]]]]
    time_slice_s: float = 0.5


def get_agent_blueprint() -> dict[str, Any]:
    return {
        **AGENT_BLUEPRINT,
        "review_alignment": REVIEW_ALIGNMENT,
        "strategy_catalog": [
            {"id": "greedy_baseline", "label": "贪心基线", "type": "baseline"},
            {"id": "single_multidispatch", "label": "单任务多派", "type": "heuristic"},
            {"id": "disjoint_gain", "label": "启发式 Gain", "type": "heuristic"},
            {"id": "pair_matching", "label": "Pair Matching", "type": "matching"},
            {"id": "sparse_cover", "label": "稀疏覆盖", "type": "set-cover"},
            {"id": "low_global_column", "label": "低意愿全局列搜索", "type": "column-search"},
            {"id": "scarce_k2_column", "label": "Scarce K2 Column", "type": "column-search"},
            {"id": "scarce_bundle_mcf", "label": "Scarce Bundle MCF", "type": "flow"},
            {"id": "production_solver", "label": "生产级综合求解器", "type": "anytime-portfolio"},
        ],
    }


def _review_alignment_report(
    rounds: list[dict[str, Any]],
    events: list[dict[str, Any]],
    best: dict[str, Any],
    wall_time_s: float,
    budget_s: float,
) -> dict[str, Any]:
    event_types = [str(event.get("type", "")) for event in events]
    strategy_attempts = sum(len(round_payload.get("strategies", [])) for round_payload in rounds)
    critic_decisions = sum(1 for event_type in event_types if event_type == "attempt_result")
    return {
        **REVIEW_ALIGNMENT,
        "alignment_evidence": {
            "strategy_attempts": strategy_attempts,
            "critic_decisions": critic_decisions,
            "accepted_updates": sum(1 for event_type in event_types if event_type == "best_update"),
            "has_autonomous_exploration": strategy_attempts > 0 and "round_start" in event_types,
            "has_automatic_evaluation": critic_decisions > 0,
            "has_iterative_adaptation": "adapt" in event_types or len(rounds) > 1,
            "has_self_evolution_track": any(event_type.startswith("evolution_") for event_type in event_types),
            "has_current_best_output": "final" in event_types and bool(best.get("valid")),
            "runtime_budget_s": budget_s,
            "wall_time_s": wall_time_s,
            "best_strategy": best.get("strategy"),
        },
    }


def _singles(candidates: list[tuple[str, tuple[str, ...], str, float, float, int]]) -> list:
    return [row for row in candidates if len(row[1]) == 1]


def _score(module: Any, solution: list[tuple[str, list[str]]], candidates: list, all_tasks: set[str]) -> float:
    return float(module._solution_expected_cost(solution, candidates, all_tasks))


def _solution_record(
    module: Any,
    solution: list[tuple[str, list[str]]],
    candidates: list,
    all_tasks: set[str],
) -> dict[str, Any]:
    score = _score(module, solution, candidates, all_tasks)
    summary = summarize_solution(solution, candidates, all_tasks, score)
    return {
        "local_cost": score,
        "valid": bool(summary["valid"]),
        "covered_tasks": int(summary["covered_tasks"]),
        "total_tasks": int(summary["total_tasks"]),
        "groups": int(summary["groups"]),
        "used_couriers": int(summary["used_couriers"]),
        "uncovered_tasks": list(summary["uncovered_tasks"]),
        "riders_per_group": summary["riders_per_group"],
        "tasks_per_group": summary["tasks_per_group"],
        "invalid_reasons": summary["invalid_reasons"],
    }


def _case_quality_gate_text(case_profile: dict[str, Any] | None) -> dict[str, str]:
    profile = case_profile or {}
    regime = str(profile.get("regime", "") or "")
    tasks = int(profile.get("tasks", 0) or 0)
    couriers = int(profile.get("couriers", 0) or 0)
    rows = int(profile.get("rows", 0) or 0)
    has_bundles = bool(profile.get("has_bundles", False))
    if regime == "low-willingness":
        return {
            "reason_label": "低意愿试跑未优于基线",
            "reason_detail": f"低意愿质量门未通过：实验策略按时返回，但没有超过 stable baseline 的低接受率风险控制；本轮画像为 {tasks} 任务、{couriers} 骑手、{rows} 行候选。",
            "rollback_label": "回退到低意愿 baseline",
        }
    if regime == "scarce":
        return {
            "reason_label": "稀缺骑手试跑未优于基线",
            "reason_detail": f"稀缺骑手质量门未通过：实验策略按时返回，但没有超过 stable baseline 的骑手复用规避和 bundle 取舍；本轮画像为 {tasks} 任务、{couriers} 骑手、{rows} 行候选。",
            "rollback_label": "回退到稀缺 baseline",
        }
    if regime == "tiny":
        return {
            "reason_label": "Tiny 试跑未优于基线",
            "reason_detail": f"Tiny 质量门未通过：样例规模很小，stable baseline 已能快速覆盖核心选择，实验排序没有产生更好的替代结构；本轮画像为 {tasks} 任务、{couriers} 骑手。",
            "rollback_label": "回退到 tiny baseline",
        }
    if regime == "large":
        return {
            "reason_label": "大规模试跑未优于基线",
            "reason_detail": f"大规模质量门未通过：实验策略按时返回，但没有超过 stable baseline 的组合搜索和局部改进链；本轮画像为 {tasks} 任务、{couriers} 骑手、{rows} 行候选。",
            "rollback_label": "回退到 large baseline",
        }
    if regime in {"medium", "small"}:
        bundle_text = "bundle 冲突" if has_bundles else "单任务候选"
        return {
            "reason_label": f"{'中型' if regime == 'medium' else '小型'}样例试跑未优于基线",
            "reason_detail": f"{'中型' if regime == 'medium' else '小型'}样例质量门未通过：实验策略按时返回，但没有超过 stable baseline 对 {bundle_text} 的筛选；本轮画像为 {tasks} 任务、{couriers} 骑手、{rows} 行候选。",
            "rollback_label": f"回退到 {regime} baseline",
        }
    return {
        "reason_label": "质量门未通过",
        "reason_detail": "质量门未通过：实验策略按时返回，但没有优于当前 stable baseline，因此拒绝采用。",
        "rollback_label": "回退到 stable baseline",
    }


def _evolution_trial_display(reason: str, accepted: bool, case_profile: dict[str, Any] | None = None) -> dict[str, str]:
    if accepted:
        return {
            "reason_label": "试跑通过",
            "reason_detail": "试跑通过：实验策略没有造成质量回退，可进入候选池。",
            "decision_action": "系统动作：进入候选池，可供后续相似样例 replay。",
            "rollback_label": "晋升为可复用候选",
        }
    if reason == "timeout":
        reason_label = "试跑超时"
        reason_detail = "试跑超时：实验策略未在短时间沙箱窗口内返回，本轮终止试跑。"
        rollback_label = "回退：试跑超时"
    elif reason == "quality regression":
        quality_text = _case_quality_gate_text(case_profile)
        reason_label = quality_text["reason_label"]
        reason_detail = quality_text["reason_detail"]
        rollback_label = quality_text["rollback_label"]
    elif reason == "invalid output format":
        reason_label = "输出格式无效"
        reason_detail = "输出格式无效：策略返回内容不符合 propose 接口要求。"
        rollback_label = "回退：输出无效"
    elif "unsafe" in reason or "propose" in reason or "syntax error" in reason or "load error" in reason:
        reason_label = "安全门拒绝"
        reason_detail = "安全门拒绝：代码未通过 AST/import/interface 检查。"
        rollback_label = "回退：安全门拒绝"
    else:
        reason_label = "试跑拒绝"
        reason_detail = f"试跑拒绝：{reason}。"
        rollback_label = "回退到 stable baseline"
    return {
        "reason_label": reason_label,
        "reason_detail": reason_detail,
        "decision_action": "系统动作：回退到 stable baseline，solver.py 未修改。",
        "rollback_label": rollback_label,
    }


def _run_greedy(module: Any, candidates: list, all_tasks: set[str], history: list, deadline: float) -> list:
    return module._fallback_official_greedy(candidates)


def _run_single(module: Any, candidates: list, all_tasks: set[str], history: list, deadline: float) -> list:
    rows = _singles(candidates)
    return module._solve_single_task_multidispatch(rows, all_tasks) if rows else []


def _run_disjoint(mode: str) -> Callable[[Any, list, set[str], list, float], list]:
    def runner(module: Any, candidates: list, all_tasks: set[str], history: list, deadline: float) -> list:
        return module._solve_disjoint_then_multidispatch(candidates, all_tasks, mode=mode, deadline=deadline)

    return runner


def _run_pair(module: Any, candidates: list, all_tasks: set[str], history: list, deadline: float) -> list:
    return module._solve_pair_potential_matching(candidates, all_tasks, deadline, lookahead=5, flexible_initial=True)


def _run_sparse(module: Any, candidates: list, all_tasks: set[str], history: list, deadline: float) -> list:
    return module._solve_sparse_cover(candidates, all_tasks, deadline)


def _run_low_global(module: Any, candidates: list, all_tasks: set[str], history: list, deadline: float) -> list:
    return module._solve_low_global_column_search(candidates, all_tasks, deadline)


def _run_low_column(module: Any, candidates: list, all_tasks: set[str], history: list, deadline: float) -> list:
    rows = _singles(candidates)
    return module._solve_low_column_search(rows, all_tasks, deadline) if rows else []


def _run_scarce_k2(module: Any, candidates: list, all_tasks: set[str], history: list, deadline: float) -> list:
    return module._solve_scarce_k2_column_search(candidates, all_tasks, deadline)


def _run_scarce_bundle(module: Any, candidates: list, all_tasks: set[str], history: list, deadline: float) -> list:
    return module._solve_scarce_bundle_mcf_enum(candidates, all_tasks, deadline)


def _run_production(module: Any, candidates: list, all_tasks: set[str], history: list, deadline: float) -> list:
    input_text = history[0]["input_text"]
    return module.solve(input_text)


def _initial_strategies(regime: str) -> list[StrategyAttempt]:
    strategies = [
        StrategyAttempt("greedy_baseline", "贪心基线", "先用最快贪心获得可行基线。", _run_greedy, 0.1),
        StrategyAttempt("single_multidispatch", "单任务多派", "尝试只用单任务行做多骑手派单。", _run_single, 0.2),
        StrategyAttempt("disjoint_gain", "启发式 Gain", "按边际收益构造互斥任务组。", _run_disjoint("gain"), 0.45),
    ]
    if regime in {"large", "medium", "small"}:
        strategies.append(StrategyAttempt("pair_matching", "Pair Matching", "当前场景包含 bundle，优先尝试二元组匹配。", _run_pair, 0.65))
    if regime in {"scarce", "low-willingness"}:
        strategies.append(StrategyAttempt("sparse_cover", "稀疏覆盖", "资源紧张或低意愿时先找高收益覆盖。", _run_sparse, 0.55))
    return strategies


def _adaptive_strategies(regime: str, best_name: str | None, best_coverage: int, total_tasks: int) -> tuple[str, list[StrategyAttempt]]:
    if regime == "low-willingness":
        return (
            "发现低意愿场景，下一轮转向低意愿专用 column search，避免继续堆叠普通贪心。",
            [
                StrategyAttempt("low_global_column", "低意愿全局列搜索", "为低接受率 case 构造全局候选列。", _run_low_global, 0.7),
                StrategyAttempt("low_single_column", "低意愿单列搜索", "从单任务候选中寻找更稳的多派结构。", _run_low_column, 0.6),
            ],
        )
    if regime == "scarce":
        reason = "发现骑手稀缺，下一轮转向 scarce 专用 K2/Bundle 搜索，并允许少量未覆盖以降低期望成本。"
        return (
            reason,
            [
                StrategyAttempt("scarce_k2_column", "Scarce K2 Column", "在骑手稀缺时搜索二任务组合列。", _run_scarce_k2, 0.7),
                StrategyAttempt("scarce_bundle_mcf", "Scarce Bundle MCF", "用小规模流模型重组稀缺骑手 bundle。", _run_scarce_bundle, 0.8),
            ],
        )
    if best_coverage < total_tasks:
        return (
            "当前最优解未完全覆盖任务，下一轮转向 sparse cover 和 pair matching 提升覆盖。",
            [
                StrategyAttempt("sparse_cover", "稀疏覆盖", "补足未覆盖任务，同时保留正收益组。", _run_sparse, 0.55),
                StrategyAttempt("pair_matching", "Pair Matching", "用二元匹配补充普通启发式遗漏。", _run_pair, 0.65),
            ],
        )
    return (
        f"当前最优来自 {best_name or 'baseline'} 且覆盖完整，下一轮调用生产级求解器做综合搜索与局部改进。",
        [StrategyAttempt("production_solver", "生产级综合求解器", "调用 solver.py 中完整 10 秒内 anytime 搜索链。", _run_production, 8.7)],
    )


def run_agent(
    input_text: str,
    case_id: str = "custom",
    budget_s: float = 10.0,
    observer: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    deadline = started + max(1.0, budget_s)
    candidates, all_tasks = parse_candidates(input_text)
    module = load_solver(SOLVER_PATH)
    regime = infer_regime(candidates, all_tasks)
    features = {
        "tasks": len(all_tasks),
        "couriers": len({row[2] for row in candidates}),
        "rows": len(candidates),
        "avg_willingness": round(sum(row[4] for row in candidates) / len(candidates), 6) if candidates else 0.0,
        "has_bundles": any(len(row[1]) > 1 for row in candidates),
    }
    case_profile = {"regime": regime, **features}

    context = [{"input_text": input_text}]
    rounds: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []

    def emit(event: dict[str, Any]) -> None:
        event = {"time_s": round(time.monotonic() - started, 3), **event}
        events.append(event)
        if observer is not None:
            observer(event)

    def evolution_helpers() -> dict[str, Any]:
        return {
            "fallback_greedy": module._fallback_official_greedy,
            "time_left": lambda target_deadline: max(0.0, target_deadline - time.monotonic()),
        }

    evolution = EvolutionManager(EVOLUTION_ROOT)

    emit({"type": "perception", "message": f"识别为 {regime} 场景", "features": features})
    emit(
        {
            "type": "critic_policy",
            "message": "Critic 只向页面输出接受/拒绝判断；内部排序信号不作为展示结论。",
        }
    )
    trusted = evolution.trusted_strategies(regime, case_profile)
    if trusted:
        emit(
            {
                "type": "evolution_recall",
                "message": f"从 Evolution Memory 检索到 {len(trusted)} 个相似历史策略，Planner 会优先复用最相近候选。",
                "strategies": [item["strategy_id"] for item in trusted[:3]],
                "similarity": [item.get("similarity", 0.0) for item in trusted[:3]],
            }
        )
    generated_strategy = evolution.generate_strategy(regime, f"run_agent:{case_id}:best-so-far experiment", case_profile)
    emit(
        {
            "type": "evolution_generate",
            "message": f"生成实验策略 {generated_strategy.strategy_id}，先进入实验轨道，不修改 solver.py。",
            "strategy_id": generated_strategy.strategy_id,
        }
    )
    safety = evolution.safety_check(generated_strategy.path, generated_strategy.strategy_id)
    emit(
        {
            "type": "evolution_validate",
            "message": f"安全门禁 {'通过' if safety.passed else '拒绝'}：{safety.reason}。",
            "strategy_id": generated_strategy.strategy_id,
            "passed": safety.passed,
        }
    )
    best_solution: list[tuple[str, list[str]]] = []
    best_record: dict[str, Any] | None = None
    best_strategy: str | None = None

    strategy_rounds: list[tuple[str, list[StrategyAttempt]]] = [
        ("initial diverse exploration", _initial_strategies(regime))
    ]
    adaptive_added = False
    round_index = 0
    while strategy_rounds and time.monotonic() < deadline - 0.2 and round_index < 3:
        round_index += 1
        reason, strategies = strategy_rounds.pop(0)
        round_payload = {"round": round_index, "reason": reason, "strategies": []}
        emit(
            {
                "type": "round_start",
                "round": round_index,
                "message": reason,
                "strategies": [strategy.name for strategy in strategies],
            }
        )
        for strategy in strategies:
            if time.monotonic() >= deadline - 0.35:
                emit({"type": "budget", "message": "接近时间限制，停止继续尝试新策略。"})
                break
            if strategy.name == "production_solver" and time.monotonic() > started + 1.5 and regime == "low-willingness":
                emit({"type": "budget", "message": "低意愿场景已接近生产求解器风险窗口，跳过完整求解器以守住 10 秒。"})
                continue
            attempt_started = time.monotonic()
            emit(
                {
                    "type": "attempt_start",
                    "round": round_index,
                    "strategy": strategy.name,
                    "label": strategy.label,
                    "message": strategy.reason,
                    "time_slice_s": strategy.time_slice_s,
                }
            )
            try:
                remaining = max(0.05, deadline - time.monotonic() - 0.2)
                local_deadline = time.monotonic() + min(strategy.time_slice_s, remaining)
                solution = strategy.runner(module, candidates, all_tasks, context, local_deadline)
                record = _solution_record(module, solution, candidates, all_tasks)
                error = None
            except Exception as exc:  # demo controller must keep the loop alive.
                solution = []
                record = {
                    "local_cost": float("inf"),
                    "valid": False,
                    "covered_tasks": 0,
                    "total_tasks": len(all_tasks),
                    "groups": 0,
                    "used_couriers": 0,
                    "uncovered_tasks": sorted(all_tasks),
                    "riders_per_group": {},
                    "tasks_per_group": {},
                    "invalid_reasons": [str(exc)],
                }
                error = str(exc)
            elapsed_ms = round((time.monotonic() - attempt_started) * 1000, 3)
            accepted = bool(record["valid"]) and (
                best_record is None or record["local_cost"] < best_record["local_cost"] - 1e-9
            )
            if accepted:
                best_solution = solution
                best_record = record
                best_strategy = strategy.name
            attempt_payload = {
                "name": strategy.name,
                "label": strategy.label,
                "reason": strategy.reason,
                "local_cost": record["local_cost"],
                "valid": record["valid"],
                "covered_tasks": record["covered_tasks"],
                "total_tasks": record["total_tasks"],
                "groups": record["groups"],
                "elapsed_ms": elapsed_ms,
                "accepted": accepted,
                "error": error,
            }
            round_payload["strategies"].append(attempt_payload)
            emit(
                {
                    "type": "attempt_result",
                    "round": round_index,
                    "strategy": strategy.name,
                    "label": strategy.label,
                    "local_cost": record["local_cost"],
                    "accepted": accepted,
                    "coverage": f"{record['covered_tasks']}/{record['total_tasks']}",
                    "elapsed_ms": elapsed_ms,
                    "valid": record["valid"],
                }
            )
            if accepted:
                emit(
                    {
                        "type": "best_update",
                        "strategy": strategy.name,
                        "message": f"保留 {strategy.label} 为当前最优。",
                        "local_cost": record["local_cost"],
                        "coverage": f"{record['covered_tasks']}/{record['total_tasks']}",
                    }
                )
        rounds.append(round_payload)
        if not adaptive_added and best_record is not None:
            adaptive_added = True
            if safety.passed:
                baseline_cost = float(best_record["local_cost"])
                trial_budget_s = min(0.15, max(0.02, deadline - time.monotonic() - 0.25))
                outcome = evolution.run_generated_strategy(
                    generated_strategy,
                    candidates,
                    all_tasks,
                    deadline_s=trial_budget_s,
                    helpers=evolution_helpers(),
                    baseline_cost=baseline_cost,
                    score_fn=lambda solution: _score(module, solution, candidates, all_tasks),
                    summarize_fn=lambda solution, cost: summarize_solution(solution, candidates, all_tasks, cost),
                    case_profile=case_profile,
                )
                trial_display = _evolution_trial_display(outcome.reason, outcome.accepted, case_profile)
                emit(
                    {
                        "type": "evolution_trial",
                        "message": f"实验策略 {outcome.strategy_id} {outcome.decision}：{trial_display['reason_detail']} {trial_display['decision_action']}",
                        "strategy_id": outcome.strategy_id,
                        "decision": outcome.decision,
                        "accepted": outcome.accepted,
                        "reason": outcome.reason,
                        "elapsed_ms": outcome.elapsed_ms,
                        "trial_budget_ms": round(trial_budget_s * 1000.0, 3),
                        **trial_display,
                    }
                )
                if outcome.accepted:
                    emit(
                        {
                            "type": "evolution_promote",
                            "message": f"实验策略 {outcome.strategy_id} 进入候选记忆；Planner 可在后续轮次复用。",
                            "strategy_id": outcome.strategy_id,
                            "decision": "promote",
                        }
                    )
                else:
                    emit(
                        {
                            "type": "evolution_rollback",
                            "message": f"实验策略 {outcome.strategy_id} 已回退到 stable baseline；solver.py 未被修改。",
                            "strategy_id": outcome.strategy_id,
                            "decision": "rollback",
                            "decision_action": trial_display["decision_action"],
                            "rollback_label": trial_display["rollback_label"],
                        }
                    )
                if outcome.accepted and outcome.solution:
                    generated_record = _solution_record(module, outcome.solution, candidates, all_tasks)
                    if bool(generated_record["valid"]) and generated_record["local_cost"] < best_record["local_cost"] - 1e-9:
                        best_solution = outcome.solution
                        best_record = generated_record
                        best_strategy = outcome.strategy_id
                        emit(
                            {
                                "type": "best_update",
                                "strategy": outcome.strategy_id,
                                "message": f"生成策略 {outcome.strategy_id} 被 Critic 接受为新的 best-so-far。",
                            }
                        )
            for item in trusted[:2]:
                if time.monotonic() >= deadline - 0.35:
                    break
                strategy_path = Path(str(item.get("file", "")))
                remembered = GeneratedStrategy(str(item["strategy_id"]), strategy_path, regime, "evolution-memory")
                outcome = evolution.run_generated_strategy(
                    remembered,
                    candidates,
                    all_tasks,
                    deadline_s=min(0.12, max(0.02, deadline - time.monotonic() - 0.25)),
                    helpers=evolution_helpers(),
                    baseline_cost=float(best_record["local_cost"]),
                    score_fn=lambda solution: _score(module, solution, candidates, all_tasks),
                    summarize_fn=lambda solution, cost: summarize_solution(solution, candidates, all_tasks, cost),
                    case_profile=case_profile,
                )
                emit(
                    {
                        "type": "evolution_replay",
                        "message": f"复用相似历史策略 {outcome.strategy_id}：{outcome.decision}，{outcome.reason}。",
                        "strategy_id": outcome.strategy_id,
                        "decision": outcome.decision,
                        "accepted": outcome.accepted,
                        "similarity": item.get("similarity", 0.0),
                    }
                )
                if outcome.accepted:
                    emit(
                        {
                            "type": "evolution_promote",
                            "message": f"历史策略 {outcome.strategy_id} 通过本轮复核，继续保留在候选记忆。",
                            "strategy_id": outcome.strategy_id,
                            "decision": "promote",
                        }
                    )
                    if outcome.solution:
                        replay_record = _solution_record(module, outcome.solution, candidates, all_tasks)
                        if bool(replay_record["valid"]) and replay_record["local_cost"] < best_record["local_cost"] - 1e-9:
                            best_solution = outcome.solution
                            best_record = replay_record
                            best_strategy = outcome.strategy_id
                            emit(
                                {
                                    "type": "best_update",
                                    "strategy": outcome.strategy_id,
                                    "message": f"历史生成策略 {outcome.strategy_id} 被 Critic 接受为新的 best-so-far。",
                                }
                            )
                else:
                    emit(
                        {
                            "type": "evolution_rollback",
                            "message": f"历史策略 {outcome.strategy_id} 本轮未通过，回退到 stable baseline。",
                            "strategy_id": outcome.strategy_id,
                            "decision": "rollback",
                        }
                    )
            next_reason, next_strategies = _adaptive_strategies(
                regime,
                best_strategy,
                int(best_record["covered_tasks"]),
                int(best_record["total_tasks"]),
            )
            strategy_rounds.append((next_reason, next_strategies))
            emit({"type": "adapt", "message": next_reason})

    if best_record is None:
        best_solution = module.solve(input_text)
        best_record = _solution_record(module, best_solution, candidates, all_tasks)
        best_strategy = "production_solver"
        emit({"type": "fallback", "message": "所有策略失败，回退到生产级 solver.py。"})

    best = {"strategy": best_strategy, **best_record}
    emit(
        {
            "type": "final",
            "message": "Agent 输出 best-so-far 最终方案。",
            "strategy": best_strategy,
            "local_cost": best_record["local_cost"],
            "coverage": f"{best_record['covered_tasks']}/{best_record['total_tasks']}",
        }
    )
    wall_time_s = round(time.monotonic() - started, 6)
    return {
        "status": "ok",
        "case_id": case_id,
        "regime": regime,
        "wall_time_s": wall_time_s,
        "budget_s": budget_s,
        "features": features,
        "evolution": {
            "memory_path": str(evolution.memory_path),
            "registry_path": str(evolution.registry_path),
            "generated_strategy": generated_strategy.strategy_id,
            "trusted_recalled": [item["strategy_id"] for item in trusted[:3]],
            "trusted_details": [
                {
                    "strategy_id": item["strategy_id"],
                    "similarity": item.get("similarity", 0.0),
                    "target_regime": item.get("target_regime"),
                }
                for item in trusted[:3]
            ],
            "case_profile": case_profile,
            "mode": "experimental-track-no-solver-mutation",
        },
        "critic_policy": {
            "internal_signal": "The ranking signal is internal to the controller and hidden from the web demo.",
            "presentation_rule": "The web demo only presents agent decisions and tool flow.",
        },
        "review_alignment": _review_alignment_report(rounds, events, best, wall_time_s, budget_s),
        "best": best,
        "rounds": rounds,
        "events": events,
        "solution": best_solution,
    }


def run_case_agent(
    case_path: Path,
    case_id: str,
    budget_s: float = 10.0,
    observer: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    return run_agent(case_path.read_text(encoding="utf-8"), case_id=case_id, budget_s=budget_s, observer=observer)
