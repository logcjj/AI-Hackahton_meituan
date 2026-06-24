from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import threading
import traceback
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autosolver_agent.system import get_agent_blueprint, run_case_agent as _run_case_agent
from tools.agent_trace_demo import parse_candidates
from web_agent_demo.compare_engine import run_comparison
from web_agent_demo.delivery_routes_clone import autosolver_map_payload
from web_agent_demo.memory_engine import SimulationMemoryStore, rank_algorithms_with_predictor
from web_agent_demo.reasongraph_clone import autosolver_mermaid
from web_agent_demo.simulation_engine import (
    ENGINE_VERSION as SIMULATION_ENGINE_VERSION,
    SimulationControls,
    advance_simulation,
    create_simulation_session,
    scenario_catalog,
    simulation_to_dict,
)

try:
    from web_agent_demo.sample_cases import SAMPLE_CASES, ensure_sample_cases
except ImportError:  # The demo can still run before optional synthetic cases are generated.
    SAMPLE_CASES = {}
    ensure_sample_cases = None


DATA_DIR = ROOT / "data" / "official_cases"
GENERATED_CASE_DIR = ROOT / "web_agent_demo" / "generated_cases"
STATIC_DIR = ROOT / "web_agent_demo" / "static"
SIMULATION_MEMORY_ROOT = Path(os.environ.get("AUTOSOLVER_MEMORY_ROOT", ROOT / "web_agent_demo" / ".simulation_memory"))
_RUNTIME_LOCK = threading.RLock()
_SIMULATION_RUNTIME: dict[str, dict[str, object]] = {}
_COMPARE_RUNTIME: dict[str, object] = {}
CASE_FILES = {
    "large_seed301": DATA_DIR / "large_seed301.txt",
}


def _case_files() -> dict[str, Path]:
    files = dict(CASE_FILES)
    if ensure_sample_cases is not None:
        files.update(ensure_sample_cases(ROOT))
    return files


def list_cases() -> list[dict[str, object]]:
    cases = []
    for case_id, path in _case_files().items():
        if not path.exists():
            continue
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        row_count = max(0, len(lines) - (1 if lines and lines[0].startswith("task_id_list") else 0))
        sample = SAMPLE_CASES.get(case_id)
        case_type = "real provided case" if case_id == "large_seed301" else "synthetic demo case"
        scenario_name = sample.name if sample is not None else case_id
        scenario_type = sample.scenario_type if sample is not None else "generic"
        risk_tags = list(sample.risk_tags) if sample is not None else []
        operator_note = sample.description if sample is not None else "Case metadata is unavailable; using technical case id."
        source_type = "official_case" if case_id == "large_seed301" else "synthetic_demo_case"
        cases.append(
            {
                "id": case_id,
                "name": scenario_name,
                "scenario_name": scenario_name,
                "scenario_type": scenario_type,
                "risk_tags": risk_tags,
                "operator_note": operator_note,
                "source_type": source_type,
                "rows": row_count,
                "type": case_type,
            }
        )
    return cases


def run_case_agent(case_id: str, budget_s: float = 10.0, observer=None) -> dict[str, object]:
    path = _case_files().get(case_id)
    if path is None or not path.exists():
        raise ValueError(f"unknown case: {case_id}")
    return _run_case_agent(path, case_id=case_id, budget_s=budget_s, observer=observer)


