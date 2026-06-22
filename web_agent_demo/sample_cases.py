from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


DATA_DIR_NAME = "data/official_cases"
GENERATED_CASE_DIR = "generated_cases"
HEADER = "task_id_list\tcourier_id\ttotal_score\twillingness"


@dataclass(frozen=True)
class SampleCase:
    """Import-friendly descriptor for web demo case pickers."""

    case_id: str
    name: str
    kind: str
    description: str
    relative_path: str
    scenario_type: str = "generic"
    risk_tags: tuple[str, ...] = ()
    rows_hint: int | None = None


@dataclass(frozen=True)
class SyntheticSpec:
    case_id: str
    seed: int
    tasks: int
    couriers: int
    single_density: float
    bundle_density: float
    willingness_profile: str
    score_profile: str


SYNTHETIC_SPECS: tuple[SyntheticSpec, ...] = (
    SyntheticSpec("tiny_seed42", 42, 6, 10, 0.62, 0.34, "normal", "tiny"),
    SyntheticSpec("small_seed100", 100, 12, 25, 0.48, 0.26, "normal", "dense"),
    SyntheticSpec("medium_seed201", 201, 24, 50, 0.30, 0.38, "normal", "bundle"),
    SyntheticSpec("medium_seed202", 202, 24, 55, 0.18, 0.16, "sparse", "sparse"),
    SyntheticSpec("medium_seed203", 203, 24, 42, 0.26, 0.30, "normal", "repeat_risk"),
    SyntheticSpec("large_seed302", 302, 40, 80, 0.25, 0.28, "normal", "large"),
    SyntheticSpec("scarce_couriers_seed401", 401, 30, 18, 0.42, 0.42, "normal", "scarce"),
    SyntheticSpec("low_willingness_seed501", 501, 30, 60, 0.30, 0.26, "low", "low_willingness"),
    SyntheticSpec("high_noise_seed601", 601, 30, 60, 0.34, 0.32, "noisy", "high_noise"),
)


SAMPLE_CASES: dict[str, SampleCase] = {
    "large_seed301": SampleCase(
        case_id="large_seed301",
        name="官方大规模候选调度",
        kind="real",
        description="官方提供的大规模候选输入，用于观察 portfolio routing、当前最优维护和安全回退。",
        relative_path=f"{DATA_DIR_NAME}/large_seed301.txt",
        scenario_type="large_peak",
        risk_tags=("候选行多", "合单密集", "预算压力"),
    ),
    "tiny_seed42": SampleCase(
        case_id="tiny_seed42",
        name="Tiny 回归调试样例",
        kind="synthetic demo",
        description="小样例便于逐条检查策略接受、拒绝和任务组解释。",
        relative_path=f"web_agent_demo/{GENERATED_CASE_DIR}/tiny_seed42.txt",
        scenario_type="tiny_debug",
        risk_tags=("可解释", "回归测试"),
    ),
    "small_seed100": SampleCase(
        case_id="small_seed100",
        name="小规模密集候选调度",
        kind="synthetic demo",
        description="普通供给下的小规模密集候选，用于验证快速基线和候选表展示。",
        relative_path=f"web_agent_demo/{GENERATED_CASE_DIR}/small_seed100.txt",
        scenario_type="small_dense",
        risk_tags=("候选较密", "基线对比"),
    ),
    "medium_seed201": SampleCase(
        case_id="medium_seed201",
        name="中型合单机会评估",
        kind="synthetic demo",
        description="中型合单结构明显，用于观察 pair matching、bundle 取舍和最终方案来源。",
        relative_path=f"web_agent_demo/{GENERATED_CASE_DIR}/medium_seed201.txt",
        scenario_type="medium_bundle",
        risk_tags=("合单机会", "组合取舍"),
    ),
    "medium_seed202": SampleCase(
        case_id="medium_seed202",
        name="中型稀疏候选覆盖",
        kind="synthetic demo",
        description="可行候选较少，用于验证 sparse cover 和覆盖不足时的控制器决策。",
        relative_path=f"web_agent_demo/{GENERATED_CASE_DIR}/medium_seed202.txt",
        scenario_type="medium_sparse",
        risk_tags=("候选稀疏", "覆盖风险"),
    ),
    "medium_seed203": SampleCase(
        case_id="medium_seed203",
        name="骑手冲突风险样例",
        kind="synthetic demo",
        description="高质量骑手重复出现，适合检查骑手冲突、拒绝原因和 best-so-far 更新。",
        relative_path=f"web_agent_demo/{GENERATED_CASE_DIR}/medium_seed203.txt",
        scenario_type="medium_conflict",
        risk_tags=("骑手冲突", "重复高质量候选"),
    ),
    "large_seed302": SampleCase(
        case_id="large_seed302",
        name="大规模压力测试样例",
        kind="synthetic demo",
        description="大规模合成压力样例，用于检查运行预算、事件流和综合求解链稳定性。",
        relative_path=f"web_agent_demo/{GENERATED_CASE_DIR}/large_seed302.txt",
        scenario_type="large_pressure",
        risk_tags=("候选行多", "预算压力"),
    ),
    "scarce_couriers_seed401": SampleCase(
        case_id="scarce_couriers_seed401",
        name="骑手稀缺商圈",
        kind="synthetic demo",
        description="骑手供给少于调度压力，重点观察稀缺骑手策略、合单和资源占用。",
        relative_path=f"web_agent_demo/{GENERATED_CASE_DIR}/scarce_couriers_seed401.txt",
        scenario_type="scarce_couriers",
        risk_tags=("骑手稀缺", "合单取舍", "资源占用"),
    ),
    "low_willingness_seed501": SampleCase(
        case_id="low_willingness_seed501",
        name="雨天低接单意愿",
        kind="synthetic demo",
        description="整体接单意愿偏低，用于观察低意愿搜索、质量门和无人接单风险控制。",
        relative_path=f"web_agent_demo/{GENERATED_CASE_DIR}/low_willingness_seed501.txt",
        scenario_type="low_willingness",
        risk_tags=("低接单意愿", "无人接单风险"),
    ),
    "high_noise_seed601": SampleCase(
        case_id="high_noise_seed601",
        name="高噪声候选质量样例",
        kind="synthetic demo",
        description="成本和意愿信号更不均匀，用于检查 Critic 接受/拒绝和候选稳定性。",
        relative_path=f"web_agent_demo/{GENERATED_CASE_DIR}/high_noise_seed601.txt",
        scenario_type="high_noise",
        risk_tags=("信号噪声", "候选稳定性"),
    ),
}


