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
        name="large_seed301",
        kind="real",
        description="Existing real benchmark-style input retained for the web demo.",
        relative_path=f"{DATA_DIR_NAME}/large_seed301.txt",
    ),
    "tiny_seed42": SampleCase(
        case_id="tiny_seed42",
        name="tiny_seed42",
        kind="synthetic demo",
        description="Tiny explainable case with a small set of single and bundle choices.",
        relative_path=f"web_agent_demo/{GENERATED_CASE_DIR}/tiny_seed42.txt",
    ),
    "small_seed100": SampleCase(
        case_id="small_seed100",
        name="small_seed100",
        kind="synthetic demo",
        description="Small dense case with ordinary rider availability and many alternatives.",
        relative_path=f"web_agent_demo/{GENERATED_CASE_DIR}/small_seed100.txt",
    ),
    "medium_seed201": SampleCase(
        case_id="medium_seed201",
        name="medium_seed201",
        kind="synthetic demo",
        description="Medium case emphasizing bundle and combination tradeoffs.",
        relative_path=f"web_agent_demo/{GENERATED_CASE_DIR}/medium_seed201.txt",
    ),
    "medium_seed202": SampleCase(
        case_id="medium_seed202",
        name="medium_seed202",
        kind="synthetic demo",
        description="Medium sparse-willingness case with fewer viable alternatives per task.",
        relative_path=f"web_agent_demo/{GENERATED_CASE_DIR}/medium_seed202.txt",
    ),
    "medium_seed203": SampleCase(
        case_id="medium_seed203",
        name="medium_seed203",
        kind="synthetic demo",
        description="Medium case where repeated high-quality couriers create conflict risk.",
        relative_path=f"web_agent_demo/{GENERATED_CASE_DIR}/medium_seed203.txt",
    ),
    "large_seed302": SampleCase(
        case_id="large_seed302",
        name="large_seed302",
        kind="synthetic demo",
        description="Large synthetic pressure case for web-agent stress demonstrations.",
        relative_path=f"web_agent_demo/{GENERATED_CASE_DIR}/large_seed302.txt",
    ),
    "scarce_couriers_seed401": SampleCase(
        case_id="scarce_couriers_seed401",
        name="scarce_couriers_seed401",
        kind="synthetic demo",
        description="Courier-scarce case where bundle coverage and reuse avoidance dominate.",
        relative_path=f"web_agent_demo/{GENERATED_CASE_DIR}/scarce_couriers_seed401.txt",
    ),
    "low_willingness_seed501": SampleCase(
        case_id="low_willingness_seed501",
        name="low_willingness_seed501",
        kind="synthetic demo",
        description="Low-willingness case for showing risk-aware assignment behavior.",
        relative_path=f"web_agent_demo/{GENERATED_CASE_DIR}/low_willingness_seed501.txt",
    ),
    "high_noise_seed601": SampleCase(
        case_id="high_noise_seed601",
        name="high_noise_seed601",
        kind="synthetic demo",
        description="Noisy quality/willingness case with deliberately uneven signals.",
        relative_path=f"web_agent_demo/{GENERATED_CASE_DIR}/high_noise_seed601.txt",
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