def _stable_point(entity_id: str, lane: int = 0) -> tuple[float, float]:
    digest = hashlib.sha1(entity_id.encode("utf-8")).digest()
    x = 12 + digest[0] / 255 * 74
    y = 16 + digest[1] / 255 * 68
    if lane:
        x = max(7, min(92, x + (lane % 3 - 1) * 9))
        y = max(9, min(90, y + ((lane // 3) % 3 - 1) * 7))
    return round(x, 1), round(y, 1)


def _unit_hash(*parts: object, salt: str = "") -> float:
    digest = hashlib.sha1(("|".join(str(part) for part in parts) + "|" + salt).encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") / 0xFFFFFFFF


def _clamp_point(x: float, y: float) -> tuple[float, float]:
    return round(max(7.5, min(92.5, x)), 1), round(max(7.5, min(92.5, y)), 1)


_DISPATCH_ROADS = [
    # Stable simulated delivery map: ring roads, arterials, feeders and service
    # alleys are predeclared so anchors and final dispatch lines share one graph.
    ((21.0, 66.0), (26.0, 55.0), (31.0, 45.0), (43.0, 36.0), (55.0, 22.0), (64.0, 24.0), (70.0, 33.0), (67.0, 45.0), (59.0, 50.0), (55.0, 61.0), (47.0, 69.0), (34.0, 67.0), (24.0, 61.0)),
    ((6.0, 36.0), (24.0, 35.0), (42.0, 35.0), (60.0, 31.0), (79.0, 27.0), (96.0, 19.0)),
    ((4.0, 60.0), (22.0, 56.0), (39.0, 53.0), (58.0, 52.0), (77.0, 55.0), (96.0, 63.0)),
    ((13.0, 90.0), (27.0, 77.0), (42.0, 63.0), (58.0, 48.0), (75.0, 35.0), (95.0, 25.0)),
    ((46.0, 18.0), (52.0, 31.0), (57.0, 45.0), (58.0, 60.0), (59.0, 82.0)),
    ((70.0, 12.0), (67.0, 24.0), (70.0, 39.0), (77.0, 54.0), (90.0, 77.0)),
    ((16.0, 18.0), (31.0, 30.0), (47.0, 45.0), (64.0, 61.0), (86.0, 81.0)),
    ((74.0, 15.0), (80.0, 25.0), (87.0, 39.0), (83.0, 52.0), (77.0, 64.0)),
    ((28.0, 28.0), (40.0, 23.0), (52.0, 26.0), (63.0, 33.0), (75.0, 43.0)),
    ((19.0, 47.0), (33.0, 44.0), (45.0, 48.0), (58.0, 57.0), (72.0, 70.0)),
    ((37.0, 12.0), (36.0, 29.0), (39.0, 46.0), (42.0, 63.0), (45.0, 86.0)),
    ((55.0, 8.0), (56.0, 22.0), (54.0, 37.0), (50.0, 52.0), (47.0, 73.0)),
    ((65.0, 18.0), (58.0, 27.0), (50.0, 36.0), (41.0, 44.0), (31.0, 52.0), (22.0, 64.0)),
    ((24.0, 74.0), (35.0, 69.0), (48.0, 66.0), (63.0, 67.0), (82.0, 73.0)),
    ((12.0, 22.0), (28.0, 28.0), (44.0, 32.0), (62.0, 34.0), (83.0, 36.0)),
    ((10.0, 45.0), (26.0, 45.0), (45.0, 47.0), (64.0, 50.0), (86.0, 52.0)),
    ((14.0, 78.0), (30.0, 75.0), (50.0, 74.0), (70.0, 76.0), (90.0, 82.0)),
    ((18.0, 14.0), (22.0, 34.0), (24.0, 56.0), (28.0, 76.0)),
    ((35.0, 18.0), (37.0, 44.0), (42.0, 63.0), (45.0, 86.0)),
    ((48.0, 12.0), (49.0, 30.0), (49.0, 50.5), (48.5, 70.0)),
    ((62.0, 14.0), (64.0, 33.0), (67.5, 48.0), (67.5, 68.0), (70.0, 84.0)),
    ((78.0, 18.0), (80.0, 36.0), (78.0, 55.0), (82.0, 72.0), (88.0, 90.0)),
    ((30.0, 40.0), (48.5, 41.5), (65.5, 36.0), (83.0, 52.0)),
    ((34.5, 73.0), (46.0, 55.5), (52.0, 43.5), (59.0, 30.5), (72.0, 39.0)),
    ((41.5, 52.0), (55.5, 52.0), (61.5, 56.0), (72.5, 47.0), (87.0, 39.0)),
    ((50.0, 35.5), (55.0, 39.0), (58.0, 48.0), (72.0, 70.0)),
    ((16.0, 52.0), (24.0, 56.0), (37.0, 44.0), (45.0, 47.0), (57.0, 45.0)),
    ((23.0, 64.0), (28.0, 67.0), (34.5, 73.0), (42.0, 63.0)),
    ((52.0, 31.0), (53.5, 27.5), (59.0, 30.5), (65.5, 36.0), (75.0, 43.0)),
    ((55.0, 22.0), (52.0, 26.0), (50.0, 35.5), (52.0, 43.5), (55.5, 52.0), (58.0, 60.0)),
    ((21.0, 66.0), (27.0, 77.0), (45.0, 86.0), (59.0, 82.0), (86.0, 81.0)),
    ((70.0, 12.0), (80.0, 25.0), (87.0, 39.0), (83.0, 52.0), (77.0, 55.0)),
    ((31.0, 30.0), (43.0, 36.0), (47.0, 45.0), (57.0, 45.0), (67.0, 45.0)),
    ((39.0, 53.0), (42.0, 63.0), (47.0, 69.0), (58.0, 60.0), (64.0, 61.0)),
    ((24.0, 35.0), (37.0, 44.0), (49.0, 50.5), (58.0, 52.0), (75.0, 43.0)),
    ((60.0, 31.0), (64.0, 33.0), (70.0, 39.0), (72.5, 47.0), (77.0, 64.0)),
    ((28.0, 67.0), (41.5, 52.0), (55.0, 39.0), (64.0, 33.0), (75.0, 35.0)),
    ((45.0, 47.0), (49.0, 50.5), (55.5, 52.0), (61.5, 56.0), (67.5, 68.0)),
    ((53.5, 27.5), (58.0, 48.0), (64.0, 61.0), (82.0, 72.0)),
    ((42.0, 35.0), (48.5, 41.5), (52.0, 43.5), (58.0, 48.0), (72.0, 70.0)),
    ((67.0, 45.0), (75.0, 43.0), (78.0, 55.0), (82.0, 72.0)),
    ((24.0, 35.0), (31.0, 30.0), (36.0, 29.0), (40.0, 23.0), (46.0, 18.0)),
    ((59.0, 82.0), (67.5, 68.0), (72.0, 70.0), (77.0, 64.0), (90.0, 77.0)),
    ((43.0, 36.0), (50.0, 36.0), (56.0, 37.0), (63.0, 33.0), (70.0, 33.0)),
    ((39.0, 53.0), (46.0, 55.5), (50.0, 52.0), (55.5, 52.0), (61.5, 56.0)),
]


_SIMULATION_STRATEGIES = {
    "S1": {"name": "组合搜索 / MCF", "label": "组合搜索 / MCF", "reason": "调用 disjoint gain、pair matching、稀缺骑手列搜索与 MCF 重组策略"},
    "S2": {"name": "单任务多派", "label": "单任务多派", "reason": "调用 _solve_single_task_multidispatch，为单任务保留多个可接骑手"},
    "S3": {"name": "覆盖修复搜索", "label": "覆盖修复搜索", "reason": "调用 _solve_sparse_cover，并在低意愿或未覆盖场景做修复"},
    "S4": {"name": "贪心基线 / 兜底", "label": "贪心基线 / 兜底", "reason": "调用 greedy baseline，快速得到可行兜底方案"},
    "S5": {"name": "低意愿 / 自适应补充", "label": "低意愿 / 自适应补充", "reason": "根据 regime 与覆盖率触发 low_global_column、low_single_column 或 production_solver 补充"},
}


_SIMULATED_SCENARIO_CONFIGS = [
    {
        "id": "commerce_peak",
        "case_id": "large_seed301",
        "name": "商圈十字路口高峰",
        "scene_type": "dense_commerce",
        "center": (49.0, 42.0),
        "merchant_range": (5, 6),
        "courier_range": (11, 14),
        "willingness_base": 0.72,
        "traffic_bias": 0.66,
        "weather": "clear",
        "density_profile": "clustered",
        "strategy_cycle": ["S1", "S2", "S1", "S3", "S1", "S5", "S2", "S4", "S3", "S1"],
        "description": "路口商圈订单集中，适合验证组合搜索、MCF 和多骑手候选比较。",
    },
    {
        "id": "medium_parallel",
        "case_id": "medium_seed201",
        "name": "中型并行派单",
        "scene_type": "medium_parallel",
        "center": (43.0, 48.0),
        "merchant_range": (4, 5),
        "courier_range": (9, 12),
        "willingness_base": 0.68,
        "traffic_bias": 0.45,
        "weather": "clear",
        "density_profile": "balanced",
        "strategy_cycle": ["S2", "S2", "S2", "S4", "S2", "S3", "S2", "S1", "S5", "S2"],
        "description": "订单不完全重叠，多个骑手候选质量接近，突出单任务多派策略。",
    },
    {
        "id": "scarce_repair",
        "case_id": "scarce_couriers_seed401",
        "name": "骑手稀缺修复",
        "scene_type": "scarce_couriers",
        "center": (58.0, 50.0),
        "merchant_range": (4, 6),
        "courier_range": (7, 9),
        "willingness_base": 0.58,
        "traffic_bias": 0.58,
        "weather": "clear",
        "density_profile": "scarce_spread",
        "strategy_cycle": ["S3", "S3", "S3", "S5", "S3", "S2", "S4", "S3", "S5", "S3"],
        "description": "骑手少且订单分布拉开，需要先覆盖再做修复搜索。",
    },
    {
        "id": "rain_low_willingness",
        "case_id": "low_willingness_seed501",
        "name": "雨天低接单意愿",
        "scene_type": "low_willingness",
        "center": (52.0, 46.0),
        "merchant_range": (4, 6),
        "courier_range": (10, 13),
        "willingness_base": 0.42,
        "traffic_bias": 0.74,
        "weather": "rain",
        "density_profile": "rain_clustered",
        "strategy_cycle": ["S5", "S3", "S5", "S1", "S5", "S2", "S5", "S3", "S4", "S5"],
        "description": "低意愿和雨天路况同时出现，重点验证无人接单风险控制。",
    },
    {
        "id": "offpeak_greedy",
        "case_id": "high_noise_seed601",
        "name": "低峰分散订单",
        "scene_type": "offpeak_balanced",
        "center": (46.0, 54.0),
        "merchant_range": (3, 5),
        "courier_range": (8, 11),
        "willingness_base": 0.82,
        "traffic_bias": 0.26,
        "weather": "clear",
        "density_profile": "spread",
        "strategy_cycle": ["S4", "S4", "S4", "S1", "S4", "S3", "S4", "S2", "S5", "S4"],
        "description": "低峰期订单分散且骑手充足，用于展示贪心基线也可能成为可接受方案。",
    },
    {
        "id": "event_mixed_pressure",
        "case_id": "large_seed302",
        "name": "活动混合压力",
        "scene_type": "event_mixed",
        "center": (55.0, 38.0),
        "merchant_range": (5, 6),
        "courier_range": (12, 15),
        "willingness_base": 0.61,
        "traffic_bias": 0.82,
        "weather": "event",
        "density_profile": "event_clustered",
        "strategy_cycle": ["S1", "S5", "S2", "S3", "S1", "S5", "S2", "S3", "S4", "S1"],
        "description": "活动流量导致局部拥堵，策略会在组合搜索、低意愿护栏和修复搜索之间切换。",
    },
    {
        "id": "night_foodcourt",
        "case_id": "night_foodcourt_seed701",
        "name": "夜间商圈宵夜",
        "scene_type": "night_commerce",
        "center": (50.0, 43.0),
        "merchant_range": (4, 6),
        "courier_range": (8, 11),
        "willingness_base": 0.64,
        "traffic_bias": 0.38,
        "weather": "clear",
        "density_profile": "clustered",
        "strategy_cycle": ["S1", "S2", "S5", "S1", "S4", "S2", "S1", "S3", "S5", "S1"],
        "description": "夜间宵夜订单集中但骑手供给下降，用于展示组合搜索和单任务多派的平衡。",
    },
    {
        "id": "campus_lunch_peak",
        "case_id": "campus_lunch_seed801",
        "name": "校园午高峰",
        "scene_type": "campus_lunch",
        "center": (42.0, 51.0),
        "merchant_range": (5, 6),
        "courier_range": (12, 14),
        "willingness_base": 0.76,
        "traffic_bias": 0.52,
        "weather": "clear",
        "density_profile": "balanced",
        "strategy_cycle": ["S2", "S1", "S2", "S4", "S2", "S5", "S1", "S2", "S3", "S2"],
        "description": "园区和校园午餐需求密集，多个骑手距离接近，适合展示单任务多派。",
    },
    {
        "id": "hospital_office_peak",
        "case_id": "hospital_office_seed901",
        "name": "医院写字楼午峰",
        "scene_type": "medical_office_peak",
        "center": (58.0, 46.0),
        "merchant_range": (4, 5),
        "courier_range": (9, 11),
        "willingness_base": 0.57,
        "traffic_bias": 0.69,
        "weather": "event",
        "density_profile": "event_clustered",
        "strategy_cycle": ["S5", "S3", "S2", "S5", "S1", "S3", "S5", "S2", "S4", "S5"],
        "description": "医院与写字楼周边停车和通行限制更强，重点验证低意愿护栏和覆盖修复。",
    },
    {
        "id": "congestion_reassign",
        "case_id": "congestion_reassign_seed1001",
        "name": "拥堵异常补单",
        "scene_type": "congestion_recovery",
        "center": (63.0, 58.0),
        "merchant_range": (5, 6),
        "courier_range": (7, 10),
        "willingness_base": 0.50,
        "traffic_bias": 0.88,
        "weather": "event",
        "density_profile": "scarce_spread",
        "strategy_cycle": ["S3", "S5", "S3", "S2", "S3", "S1", "S5", "S3", "S4", "S3"],
        "description": "局部拥堵叠加异常补单，需要用覆盖修复减少无人接单和超时风险。",
    },
]


def _project_to_segment(point: tuple[float, float], start: tuple[float, float], end: tuple[float, float]) -> tuple[float, tuple[float, float]]:
    px, py = point
    sx, sy = start
    ex, ey = end
    dx = ex - sx
    dy = ey - sy
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        distance_sq = (px - sx) ** 2 + (py - sy) ** 2
        return distance_sq, start
    t = max(0.0, min(1.0, ((px - sx) * dx + (py - sy) * dy) / length_sq))
    projected = (sx + t * dx, sy + t * dy)
    distance_sq = (px - projected[0]) ** 2 + (py - projected[1]) ** 2
    return distance_sq, projected


def _snap_to_dispatch_road(
    point: tuple[float, float],
    entity_id: str,
    offset_scale: float = 1.7,
    min_curb: float = 0.0,
) -> tuple[float, float]:
    """Attach simulated locations to the nearest demo road with a tiny deterministic curb offset."""

    best_distance = float("inf")
    best_point = point
    best_segment = ((0.0, 0.0), (1.0, 0.0))
    for road in _DISPATCH_ROADS:
        for start, end in zip(road, road[1:]):
            distance, projected = _project_to_segment(point, start, end)
            if distance < best_distance:
                best_distance = distance
                best_point = projected
                best_segment = (start, end)
    sx, sy = best_segment[0]
    ex, ey = best_segment[1]
    dx = ex - sx
    dy = ey - sy
    length = math.hypot(dx, dy) or 1.0
    side = -1.0 if _unit_hash(entity_id, salt="curb-side") < 0.5 else 1.0
    curb = (_unit_hash(entity_id, salt="curb-offset") - 0.5) * offset_scale
    if min_curb:
        curb = (min_curb + abs(curb)) * (1 if curb >= 0 else -1)
    return _clamp_point(best_point[0] + side * (-dy / length) * curb, best_point[1] + side * (dx / length) * curb)


def _distance_to_dispatch_road(point: tuple[float, float]) -> float:
    return _nearest_dispatch_road_projection(point)["distance"]


def _nearest_dispatch_road_projection(point: tuple[float, float]) -> dict[str, object]:
    best_distance = float("inf")
    best_point = point
    best_segment = ((0.0, 0.0), (1.0, 0.0))
    best_index = 0
    for road_index, road in enumerate(_DISPATCH_ROADS):
        for start, end in zip(road, road[1:]):
            distance, _ = _project_to_segment(point, start, end)
            if distance < best_distance:
                best_distance = distance
                _, projected = _project_to_segment(point, start, end)
                best_point = projected
                best_segment = (start, end)
                best_index = road_index
    return {
        "distance": math.sqrt(best_distance),
        "projected": best_point,
        "segment": best_segment,
        "road_id": f"R{best_index + 1:02d}",
    }


def _nearest_dispatch_road_id(point: tuple[float, float]) -> str:
    best_distance = float("inf")
    best_index = 0
    for road_index, road in enumerate(_DISPATCH_ROADS):
        for start, end in zip(road, road[1:]):
            distance, _ = _project_to_segment(point, start, end)
            if distance < best_distance:
                best_distance = distance
                best_index = road_index
    return f"R{best_index + 1:02d}"


def _push_merchant_anchor_off_road(point: tuple[float, float], anchor_id: str) -> tuple[float, float]:
    x, y = point
    for attempt in range(14):
        nearest = _nearest_dispatch_road_projection((x, y))
        if float(nearest["distance"]) >= 1.42:
            break
        projected = nearest["projected"]
        segment = nearest["segment"]
        px, py = projected
        (sx, sy), (ex, ey) = segment
        dx = ex - sx
        dy = ey - sy
        length = math.hypot(dx, dy) or 1.0
        target_curb = 2.15 + attempt * 0.28
        preferred_side = -1.0 if _unit_hash(anchor_id, attempt, salt="merchant-anchor-side") < 0.5 else 1.0
        candidates = []
        for side in (preferred_side, -preferred_side):
            candidate = _clamp_point(px + side * (-dy / length) * target_curb, py + side * (dx / length) * target_curb)
            candidates.append((candidate, _distance_to_dispatch_road(candidate)))
        x, y = max(candidates, key=lambda item: item[1])[0]
    return x, y


_MERCHANT_ANCHOR_BLUEPRINTS = [
    {"id": "MA-CBD-01", "point": (48.5, 41.5), "zone": "central_foodcourt", "tags": ["dense_commerce", "clustered", "rain_clustered", "event_clustered", "night_commerce"]},
    {"id": "MA-CBD-02", "point": (52.0, 43.5), "zone": "central_foodcourt", "tags": ["dense_commerce", "clustered", "rain_clustered", "event_clustered", "night_commerce"]},
    {"id": "MA-CBD-03", "point": (55.0, 39.0), "zone": "central_mall_edge", "tags": ["dense_commerce", "clustered", "event_mixed", "night_commerce"]},
    {"id": "MA-CBD-04", "point": (45.0, 47.0), "zone": "central_mall_edge", "tags": ["dense_commerce", "medium_parallel", "campus_lunch"]},
    {"id": "MA-CBD-05", "point": (58.0, 48.0), "zone": "office_food_street", "tags": ["dense_commerce", "clustered", "medium_parallel", "event_mixed", "medical_office_peak"]},
    {"id": "MA-CBD-06", "point": (50.0, 35.5), "zone": "office_food_street", "tags": ["dense_commerce", "clustered", "medium_parallel", "rain_clustered"]},
    {"id": "MA-RAIN-01", "point": (49.0, 50.5), "zone": "rain_sheltered_block", "tags": ["low_willingness", "rain_clustered", "medium_parallel"]},
    {"id": "MA-RAIN-02", "point": (55.5, 52.0), "zone": "rain_sheltered_block", "tags": ["low_willingness", "rain_clustered", "event_clustered"]},
    {"id": "MA-RAIN-03", "point": (46.0, 55.5), "zone": "rain_sheltered_block", "tags": ["low_willingness", "rain_clustered"]},
    {"id": "MA-MID-01", "point": (37.0, 44.0), "zone": "midtown_restaurant", "tags": ["medium_parallel", "balanced", "campus_lunch"]},
    {"id": "MA-MID-02", "point": (41.5, 52.0), "zone": "midtown_restaurant", "tags": ["medium_parallel", "balanced", "spread", "campus_lunch"]},
    {"id": "MA-MID-03", "point": (61.5, 56.0), "zone": "midtown_restaurant", "tags": ["medium_parallel", "balanced", "event_mixed", "medical_office_peak"]},
    {"id": "MA-SPR-01", "point": (28.0, 67.0), "zone": "residential_edge", "tags": ["offpeak_balanced", "spread", "scarce_spread"]},
    {"id": "MA-SPR-02", "point": (34.5, 73.0), "zone": "residential_edge", "tags": ["offpeak_balanced", "spread"]},
    {"id": "MA-SPR-03", "point": (67.5, 68.0), "zone": "residential_edge", "tags": ["offpeak_balanced", "spread", "scarce_spread"]},
    {"id": "MA-SPR-04", "point": (78.0, 55.0), "zone": "residential_edge", "tags": ["offpeak_balanced", "spread"]},
    {"id": "MA-SCA-01", "point": (64.0, 33.0), "zone": "scarce_far_cluster", "tags": ["scarce_couriers", "scarce_spread", "event_mixed", "congestion_recovery"]},
    {"id": "MA-SCA-02", "point": (72.0, 39.0), "zone": "scarce_far_cluster", "tags": ["scarce_couriers", "scarce_spread", "congestion_recovery"]},
    {"id": "MA-SCA-03", "point": (82.0, 72.0), "zone": "scarce_far_cluster", "tags": ["scarce_couriers", "scarce_spread", "spread", "congestion_recovery"]},
    {"id": "MA-SCA-04", "point": (24.0, 56.0), "zone": "scarce_far_cluster", "tags": ["scarce_couriers", "scarce_spread", "congestion_recovery"]},
    {"id": "MA-EVT-01", "point": (59.0, 30.5), "zone": "event_gate_food", "tags": ["event_mixed", "event_clustered", "dense_commerce", "medical_office_peak"]},
    {"id": "MA-EVT-02", "point": (65.5, 36.0), "zone": "event_gate_food", "tags": ["event_mixed", "event_clustered", "medical_office_peak"]},
    {"id": "MA-EVT-03", "point": (53.5, 27.5), "zone": "event_gate_food", "tags": ["event_mixed", "event_clustered", "medical_office_peak"]},
    {"id": "MA-EVT-04", "point": (72.5, 47.0), "zone": "event_gate_food", "tags": ["event_mixed", "event_clustered", "low_willingness", "medical_office_peak"]},
]


_COURIER_ANCHOR_BLUEPRINTS = [
    {"id": "CA-CBD-01", "point": (43.0, 36.0), "zone": "central_ring", "tags": ["dense_commerce", "clustered", "medium_parallel", "campus_lunch"]},
    {"id": "CA-CBD-02", "point": (55.0, 22.0), "zone": "central_ring", "tags": ["dense_commerce", "event_clustered"]},
    {"id": "CA-CBD-03", "point": (59.0, 50.0), "zone": "central_ring", "tags": ["dense_commerce", "rain_clustered"]},
    {"id": "CA-CBD-04", "point": (47.0, 45.0), "zone": "central_ring", "tags": ["dense_commerce", "medium_parallel"]},
    {"id": "CA-CBD-05", "point": (39.0, 53.0), "zone": "central_ring", "tags": ["dense_commerce", "balanced"]},
    {"id": "CA-MID-01", "point": (24.0, 35.0), "zone": "midtown_corridor", "tags": ["medium_parallel", "balanced", "spread", "campus_lunch"]},
    {"id": "CA-MID-02", "point": (42.0, 35.0), "zone": "midtown_corridor", "tags": ["medium_parallel", "balanced", "campus_lunch"]},
    {"id": "CA-MID-03", "point": (60.0, 31.0), "zone": "midtown_corridor", "tags": ["medium_parallel", "event_mixed", "medical_office_peak"]},
    {"id": "CA-MID-04", "point": (58.0, 52.0), "zone": "midtown_corridor", "tags": ["medium_parallel", "rain_clustered"]},
    {"id": "CA-MID-05", "point": (77.0, 55.0), "zone": "midtown_corridor", "tags": ["medium_parallel", "scarce_spread", "congestion_recovery"]},
    {"id": "CA-RAIN-01", "point": (52.0, 31.0), "zone": "rain_standby", "tags": ["low_willingness", "rain_clustered"]},
    {"id": "CA-RAIN-02", "point": (57.0, 45.0), "zone": "rain_standby", "tags": ["low_willingness", "rain_clustered"]},
    {"id": "CA-RAIN-03", "point": (58.0, 60.0), "zone": "rain_standby", "tags": ["low_willingness", "rain_clustered", "spread"]},
    {"id": "CA-RAIN-04", "point": (67.0, 45.0), "zone": "rain_standby", "tags": ["low_willingness", "event_clustered"]},
    {"id": "CA-RAIN-05", "point": (42.0, 63.0), "zone": "rain_standby", "tags": ["low_willingness", "rain_clustered"]},
    {"id": "CA-SPR-01", "point": (21.0, 66.0), "zone": "outer_loop", "tags": ["offpeak_balanced", "spread", "scarce_spread"]},
    {"id": "CA-SPR-02", "point": (27.0, 77.0), "zone": "outer_loop", "tags": ["offpeak_balanced", "spread"]},
    {"id": "CA-SPR-03", "point": (45.0, 86.0), "zone": "outer_loop", "tags": ["offpeak_balanced", "spread"]},
    {"id": "CA-SPR-04", "point": (59.0, 82.0), "zone": "outer_loop", "tags": ["offpeak_balanced", "scarce_spread", "congestion_recovery"]},
    {"id": "CA-SPR-05", "point": (86.0, 81.0), "zone": "outer_loop", "tags": ["offpeak_balanced", "spread", "event_mixed"]},
    {"id": "CA-SCA-01", "point": (70.0, 12.0), "zone": "scarce_remote", "tags": ["scarce_couriers", "scarce_spread", "congestion_recovery"]},
    {"id": "CA-SCA-02", "point": (80.0, 25.0), "zone": "scarce_remote", "tags": ["scarce_couriers", "event_mixed", "congestion_recovery"]},
    {"id": "CA-SCA-03", "point": (87.0, 39.0), "zone": "scarce_remote", "tags": ["scarce_couriers", "scarce_spread", "congestion_recovery"]},
    {"id": "CA-SCA-04", "point": (83.0, 52.0), "zone": "scarce_remote", "tags": ["scarce_couriers", "scarce_spread", "congestion_recovery"]},
    {"id": "CA-SCA-05", "point": (75.0, 35.0), "zone": "scarce_remote", "tags": ["scarce_couriers", "event_clustered", "medical_office_peak", "congestion_recovery"]},
    {"id": "CA-EVT-01", "point": (64.0, 61.0), "zone": "event_buffer", "tags": ["event_mixed", "event_clustered", "medical_office_peak"]},
    {"id": "CA-EVT-02", "point": (75.0, 43.0), "zone": "event_buffer", "tags": ["event_mixed", "event_clustered", "medical_office_peak"]},
    {"id": "CA-EVT-03", "point": (52.0, 26.0), "zone": "event_buffer", "tags": ["event_mixed", "dense_commerce"]},
    {"id": "CA-EVT-04", "point": (31.0, 30.0), "zone": "event_buffer", "tags": ["event_mixed", "medium_parallel"]},
    {"id": "CA-EVT-05", "point": (72.0, 70.0), "zone": "event_buffer", "tags": ["event_mixed", "low_willingness", "congestion_recovery"]},
]


def _materialize_anchor(blueprint: dict[str, object], role: str) -> dict[str, object]:
    raw_point = blueprint["point"]
    if not isinstance(raw_point, tuple):
        raw_point = tuple(raw_point)  # type: ignore[arg-type]
    if role == "merchant":
        x, y = _snap_to_dispatch_road(raw_point, str(blueprint["id"]), 0.75, min_curb=3.1)
        x, y = _push_merchant_anchor_off_road((x, y), str(blueprint["id"]))
    else:
        x, y = _snap_to_dispatch_road(raw_point, str(blueprint["id"]), 0.22, min_curb=0.03)
    point = (x, y)
    return {
        "id": str(blueprint["id"]),
        "role": role,
        "x": x,
        "y": y,
        "raw_x": round(float(raw_point[0]), 1),
        "raw_y": round(float(raw_point[1]), 1),
        "zone": str(blueprint["zone"]),
        "tags": list(blueprint["tags"]),
        "road_id": _nearest_dispatch_road_id(point),
        "curb_distance": round(_distance_to_dispatch_road(point), 2),
    }


_MERCHANT_ANCHORS = [_materialize_anchor(item, "merchant") for item in _MERCHANT_ANCHOR_BLUEPRINTS]
_COURIER_ANCHORS = [_materialize_anchor(item, "courier") for item in _COURIER_ANCHOR_BLUEPRINTS]


def _scene_anchor_tags(config: dict[str, object]) -> set[str]:
    return {
        str(config.get("id", "")),
        str(config.get("scene_type", "")),
        str(config.get("density_profile", "")),
        str(config.get("weather", "")),
    }


def _anchor_match_score(anchor: dict[str, object], config: dict[str, object]) -> int:
    anchor_tags = set(str(item) for item in anchor.get("tags", []))
    return len(anchor_tags & _scene_anchor_tags(config))


def _anchor_screen_distance(left: dict[str, object], right: dict[str, object]) -> float:
    return math.hypot((float(left["x"]) - float(right["x"])) * 7.04, (float(left["y"]) - float(right["y"])) * 3.98)


def _select_spread_courier_anchors(ranked: list[dict[str, object]], count: int, density_profile: str) -> list[dict[str, object]]:
    min_px = 56.0 if density_profile in {"clustered", "rain_clustered", "event_clustered"} else 48.0
    for threshold in (min_px, 48.0, 42.0, 36.0):
        selected: list[dict[str, object]] = []
        for anchor in ranked:
            if any(str(item["id"]) == str(anchor["id"]) for item in selected):
                continue
            if all(_anchor_screen_distance(anchor, chosen) >= threshold for chosen in selected):
                selected.append(anchor)
            if len(selected) >= count:
                return selected
    selected = []
    for anchor in ranked:
        if any(str(item["id"]) == str(anchor["id"]) for item in selected):
            continue
        selected.append(anchor)
        if len(selected) >= count:
            break
    return selected


def _select_scene_anchors(config: dict[str, object], role: str, count: int, sample_key: object) -> list[dict[str, object]]:
    anchors = _MERCHANT_ANCHORS if role == "merchant" else _COURIER_ANCHORS
    center = config.get("center", (50.0, 50.0))
    if not isinstance(center, tuple):
        center = tuple(center)  # type: ignore[arg-type]
    density_profile = str(config.get("density_profile", "balanced"))
    center_weight = -0.025 if density_profile in {"spread", "scarce_spread"} else 0.045
    matched = [anchor for anchor in anchors if _anchor_match_score(anchor, config) > 0]
    candidates = matched if len(matched) >= count else anchors
    if role == "courier":
        candidates = anchors
    ranked = sorted(
        candidates,
        key=lambda anchor: (
            -_anchor_match_score(anchor, config),
            _euclidean_distance((float(anchor["x"]), float(anchor["y"])), (float(center[0]), float(center[1]))) * center_weight
            + _unit_hash(config.get("id", ""), sample_key, anchor["id"], salt=f"{role}-anchor") * 9.0,
            str(anchor["id"]),
        ),
    )
    if role == "courier":
        return _select_spread_courier_anchors(ranked, count, density_profile)
    selected = ranked[:count]
    if len(selected) < count:
        selected_ids = {str(anchor["id"]) for anchor in selected}
        selected.extend([anchor for anchor in anchors if str(anchor["id"]) not in selected_ids][: count - len(selected)])
    return selected


def _simulated_dispatch_points(
    index: int,
    total: int,
    task_key: str,
    courier_id: str,
    score: float,
    willingness: float,
    order_count: int,
) -> tuple[tuple[float, float], tuple[float, float], list[tuple[float, float]]]:
    """Derive demo coordinates from case data when real geo coordinates are unavailable."""

    normalized_cost = max(0.0, min(1.0, score / 110.0))
    willingness = max(0.0, min(1.0, willingness))
    total = max(1, total)

    # Golden-angle placement avoids rows while keeping clusters readable around the city center.
    base_angle = index * 2.3999632297 + _unit_hash(task_key, courier_id, salt="cluster-angle") * 0.72
    ring = 0 if total <= 4 else index % 3
    radius = 8.0 + min(28.0, math.sqrt(index + 1) * 8.2) + ring * 4.6
    center_x = 50.0 + math.cos(base_angle) * radius + (_unit_hash(task_key, salt="cluster-x") - 0.5) * 9.0
    center_y = 50.0 + math.sin(base_angle) * radius * 0.78 + (_unit_hash(courier_id, salt="cluster-y") - 0.5) * 8.0
    pickup_x, pickup_y = _snap_to_dispatch_road(_clamp_point(center_x, center_y), f"{task_key}:pickup", 1.1)

    courier_angle = base_angle + math.pi + (_unit_hash(courier_id, task_key, salt="courier-angle") - 0.5) * 1.05
    courier_radius = 9.0 + (1.0 - willingness) * 17.0 + normalized_cost * 5.0
    courier_x = pickup_x + math.cos(courier_angle) * courier_radius
    courier_y = pickup_y + math.sin(courier_angle) * courier_radius * 0.86
    courier_point = _snap_to_dispatch_road(_clamp_point(courier_x, courier_y), f"{courier_id}:courier", 1.9)

    order_direction = base_angle + 0.35 + (_unit_hash(task_key, salt="orders-angle") - 0.5) * 0.8
    points = []
    for order_index in range(max(1, order_count)):
        spoke = order_index - (order_count - 1) / 2
        order_angle = order_direction + spoke * 0.42 + (_unit_hash(task_key, order_index, salt="order-jitter") - 0.5) * 0.25
        order_radius = 11.5 + normalized_cost * 13.0 + abs(spoke) * 5.2 + _unit_hash(task_key, order_index, salt="order-radius") * 5.0
        order_x = pickup_x + math.cos(order_angle) * order_radius
        order_y = pickup_y + math.sin(order_angle) * order_radius * 0.9
        points.append(_snap_to_dispatch_road(_clamp_point(order_x, order_y), f"{task_key}:order:{order_index}", 1.6))
    return (pickup_x, pickup_y), courier_point, points


def _simulated_scenario_config(scenario_id: str) -> dict[str, object]:
    for config in _SIMULATED_SCENARIO_CONFIGS:
        if config["id"] == scenario_id or config["case_id"] == scenario_id:
            return config
    return _SIMULATED_SCENARIO_CONFIGS[0]


def list_simulated_scenarios() -> list[dict[str, object]]:
    return [
        {
            "id": str(config["id"]),
            "case_id": str(config["case_id"]),
            "name": str(config["name"]),
            "scene_type": str(config["scene_type"]),
            "sample_count": 10,
            "primary_strategies": sorted(set(config["strategy_cycle"])),
            "map_style": "meituan_delivery_project_map_v3",
            "hide_road_names": True,
            "description": str(config["description"]),
        }
        for config in _SIMULATED_SCENARIO_CONFIGS
    ]


def _euclidean_distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _risk_level(willingness: float, traffic: float) -> str:
    if willingness < 0.38 or traffic > 0.78:
        return "High"
    if willingness < 0.62 or traffic > 0.55:
        return "Medium"
    return "Low"


def _road_condition(level: float) -> str:
    if level >= 0.75:
        return "heavy"
    if level >= 0.48:
        return "moderate"
    return "smooth"


def _traffic_label(condition: str) -> str:
    if condition == "heavy":
        return "拥堵"
    if condition == "moderate":
        return "缓行"
    return "畅通"


def _weather_label(weather: object) -> str:
    if weather == "rain":
        return "雨天 · 路面湿滑"
    if weather == "event":
        return "活动 · 局部管制"
    return "晴朗 · 正常履约"


def _strategy_score_model(
    config: dict[str, object],
    sample_key: object,
    sample_index: int,
    density_profile: str,
    traffic_level: float,
    merchants: list[dict[str, object]],
    couriers: list[dict[str, object]],
    candidates: list[dict[str, object]],
) -> dict[str, object]:
    """Score dispatch strategies from the generated operating features, not a fixed display order."""

    merchant_count = len(merchants)
    courier_count = len(couriers)
    avg_willingness = sum(float(item["willingness"]) for item in couriers) / max(1, courier_count)
    avg_orders = sum(float(item["order_count"]) for item in merchants) / max(1, merchant_count)
    merchant_xs = [float(item["x"]) for item in merchants]
    merchant_ys = [float(item["y"]) for item in merchants]
    spread = (max(merchant_xs) - min(merchant_xs) + max(merchant_ys) - min(merchant_ys)) / 2 if merchants else 0.0
    density_score = max(0.0, min(1.0, 1.0 - spread / 42.0))
    shortage_score = max(0.0, min(1.0, (merchant_count * 2.15 - courier_count) / max(1.0, merchant_count * 1.45)))
    risk_candidate_rate = sum(1 for item in candidates if item.get("risk") == "High") / max(1, len(candidates))

    candidate_groups: dict[str, list[dict[str, object]]] = {}
    for candidate in candidates:
        candidate_groups.setdefault(str(candidate["merchant_id"]), []).append(candidate)
    close_choice_scores = []
    best_risks = []
    for merchant_id, grouped in candidate_groups.items():
        ranked = sorted(grouped, key=lambda item: float(item["cost"]))
        if len(ranked) >= 2:
            gap = float(ranked[1]["cost"]) - float(ranked[0]["cost"])
            close_choice_scores.append(max(0.0, min(1.0, 1.0 - gap / 18.0)))
        if ranked:
            best_risks.append(1.0 if ranked[0].get("risk") == "High" else 0.55 if ranked[0].get("risk") == "Medium" else 0.0)
    candidate_competition = sum(close_choice_scores) / max(1, len(close_choice_scores))
    best_risk_pressure = sum(best_risks) / max(1, len(best_risks))

    weather = str(config.get("weather", "clear"))
    rain_or_event = 1.0 if weather in {"rain", "event"} else 0.0
    traffic_pressure = max(0.0, min(1.0, traffic_level))
    low_willingness = max(0.0, min(1.0, (0.72 - avg_willingness) / 0.45))
    offpeak_stability = max(0.0, min(1.0, (avg_willingness - 0.62) / 0.3)) * max(0.0, min(1.0, (0.58 - traffic_level) / 0.42))
    spread_score = max(0.0, min(1.0, spread / 44.0))
    sample_hint = str(config["strategy_cycle"][sample_index % len(config["strategy_cycle"])])

    signals = {
        "S1": 0.40 + density_score * 0.26 + min(1.0, (avg_orders - 1.0) * 0.9) * 0.13 + traffic_pressure * 0.08,
        "S2": 0.39 + candidate_competition * 0.27 + min(1.0, courier_count / max(1, merchant_count * 2.4)) * 0.14 + (1.0 - abs(density_score - 0.45)) * 0.08,
        "S3": 0.38 + shortage_score * 0.24 + spread_score * 0.14 + traffic_pressure * 0.1 + best_risk_pressure * 0.08,
        "S4": 0.40 + offpeak_stability * 0.30 + spread_score * 0.11 + (1.0 - candidate_competition) * 0.07,
        "S5": 0.38 + low_willingness * 0.27 + traffic_pressure * 0.16 + rain_or_event * 0.09 + risk_candidate_rate * 0.09,
    }
    if str(config.get("scene_type")) == "scarce_couriers":
        signals["S3"] += 0.11
    scores: dict[str, float] = {}
    for strategy_id, raw_score in signals.items():
        prior = 0.165 if strategy_id == sample_hint else 0.0
        jitter = (_unit_hash(config["id"], sample_key, strategy_id, salt="feature-score-jitter") - 0.5) * 0.055
        scores[strategy_id] = round(max(0.32, min(0.99, raw_score + prior + jitter)), 2)

    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    selected_strategy_id = ranked[0][0]
    metrics = {
        "density_score": round(density_score, 2),
        "spread_score": round(spread_score, 2),
        "candidate_competition": round(candidate_competition, 2),
        "shortage_score": round(shortage_score, 2),
        "risk_candidate_rate": round(risk_candidate_rate, 2),
        "best_risk_pressure": round(best_risk_pressure, 2),
        "traffic_pressure": round(traffic_pressure, 2),
        "avg_willingness": round(avg_willingness, 2),
        "offpeak_stability": round(offpeak_stability, 2),
        "sample_hint": sample_hint,
    }
    evidence = {
        "S1": f"密度 {metrics['density_score']} / 合单需求 {round(avg_orders, 2)}",
        "S2": f"候选竞争 {metrics['candidate_competition']} / 骑手池 {courier_count}",
        "S3": f"稀缺 {metrics['shortage_score']} / 分散 {metrics['spread_score']}",
        "S4": f"低峰稳定 {metrics['offpeak_stability']} / 风险 {metrics['best_risk_pressure']}",
        "S5": f"低意愿 {round(low_willingness, 2)} / 路况 {metrics['traffic_pressure']}",
    }
    return {
        "selected_strategy_id": selected_strategy_id,
        "scores": scores,
        "ranked": [{"id": strategy_id, "score": score} for strategy_id, score in ranked],
        "metrics": metrics,
        "evidence": evidence,
    }


def _strategy_attempt_flow(config: dict[str, object], strategy_decision: dict[str, object]) -> list[dict[str, object]]:
    """Mirror the planner's real initial/adaptive strategy pool for the demo stream."""

    scene_type = str(config.get("scene_type", ""))
    weather = str(config.get("weather", "clear"))
    metrics = dict(strategy_decision.get("metrics") or {})
    scores = dict(strategy_decision.get("scores") or {})
    ranks = {str(item["id"]): index + 1 for index, item in enumerate(strategy_decision.get("ranked") or [])}
    selected = str(strategy_decision.get("selected_strategy_id") or "")
    preferred_selected_name = {
        "S1": "disjoint_gain",
        "S2": "single_multidispatch",
        "S3": "sparse_cover",
        "S4": "greedy_baseline",
        "S5": "production_solver",
    }.get(selected, "")
    flow: list[dict[str, object]] = []
    seen: set[str] = set()

    def add(name: str, branch: str, phase: str, trigger: str) -> None:
        if name in seen:
            return
        seen.add(name)
        flow.append(
            {
                "name": name,
                "branch": branch,
                "phase": phase,
                "trigger": trigger,
                "score": scores.get(branch),
                "rank": ranks.get(branch),
                "selected_branch": branch == selected and name == preferred_selected_name,
            }
        )

    add("greedy_baseline", "S4", "initial", "先构造最快可行基线")
    add("single_multidispatch", "S2", "initial", "为每个商家保留多个候选骑手")
    add("disjoint_gain", "S1", "initial", "搜索互不冲突的高收益组合")

    dense_or_medium = scene_type in {"dense_commerce", "medium_parallel", "night_commerce", "campus_lunch", "event_mixed"}
    if dense_or_medium or float(metrics.get("density_score", 0.0)) >= 0.46:
        add("pair_matching", "S1", "initial", "订单/骑手候选接近时做二元匹配")

    scarce = scene_type in {"scarce_couriers", "congestion_recovery"} or float(metrics.get("shortage_score", 0.0)) >= 0.32
    low_willingness = scene_type in {"low_willingness", "medical_office_peak"} or weather in {"rain", "event"} or float(metrics.get("avg_willingness", 1.0)) <= 0.60
    incomplete_pressure = scarce or low_willingness or float(metrics.get("best_risk_pressure", 0.0)) >= 0.46
    if incomplete_pressure:
        add("sparse_cover", "S3", "adaptive", "覆盖不足或风险偏高时补足商家覆盖")
    if scarce:
        add("scarce_k2_column", "S1", "adaptive", "骑手稀缺时放大二阶组合列")
        add("scarce_bundle_mcf", "S1", "adaptive", "稀缺场景用 MCF 重组候选包")
    if low_willingness:
        add("low_global_column", "S5", "adaptive", "低意愿场景先做全局风险护栏")
        add("low_single_column", "S5", "adaptive", "对高风险商家做单点补充")

    add("production_solver", "S5", "production", "进入生产级 anytime 求解器复核")
    add("evolution_replay", "S5", "evolution", "复用历史有效策略事件")
    return flow


def _delivery_project_map_traces(config: dict[str, object], sample_key: object) -> list[dict[str, object]]:
    """Dense non-routing basemap traces inspired by the delivery-routes map layer."""

    traces: list[dict[str, object]] = []
    trace_index = 0

    for row in range(11):
        y = 7.0 + row * 8.2 + (_unit_hash(config["id"], sample_key, row, salt="trace-row-y") - 0.5) * 3.4
        x_start = 1.5 + (_unit_hash(config["id"], sample_key, row, salt="trace-row-start") - 0.5) * 4.2
        points = []
        for column in range(7):
            x = x_start + column * 16.3
            bend = (_unit_hash(config["id"], sample_key, row, column, salt="trace-row-bend") - 0.5) * 4.8
            points.append(_clamp_point(x, y + bend))
        trace_index += 1
        traces.append({"id": f"MT{trace_index:02d}", "class": "collector", "points": [{"x": round(x, 1), "y": round(y, 1)} for x, y in points]})

    for column in range(12):
        x = 4.0 + column * 8.4 + (_unit_hash(config["id"], sample_key, column, salt="trace-col-x") - 0.5) * 2.8
        y_start = 4.0 + (_unit_hash(config["id"], sample_key, column, salt="trace-col-start") - 0.5) * 4.0
        points = []
        for row in range(6):
            y = y_start + row * 17.5
            bend = (_unit_hash(config["id"], sample_key, column, row, salt="trace-col-bend") - 0.5) * 3.8
            points.append(_clamp_point(x + bend, y))
        trace_index += 1
        traces.append({"id": f"MT{trace_index:02d}", "class": "local", "points": [{"x": round(x, 1), "y": round(y, 1)} for x, y in points]})

    diagonal_templates = [
        ((4.0, 78.0), (22.0, 58.0), (44.0, 41.0), (68.0, 26.0), (96.0, 15.0)),
        ((6.0, 24.0), (29.0, 38.0), (49.0, 48.0), (70.0, 62.0), (94.0, 82.0)),
        ((14.0, 92.0), (31.0, 72.0), (53.0, 56.0), (77.0, 38.0), (97.0, 22.0)),
        ((10.0, 12.0), (28.0, 24.0), (48.0, 36.0), (72.0, 50.0), (96.0, 67.0)),
        ((2.0, 48.0), (20.0, 43.0), (41.0, 50.0), (63.0, 47.0), (90.0, 57.0)),
        ((20.0, 6.0), (28.0, 26.0), (41.0, 45.0), (48.0, 64.0), (52.0, 91.0)),
    ]
    for index, template in enumerate(diagonal_templates):
        jittered = []
        for point_index, point in enumerate(template):
            x = point[0] + (_unit_hash(config["id"], sample_key, index, point_index, salt="trace-diag-x") - 0.5) * 2.2
            y = point[1] + (_unit_hash(config["id"], sample_key, index, point_index, salt="trace-diag-y") - 0.5) * 2.2
            jittered.append(_clamp_point(x, y))
        trace_index += 1
        traces.append({"id": f"MT{trace_index:02d}", "class": "ring", "points": [{"x": round(x, 1), "y": round(y, 1)} for x, y in jittered]})

    return traces


def _simulated_map_layers(config: dict[str, object], sample_index: int, variant_seed: str | None = None) -> dict[str, object]:
    sample_key = variant_seed or sample_index
    traffic_bias = float(config["traffic_bias"])
    density_profile = str(config.get("density_profile", "balanced"))
    weather = str(config.get("weather", "clear"))
    base_map_traces = _delivery_project_map_traces(config, sample_key)
    roads = []
    for index, road in enumerate(_DISPATCH_ROADS):
        traffic_level = max(0.12, min(0.94, traffic_bias + (_unit_hash(config["id"], sample_key, index, salt="traffic") - 0.5) * 0.32))
        road_type = "arterial" if index < 4 else "secondary" if index < 12 else "service"
        condition = _road_condition(traffic_level)
        roads.append(
            {
                "id": f"R{index + 1:02d}",
                "type": road_type,
                "corridor": "主干道" if road_type == "arterial" else "次干道" if road_type == "secondary" else "支路",
                "traffic": condition,
                "traffic_label": _traffic_label(condition),
                "traffic_level": round(traffic_level, 2),
                "width": 8.8 if road_type == "arterial" else 4.9 if road_type == "secondary" else 2.6,
                "name_visible": False,
                "points": [{"x": point[0], "y": point[1]} for point in road],
            }
        )
    districts = []
    for row in range(3):
        for column in range(4):
            index = row * 4 + column
            districts.append(
                {
                    "id": f"Z{index + 1:02d}",
                    "x": round(5.0 + column * 23.0 + (_unit_hash(config["id"], sample_key, index, salt="zone-x") - 0.5) * 2.8, 1),
                    "y": round(8.0 + row * 27.0 + (_unit_hash(config["id"], sample_key, index, salt="zone-y") - 0.5) * 2.5, 1),
                    "width": round(18.5 + _unit_hash(config["id"], index, salt="zone-w") * 7.5, 1),
                    "height": round(18.0 + _unit_hash(config["id"], index, salt="zone-h") * 8.0, 1),
                    "intensity": round(0.22 + _unit_hash(config["id"], sample_key, index, salt="zone-intensity") * 0.38, 2),
                }
            )
    blocks = []
    for index in range(36):
        column = index % 9
        row = index // 9
        x = 6 + column * 10.1 + (_unit_hash(config["id"], sample_key, index, salt="block-x") - 0.5) * 3.4
        y = 9 + row * 20.5 + (_unit_hash(config["id"], sample_key, index, salt="block-y") - 0.5) * 4.0
        width = 5.8 + _unit_hash(config["id"], index, salt="block-w") * 6.6
        height = 5.6 + _unit_hash(config["id"], index, salt="block-h") * 8.0
        usage_seed = _unit_hash(config["scene_type"], index, salt="usage")
        commerce_cutoff = 0.48 if "clustered" in density_profile else 0.68
        usage = "commerce" if usage_seed > commerce_cutoff else "office" if usage_seed > 0.36 else "residential"
        blocks.append(
            {
                "id": f"B{index + 1:02d}",
                "x": round(max(5.0, min(90.0, x)), 1),
                "y": round(max(6.0, min(86.0, y)), 1),
                "width": round(width, 1),
                "height": round(height, 1),
                "usage": usage,
                "rotation": round((_unit_hash(config["id"], sample_key, index, salt="block-rot") - 0.5) * 5.0, 1),
                "intensity": round(0.28 + _unit_hash(config["id"], sample_key, index, salt="block-intensity") * 0.55, 2),
            }
        )
    center_x, center_y = config["center"]
    hotspots = []
    hotspot_count = 4 if "clustered" in density_profile else 3
    hotspot_base_radius = 10.5 if density_profile in {"clustered", "rain_clustered", "event_clustered"} else 8.0
    for index in range(hotspot_count):
        hotspot_x = float(center_x) + (index - 1) * 7.0 + (_unit_hash(config["id"], sample_key, index, salt="hotspot-x") - 0.5) * 5.0
        hotspot_y = float(center_y) + (index % 2 - 0.5) * 8.0 + (_unit_hash(config["id"], sample_key, index, salt="hotspot-y") - 0.5) * 4.5
        hotspots.append(
            {
                "id": f"H{index + 1:02d}",
                "x": round(max(10.0, min(90.0, hotspot_x)), 1),
                "y": round(max(10.0, min(86.0, hotspot_y)), 1),
                "radius": round(hotspot_base_radius + _unit_hash(config["id"], sample_key, index, salt="hotspot-r") * 7.2, 1),
                "intensity": round(0.34 + _unit_hash(config["id"], sample_key, index, salt="hotspot-i") * 0.48, 2),
                "type": "commerce_cluster" if index == 1 else "demand_spillover",
            }
        )
    rain_streaks = []
    if weather == "rain":
        for index in range(76):
            x = _unit_hash(config["id"], sample_key, index, salt="rain-x") * 100
            y = _unit_hash(config["id"], sample_key, index, salt="rain-y") * 100
            rain_streaks.append(
                {
                    "id": f"W{index + 1:02d}",
                    "x": round(x, 1),
                    "y": round(y, 1),
                    "length": round(4.5 + _unit_hash(config["id"], sample_key, index, salt="rain-l") * 5.8, 1),
                    "opacity": round(0.18 + _unit_hash(config["id"], sample_key, index, salt="rain-o") * 0.24, 2),
                }
            )
    intersections = []
    seen_intersections: set[tuple[int, int]] = set()
    for road in _DISPATCH_ROADS[:12]:
        for point in road[1:-1]:
            key = (round(point[0]), round(point[1]))
            if key in seen_intersections:
                continue
            seen_intersections.add(key)
            intersections.append(
                {
                    "id": f"J{len(intersections) + 1:02d}",
                    "x": round(point[0], 1),
                    "y": round(point[1], 1),
                    "signal_load": round(0.32 + _unit_hash(config["id"], sample_key, len(intersections), salt="signal") * 0.54, 2),
                }
            )
            if len(intersections) >= 10:
                break
        if len(intersections) >= 10:
            break
    return {
        "style": "meituan_delivery_project_map_v3",
        "canvas": {"width": 980, "height": 640},
        "map_provider": "delivery_routes_clone_meituan_grid",
        "road_graph": "delivery_routes_project_road_graph_v3",
        "layer_schema": "delivery_routes_optimization_maplibre_clone",
        "hide_road_names": True,
        "road_name_labels": [],
        "layers": ["delivery_project_trace_map", "delivery_route_source", "candidate_route_layer", "selected_route_layer", "meituan_delivery_grid", "district_blocks", "building_blocks", "arterial_roads", "secondary_roads", "service_roads", "traffic_overlay", "commerce_hotspots", "signal_intersections"],
        "districts": districts,
        "base_map_traces": base_map_traces,
        "roads": roads,
        "building_blocks": blocks,
        "commerce_hotspots": hotspots,
        "intersections": intersections,
        "weather": weather,
        "weather_label": _weather_label(weather),
        "density_profile": density_profile,
        "rain_streaks": rain_streaks,
        "anonymous_note": "Simulated navigation layer only; road names and exact addresses are intentionally hidden.",
    }


def build_simulated_scenario_sample(scenario_id: str, sample_index: int = 0, variant_seed: str | None = None) -> dict[str, object]:
    config = _simulated_scenario_config(scenario_id)
    sample_index = int(sample_index) % 10
    sample_key = variant_seed or sample_index
    merchant_min, merchant_max = config["merchant_range"]
    courier_min, courier_max = config["courier_range"]
    density_profile = str(config.get("density_profile", "balanced"))
    merchant_count = int(merchant_min) + (sample_index + int(_unit_hash(config["id"], sample_key, salt="merchant-count") * 10)) % (int(merchant_max) - int(merchant_min) + 1)
    courier_count = int(courier_min) + int(_unit_hash(config["id"], sample_key, salt="courier-count") * (int(courier_max) - int(courier_min) + 1))
    map_layers = _simulated_map_layers(config, sample_index, variant_seed)
    traffic_level = sum(float(road["traffic_level"]) for road in map_layers["roads"][:4]) / 4
    merchant_anchors = _select_scene_anchors(config, "merchant", merchant_count, sample_key)
    courier_anchors = _select_scene_anchors(config, "courier", courier_count, sample_key)
    map_layers["anchor_model"] = "predefined_dispatch_anchor_pool_v1"
    map_layers["anchor_pools"] = {
        "merchant_total": len(_MERCHANT_ANCHORS),
        "courier_total": len(_COURIER_ANCHORS),
        "merchant_selected": [anchor["id"] for anchor in merchant_anchors],
        "courier_selected": [anchor["id"] for anchor in courier_anchors],
        "scene_tags": sorted(_scene_anchor_tags(config)),
    }

    merchants = []
    for index, anchor in enumerate(merchant_anchors):
        x, y = float(anchor["x"]), float(anchor["y"])
        order_count = 1 + ((sample_index + index) % 2)
        demand = 0.48 + _unit_hash(config["id"], sample_key, anchor["id"], salt="merchant-demand") * 0.47
        merchant_id = f"M{sample_index + 1:02d}{index + 1:02d}"
        delivery_points = [
            {
                "id": merchant_id,
                "kind": "merchant_order",
                "label": f"商家 {index + 1}",
                "x": x,
                "y": y,
                "anchor_id": anchor["id"],
                "anchor_zone": anchor["zone"],
                "anchor_road_id": anchor["road_id"],
                "anchor_role": "merchant",
                "curb_distance": anchor["curb_distance"],
                "expected_eta_min": int(22 + demand * 18 + traffic_level * 10),
                "expected_price": round(18 + demand * 18 + traffic_level * 8, 1),
                "parent_merchant_id": merchant_id,
            }
        ]
        merchants.append(
            {
                "id": merchant_id,
                "kind": "merchant_order",
                "label": f"订单 {index + 1}",
                "x": x,
                "y": y,
                "anchor_id": anchor["id"],
                "anchor_zone": anchor["zone"],
                "anchor_road_id": anchor["road_id"],
                "anchor_role": "merchant",
                "curb_distance": anchor["curb_distance"],
                "on_road": False,
                "order_count": order_count,
                "expected_eta_min": int(22 + demand * 18 + traffic_level * 10),
                "expected_price": round(18 + demand * 18 + traffic_level * 8, 1),
                "demand_level": round(demand, 2),
                "hotspot": anchor["zone"],
                "delivery_points": delivery_points,
            }
        )

    couriers = []
    for index, anchor in enumerate(courier_anchors):
        x, y = float(anchor["x"]), float(anchor["y"])
        willingness = max(0.18, min(0.96, float(config["willingness_base"]) + (_unit_hash(config["id"], sample_key, anchor["id"], salt="willingness") - 0.5) * 0.34 - traffic_level * 0.12))
        couriers.append(
            {
                "id": f"R{sample_index + 1:02d}{index + 1:02d}",
                "kind": "courier",
                "label": f"骑手 {index + 1}",
                "x": x,
                "y": y,
                "anchor_id": anchor["id"],
                "anchor_zone": anchor["zone"],
                "anchor_road_id": anchor["road_id"],
                "anchor_role": "courier",
                "curb_distance": anchor["curb_distance"],
                "willingness": round(willingness, 2),
                "capacity": 1,
                "status": "available" if willingness >= 0.36 else "hesitant",
                "on_road": True,
            }
        )

    candidates = []
    all_candidates_by_merchant: dict[str, list[dict[str, object]]] = {}
    for merchant in merchants:
        ranked = []
        merchant_point = (float(merchant["x"]), float(merchant["y"]))
        for courier in couriers:
            courier_point = (float(courier["x"]), float(courier["y"]))
            distance = _euclidean_distance(merchant_point, courier_point)
            willingness = float(courier["willingness"])
            cost = distance * 2.15 + float(merchant["order_count"]) * 6.5 + traffic_level * 16 - willingness * 7.5
            eta = max(6, min(35, round(distance * 0.72 + traffic_level * 12 + 4)))
            risk = _risk_level(willingness, traffic_level)
            ranked.append(
                {
                    "merchant_id": merchant["id"],
                    "courier_id": courier["id"],
                    "distance": round(distance, 1),
                    "cost": round(cost, 1),
                    "eta_min": eta,
                    "accept_probability": round(willingness, 2),
                    "risk": risk,
                }
            )
        ranked.sort(key=lambda item: (item["risk"] == "High", item["cost"]))
        all_candidates_by_merchant[str(merchant["id"])] = ranked
        candidates.extend(ranked[:3])

    strategy_decision = _strategy_score_model(config, sample_key, sample_index, density_profile, traffic_level, merchants, couriers, candidates)
    selected_strategy_id = str(strategy_decision["selected_strategy_id"])
    for courier in couriers:
        courier["capacity"] = 1

    assignments = []
    used_courier_ids: set[str] = set()
    for merchant_index, merchant in enumerate(merchants):
        merchant_candidates = list(all_candidates_by_merchant.get(str(merchant["id"]), []))
        if selected_strategy_id == "S5":
            merchant_candidates.sort(key=lambda item: (item["risk"] == "High", -item["accept_probability"], item["cost"]))
        elif selected_strategy_id == "S4":
            merchant_candidates.sort(key=lambda item: item["distance"])
        elif selected_strategy_id == "S1":
            merchant_candidates.sort(key=lambda item: (item["cost"] - float(merchant["demand_level"]) * 8, item["eta_min"]))
        else:
            merchant_candidates.sort(key=lambda item: (item["cost"], item["eta_min"]))
        available_candidates = [candidate for candidate in merchant_candidates if str(candidate["courier_id"]) not in used_courier_ids]
        chosen = available_candidates[0] if available_candidates else merchant_candidates[0]
        allocated_courier_ids = [chosen["courier_id"]]
        if selected_strategy_id == "S2":
            allocated_courier_ids = [chosen["courier_id"]]
            remaining_merchants = max(0, len(merchants) - merchant_index - 1)
            remaining_unused = max(0, len(couriers) - len(used_courier_ids) - len(allocated_courier_ids))
            extra_slots = max(0, min(2, remaining_unused - remaining_merchants))
            for candidate in merchant_candidates:
                candidate_id = str(candidate["courier_id"])
                if candidate_id in used_courier_ids or candidate_id in allocated_courier_ids:
                    continue
                if len(allocated_courier_ids) >= 1 + extra_slots:
                    break
                allocated_courier_ids.append(candidate["courier_id"])
        used_courier_ids.update(str(courier_id) for courier_id in allocated_courier_ids)
        current_allocated = set(str(courier_id) for courier_id in allocated_courier_ids)
        backup = next(
            (
                candidate
                for candidate in merchant_candidates
                if str(candidate["courier_id"]) not in used_courier_ids
            ),
            None,
        ) or next(
            (
                candidate
                for candidate in merchant_candidates
                if str(candidate["courier_id"]) not in current_allocated
            ),
            chosen,
        )
        assignments.append(
            {
                "id": f"A{sample_index + 1:02d}{len(assignments) + 1:02d}",
                "merchant_id": merchant["id"],
                "courier_id": chosen["courier_id"],
                "backup_courier_id": backup["courier_id"],
                "allocated_courier_ids": allocated_courier_ids,
                "strategy_id": selected_strategy_id,
                "cost": chosen["cost"],
                "eta_min": chosen["eta_min"],
                "accept_probability": chosen["accept_probability"],
                "risk": chosen["risk"],
                "route": [chosen["courier_id"], merchant["id"]],
                "reason": [
                    _SIMULATION_STRATEGIES[selected_strategy_id]["reason"],
                    f"接单概率 {round(chosen['accept_probability'] * 100)}%，预计 {chosen['eta_min']} 分钟送达",
                    f"分配骑手集合 {' / '.join(allocated_courier_ids)} 用于最大化当前期望值",
                ],
            }
        )

    strategy_path = []
    for strategy_id, strategy in _SIMULATION_STRATEGIES.items():
        score = float(strategy_decision["scores"][strategy_id])
        strategy_path.append(
            {
                "id": strategy_id,
                "name": strategy["name"],
                "label": strategy["label"],
                "status": "selected" if strategy_id == selected_strategy_id else "rejected",
                "score": score,
                "rank": next(index + 1 for index, item in enumerate(strategy_decision["ranked"]) if item["id"] == strategy_id),
                "evidence": strategy_decision["evidence"][strategy_id],
            }
        )
    strategy_path.sort(key=lambda item: item["rank"])

    return {
        "scenario_id": str(config["id"]),
        "case_id": str(config["case_id"]),
        "sample_index": sample_index,
        "seed": str(variant_seed or f"{config['id']}-{sample_index:02d}"),
        "variant_seed": variant_seed or "",
        "name": str(config["name"]),
        "scene_type": str(config["scene_type"]),
        "stage": "preview",
        "selected_strategy_id": selected_strategy_id,
        "selected_strategy": _SIMULATION_STRATEGIES[selected_strategy_id],
        "strategy_path": strategy_path,
        "strategy_attempt_flow": _strategy_attempt_flow(config, strategy_decision),
        "strategy_decision": strategy_decision,
        "map_layers": map_layers,
        "merchants": merchants,
        "couriers": couriers,
        "candidates": candidates,
        "assignments": assignments,
        "summary": {
            "merchant_count": len(merchants),
            "courier_count": len(couriers),
            "candidate_count": len(candidates),
            "traffic": _road_condition(traffic_level),
            "weather": str(config.get("weather", "clear")),
            "weather_label": _weather_label(config.get("weather", "clear")),
            "density_profile": density_profile,
            "anchor_model": map_layers["anchor_model"],
            "avg_willingness": round(sum(float(item["willingness"]) for item in couriers) / max(1, len(couriers)), 2),
        },
    }


def build_simulated_scenario_samples() -> list[dict[str, object]]:
    return [
        build_simulated_scenario_sample(str(config["id"]), sample_index)
        for config in _SIMULATED_SCENARIO_CONFIGS
        for sample_index in range(10)
    ]


def _candidate_lookup(candidates: list[tuple[str, tuple[str, ...], str, float, float, int]]) -> dict[tuple[str, str], tuple[str, tuple[str, ...], str, float, float, int]]:
    return {(row[0], row[2]): row for row in candidates}


def _preview_solution(candidates: list[tuple[str, tuple[str, ...], str, float, float, int]], limit: int = 8) -> list[tuple[str, list[str]]]:
    used_tasks: set[str] = set()
    used_couriers: set[str] = set()
    solution: list[tuple[str, list[str]]] = []
    ranked = sorted(candidates, key=lambda row: (row[3] / max(row[4], 0.05), -len(row[1]), row[5]))
    for task_key, task_ids, courier_id, _score, _willingness, _row_index in ranked:
        if courier_id in used_couriers or any(task_id in used_tasks for task_id in task_ids):
            continue
        used_couriers.add(courier_id)
        used_tasks.update(task_ids)
        solution.append((task_key, [courier_id]))
        if len(solution) >= limit:
            break
    return solution


def build_dispatch_assignment_map(case_id: str, report: dict[str, object] | None = None, limit: int = 8) -> dict[str, object]:
    path = _case_files().get(case_id)
    if path is None or not path.exists():
        return {"case_id": case_id, "stage": "unavailable", "assignments": [], "entities": []}
    candidates, all_tasks = parse_candidates(path.read_text(encoding="utf-8"))
    rows = _candidate_lookup(candidates)
    raw_solution = report.get("solution") if isinstance(report, dict) else None
    stage = "final" if raw_solution else "preview"
    solution = raw_solution if isinstance(raw_solution, list) and raw_solution else _preview_solution(candidates, limit=limit)
    assignments: list[dict[str, object]] = []
    entities: dict[str, dict[str, object]] = {}

    def add_entity(entity_id: str, kind: str, label: str, lane: int, point: tuple[float, float] | None = None) -> None:
        if entity_id in entities:
            return
        x, y = point or _stable_point(entity_id, lane)
        entities[entity_id] = {"id": entity_id, "kind": kind, "label": label, "x": x, "y": y}

    visible_solution = solution[:limit]
    for index, item in enumerate(visible_solution):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            continue
        task_key = str(item[0])
        couriers = [str(courier) for courier in item[1] if courier]
        if not couriers:
            continue
        courier_id = couriers[0]
        row = rows.get((task_key, courier_id))
        if row is None:
            task_ids = tuple(part.strip() for part in task_key.split(",") if part.strip())
            score = 0.0
            willingness = 0.0
        else:
            _task_key, task_ids, _courier, score, willingness, _row_index = row
        pickup_id = "G" + str(index + 1).zfill(2)
        pickup_point, courier_point, order_points = _simulated_dispatch_points(
            index,
            len(visible_solution),
            task_key,
            courier_id,
            score,
            willingness,
            len(task_ids),
        )
        add_entity(pickup_id, "pickup_cluster", f"{pickup_id} 商家", index, pickup_point)
        display_couriers = couriers[:1]
        for courier_index, visible_courier in enumerate(display_couriers):
            courier_offset = (
                round(min(92.0, courier_point[0] + courier_index * 2.8), 1),
                round(max(8.0, min(92.0, courier_point[1] + (courier_index - (len(couriers) - 1) / 2) * 5.0)), 1),
            )
            add_entity(visible_courier, "courier", visible_courier, index + 3 + courier_index, courier_offset)
        order_count = max(1, len(task_ids))
        display_task_ids = list(task_ids) if index == 0 else list(task_ids[:1])
        risk = "High" if willingness < 0.25 else "Medium" if willingness < 0.55 else "Low"
        assignments.append(
            {
                "id": f"A{index + 1}",
                "task_key": task_key,
                "pickup": pickup_id,
                "pickup_label": f"{pickup_id}：{task_key}",
                "merchant": pickup_id,
                "merchant_note": "输入文件不包含真实商家坐标；此处为由 task_id_list 推断的商家取餐点。",
                "courier": courier_id,
                "map_couriers": display_couriers,
                "backup_couriers": couriers[1:],
                "map_orders": [],
                "orders": list(task_ids),
                "order_count": order_count,
                "eta": f"{max(6, min(28, round(score / 5)))} min",
                "cost": f"${score:.1f}",
                "probability": f"{round(willingness * 100)}%",
                "fit": f"{round(max(0.0, min(1.0, willingness)) * 100)}%",
                "distance": f"{max(2.0, min(32.0, score / 4.0)):.1f} km",
                "risk": risk,
                "reason": [
                    f"来自输入候选行：{task_key} -> {courier_id}",
                    f"候选 total_score={score:.3f}，willingness={willingness:.4f}",
                    "位置由 score/willingness 模拟：高意愿更近，成本越高距离越长",
                    "派单分配关系以求解器 solution 为准" if stage == "final" else "当前为未运行前的真实候选预览",
                ],
            }
        )
    return {
        "case_id": case_id,
        "stage": stage,
        "total_tasks": len(all_tasks),
        "total_couriers": len({row[2] for row in candidates}),
        "rows": len(candidates),
        "assignments": assignments,
        "entities": list(entities.values()),
        "map_layers": _simulated_map_layers(_simulated_scenario_config(case_id), 0),
        "note": "Case files contain task groups, couriers, score, and willingness, but no real merchant coordinates.",
    }


def build_agent_payload(case_id: str, budget_s: float = 10.0) -> dict[str, object]:
    try:
        report = run_case_agent(case_id, budget_s=budget_s)
    except Exception as exc:
        dispatch_map = build_dispatch_assignment_map(case_id)
        return {
            "status": "ok",
            "report": {
                "case_id": case_id,
                "status": "preview_fallback",
                "wall_time_s": 0,
                "features": {
                    "tasks": dispatch_map.get("total_tasks", 0),
                    "couriers": dispatch_map.get("total_couriers", 0),
                    "rows": dispatch_map.get("rows", 0),
                },
                "best": {
                    "strategy": "candidate_preview",
                    "valid": True,
                    "covered_tasks": dispatch_map.get("total_tasks", 0),
                    "total_tasks": dispatch_map.get("total_tasks", 0),
                    "groups": len(dispatch_map.get("assignments", [])),
                    "used_couriers": len({item.get("courier") for item in dispatch_map.get("assignments", [])}),
                    "uncovered_tasks": [],
                    "local_cost": sum(float(str(item.get("cost", "$0")).replace("$", "") or 0) for item in dispatch_map.get("assignments", [])),
                },
                "rounds": [],
                "events": [{"type": "fallback", "reason": str(exc)}],
                "solution": [(item["task_key"], [str(item["courier"]).split(" + ")[0]]) for item in dispatch_map.get("assignments", [])],
                "dispatch_assignment_map": dispatch_map,
            },
        }
    report["reasongraph_mermaid"] = autosolver_mermaid("final", report)
    report["delivery_routes_map"] = autosolver_map_payload("final")
    report["dispatch_assignment_map"] = build_dispatch_assignment_map(case_id, report)
    return {"status": "ok", "report": report}


def _controls_from_payload(payload: dict[str, object] | None) -> SimulationControls | None:
    if not payload:
        return None
    return SimulationControls(
        courier_count=int(payload.get("courier_count", SimulationControls.courier_count)),
        order_intensity=float(payload.get("order_intensity", SimulationControls.order_intensity)),
        burstiness=float(payload.get("burstiness", SimulationControls.burstiness)),
        weather=str(payload.get("weather", SimulationControls.weather)),
        congestion_level=float(payload.get("congestion_level", SimulationControls.congestion_level)),
        playback_speed=float(payload.get("playback_speed", SimulationControls.playback_speed)),
        compare_enabled=bool(payload.get("compare_enabled", SimulationControls.compare_enabled)),
    ).normalized()


def _simulation_scenarios_payload() -> dict[str, object]:
    scenarios = scenario_catalog()
    default_controls = scenarios[0].default_controls if scenarios else SimulationControls()
    return {
        "status": "ok",
        "scenarios": simulation_to_dict(scenarios),
        "defaults": simulation_to_dict(default_controls),
        "engine": {
            "version": SIMULATION_ENGINE_VERSION,
            "routing_provider": "local-road-graph",
            "map_provider": "maplibre-with-offline-schematic-fallback",
        },
    }


def _memory_store() -> SimulationMemoryStore:
    return SimulationMemoryStore(SIMULATION_MEMORY_ROOT)


def _runtime_session(session_id: str) -> dict[str, object]:
    with _RUNTIME_LOCK:
        item = _SIMULATION_RUNTIME.get(session_id)
        if item is None:
            raise ValueError(f"unknown simulation session: {session_id}")
        return dict(item)


def _create_simulation_session_payload(payload: dict[str, object]) -> dict[str, object]:
    start = create_simulation_session(
        scenario_id=str(payload.get("scenario_id") or "commerce_peak"),
        seed=str(payload.get("seed") or "demo"),
        controls=_controls_from_payload(payload.get("controls") if isinstance(payload.get("controls"), dict) else None),
        map_provider=str(payload.get("map_provider") or "maplibre"),
    )
    with _RUNTIME_LOCK:
        _SIMULATION_RUNTIME[start.session.session_id] = {"session": start.session, "tick": start.tick, "timeline": list(start.timeline)}
    return {
        "status": "ok",
        "session": simulation_to_dict(start.session),
        "tick": simulation_to_dict(start.tick),
        "timeline": simulation_to_dict(start.timeline),
    }


def _advance_simulation_payload(payload: dict[str, object]) -> dict[str, object]:
    session_id = str(payload.get("session_id") or "")
    if not session_id:
        raise ValueError("session_id is required")
    runtime = _runtime_session(session_id)
    session = runtime["session"]
    tick = runtime["tick"]
    if not hasattr(session, "controls") or not hasattr(tick, "tick_id"):
        raise ValueError(f"invalid simulation runtime for session: {session_id}")
    controls_patch = payload.get("controls_patch") if isinstance(payload.get("controls_patch"), dict) else None
    advanced = advance_simulation(
        session,
        tick,
        advance_seconds=int(payload.get("advance_seconds") or 20),
        controls_patch=controls_patch,
        compare_if_due=bool(payload.get("compare_if_due", True)),
    )
    next_session = replace(session, controls=session.controls.with_patch(controls_patch))
    with _RUNTIME_LOCK:
        existing = _SIMULATION_RUNTIME.get(session_id, {})
        timeline = list(existing.get("timeline", []))
        timeline.extend(advanced.timeline_delta)
        _SIMULATION_RUNTIME[session_id] = {"session": next_session, "tick": advanced.tick, "timeline": timeline}
    return {
        "status": "ok",
        "tick": simulation_to_dict(advanced.tick),
        "timeline_delta": simulation_to_dict(advanced.timeline_delta),
        "compare_trigger": simulation_to_dict(advanced.compare_trigger),
    }


def _run_compare_payload(payload: dict[str, object]) -> dict[str, object]:
    session_id = str(payload.get("session_id") or "")
    if not session_id:
        raise ValueError("session_id is required")
    runtime = _runtime_session(session_id)
    session = runtime["session"]
    tick = runtime["tick"]
    if payload.get("tick_id") and str(payload.get("tick_id")) != tick.tick_id:
        raise ValueError(f"unknown tick for session {session_id}: {payload.get('tick_id')}")
    memory_mode = str(payload.get("memory_mode") or "off")
    predictor_mode = str(payload.get("predictor_mode") or "fallback")
    store = _memory_store() if memory_mode != "off" else None
    algorithms = payload.get("algorithms")
    compare = run_comparison(
        session,
        tick,
        time_budget_ms=int(payload.get("time_budget_ms") or 10_000),
        algorithms=tuple(str(item) for item in algorithms) if isinstance(algorithms, list) else None,
        memory_store=store,
        memory_mode=memory_mode,
        predictor_mode=predictor_mode,
    )
    with _RUNTIME_LOCK:
        _COMPARE_RUNTIME[compare.compare_run.compare_run_id] = compare
    return {
        "status": "ok",
        "compare_run": simulation_to_dict(compare.compare_run),
        "results": simulation_to_dict(compare.results),
        "selected": simulation_to_dict(compare.selected),
        "decision_points": simulation_to_dict(compare.decision_points),
        "memory": simulation_to_dict(compare.memory),
        "predictor": simulation_to_dict(compare.predictor),
        "timeline_delta": simulation_to_dict(compare.timeline_delta),
    }


def _get_compare_payload(compare_run_id: str) -> dict[str, object]:
    with _RUNTIME_LOCK:
        compare = _COMPARE_RUNTIME.get(compare_run_id)
    if compare is None:
        raise ValueError(f"unknown compare run: {compare_run_id}")
    return {
        "status": "ok",
        "compare_run": simulation_to_dict(compare.compare_run),
        "results": simulation_to_dict(compare.results),
        "selected": simulation_to_dict(compare.selected),
        "decision_points": simulation_to_dict(compare.decision_points),
        "memory": simulation_to_dict(compare.memory),
        "predictor": simulation_to_dict(compare.predictor),
    }


def _memory_recall_payload(query: dict[str, list[str]]) -> dict[str, object]:
    features = {
        "scenario_id": query.get("scenario_id", ["commerce_peak"])[0],
        "scene_type": query.get("scene_type", ["dense_commerce"])[0],
        "weather": query.get("weather", ["clear"])[0],
        "traffic_profile": query.get("traffic_profile", ["normal"])[0],
        "congestion_level": float(query.get("congestion_level", ["0.5"])[0]),
        "order_pressure": float(query.get("order_pressure", ["0.5"])[0]),
        "courier_pressure": float(query.get("courier_pressure", ["1.0"])[0]),
        "active_order_count": int(query.get("active_order_count", ["0"])[0]),
        "courier_count": int(query.get("courier_count", ["1"])[0]),
        "avg_willingness": float(query.get("avg_willingness", ["0.6"])[0]),
        "burst_active": query.get("burst_active", ["false"])[0].lower() == "true",
    }
    recall = _memory_store().recall_similar_context(features, mode="read-only")
    return {"status": "ok", "recall": simulation_to_dict(recall)}


def _memory_event_payload(payload: dict[str, object]) -> dict[str, object]:
    event = payload.get("event") if isinstance(payload.get("event"), dict) else payload
    accepted = _memory_store().append_memory_event(event, dry_run=bool(payload.get("dry_run", False)))
    return {"status": "ok", "accepted": True, "event_id": accepted["event_id"], "write_mode": "append-only-jsonl"}


def _predictor_rank_payload(payload: dict[str, object]) -> dict[str, object]:
    compare_run_id = str(payload.get("compare_run_id") or "")
    if compare_run_id:
        with _RUNTIME_LOCK:
            compare = _COMPARE_RUNTIME.get(compare_run_id)
        if compare is None:
            raise ValueError(f"unknown compare run: {compare_run_id}")
        trace = rank_algorithms_with_predictor(
            compare.compare_run.scenario_features,
            compare.results,
            compare.memory,
            mode=str(payload.get("mode") or "fallback"),
        )
        return {"status": "ok", "predictor": simulation_to_dict(trace), "ranked_algorithms": simulation_to_dict(trace.ranked_algorithms)}
    algorithms = payload.get("candidate_algorithms") if isinstance(payload.get("candidate_algorithms"), list) else []
    ranked = tuple({"algorithm_id": str(algorithm), "rank": index + 1, "reason": "fallback order"} for index, algorithm in enumerate(algorithms))
    return {
        "status": "ok",
        "predictor": {
            "mode": str(payload.get("mode") or "fallback"),
            "provider": "local-heuristic",
            "model": "local-heuristic-v1",
            "used_external_api": False,
            "timeout_ms": 800,
            "status": "fallback",
            "secret_handling": "env-only-redacted",
            "ranking_reason": "No compare run supplied; returned candidate fallback order.",
            "ranked_algorithms": list(ranked),
        },
        "ranked_algorithms": list(ranked),
    }


def _sse(event: str, data: dict[str, object]) -> bytes:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n".encode("utf-8")


def render_index() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AutoSolver Agent - 动态配送仿真对比沙盘</title>
  <link rel="stylesheet" href="https://unpkg.com/maplibre-gl@5.24.0/dist/maplibre-gl.css">
  <style>
    :root {
      --sandbox-scale: 1;
      --bg: #07130f;
      --bg-deep: #030805;
      --panel: rgba(247, 239, 217, .94);
      --panel-dark: rgba(16, 35, 28, .93);
      --ink: #17231d;
      --muted: #6f7568;
      --line: rgba(88, 77, 52, .22);
      --route: #c66a21;
      --route-soft: rgba(198, 106, 33, .25);
      --merchant: #d9901f;
      --courier: #0f766e;
      --order: #b3382f;
      --agent: #1f4f46;
      --good: #216e43;
      --warn: #b7791f;
      --bad: #b42318;
      --paper: #fbf4dd;
      --shadow: 0 18px 50px rgba(0, 0, 0, .24);
      --mono: "SFMono-Regular", "Cascadia Mono", "Menlo", monospace;
    }
    * { box-sizing: border-box; }
    html, body { margin: 0; min-height: 100%; }
    body {
      color: var(--ink);
      background:
        radial-gradient(circle at 15% 4%, rgba(228, 167, 72, .22), transparent 30%),
        radial-gradient(circle at 75% 12%, rgba(28, 113, 91, .22), transparent 34%),
        linear-gradient(135deg, #10231c 0%, #07130f 52%, #1f170f 100%);
      font-family: "Aptos", "PingFang SC", "Microsoft YaHei", sans-serif;
      overflow: hidden;
    }
    button, select, input { font: inherit; }
    .simulation-shell {
      width: 100vw;
      height: 100vh;
      padding: 14px;
      display: grid;
      grid-template-rows: 68px minmax(0, 1fr) 118px;
      gap: 12px;
      transform-origin: top left;
      transform: scale(var(--sandbox-scale));
    }
    .topbar, .control-rail, .map-board, .compare-rail, .timeline-dock {
      border: 1px solid rgba(251, 244, 221, .18);
      box-shadow: var(--shadow);
      backdrop-filter: blur(18px);
    }
    .topbar {
      display: grid;
      grid-template-columns: minmax(0, 1.3fr) auto auto;
      align-items: center;
      gap: 16px;
      padding: 12px 16px;
      color: #f9f1dd;
      background: linear-gradient(100deg, rgba(12, 37, 31, .9), rgba(56, 38, 20, .78));
      border-radius: 24px;
    }
    .brand-eyebrow { color: #e3b262; font-size: 12px; letter-spacing: .18em; text-transform: uppercase; }
    .topbar h1 { margin: 4px 0 0; font-size: 24px; letter-spacing: -.03em; }
    .topbar p { margin: 0; max-width: 720px; color: rgba(249, 241, 221, .76); line-height: 1.45; }
    .status-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 10px 12px;
      border-radius: 999px;
      color: #fff7df;
      background: rgba(255, 255, 255, .08);
      border: 1px solid rgba(255, 255, 255, .16);
      white-space: nowrap;
    }
    .status-pill::before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: #5ee0a2; box-shadow: 0 0 16px #5ee0a2; }
    .main-grid {
      min-height: 0;
      display: grid;
      grid-template-columns: 260px minmax(560px, 1fr) 360px;
      gap: 12px;
    }
    .control-rail, .compare-rail {
      min-height: 0;
      overflow: hidden;
      border-radius: 26px;
      background: var(--panel);
    }
    .section { padding: 16px; border-bottom: 1px solid var(--line); }
    .section:last-child { border-bottom: 0; }
    .section h2, .map-card h2, .compare-card h2, .memory-card h2, .timeline-dock h2 {
      margin: 0 0 10px;
      font-size: 14px;
      letter-spacing: .08em;
      text-transform: uppercase;
      color: #304137;
    }
    .scenario-picker, .control-field { display: grid; gap: 8px; margin-top: 12px; }
    .scenario-picker label, .control-field label { font-size: 12px; color: var(--muted); }
    select, input[type="range"] { width: 100%; }
    select {
      height: 38px;
      border: 1px solid rgba(47, 64, 55, .22);
      border-radius: 12px;
      color: var(--ink);
      background: rgba(255, 255, 255, .62);
      padding: 0 10px;
    }
    input[type="range"] { accent-color: #b86f24; }
    .control-value { font-family: var(--mono); color: #164b40; font-size: 12px; }
    .button-row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 14px; }
    .button-row.single { grid-template-columns: 1fr; }
    .sim-button {
      border: 0;
      border-radius: 14px;
      padding: 10px 12px;
      color: #fff7e2;
      background: linear-gradient(135deg, #254d3f, #bf7224);
      cursor: pointer;
      box-shadow: 0 10px 24px rgba(77, 46, 16, .18);
    }
    .sim-button.secondary { color: #253328; background: rgba(37, 77, 63, .12); border: 1px solid rgba(37, 77, 63, .22); box-shadow: none; }
    .mechanic-list { display: grid; gap: 8px; margin-top: 12px; }
    .mechanic { padding: 9px; border-radius: 14px; background: rgba(255, 255, 255, .52); border: 1px solid rgba(47, 64, 55, .12); }
    .mechanic b { display: block; font-size: 13px; }
    .mechanic span { display: block; margin-top: 3px; color: var(--muted); font-size: 12px; line-height: 1.35; }
    .map-board {
      min-height: 0;
      position: relative;
      overflow: hidden;
      border-radius: 30px;
      background: linear-gradient(145deg, #e7d9b5 0%, #f6ecd0 48%, #d7c095 100%);
    }
    .map-card { position: absolute; inset: 0; display: grid; grid-template-rows: auto minmax(0, 1fr) auto; }
    .map-header {
      z-index: 5;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 16px 18px 8px;
      pointer-events: none;
    }
    .map-header p { margin: 3px 0 0; color: #5e6358; font-size: 13px; }
    .map-stats { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
    .stat-chip {
      padding: 8px 10px;
      border-radius: 999px;
      font-family: var(--mono);
      font-size: 12px;
      color: #17372f;
      background: rgba(255, 255, 255, .72);
      border: 1px solid rgba(37, 77, 63, .14);
    }
    .map-viewport { position: relative; min-height: 0; margin: 0 14px; border-radius: 24px; overflow: hidden; border: 1px solid rgba(73, 62, 39, .24); background: #dfd1ad; }
    #simulation-map { position: absolute; inset: 0; z-index: 1; opacity: .74; }
    .map-fallback {
      position: absolute;
      inset: 0;
      z-index: 0;
      background:
        linear-gradient(90deg, rgba(73, 62, 39, .11) 1px, transparent 1px),
        linear-gradient(0deg, rgba(73, 62, 39, .11) 1px, transparent 1px),
        radial-gradient(circle at 36% 42%, rgba(191, 114, 36, .16), transparent 18%),
        radial-gradient(circle at 68% 58%, rgba(20, 104, 89, .18), transparent 22%),
        #eadbb7;
      background-size: 64px 64px, 64px 64px, auto, auto, auto;
    }
    .congestion-band, .weather-zone {
      position: absolute;
      z-index: 2;
      pointer-events: none;
      border-radius: 999px;
      filter: blur(.2px);
    }
    .congestion-band { width: 52%; height: 16%; left: 24%; top: 42%; background: rgba(185, 91, 32, .18); transform: rotate(-12deg); border: 1px dashed rgba(185, 91, 32, .38); }
    .weather-zone { width: 34%; height: 34%; right: 7%; top: 8%; background: rgba(51, 105, 130, .12); border: 1px solid rgba(51, 105, 130, .2); }
    .route-layer { position: absolute; inset: 0; z-index: 3; pointer-events: none; }
    .route-layer path { fill: none; stroke: var(--route); stroke-width: 2.4; stroke-linecap: round; stroke-dasharray: 8 7; opacity: .78; }
    .entity-layer { position: absolute; inset: 0; z-index: 4; pointer-events: none; }
    .entity-pin {
      position: absolute;
      min-width: 30px;
      height: 30px;
      display: grid;
      place-items: center;
      border-radius: 999px;
      color: white;
      font-weight: 800;
      font-size: 12px;
      transform: translate(-50%, -50%);
      border: 2px solid rgba(255, 255, 255, .78);
      box-shadow: 0 10px 22px rgba(0, 0, 0, .22);
    }
    .entity-pin::after {
      content: attr(data-label);
      position: absolute;
      left: 50%;
      top: 33px;
      transform: translateX(-50%);
      min-width: max-content;
      padding: 3px 6px;
      border-radius: 8px;
      color: #233126;
      background: rgba(255, 250, 235, .88);
      border: 1px solid rgba(50, 42, 28, .16);
      font-size: 11px;
      font-weight: 700;
    }
    .entity-pin.merchant { background: var(--merchant); }
    .entity-pin.courier { background: var(--courier); }
    .entity-pin.order { background: var(--order); width: 24px; height: 24px; min-width: 24px; font-size: 10px; }
    .map-legend {
      z-index: 5;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      padding: 10px 18px 16px;
      color: #4b5148;
      font-size: 12px;
    }
    .legend-items { display: flex; gap: 10px; flex-wrap: wrap; }
    .legend-items span { display: inline-flex; align-items: center; gap: 5px; }
    .legend-dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
    .compare-rail { display: grid; grid-template-rows: minmax(0, 1fr) minmax(190px, .72fr); gap: 0; }
    .compare-card, .memory-card { min-height: 0; padding: 16px; overflow: auto; }
    .compare-card { border-bottom: 1px solid var(--line); }
    .compare-table { width: 100%; border-collapse: collapse; font-size: 12px; }
    .compare-table th { text-align: left; color: #6b6f63; font-weight: 700; padding: 0 0 8px; }
    .compare-table td { padding: 9px 0; border-top: 1px solid rgba(47, 64, 55, .12); vertical-align: top; }
    .compare-table tr.selected { color: #0f3e34; font-weight: 800; }
    .compare-table .family { color: #7b7868; font-size: 11px; font-family: var(--mono); }
    .decision-list, .memory-list { display: grid; gap: 9px; margin-top: 12px; }
    .decision, .memory-item {
      padding: 10px;
      border-radius: 14px;
      background: rgba(255, 255, 255, .56);
      border: 1px solid rgba(47, 64, 55, .12);
      line-height: 1.42;
      font-size: 12px;
    }
    .decision b, .memory-item b { display: block; color: #253629; margin-bottom: 4px; }
    .memory-meta { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 8px; }
    .memory-meta span { padding: 8px; border-radius: 12px; background: rgba(37, 77, 63, .08); font-family: var(--mono); font-size: 11px; }
    .evolution-track { display: grid; grid-template-columns: repeat(5, 1fr); gap: 5px; margin-top: 10px; }
    .evolution-stage { padding: 7px 5px; border-radius: 10px; text-align: center; background: rgba(191, 114, 36, .12); font-size: 11px; }
    .timeline-dock {
      display: grid;
      grid-template-columns: 210px minmax(0, 1fr);
      gap: 12px;
      overflow: hidden;
      border-radius: 26px;
      color: #f8efd9;
      background: linear-gradient(100deg, rgba(13, 35, 29, .92), rgba(42, 30, 18, .86));
    }
    .timeline-title { padding: 16px; border-right: 1px solid rgba(255, 255, 255, .12); }
    .timeline-title p { margin: 4px 0 0; color: rgba(248, 239, 217, .68); font-size: 12px; line-height: 1.4; }
    .event-timeline { display: flex; gap: 10px; align-items: stretch; overflow-x: auto; padding: 14px 14px 14px 0; }
    .timeline-event {
      min-width: 190px;
      padding: 12px;
      border-radius: 18px;
      background: rgba(255, 255, 255, .08);
      border: 1px solid rgba(255, 255, 255, .14);
    }
    .timeline-event time { font-family: var(--mono); color: #e5b86e; font-size: 12px; }
    .timeline-event b { display: block; margin: 6px 0 4px; }
    .timeline-event span { color: rgba(248, 239, 217, .7); font-size: 12px; line-height: 1.38; }
    .loading-note { color: var(--muted); font-size: 12px; line-height: 1.45; }
    @media (max-width: 1100px) {
      body { overflow: auto; }
      .simulation-shell { height: auto; min-height: 100vh; grid-template-rows: auto auto auto; transform: none; }
      .topbar, .main-grid, .timeline-dock { grid-template-columns: 1fr; }
      .main-grid { grid-template-columns: 1fr; }
      .map-board { min-height: 560px; }
      .timeline-dock { min-height: 220px; }
      .timeline-title { border-right: 0; border-bottom: 1px solid rgba(255, 255, 255, .12); }
      .event-timeline { padding: 0 14px 14px; }
    }
  </style>
</head>
<body>
  <main class="simulation-shell" id="simulation-sandbox" data-mode="simulation-comparison" data-map-provider="maplibre-with-offline-schematic-fallback">
    <header class="topbar">
      <div>
        <div class="brand-eyebrow">AutoSolver Agent Simulation Sandbox</div>
        <h1>美团即时配送动态仿真对比沙盘</h1>
        <p>以真实地图语义承载骑手、商家、订单突发和拥堵状态，在同一时间片内对比贪心、高级匹配/流方法与 AutoSolver Agent，并展示 Memory 如何影响下一次决策。</p>
      </div>
      <div class="status-pill" id="engine-status">引擎初始化中</div>
      <div class="status-pill">10 秒内输出对比和关键决策点</div>
    </header>

    <section class="main-grid">
      <aside class="control-rail" aria-label="仿真控制台">
        <div class="section">
          <h2>推演控制</h2>
          <div class="scenario-picker">
            <label for="scenario-select">调度场景</label>
            <select id="scenario-select"><option value="commerce_peak">商圈十字路口高峰</option></select>
          </div>
          <div class="control-field">
            <label for="courier-count">骑手人数 <span class="control-value" id="courier-count-value">12</span></label>
            <input id="courier-count" type="range" min="4" max="28" value="12">
          </div>
          <div class="control-field">
            <label for="order-intensity">订单强度 <span class="control-value" id="order-intensity-value">0.62</span></label>
            <input id="order-intensity" type="range" min="0" max="1" step="0.01" value="0.62">
          </div>
          <div class="control-field">
            <label for="burstiness">突发波峰 <span class="control-value" id="burstiness-value">0.56</span></label>
            <input id="burstiness" type="range" min="0" max="1" step="0.01" value="0.56">
          </div>
          <div class="control-field">
            <label for="weather-mode">天气</label>
            <select id="weather-mode">
              <option value="clear">晴天</option>
              <option value="rain">雨天</option>
              <option value="storm">暴雨</option>
              <option value="event">活动日</option>
            </select>
          </div>
          <div class="control-field">
            <label for="congestion-level">拥堵水平 <span class="control-value" id="congestion-level-value">0.48</span></label>
            <input id="congestion-level" type="range" min="0" max="1" step="0.01" value="0.48">
          </div>
          <div class="button-row">
            <button class="sim-button" id="play-sim">播放推演</button>
            <button class="sim-button secondary" id="pause-sim">暂停</button>
          </div>
          <div class="button-row">
            <button class="sim-button secondary" id="reset-sim">重置</button>
            <button class="sim-button" id="run-compare">决策对比</button>
          </div>
        </div>
        <div class="section">
          <h2>机制参考</h2>
          <div class="mechanic-list">
            <div class="mechanic"><b>策略游戏式态势</b><span>大地图展示骑手、商家、订单波峰、拥堵带和天气区域，不再用复杂线框图讲故事。</span></div>
            <div class="mechanic"><b>模拟人生式事件流</b><span>时间线持续记录商家下单、骑手移动、突发订单和系统触发求解。</span></div>
            <div class="mechanic"><b>对比模式为核心</b><span>同一批订单并排比较 nearest greedy、matching、flow 和 AutoSolver Agent。</span></div>
          </div>
        </div>
      </aside>

      <section class="map-board" aria-label="动态配送仿真大地图">
        <div class="map-card">
          <div class="map-header">
            <div>
              <h2>动态配送仿真沙盘</h2>
              <p id="scenario-description">基于当前项目地图风格构建动态仿真环境。</p>
            </div>
            <div class="map-stats">
              <span class="stat-chip" id="sim-time">T+00:00</span>
              <span class="stat-chip" id="active-orders">订单 0</span>
              <span class="stat-chip" id="active-couriers">骑手 0</span>
              <span class="stat-chip" id="weather-state">天气 clear</span>
              <span class="stat-chip" id="compare-budget">对比预算 10.0s</span>
            </div>
          </div>
          <div class="map-viewport" id="map-viewport">
            <div class="map-fallback" aria-hidden="true"></div>
            <div id="simulation-map" aria-label="MapLibre 真实地图底图"></div>
            <div class="weather-zone" id="weather-zone"></div>
            <div class="congestion-band" id="congestion-band"></div>
            <svg class="route-layer" id="route-layer" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"></svg>
            <div class="entity-layer" id="entity-layer" aria-label="骑手商家订单图层"></div>
          </div>
          <div class="map-legend">
            <div class="legend-items">
              <span><i class="legend-dot" style="background: var(--merchant)"></i>商家</span>
              <span><i class="legend-dot" style="background: var(--courier)"></i>骑手</span>
              <span><i class="legend-dot" style="background: var(--order)"></i>订单目的地</span>
              <span><i class="legend-dot" style="background: var(--route)"></i>选中策略路线</span>
            </div>
            <span id="compare-status">等待对比运行</span>
          </div>
        </div>
      </section>

      <aside class="compare-rail" aria-label="算法对比与 Memory 自进化">
        <section class="compare-card">
          <h2>多算法决策对比</h2>
          <table class="compare-table" id="algorithm-compare-table">
            <thead>
              <tr><th>算法</th><th>覆盖</th><th>ETA</th><th>风险</th><th>提升</th></tr>
            </thead>
            <tbody id="compare-body">
              <tr data-algorithm="nearest_greedy"><td>Nearest Greedy<div class="family">baseline</div></td><td colspan="4">等待运行</td></tr>
              <tr data-algorithm="cost_greedy"><td>Cost Greedy<div class="family">baseline</div></td><td colspan="4">等待运行</td></tr>
              <tr data-algorithm="risk_aware_greedy"><td>Risk-aware Greedy<div class="family">baseline</div></td><td colspan="4">等待运行</td></tr>
              <tr data-algorithm="min_cost_matching"><td>Min-cost Matching<div class="family">advanced</div></td><td colspan="4">等待运行</td></tr>
              <tr data-algorithm="sparse_cover"><td>Sparse Cover<div class="family">advanced</div></td><td colspan="4">等待运行</td></tr>
              <tr data-algorithm="flow_mcf"><td>Flow MCF<div class="family">advanced</div></td><td colspan="4">等待运行</td></tr>
              <tr data-algorithm="autosolver_agent"><td>AutoSolver Agent<div class="family">ours</div></td><td colspan="4">等待运行</td></tr>
            </tbody>
          </table>
          <div class="decision-list" id="decision-point-list">
            <div class="decision"><b>关键决策点</b>等待实时求解后展示候选策略胜负、风险变化和 Agent 选择理由。</div>
          </div>
        </section>
        <section class="memory-card" id="memory-evolution-panel">
          <h2>自动化 Memory 自进化</h2>
          <p class="loading-note" id="memory-summary">Memory 默认使用本地 fallback；外部 predictor 只允许环境变量接入，界面只展示 env-only-redacted。</p>
          <div class="memory-meta">
            <span id="memory-source">source: external-disabled</span>
            <span id="predictor-source">predictor: local-heuristic</span>
          </div>
          <div class="evolution-track" aria-label="Hermes style memory evolution lifecycle">
            <div class="evolution-stage" data-memory-event="evolution_generate">evolution_generate</div>
            <div class="evolution-stage" data-memory-event="evolution_validate">evolution_validate</div>
            <div class="evolution-stage" data-memory-event="evolution_trial">evolution_trial</div>
            <div class="evolution-stage" data-memory-event="evolution_promote">promote</div>
            <div class="evolution-stage" data-memory-event="evolution_rollback">rollback</div>
          </div>
          <div class="memory-list" id="memory-list">
            <div class="memory-item"><b>Scenario Memory</b>历史画像会沉淀为雨天、骑手稀缺、订单爆发、拥堵等可 recall 的经验。</div>
          </div>
        </section>
      </aside>
    </section>

    <section class="timeline-dock" aria-label="动态事件时间线">
      <div class="timeline-title">
        <h2>事件时间线</h2>
        <p>用事件推演替代旧线框图：下单、移动、突发、求解、Memory 写入都在这里沉淀。</p>
      </div>
      <div class="event-timeline" id="event-timeline">
        <article class="timeline-event"><time>00:00</time><b>等待初始化</b><span>加载场景后开始动态仿真。</span></article>
      </div>
    </section>
  </main>

  <script src="https://unpkg.com/maplibre-gl@5.24.0/dist/maplibre-gl.js"></script>
  <script>
    const API_ENDPOINTS = Object.freeze({
      scenarios: "/api/simulation/scenarios",
      session: "/api/simulation/session",
      tick: "/api/simulation/tick",
      compare: "/api/compare/run",
      memoryRecall: "/api/memory/recall",
      predictorRank: "/api/predictor/rank"
    });
    const ALGORITHM_ORDER = ["nearest_greedy", "cost_greedy", "risk_aware_greedy", "min_cost_matching", "sparse_cover", "flow_mcf", "autosolver_agent"];
    const $ = (id) => document.getElementById(id);
    const appState = {
      scenarios: [],
      session: null,
      tick: null,
      compare: null,
      timeline: [],
      map: null,
      playing: false,
      advancing: false,
      comparing: false,
      playTimer: null,
      compareTimer: null,
      controlApplyTimer: null,
      lastControlSignature: "",
      lastCompareElapsedMs: 0
    };

    function syncSandboxScale() {
      const shell = $("simulation-sandbox");
      if (!shell || window.innerWidth < 1100) return;
      document.documentElement.style.setProperty("--sandbox-scale", "1");
    }

    function text(value, fallback = "--") {
      if (value === null || value === undefined || value === "") return fallback;
      const escapes = {"&":"&amp;", "<":"&lt;", ">":"&gt;", "'":"&#39;"};
      escapes[String.fromCharCode(34)] = "&quot;";
      return String(value).replace(/[&<>"']/g, (ch) => escapes[ch]);
    }

    function secondsToClock(seconds) {
      const total = Math.max(0, Math.round(Number(seconds) || 0));
      const min = String(Math.floor(total / 60)).padStart(2, "0");
      const sec = String(total % 60).padStart(2, "0");
      return `${min}:${sec}`;
    }

    function controlPayload() {
      return {
        courier_count: Number($("courier-count").value),
        order_intensity: Number($("order-intensity").value),
        burstiness: Number($("burstiness").value),
        weather: $("weather-mode").value,
        congestion_level: Number($("congestion-level").value),
        compare_enabled: true
      };
    }

    function controlSignature() {
      return JSON.stringify(controlPayload());
    }

    function bindControlLabels() {
      const pairs = [["courier-count", 0], ["order-intensity", 2], ["burstiness", 2], ["congestion-level", 2]];
      pairs.forEach(([id, digits]) => {
        const input = $(id);
        const label = $(`${id}-value`);
        const update = () => { if (label) label.textContent = Number(input.value).toFixed(digits); };
        input.addEventListener("input", update);
        update();
      });
    }

    function setControlsDisabled(disabled) {
      ["scenario-select", "play-sim", "pause-sim", "reset-sim", "run-compare"].forEach((id) => {
        const node = $(id);
        if (node) node.disabled = Boolean(disabled && id !== "pause-sim");
      });
    }

    function setStatus(message) {
      $("engine-status").textContent = message;
    }

    function reportInteractionError(error, context = "交互异常") {
      console.error(context, error);
      setStatus(`${context}: ${error && error.message ? error.message : error}`);
    }

    async function apiJson(path, options = {}) {
      const response = await fetch(path, {
        headers: {"Content-Type": "application/json"},
        ...options,
        body: options.body && typeof options.body !== "string" ? JSON.stringify(options.body) : options.body
      });
      const payload = await response.json();
      if (!response.ok || payload.status === "error") throw new Error(payload.error || `request failed: ${path}`);
      return payload;
    }

    function scenarioById(id) {
      return appState.scenarios.find((item) => item.id === id) || appState.scenarios[0] || null;
    }

    function applyScenarioDefaults(scenario) {
      if (!scenario || !scenario.default_controls) return;
      const controls = scenario.default_controls;
      $("courier-count").value = controls.courier_count;
      $("order-intensity").value = controls.order_intensity;
      $("burstiness").value = controls.burstiness;
      $("weather-mode").value = controls.weather;
      $("congestion-level").value = controls.congestion_level;
      bindControlLabels();
      $("scenario-description").textContent = scenario.description || "动态配送仿真场景";
    }

    function renderScenarioOptions() {
      const select = $("scenario-select");
      select.innerHTML = appState.scenarios.map((scenario) => `<option value="${text(scenario.id)}">${text(scenario.name)}</option>`).join("");
      const current = scenarioById(select.value) || appState.scenarios[0];
      if (current) {
        select.value = current.id;
        applyScenarioDefaults(current);
      }
    }

    function initMapForTick(tick) {
      if (appState.map || !window.maplibregl || !tick || !tick.map_state) return;
      try {
        const center = tick.map_state.center || {lng: 121.4737, lat: 31.2304};
        appState.map = new maplibregl.Map({
          container: "simulation-map",
          style: "https://tiles.openfreemap.org/styles/positron",
          center: [center.lng, center.lat],
          zoom: 13.1,
          interactive: true,
          attributionControl: false
        });
        appState.map.addControl(new maplibregl.NavigationControl({showCompass: false}), "bottom-right");
      } catch (error) {
        console.warn("MapLibre fallback schematic is active", error);
      }
    }

    function pinStyle(position) {
      const x = Math.max(3, Math.min(97, Number(position && position.screen_x) || 50));
      const y = Math.max(3, Math.min(97, Number(position && position.screen_y) || 50));
      return `left:${x}%;top:${y}%;`;
    }

    function renderEntities(tick) {
      const layer = $("entity-layer");
      if (!tick) return;
      const merchants = (tick.merchants || []).map((item) => `<div class="entity-pin merchant" data-label="${text(item.id)}" style="${pinStyle(item.position)}">商</div>`);
      const couriers = (tick.couriers || []).map((item) => `<div class="entity-pin courier" data-label="${text(item.id)}" style="${pinStyle(item.position)}">骑</div>`);
      const orders = (tick.orders || []).filter((item) => tick.active_order_ids.includes(item.id)).slice(-14).map((item) => `<div class="entity-pin order" data-label="${text(item.id)}" style="${pinStyle(item.destination)}">单</div>`);
      layer.innerHTML = [...merchants, ...couriers, ...orders].join("");
    }

    function routePath(points) {
      if (!Array.isArray(points) || points.length < 2) return "";
      return points.map((point, index) => `${index ? "L" : "M"}${Number(point.screen_x || 50).toFixed(2)} ${Number(point.screen_y || 50).toFixed(2)}`).join(" ");
    }

    function renderRoutes(compare) {
      const svg = $("route-layer");
      const selected = compare && compare.selected;
      const routes = selected && Array.isArray(selected.route_overlays) ? selected.route_overlays.slice(0, 9) : [];
      svg.innerHTML = routes.map((route) => `<path data-order="${text(route.order_id)}" d="${routePath(route.points)}"></path>`).join("");
    }

    function renderTick(tick) {
      appState.tick = tick;
      initMapForTick(tick);
      renderEntities(tick);
      $("sim-time").textContent = `T+${secondsToClock(tick.sim_time_s)}`;
      $("active-orders").textContent = `订单 ${(tick.active_order_ids || []).length}`;
      $("active-couriers").textContent = `骑手 ${(tick.couriers || []).length}`;
      const traffic = tick.traffic_state || {};
      $("weather-state").textContent = `天气 ${traffic.weather || controlPayload().weather}`;
      $("weather-zone").style.opacity = ["rain", "storm"].includes(traffic.weather) ? ".95" : ".38";
      $("congestion-band").style.opacity = Math.max(.22, Number(traffic.congestion_level || 0.45)).toFixed(2);
      if (appState.map && tick.map_state && tick.map_state.center) {
        appState.map.easeTo({center: [tick.map_state.center.lng, tick.map_state.center.lat], duration: 320});
      }
    }

    function appendTimeline(events) {
      appState.timeline = [...appState.timeline, ...(events || [])].slice(-24);
      const timeline = $("event-timeline");
      timeline.innerHTML = appState.timeline.map((event) => `
        <article class="timeline-event" data-event-type="${text(event.event_type)}">
          <time>${secondsToClock(event.sim_time_s)}</time>
          <b>${text(event.title)}</b>
          <span>${text(event.summary)}</span>
        </article>
      `).join("");
      timeline.scrollLeft = timeline.scrollWidth;
    }

    function metricPercent(value) {
      return `${Math.round((Number(value) || 0) * 100)}%`;
    }

    function renderCompare(compare) {
      appState.compare = compare;
      const selectedId = compare && compare.selected ? compare.selected.algorithm_id : "";
      const results = new Map((compare && compare.results || []).map((item) => [item.algorithm_id, item]));
      $("compare-body").innerHTML = ALGORITHM_ORDER.map((id) => {
        const item = results.get(id);
        if (!item) return `<tr data-algorithm="${id}"><td>${id}<div class="family">pending</div></td><td colspan="4">等待运行</td></tr>`;
        const metrics = item.metrics || {};
        const rel = metrics.relative_to_baseline || {};
        const etaMin = Math.round((Number(metrics.avg_eta_s) || 0) / 60);
        const risk = metricPercent(metrics.no_accept_risk);
        const delta = `${Number(rel.score_delta_pct || 0).toFixed(1)}%`;
        return `<tr class="${id === selectedId ? "selected" : ""}" data-algorithm="${id}">
          <td>${text(item.label || id)}<div class="family">${text(item.algorithm_family)}</div></td>
          <td>${metricPercent(metrics.coverage_rate)}</td>
          <td>${etaMin}m</td>
          <td>${risk}</td>
          <td>${delta}</td>
        </tr>`;
      }).join("");
      const elapsed = appState.lastCompareElapsedMs ? `${(appState.lastCompareElapsedMs / 1000).toFixed(2)}s` : "实时";
      $("compare-status").textContent = selectedId ? `当前采纳 ${selectedId} · ${elapsed}` : "等待对比运行";
      renderRoutes(compare);
      renderDecisionPoints(compare && compare.decision_points || []);
      renderMemory(compare && compare.memory, compare && compare.predictor);
    }

    function resetCompareView() {
      appState.compare = null;
      appState.lastCompareElapsedMs = 0;
      $("compare-budget").textContent = "对比预算 10.0s";
      $("compare-status").textContent = "等待对比运行";
      $("route-layer").innerHTML = "";
      $("compare-body").innerHTML = ALGORITHM_ORDER.map((id) => `<tr data-algorithm="${id}"><td>${id}<div class="family">pending</div></td><td colspan="4">等待运行</td></tr>`).join("");
      $("decision-point-list").innerHTML = `<div class="decision"><b>关键决策点</b>等待实时求解后展示候选策略胜负、风险变化和 Agent 选择理由。</div>`;
      $("memory-source").textContent = "source: external-disabled";
      $("predictor-source").textContent = "predictor: local-heuristic";
      $("memory-summary").textContent = "Memory 默认使用本地 fallback；外部 predictor 只允许环境变量接入，界面只展示 env-only-redacted。";
      $("memory-list").innerHTML = `<div class="memory-item"><b>Scenario Memory</b>历史画像会沉淀为雨天、骑手稀缺、订单爆发、拥堵等可 recall 的经验。</div>`;
    }

    function stopCompareCountdown(finalText = null) {
      if (appState.compareTimer) window.clearInterval(appState.compareTimer);
      appState.compareTimer = null;
      if (finalText) $("compare-budget").textContent = finalText;
    }

    function startCompareCountdown(startedAt, budgetMs = 10000) {
      stopCompareCountdown();
      const update = () => {
        const elapsed = Date.now() - startedAt;
        const remaining = Math.max(0, budgetMs - elapsed);
        $("compare-budget").textContent = `对比预算 ${(remaining / 1000).toFixed(1)}s`;
      };
      update();
      appState.compareTimer = window.setInterval(update, 120);
    }

    function renderDecisionPoints(points) {
      const list = $("decision-point-list");
      if (!points.length) {
        list.innerHTML = `<div class="decision"><b>关键决策点</b>等待实时求解后展示。</div>`;
        return;
      }
      list.innerHTML = points.slice(0, 5).map((point) => `<div class="decision"><b>${text(point.title || point.decision_type || "决策点")}</b>${text(point.summary || point.reason || "策略对比完成")}</div>`).join("");
    }

    function renderMemory(memory, predictor) {
      if (!memory && !predictor) return;
      $("memory-source").textContent = `source: ${memory ? memory.source : "external-disabled"}`;
      $("predictor-source").textContent = `predictor: ${predictor ? predictor.model : "local-heuristic-v1"}`;
      $("memory-summary").textContent = memory ? memory.effect_on_ranking : "Memory recall pending.";
      const groups = ["scenario_memory", "decision_memory", "strategy_memory", "evolution_memory"];
      const cards = groups.flatMap((key) => (memory && memory[key] || []).slice(0, 2).map((item) => `<div class="memory-item"><b>${text(key)}</b>${text(item.summary || item.reason || item.strategy_id || JSON.stringify(item).slice(0, 110))}</div>`));
      if (predictor) cards.unshift(`<div class="memory-item"><b>Predictor Trace</b>${text(predictor.ranking_reason || "local fallback ranking")} · ${text(predictor.secret_handling || "env-only-redacted")}</div>`);
      $("memory-list").innerHTML = cards.length ? cards.join("") : `<div class="memory-item"><b>Memory Recall</b>暂无相似历史，使用当前 tick 指标进行排序。</div>`;
    }

    async function createSession() {
      const scenarioId = $("scenario-select").value || "commerce_peak";
      setStatus("创建仿真会话");
      const payload = await apiJson(API_ENDPOINTS.session, {method: "POST", body: {scenario_id: scenarioId, seed: `ui-${scenarioId}`, controls: controlPayload()}});
      appState.session = payload.session;
      appState.timeline = [];
      appState.lastControlSignature = controlSignature();
      resetCompareView();
      renderTick(payload.tick);
      appendTimeline(payload.timeline);
      setStatus("仿真会话就绪");
      return payload;
    }

    async function advanceSimulation(seconds = 20) {
      if (!appState.session) await createSession();
      if (appState.advancing) return null;
      appState.advancing = true;
      const controlsChanged = controlSignature() !== appState.lastControlSignature;
      setStatus("推进仿真 tick");
      try {
        const payload = await apiJson(API_ENDPOINTS.tick, {method: "POST", body: {session_id: appState.session.session_id, advance_seconds: seconds, controls_patch: controlPayload(), compare_if_due: true}});
        appState.lastControlSignature = controlSignature();
        renderTick(payload.tick);
        if (controlsChanged) resetCompareView();
        appendTimeline(payload.timeline_delta);
        setStatus(payload.compare_trigger ? "已触发实时对比" : (controlsChanged ? "参数已应用" : "仿真推进完成"));
        return payload;
      } finally {
        appState.advancing = false;
      }
    }

    async function runComparison() {
      if (!appState.session) await createSession();
      if (!appState.tick || !(appState.tick.active_order_ids || []).length) await advanceSimulation(60);
      if (appState.comparing) return null;
      appState.comparing = true;
      $("compare-status").textContent = "10 秒预算内并行评估算法";
      setStatus("运行多算法对比");
      const startedAt = Date.now();
      startCompareCountdown(startedAt, 10000);
      try {
        const payload = await apiJson(API_ENDPOINTS.compare, {method: "POST", body: {session_id: appState.session.session_id, tick_id: appState.tick.tick_id, time_budget_ms: 10000, memory_mode: "off", predictor_mode: "fallback"}});
        appState.lastCompareElapsedMs = Date.now() - startedAt;
        renderCompare(payload);
        appendTimeline(payload.timeline_delta);
        const elapsedText = `${(appState.lastCompareElapsedMs / 1000).toFixed(2)}s`;
        stopCompareCountdown(`对比完成 ${elapsedText}`);
        setStatus(appState.lastCompareElapsedMs <= 10000 ? "对比完成" : "对比超出10秒预算");
        return payload;
      } finally {
        appState.comparing = false;
      }
    }

    function scheduleNextPlaybackTick(delayMs = 1350) {
      if (appState.playTimer) window.clearTimeout(appState.playTimer);
      if (!appState.playing) return;
      appState.playTimer = window.setTimeout(playbackStep, delayMs);
    }

    async function playbackStep() {
      if (!appState.playing) return;
      try {
        const payload = await advanceSimulation(20);
        if (payload && payload.compare_trigger) await runComparison();
      } catch (error) {
        appState.playing = false;
        reportInteractionError(error, "播放推演失败");
      } finally {
        scheduleNextPlaybackTick();
      }
    }

    function startPlaybackLoop() {
      if (appState.playing) return;
      appState.playing = true;
      setStatus("播放推演中");
      appendTimeline([{sim_time_s: appState.tick ? appState.tick.sim_time_s : 0, event_type: "playback_started", title: "播放推演", summary: "时间线开始自动推进，控制台参数会在下一 tick 生效。"}]);
      scheduleNextPlaybackTick(10);
    }

    function pausePlayback() {
      appState.playing = false;
      if (appState.playTimer) window.clearTimeout(appState.playTimer);
      appState.playTimer = null;
      setStatus("已暂停");
      appendTimeline([{sim_time_s: appState.tick ? appState.tick.sim_time_s : 0, event_type: "playback_paused", title: "暂停推演", summary: "时间线已暂停，当前地图态势保留。"}]);
    }

    async function resetSimulation() {
      pausePlayback();
      stopCompareCountdown("对比预算 10.0s");
      await createSession();
      appendTimeline([{sim_time_s: 0, event_type: "simulation_reset", title: "重置推演", summary: "已清空路线、对比结果与事件缓存，重新初始化当前场景。"}]);
    }

    function scheduleControlPatch() {
      if (appState.controlApplyTimer) window.clearTimeout(appState.controlApplyTimer);
      appState.controlApplyTimer = window.setTimeout(async () => {
        if (!appState.session || appState.advancing || controlSignature() === appState.lastControlSignature) return;
        try {
          const payload = await advanceSimulation(1);
          if (payload && payload.compare_trigger) await runComparison();
        } catch (error) {
          reportInteractionError(error, "参数应用失败");
        }
      }, 420);
    }

    async function bootstrapSimulationSandbox() {
      bindControlLabels();
      syncSandboxScale();
      try {
        const catalog = await apiJson(API_ENDPOINTS.scenarios);
        appState.scenarios = catalog.scenarios || [];
        renderScenarioOptions();
        await createSession();
        await advanceSimulation(60);
        await runComparison();
      } catch (error) {
        console.error(error);
        $("engine-status").textContent = "使用离线沙盘壳";
        $("compare-status").textContent = error.message || "API 暂不可用";
      }
    }

    function handleProgressEvent(event) {
      if (!event) return;
      appendTimeline([{sim_time_s: appState.tick ? appState.tick.sim_time_s : 0, event_type: event.type || "progress", title: event.title || "进度事件", summary: event.summary || event.message || "事件已记录"}]);
    }

    $("scenario-select").addEventListener("change", async () => {
      applyScenarioDefaults(scenarioById($("scenario-select").value));
      try {
        await resetSimulation();
      } catch (error) {
        reportInteractionError(error, "切换场景失败");
      }
    });
    ["courier-count", "order-intensity", "burstiness", "weather-mode", "congestion-level"].forEach((id) => {
      $(id).addEventListener("change", scheduleControlPatch);
      $(id).addEventListener("input", () => { if (appState.playing) scheduleControlPatch(); });
    });
    $("play-sim").addEventListener("click", startPlaybackLoop);
    $("pause-sim").addEventListener("click", pausePlayback);
    $("reset-sim").addEventListener("click", () => resetSimulation().catch((error) => reportInteractionError(error, "重置推演失败")));
    $("run-compare").addEventListener("click", () => runComparison().catch((error) => reportInteractionError(error, "决策对比失败")));
    window.addEventListener("resize", syncSandboxScale);
    document.addEventListener("DOMContentLoaded", bootstrapSimulationSandbox);
    window.__AUTO_SOLVER_SIMULATION_SANDBOX__ = {
      API_ENDPOINTS,
      ALGORITHM_ORDER,
      appState,
      handleProgressEvent,
      startPlaybackLoop,
      pausePlayback,
      resetSimulation,
      scheduleControlPatch,
      runComparison
    };
  </script>
</body>
</html>"""


class AgentRequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict[str, object], status: int = 200) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _read_json(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("JSON request body must be an object")
        return payload

    def _send_html(self, html: str) -> None:
        raw = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _send_static_asset(self, path: str) -> bool:
        allowed = {
        }
        asset = allowed.get(path)
        if not asset:
            return False
        content_type, asset_path = asset
        if not asset_path.exists():
            return False
        raw = asset_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "public, max-age=3600")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)
        return True

    def _send_empty_icon(self) -> None:
        self.send_response(204)
        self.send_header("Cache-Control", "public, max-age=86400")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API.
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/favicon.ico":
                self._send_empty_icon()
                return
            if parsed.path.startswith("/assets/") and self._send_static_asset(parsed.path):
                return
            if parsed.path == "/":
                self._send_html(render_index())
                return
            if parsed.path == "/api/blueprint":
                self._send_json({"status": "ok", "blueprint": get_agent_blueprint()})
                return
            if parsed.path == "/api/cases":
                self._send_json({"status": "ok", "cases": list_cases()})
                return
            if parsed.path == "/api/simulation-scenarios":
                self._send_json({"status": "ok", "scenarios": list_simulated_scenarios()})
                return
            if parsed.path == "/api/simulation/scenarios":
                self._send_json(_simulation_scenarios_payload())
                return
            if parsed.path == "/api/simulation-sample":
                qs = parse_qs(parsed.query)
                scenario_id = qs.get("scenario", ["commerce_peak"])[0]
                try:
                    sample_index = int(qs.get("sample", ["0"])[0])
                except ValueError:
                    sample_index = 0
                variant_seed = qs.get("seed", [""])[0].strip() or None
                self._send_json({"status": "ok", "sample": build_simulated_scenario_sample(scenario_id, sample_index, variant_seed)})
                return
            if parsed.path == "/api/reasongraph":
                qs = parse_qs(parsed.query)
                mode = qs.get("mode", ["initial"])[0]
                self._send_json({"status": "ok", "mermaid": autosolver_mermaid(mode)})
                return
            if parsed.path == "/api/delivery-map":
                qs = parse_qs(parsed.query)
                stage = qs.get("stage", ["final"])[0]
                self._send_json({"status": "ok", "map": autosolver_map_payload(stage)})
                return
            if parsed.path == "/api/dispatch-map":
                qs = parse_qs(parsed.query)
                case_id = qs.get("case", ["large_seed301"])[0]
                self._send_json({"status": "ok", "map": build_dispatch_assignment_map(case_id)})
                return
            if parsed.path == "/api/run":
                qs = parse_qs(parsed.query)
                case_id = qs.get("case", ["large_seed301"])[0]
                budget_s = float(qs.get("budget", ["10"])[0])
                self._send_json(build_agent_payload(case_id, budget_s=budget_s))
                return
            if parsed.path.startswith("/api/compare/run/"):
                compare_run_id = parsed.path.rsplit("/", 1)[-1]
                self._send_json(_get_compare_payload(compare_run_id))
                return
            if parsed.path == "/api/memory/recall":
                self._send_json(_memory_recall_payload(parse_qs(parsed.query)))
                return
            if parsed.path == "/api/stream":
                qs = parse_qs(parsed.query)
                case_id = qs.get("case", ["large_seed301"])[0]
                budget_s = float(qs.get("budget", ["10"])[0])
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(_sse("start", {"message": f"starting agent session for {case_id}"}))
                self.wfile.flush()

                def observer(event: dict[str, object]) -> None:
                    self.wfile.write(_sse(event["type"], event))
                    self.wfile.flush()

                report = run_case_agent(case_id, budget_s=budget_s, observer=observer)
                report["reasongraph_mermaid"] = autosolver_mermaid("final", report)
                report["delivery_routes_map"] = autosolver_map_payload("final")
                self.wfile.write(_sse("result", {"report": report}))
                self.wfile.write(_sse("done", {"message": "stream complete"}))
                self.wfile.flush()
                self.close_connection = True
                return
            self._send_json({"status": "error", "error": "not found"}, status=404)
        except Exception as exc:
            self._send_json(
                {"status": "error", "error": str(exc), "traceback": traceback.format_exc()},
                status=500,
            )

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API.
        parsed = urlparse(self.path)
        try:
            payload = self._read_json()
            if parsed.path == "/api/simulation/session":
                self._send_json(_create_simulation_session_payload(payload))
                return
            if parsed.path == "/api/simulation/tick":
                self._send_json(_advance_simulation_payload(payload))
                return
            if parsed.path == "/api/compare/run":
                self._send_json(_run_compare_payload(payload))
                return
            if parsed.path == "/api/memory/event":
                self._send_json(_memory_event_payload(payload))
                return
            if parsed.path == "/api/predictor/rank":
                self._send_json(_predictor_rank_payload(payload))
                return
            self._send_json({"status": "error", "error": "not found"}, status=404)
        except Exception as exc:
            self._send_json(
                {"status": "error", "error": str(exc), "traceback": traceback.format_exc()},
                status=500,
            )

    def log_message(self, format: str, *args: object) -> None:
        print(f"[web-agent] {self.address_string()} - {format % args}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local AutoSolver Agent web demo.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    server = ThreadingHTTPServer((args.host, args.port), AgentRequestHandler)
    print(f"AutoSolver Agent System running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