def ensure_sample_cases(base_dir: str | Path) -> dict[str, Path]:
    """Create deterministic synthetic demo files and return all sample paths."""

    root = Path(base_dir)
    generated_dir = root / "web_agent_demo" / GENERATED_CASE_DIR
    generated_dir.mkdir(parents=True, exist_ok=True)

    paths: dict[str, Path] = {}
    for case_id, sample in SAMPLE_CASES.items():
        path = root / sample.relative_path
        if case_id == "large_seed301":
            paths[case_id] = path
            continue
        spec = _spec_by_case_id(case_id)
        if not path.exists():
            path.write_text(_render_case(spec), encoding="utf-8")
        paths[case_id] = path
    return paths


def _spec_by_case_id(case_id: str) -> SyntheticSpec:
    for spec in SYNTHETIC_SPECS:
        if spec.case_id == case_id:
            return spec
    raise KeyError(case_id)


def _render_case(spec: SyntheticSpec) -> str:
    rng = random.Random(spec.seed)
    tasks = [f"T{i:04d}" for i in range(spec.tasks)]
    couriers = [f"C{i:03d}" for i in range(spec.couriers)]
    rows: dict[tuple[str, str], tuple[str, str, float, float]] = {}

    def add(task_ids: tuple[str, ...], courier: str, score: float, willingness: float) -> None:
        task_key = ",".join(task_ids)
        rows[(task_key, courier)] = (
            task_key,
            courier,
            round(max(8.0, min(100.0, score)), 3),
            round(max(0.012, min(0.965, willingness)), 4),
        )

    single_bias = _profile_functions(spec)[0]
    willingness_fn = _profile_functions(spec)[1]

    for task_index, task_id in enumerate(tasks):
        mandatory = _mandatory_couriers(task_index, couriers, spec)
        for courier in mandatory:
            add((task_id,), courier, _single_score(rng, task_index, courier, single_bias), willingness_fn(rng, task_index, courier, 1))
        for courier in couriers:
            if courier in mandatory:
                continue
            if rng.random() < spec.single_density:
                add((task_id,), courier, _single_score(rng, task_index, courier, single_bias), willingness_fn(rng, task_index, courier, 1))

    for task_index, task_id in enumerate(tasks):
        next_task = tasks[(task_index + 1) % len(tasks)]
        if task_id < next_task:
            _add_bundle_rows(add, rng, spec, (task_id, next_task), couriers, task_index, willingness_fn)

    for task_index in range(0, len(tasks) - 2, 3):
        if spec.score_profile in {"bundle", "scarce", "large", "high_noise"}:
            task_ids = (tasks[task_index], tasks[task_index + 1], tasks[task_index + 2])
            _add_bundle_rows(add, rng, spec, task_ids, couriers, task_index, willingness_fn, scale=1.18)

    ordered = sorted(rows.values(), key=lambda row: (_task_sort_key(row[0]), row[1]))
    body = "\n".join(f"{task_key}\t{courier}\t{score:.3f}\t{willingness:.4f}" for task_key, courier, score, willingness in ordered)
    return f"{HEADER}\n{body}\n"


def _profile_functions(spec: SyntheticSpec) -> tuple[Callable[[int, str], float], Callable[[random.Random, int, str, int], float]]:
    favored = {f"C{i:03d}" for i in range(min(8, spec.couriers))}

    def score_bias(task_index: int, courier: str) -> float:
        if spec.score_profile == "repeat_risk" and courier in favored:
            return -18.0 + (task_index % 4) * 1.8
        if spec.score_profile == "sparse":
            return 4.0 if task_index % 5 else -6.0
        if spec.score_profile == "scarce":
            return -8.0 if int(courier[1:]) % 3 == task_index % 3 else 5.0
        if spec.score_profile == "high_noise":
            return -12.0 if (task_index + int(courier[1:])) % 7 == 0 else 6.0
        if spec.score_profile == "bundle":
            return -3.0 if task_index % 4 in {1, 2} else 3.0
        return 0.0

    def willingness(rng: random.Random, task_index: int, courier: str, size: int) -> float:
        if spec.willingness_profile == "low":
            base = rng.uniform(0.045, 0.235)
            return base + (0.018 if size > 1 else 0.0)
        if spec.willingness_profile == "sparse":
            base = rng.uniform(0.035, 0.30)
            return base + (0.28 if (task_index + int(courier[1:])) % 11 == 0 else 0.0)
        if spec.willingness_profile == "noisy":
            return rng.uniform(0.045, 0.94) if rng.random() < 0.56 else rng.uniform(0.18, 0.64)
        base = rng.uniform(0.08, 0.82)
        if spec.score_profile == "repeat_risk" and courier in favored:
            base += 0.08
        if spec.score_profile == "scarce":
            base += 0.10 if size > 1 else 0.0
        return base

    return score_bias, willingness


def _mandatory_couriers(task_index: int, couriers: list[str], spec: SyntheticSpec) -> set[str]:
    needed = 2 if spec.willingness_profile == "sparse" else 3
    if spec.score_profile == "repeat_risk":
        return set(couriers[: min(needed + 2, len(couriers))])
    start = (task_index * 5 + spec.seed) % len(couriers)
    return {couriers[(start + offset) % len(couriers)] for offset in range(min(needed, len(couriers)))}


def _single_score(rng: random.Random, task_index: int, courier: str, bias_fn: Callable[[int, str], float]) -> float:
    courier_num = int(courier[1:])
    locality = abs((task_index * 7 + 3) % 29 - (courier_num * 5) % 29)
    return 28.0 + locality * 1.7 + rng.uniform(0.0, 25.0) + bias_fn(task_index, courier)


def _add_bundle_rows(
    add: Callable[[tuple[str, ...], str, float, float], None],
    rng: random.Random,
    spec: SyntheticSpec,
    task_ids: tuple[str, ...],
    couriers: list[str],
    task_index: int,
    willingness_fn: Callable[[random.Random, int, str, int], float],
    scale: float = 1.0,
) -> None:
    bundle_slots = max(2, int(len(couriers) * spec.bundle_density / max(1, len(task_ids))))
    if spec.score_profile == "repeat_risk":
        candidates = couriers[: min(len(couriers), bundle_slots + 6)]
    else:
        start = (task_index * 7 + spec.seed) % len(couriers)
        candidates = [couriers[(start + offset * 3) % len(couriers)] for offset in range(min(len(couriers), bundle_slots + 4))]
    for courier in candidates:
        if rng.random() <= spec.bundle_density or courier in candidates[:2]:
            raw = 18.0 * len(task_ids) * scale + rng.uniform(8.0, 34.0)
            if spec.score_profile in {"bundle", "scarce"}:
                raw -= 7.0 * len(task_ids)
            if spec.score_profile == "high_noise" and rng.random() < 0.35:
                raw += rng.uniform(-24.0, 30.0)
            add(task_ids, courier, raw, willingness_fn(rng, task_index, courier, len(task_ids)))


def _task_sort_key(task_key: str) -> tuple[int, str]:
    first = task_key.split(",", 1)[0]
    return (int(first[1:]) if first.startswith("T") and first[1:].isdigit() else 0, task_key)
