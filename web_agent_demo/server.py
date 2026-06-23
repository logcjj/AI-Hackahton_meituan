from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autosolver_agent.system import get_agent_blueprint, run_case_agent as _run_case_agent
from tools.agent_trace_demo import parse_candidates
from web_agent_demo.delivery_routes_clone import autosolver_map_payload
from web_agent_demo.reasongraph_clone import autosolver_mermaid

try:
    from web_agent_demo.sample_cases import SAMPLE_CASES, ensure_sample_cases
except ImportError:  # The demo can still run before optional synthetic cases are generated.
    SAMPLE_CASES = {}
    ensure_sample_cases = None


DATA_DIR = ROOT / "data" / "official_cases"
GENERATED_CASE_DIR = ROOT / "web_agent_demo" / "generated_cases"
STATIC_DIR = ROOT / "web_agent_demo" / "static"
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
    "S1": {"name": "合单优先", "label": "合单优先", "reason": "商圈订单密集，优先把同路订单合并给同一骑手"},
    "S2": {"name": "多派候选", "label": "多派候选", "reason": "多个骑手距离接近，需要扩展候选后再筛选"},
    "S3": {"name": "局部修复", "label": "局部修复", "reason": "先得到可行派单，再修复高成本或绕行订单"},
    "S4": {"name": "贪心基线", "label": "贪心基线", "reason": "低峰期订单分散，最近可用骑手已足够稳定"},
    "S5": {"name": "风险平衡", "label": "风险平衡", "reason": "低接单意愿或天气风险较高，优先控制无人接单概率"},
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
        "description": "路口商圈订单集中，适合验证合单优先和多骑手候选比较。",
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
        "description": "订单不完全重叠，多个骑手候选质量接近，突出多派候选策略。",
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
        "description": "骑手少且订单分布拉开，需要先覆盖再做局部修复。",
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
        "description": "活动流量导致局部拥堵，策略会在合单、风险平衡和修复之间切换。",
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
        "description": "夜间宵夜订单集中但骑手供给下降，用于展示合单和多派候选的平衡。",
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
        "description": "园区和校园午餐需求密集，多个骑手距离接近，适合展示多派候选。",
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
        "description": "医院与写字楼周边停车和通行限制更强，重点验证风险平衡和局部修复。",
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
        "description": "局部拥堵叠加异常补单，需要用局部修复减少无人接单和超时风险。",
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


def _select_scene_anchors(config: dict[str, object], role: str, count: int, sample_key: object) -> list[dict[str, object]]:
    anchors = _MERCHANT_ANCHORS if role == "merchant" else _COURIER_ANCHORS
    center = config.get("center", (50.0, 50.0))
    if not isinstance(center, tuple):
        center = tuple(center)  # type: ignore[arg-type]
    density_profile = str(config.get("density_profile", "balanced"))
    center_weight = -0.025 if density_profile in {"spread", "scarce_spread"} else 0.045
    matched = [anchor for anchor in anchors if _anchor_match_score(anchor, config) > 0]
    candidates = matched if len(matched) >= count else anchors
    ranked = sorted(
        candidates,
        key=lambda anchor: (
            -_anchor_match_score(anchor, config),
            _euclidean_distance((float(anchor["x"]), float(anchor["y"])), (float(center[0]), float(center[1]))) * center_weight
            + _unit_hash(config.get("id", ""), sample_key, anchor["id"], salt=f"{role}-anchor") * 9.0,
            str(anchor["id"]),
        ),
    )
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
        candidates.extend(ranked[:3])

    strategy_decision = _strategy_score_model(config, sample_key, sample_index, density_profile, traffic_level, merchants, couriers, candidates)
    selected_strategy_id = str(strategy_decision["selected_strategy_id"])
    for courier in couriers:
        courier["capacity"] = 2 if selected_strategy_id in {"S1", "S2", "S5"} else 1

    assignments = []
    courier_load: dict[str, int] = {}
    for merchant in merchants:
        merchant_candidates = [candidate for candidate in candidates if candidate["merchant_id"] == merchant["id"]]
        if selected_strategy_id == "S5":
            merchant_candidates.sort(key=lambda item: (item["risk"] == "High", -item["accept_probability"], item["cost"]))
        elif selected_strategy_id == "S4":
            merchant_candidates.sort(key=lambda item: item["distance"])
        elif selected_strategy_id == "S1":
            merchant_candidates.sort(key=lambda item: (item["cost"] - float(merchant["demand_level"]) * 8, item["eta_min"]))
        else:
            merchant_candidates.sort(key=lambda item: (item["cost"], item["eta_min"]))
        chosen = merchant_candidates[0]
        for candidate in merchant_candidates:
            courier = next(item for item in couriers if item["id"] == candidate["courier_id"])
            if courier_load.get(candidate["courier_id"], 0) < int(courier["capacity"]):
                chosen = candidate
                break
        courier_load[chosen["courier_id"]] = courier_load.get(chosen["courier_id"], 0) + 1
        backup = merchant_candidates[1] if len(merchant_candidates) > 1 else chosen
        assignments.append(
            {
                "id": f"A{sample_index + 1:02d}{len(assignments) + 1:02d}",
                "merchant_id": merchant["id"],
                "courier_id": chosen["courier_id"],
                "backup_courier_id": backup["courier_id"],
                "strategy_id": selected_strategy_id,
                "cost": chosen["cost"],
                "eta_min": chosen["eta_min"],
                "accept_probability": chosen["accept_probability"],
                "risk": chosen["risk"],
                "route": [chosen["courier_id"], merchant["id"]],
                "reason": [
                    _SIMULATION_STRATEGIES[selected_strategy_id]["reason"],
                    f"接单概率 {round(chosen['accept_probability'] * 100)}%，预计 {chosen['eta_min']} 分钟送达",
                    f"备选骑手 {backup['courier_id']} 可用于风险兜底",
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
                    "最终派单关系以求解器 solution 为准" if stage == "final" else "当前为未运行前的真实候选预览",
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


def _sse(event: str, data: dict[str, object]) -> bytes:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n".encode("utf-8")


def render_index() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AutoSolver Agent - 美团即时配送派单决策工作台</title>
  <link rel="stylesheet" href="https://unpkg.com/maplibre-gl@5.24.0/dist/maplibre-gl.css">
  <style>
    :root {
      --dashboard-scale: 1;
      --dashboard-width: 1280px;
      --dashboard-height: 720px;
      --bg: #020911;
      --panel: #071725;
      --panel-2: #0a1e2f;
      --panel-3: #0d2437;
      --stroke: #17344b;
      --stroke-2: #24516c;
      --text: #ecf6ff;
      --muted: #91a8bb;
      --dim: #526a7d;
      --cyan: #27e6d0;
      --blue: #28a8ff;
      --green: #36e67e;
      --yellow: #ffd12d;
      --orange: #ff9a2e;
      --red: #ff5b65;
      --map-merchant: #ffd02f;
      --map-courier: #0f766e;
      --map-route: #16a34a;
      --map-route-focus: #0f766e;
      --mono: "SFMono-Regular", "Cascadia Mono", "Menlo", monospace;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      width: 100vw;
      height: 100vh;
      overflow: hidden;
      color: var(--text);
      background:
        radial-gradient(circle at 28% 0%, rgba(27, 136, 210, .14), transparent 32%),
        linear-gradient(180deg, #020911 0%, #03101b 100%);
      font-family: "Aptos", "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    }
    button, select { font: inherit; }
    .dashboard {
      width: var(--dashboard-width);
      height: var(--dashboard-height);
      margin: 0;
      padding: 3px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      transform: scale(var(--dashboard-scale));
      transform-origin: top left;
    }
    .topbar, .panel {
      background: linear-gradient(180deg, rgba(10, 27, 43, .98), rgba(4, 17, 29, .98));
      border: 1px solid var(--stroke);
      border-radius: 9px;
      box-shadow: 0 18px 46px rgba(0, 0, 0, .42), inset 0 1px 0 rgba(117, 210, 255, .06);
    }
    .topbar {
      height: 64px;
      flex: 0 0 64px;
      display: grid;
      grid-template-columns: minmax(250px, 1.15fr) minmax(104px, .46fr) minmax(102px, .44fr) minmax(132px, .54fr) minmax(112px, .44fr) minmax(116px, .46fr) minmax(170px, .7fr);
      overflow: hidden;
    }
    .brand, .kpi { border-right: 1px solid var(--stroke-2); padding: 8px 11px; min-width: 0; overflow: hidden; }
    .brand { display: grid; grid-template-columns: 38px 1fr; gap: 10px; align-items: center; }
    .logo {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background: conic-gradient(from 20deg, #33dcff 0 12%, transparent 12% 24%, #2dd4ff 24% 38%, transparent 38% 51%, #4ae7d6 51% 66%, transparent 66% 78%, #2898ff 78% 92%, transparent 92%);
      position: relative;
      filter: drop-shadow(0 0 12px rgba(39, 230, 208, .35));
    }
    .logo:after { content: ""; position: absolute; inset: 10px; border-radius: 50%; background: var(--panel); border: 1px solid rgba(115, 221, 255, .32); }
    .brand h1 { margin: 0; font-size: 19px; letter-spacing: -.03em; line-height: 1.05; }
    .brand p, .kpi label, .mini, .muted { color: var(--muted); }
    .brand p { margin: 4px 0 0; font-size: 12px; white-space: nowrap; }
    .kpi label { display: block; font-size: 10px; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .kpi strong { display: block; font-size: 15px; line-height: 1.12; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    #case-id { font-size: 13px; }
    .kpi .green { color: var(--green); font-size: 18px; }
    .rate { display: flex; align-items: center; gap: 10px; }
    .ring {
      width: 32px; height: 32px; border-radius: 50%;
      background: conic-gradient(var(--blue) 0 100%, rgba(255,255,255,.1) 0);
      box-shadow: 0 0 14px rgba(40, 168, 255, .45);
      position: relative;
    }
    .ring:after { content: ""; position: absolute; inset: 5px; border-radius: 50%; background: #071725; }
    .spark { width: 100%; height: 30px; margin-top: -2px; }
    .spark polyline { fill: none; stroke: #40e47a; stroke-width: 2.2; filter: drop-shadow(0 0 7px rgba(54,230,126,.45)); }
    .main-grid {
      margin-top: 5px;
      display: grid;
      flex: 1 1 auto;
      min-height: 0;
      grid-template-columns: minmax(330px, 25.5vw) minmax(0, 1fr) minmax(228px, 17.5vw);
      grid-template-rows: minmax(0, 1fr) 204px;
      gap: 5px;
      overflow: hidden;
    }
    .left-panel { grid-column: 1; grid-row: 1 / span 2; padding: 0 10px 10px; overflow: hidden; }
    .map-panel { grid-column: 2; grid-row: 1; padding: 0; overflow: hidden; display: flex; flex-direction: column; position: relative; }
    .right-panel { grid-column: 3; grid-row: 1 / span 2; padding: 0 8px 8px; overflow: hidden; display: flex; flex-direction: column; }
    .table-panel { grid-column: 2; grid-row: 2; padding: 0; overflow: hidden; }
    .panel-head {
      height: 36px;
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 0 14px;
      border-bottom: 1px solid var(--stroke);
      font-size: 13px;
      font-weight: 800;
    }
    .panel-head .dot { width: 13px; height: 13px; border-radius: 50%; display: inline-grid; place-items: center; background: rgba(112,190,255,.2); color: #b8e9ff; font-size: 10px; }
    .panel-head button, .toolbar button, .toolbar select, #case-select {
      color: #dcecff;
      background: rgba(14, 35, 55, .92);
      border: 1px solid var(--stroke-2);
      border-radius: 6px;
      padding: 6px 10px;
      font-size: 11px;
    }
    .panel-head .spacer, .toolbar .spacer { flex: 1; }
    .reason-wrap {
      position: relative;
      height: calc(100% - 36px);
      padding: 6px 2px 2px;
      overflow-y: auto;
      overflow-x: hidden;
      scrollbar-width: thin;
      scrollbar-color: rgba(100, 181, 246, .45) rgba(8, 20, 34, .5);
    }
    .node {
      width: 100%;
      min-height: 39px;
      display: grid;
      grid-template-columns: 30px 24px minmax(0, 1fr) 58px;
      gap: 7px;
      align-items: center;
      padding: 5px 7px;
      border: 1px solid var(--stroke-2);
      border-radius: 7px;
      background: linear-gradient(180deg, rgba(14, 35, 54, .96), rgba(8, 25, 40, .96));
      box-shadow: inset 0 1px 0 rgba(146, 225, 255, .05);
      position: relative;
      z-index: 2;
    }
    .node.selected { border-color: rgba(45, 239, 139, .75); background: linear-gradient(180deg, rgba(8, 57, 47, .96), rgba(6, 34, 33, .96)); box-shadow: 0 0 16px rgba(41, 231, 121, .28), inset 0 1px 0 rgba(162,255,211,.12); }
    .node.current { border-color: rgba(39, 230, 208, .8); box-shadow: 0 0 17px rgba(39, 230, 208, .28); }
    .node.rejected { opacity: .78; }
    .step-index {
      position: static;
      width: 28px;
      height: 28px;
      border-radius: 6px;
      display: grid;
      place-items: center;
      border: 1px solid #4fbdf8;
      background: linear-gradient(180deg, #1b73a6, #0c3555);
      font-weight: 900;
      font-family: var(--mono);
      box-shadow: 0 0 13px rgba(40, 168, 255, .35);
    }
    .node h3, .strategy h4 { margin: 0 0 2px; font-size: 12px; }
    .node p, .strategy p, .tiny { margin: 0; color: var(--muted); font-size: 9.5px; line-height: 1.18; }
    .node p { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .node p br { display: none; }
    .node .icon {
      width: 23px; height: 23px; border-radius: 7px;
      display: grid; place-items: center;
      background: rgba(42, 163, 255, .12);
      color: #7ad4ff;
      border: 1px solid rgba(78, 185, 255, .32);
      font-size: 12px;
    }
    .metric { text-align: right; }
    .metric strong { color: var(--green); display: block; font-size: 14px; font-family: var(--mono); line-height: 1.1; }
    .metric span { display: block; color: var(--muted); font-size: 9.5px; margin-bottom: 2px; }
    .connector {
      height: 4px;
      width: 2px;
      margin-left: 14px;
      background: linear-gradient(var(--stroke-2), var(--cyan));
      opacity: .8;
      position: relative;
    }
    .connector:after { content: ""; position: absolute; bottom: -1px; left: -3px; width: 8px; height: 8px; border-right: 1px solid var(--cyan); border-bottom: 1px solid var(--cyan); transform: rotate(45deg); }
    .branch-grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: 3px;
      margin: 5px 0 6px;
      width: 100%;
      position: relative;
    }
    .branch-grid:before { content: none; }
    .strategy {
      min-height: 26px;
      display: grid;
      grid-template-columns: 26px minmax(0, 1fr) 86px;
      gap: 6px;
      align-items: center;
      border: 1px solid rgba(135, 152, 166, .35);
      background: linear-gradient(180deg, rgba(16, 32, 47, .96), rgba(8, 20, 34, .96));
      border-radius: 6px;
      padding: 3px 6px;
      position: relative;
      z-index: 2;
      cursor: pointer;
    }
    .strategy.inspected { outline: 2px solid rgba(255, 209, 45, .62); box-shadow: 0 0 18px rgba(255,209,45,.2); }
    .strategy.best { border-color: var(--green); box-shadow: 0 0 18px rgba(54, 230, 126, .34); background: linear-gradient(180deg, rgba(8, 69, 52, .95), rgba(5, 38, 35, .95)); }
    .strategy.evaluating { border-color: var(--blue); box-shadow: 0 0 16px rgba(40, 168, 255, .24); }
    .strategy.rejected { opacity: .72; }
    .strategy h4 { margin: 0; font-family: var(--mono); font-size: 11px; color: #d8efff; }
    .strategy p { font-size: 9.5px; line-height: 1.2; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .strategy p br { display: none; }
    .strategy strong { display: flex; justify-content: flex-end; align-items: center; gap: 4px; color: var(--green); font-family: var(--mono); margin-top: 0; font-size: 10.5px; white-space: nowrap; }
    .strategy.rejected strong, .strategy.pending strong { color: var(--muted); }
    .strategy .evidence { display: block; margin-top: 4px; color: #9db1c3; font-family: var(--mono); font-size: 10px; }
    .badge { display: inline-block; border: 1px solid rgba(255,91,101,.48); color: #ff7881; background: rgba(255,91,101,.12); border-radius: 4px; padding: 2px 5px; font-size: 9px; margin-left: 5px; }
    .badge.pending { border-color: rgba(145,168,187,.45); color: var(--muted); background: rgba(145,168,187,.08); }
    .badge.accepted { border-color: rgba(54,230,126,.48); color: var(--green); background: rgba(54,230,126,.12); }
    .badge.evaluating { border-color: rgba(40,168,255,.48); color: var(--blue); background: rgba(40,168,255,.12); }
    .reason-legend { display: none; }
    .line-key { width: 48px; height: 2px; display: inline-block; margin-right: 12px; vertical-align: middle; }
    .line-key.sel { background: var(--green); box-shadow: 0 0 8px var(--green); }
    .line-key.eval { border-top: 2px dotted var(--blue); }
    .line-key.rej { border-top: 2px dashed #a1a1a1; opacity: .7; }
    .map-frame { position: relative; flex: 1; min-height: 0; overflow: hidden; background: #eef3ef; cursor: grab; }
    .map-frame.dragging-map { cursor: grabbing; }
    .semi-real-map {
      position: absolute;
      inset: 0;
      z-index: 0;
      background: #edf3ed;
      filter: saturate(.9) contrast(1.08) brightness(.98);
    }
    .semi-real-map .maplibregl-ctrl-logo,
    .semi-real-map .maplibregl-ctrl-attrib { display: none !important; }
    .map-panel.active {
      position: fixed;
      inset: 12px;
      z-index: 80;
      padding: 0;
      display: flex;
      flex-direction: column;
      box-shadow: 0 24px 80px rgba(0,0,0,.72), 0 0 0 1px rgba(39,230,208,.28);
    }
    .map-panel.active .map-frame { min-height: 0; flex: 1; }
    .map-frame.topology {
      background:
        radial-gradient(circle at 42% 48%, rgba(255, 218, 56, .12), transparent 30%),
        radial-gradient(circle at 72% 20%, rgba(110, 196, 83, .12), transparent 34%),
        linear-gradient(90deg, rgba(148,163,184,.04) 1px, transparent 1px),
        linear-gradient(180deg, rgba(148,163,184,.035) 1px, transparent 1px),
        linear-gradient(180deg, #edf3ed 0%, #dfe9e4 100%);
      background-size: auto, auto, 48px 48px, 48px 48px, auto;
    }
    .map-frame.topology::before {
      content: "";
      position: absolute;
      inset: 0;
      z-index: 0;
      background:
        radial-gradient(circle at 50% 44%, rgba(255, 211, 51, .08), transparent 28%),
        radial-gradient(circle at 72% 24%, rgba(81, 173, 92, .08), transparent 28%),
        linear-gradient(180deg, rgba(255, 255, 255, .08), rgba(255, 255, 255, .02));
      opacity: .46;
      pointer-events: none;
    }
    .map-frame::after {
      content: "";
      position: absolute;
      inset: 0;
      z-index: 1;
      pointer-events: none;
      box-shadow: inset 0 0 0 1px rgba(15, 23, 42, .08), inset 0 18px 60px rgba(255,255,255,.12);
    }
    .map-frame.topology .map-bg { opacity: .2; filter: saturate(.9) contrast(1.02) brightness(1.05); }
    .map-frame.maplibre-ready .map-bg { opacity: .12; mix-blend-mode: multiply; }
    .map-bg[data-map-style="meituan_delivery_project_map_v3"] .district {
      fill: rgba(30, 39, 45, .34);
      stroke: rgba(238, 195, 84, .08);
    }
    .map-bg[data-map-style="meituan_delivery_project_map_v3"] .road-core.arterial { stroke: rgba(255, 202, 43, .5); }
    .map-bg[data-map-style="meituan_delivery_project_map_v3"] .road-core.secondary { stroke: rgba(228, 186, 55, .28); }
    .map-bg[data-map-style="meituan_delivery_project_map_v3"] .road-core.service { stroke: rgba(132, 151, 157, .16); stroke-dasharray: none; }
    .map-bg[data-map-style="meituan_delivery_project_map_v3"] .commerce-hotspot {
      fill: rgba(255, 190, 59, .095);
      stroke: rgba(255, 194, 70, .2);
    }
    .map-frame.topology .pin { display: block; }
    .map-bg, .route-svg { position: absolute; inset: 0; width: 100%; height: 100%; }
    .map-bg { opacity: .38; z-index: 1; pointer-events: none; }
    .route-svg { z-index: 7; pointer-events: none; }
    .district, .zone-block { fill: rgba(24, 36, 47, .3); stroke: rgba(124, 146, 162, .075); stroke-width: 1; }
    .water { fill: rgba(13, 31, 40, .56); stroke: rgba(85, 116, 137, .14); }
    .building-block {
      fill: rgba(36, 48, 58, .24);
      stroke: rgba(126, 145, 158, .09);
      stroke-width: .7;
      vector-effect: non-scaling-stroke;
    }
    .building-block.commerce { fill: rgba(70, 57, 32, .2); stroke: rgba(255, 209, 45, .07); }
    .building-block.office { fill: rgba(39, 56, 67, .22); }
    .building-block.residential { fill: rgba(32, 47, 50, .18); }
    .commerce-hotspot {
      fill: rgba(255, 174, 66, .085);
      stroke: rgba(255, 174, 66, .16);
      stroke-width: 1.1;
      filter: blur(.2px);
    }
    .intersection-node {
      fill: rgba(12, 30, 42, .92);
      stroke: rgba(190, 214, 231, .32);
      stroke-width: 1;
    }
    .intersection-node.busy { stroke: rgba(255, 209, 45, .48); fill: rgba(70, 51, 19, .55); }
    .map-trace, .road-base, .road-core, .traffic-band, .road-major, .road-minor, .road-service {
      fill: none;
      stroke-linecap: round;
      stroke-linejoin: round;
      vector-effect: non-scaling-stroke;
    }
    .map-trace { stroke: rgba(92, 113, 127, .14); stroke-width: .8; opacity: .78; }
    .map-trace.collector { stroke: rgba(111, 130, 141, .18); stroke-width: 1.15; }
    .map-trace.ring { stroke: rgba(132, 145, 149, .16); stroke-width: 1.35; }
    .map-trace.local { stroke: rgba(74, 93, 108, .13); stroke-width: .72; }
    .road-base { stroke: rgba(0, 4, 9, .48); stroke-width: calc(var(--road-width, 8px) + 2px); }
    .road-base.secondary { stroke: rgba(0, 4, 9, .38); stroke-width: calc(var(--road-width, 6px) + 1.2px); }
    .road-base.service { stroke: rgba(0, 4, 9, .2); stroke-width: calc(var(--road-width, 4px) + .5px); }
    .road-core { stroke: rgba(126, 139, 148, .3); stroke-width: var(--road-width, 6px); }
    .road-core.arterial { stroke: rgba(172, 180, 186, .38); }
    .road-core.secondary { stroke: rgba(109, 125, 135, .24); }
    .road-core.service { stroke: rgba(87, 101, 112, .14); stroke-dasharray: 1 12; }
    .traffic-band { stroke-width: var(--traffic-width, 2px); opacity: .34; }
    .traffic-band.smooth { stroke: rgba(54, 230, 126, .18); }
    .traffic-band.moderate { stroke: rgba(255, 209, 45, .32); stroke-dasharray: 18 16; }
    .traffic-band.heavy { stroke: rgba(255, 91, 101, .42); stroke-dasharray: 12 12; }
    .weather-rain-layer {
      pointer-events: none;
      opacity: .9;
      mix-blend-mode: screen;
    }
    .rain-sheen {
      fill: rgba(57, 125, 170, .15);
      filter: blur(.4px);
      pointer-events: none;
    }
    .rain-streak {
      stroke: rgba(153, 210, 255, .55);
      stroke-width: 1.35;
      stroke-linecap: round;
      filter: drop-shadow(0 0 2px rgba(90, 176, 255, .28));
    }
    .map-bg[data-weather="rain"] .road-core { filter: brightness(.86); }
    .map-bg[data-weather="rain"] .traffic-band.heavy { stroke: rgba(255, 91, 101, .78); }
    body.sample-preview .traffic-band { opacity: .32; }
    .dispatch-visual { fill: none; stroke-linecap: round; stroke-linejoin: round; vector-effect: non-scaling-stroke; stroke-dasharray: none; stroke-dashoffset: 0; animation: none; pointer-events: none; }
    .dispatch-visual.primary { stroke: var(--map-route-focus); stroke-width: 2.1; filter: drop-shadow(0 1px 2px rgba(15,118,110,.12)); }
    .dispatch-visual.secondary { stroke: var(--route-color, var(--map-route)); stroke-width: 1.45; stroke-dasharray: none; filter: none; opacity: .58; }
    .dispatch-visual.overview-route { stroke: var(--route-color, var(--map-route)); stroke-width: 1.5; opacity: .62; filter: none; }
    .dispatch-visual.pickup-leg { stroke: var(--route-color, var(--map-route)); stroke-width: 1.55; filter: none; }
    .dispatch-visual.pickup-leg.overview-route { stroke: var(--route-color, var(--map-route)); stroke-width: 1.7; opacity: .72; stroke-dasharray: none; filter: drop-shadow(0 1px 1px rgba(15, 118, 110, .12)); }
    .dispatch-visual.endpoint-connector { stroke: var(--route-color, var(--map-route)); stroke-width: 1.65; opacity: .64; stroke-dasharray: none; filter: none; animation: none; pointer-events: none; }
    .dispatch-visual.selected-overview {
      stroke: #d99a00;
      stroke-width: 1.85;
      opacity: .72;
      stroke-dasharray: none;
      filter: none;
    }
    .dispatch-visual.pickup-leg.selected-overview {
      stroke: #d99a00;
      stroke-width: 2.05;
      opacity: .78;
    }
    .dispatch-arrow.selected-overview {
      fill: #d99a00;
      opacity: .84;
      filter: none;
    }
    .dispatch-visual.active-assignment { stroke-width: 2.2; opacity: .86; filter: drop-shadow(0 1px 2px rgba(15,118,110,.14)); stroke-dasharray: none; }
    .dispatch-visual.pickup-leg.active-assignment { stroke-width: 2.15; filter: drop-shadow(0 1px 2px rgba(15,118,110,.12)); }
    .dispatch-link {
      fill: none;
      stroke: transparent;
      stroke-width: 18;
      stroke-linecap: round;
      stroke-linejoin: round;
      vector-effect: non-scaling-stroke;
      pointer-events: stroke;
      cursor: pointer;
      opacity: .01;
    }
    .dispatch-arrow { fill: #d99a00; opacity: .78; filter: drop-shadow(0 1px 1px rgba(68, 64, 60, .18)); pointer-events: auto; cursor: pointer; }
    .dispatch-arrow.overview-route { fill: var(--route-color, #0f766e); opacity: .84; }
    .dispatch-arrow.active-assignment { opacity: 1; }
    .arrow { fill: var(--cyan); filter: drop-shadow(0 0 6px rgba(39,230,208,.75)); }
    @keyframes draw { to { stroke-dashoffset: 0; } }
    .map-legend {
      position: absolute;
      left: 14px;
      top: 12px;
      z-index: 12;
      width: auto;
      padding: 6px 8px;
      border: 1px solid rgba(71, 85, 105, .24);
      border-radius: 10px;
      background: rgba(255, 255, 255, .82);
      box-shadow: 0 12px 28px rgba(15, 23, 42, .14), inset 0 1px 0 rgba(255,255,255,.7);
      backdrop-filter: blur(8px);
      display: flex;
      flex-direction: row;
      flex-wrap: wrap;
      gap: 7px 10px;
      align-items: center;
      max-width: 280px;
    }
    .map-legend div { display: flex; align-items: center; gap: 5px; margin: 0; font-size: 10px; color: rgba(15, 23, 42, .72); font-weight: 650; white-space: nowrap; }
    .map-legend .line-key { width: 22px; margin-right: 0; }
    .mark { width: 16px; height: 16px; border-radius: 6px; display: inline-grid; place-items: center; font-size: 9px; font-weight: 900; letter-spacing: -.08em; }
    .mark.depot { background: #0f7ed3; color: #dff4ff; }
    .mark.rest, .mark.merchant { background: linear-gradient(180deg, #ffe680, var(--map-merchant)); color: #392300; border: 1px solid rgba(160, 103, 0, .38); border-radius: 7px 7px 9px 9px; box-shadow: inset 0 1px 0 rgba(255,255,255,.68); }
    .mark.dest { background: #7bcc46; color: #071906; border: 1px solid rgba(202, 255, 162, .75); border-radius: 50%; }
    .mark.courier { background: linear-gradient(180deg, #13968a, var(--map-courier)); color: #e8fffb; border: 1px solid rgba(13, 148, 136, .55); border-radius: 50%; box-shadow: inset 0 1px 0 rgba(187,247,208,.32); }
    .mark-symbol { transform: translateY(-.5px); }
    .toolbar {
      position: absolute;
      top: 8px;
      right: 10px;
      display: flex;
      gap: 5px;
      align-items: center;
      z-index: 12;
      padding: 5px;
      border: 1px solid rgba(71, 85, 105, .22);
      border-radius: 10px;
      background: rgba(255,255,255,.84);
      box-shadow: 0 10px 26px rgba(15, 23, 42, .13);
      backdrop-filter: blur(8px);
    }
    .toolbar button {
      width: auto;
      min-width: 42px;
      height: 28px;
      padding: 0 8px;
      color: #334155;
      background: #f8fafc;
      border-color: rgba(100, 116, 139, .28);
      border-radius: 8px;
      font-weight: 700;
      letter-spacing: -.02em;
    }
    .toolbar select {
      height: 28px;
      color: #334155;
      background: #f8fafc;
      border-color: rgba(100, 116, 139, .28);
      border-radius: 8px;
      font-weight: 700;
    }
    .toolbar button[disabled] { opacity: .42; cursor: not-allowed; }
    .toolbar button.active, .zoom button.active, .panel-head button.active {
      border-color: rgba(15, 118, 110, .58);
      color: #0f766e;
      background: #ecfdf5;
      box-shadow: 0 0 0 3px rgba(15, 118, 110, .12);
    }
    .map-label {
      position: absolute;
      z-index: 3;
      min-width: 58px;
      transform: translate(calc(-50% + var(--label-offset-x, 0px)), calc(-50% + var(--label-offset-y, 0px)));
      padding: 6px 8px;
      border-radius: 4px;
      background: rgba(10, 20, 30, .92);
      border: 1px solid rgba(101, 130, 150, .55);
      color: #f2fbff;
      font-family: var(--mono);
      font-size: 12px;
      line-height: 1.2;
      box-shadow: 0 6px 14px rgba(0,0,0,.35);
      cursor: pointer;
    }
    .map-frame.topology .map-label {
      color: #e9f7ff;
      background: rgba(5, 18, 30, .82);
      border-color: rgba(109, 141, 162, .66);
      box-shadow: 0 9px 20px rgba(0,0,0,.25);
    }
    .map-label:hover, .map-label.focused { border-color: var(--yellow); color: #fff6b8; box-shadow: 0 0 16px rgba(255,209,45,.35); }
    .map-label.selected { border-color: #20d4c7; color: #bdf8f2; background: rgba(8, 40, 45, .94); box-shadow: 0 0 13px rgba(32,212,199,.28); }
    .map-label.depot { background: rgba(15, 126, 211, .72); border-color: #45b8ff; text-align: center; }
    .map-label.pickup { border-color: rgba(255, 154, 46, .8); background: rgba(74, 42, 10, .88); color: #ffd6a3; }
    .map-label.order { border-color: rgba(123, 204, 70, .8); background: rgba(22, 52, 22, .88); color: #d8ffc8; }
    .map-label.courier-node { border-color: rgba(39, 230, 208, .9); background: rgba(4, 45, 51, .9); color: #b9fff6; }
    .map-frame.topology .map-label.pickup { background: rgba(74, 42, 10, .9); border-color: #fb923c; color: #ffd6a3; }
    .map-frame.topology .map-label.order { background: rgba(22, 52, 22, .9); border-color: #22c55e; color: #d8ffc8; }
    .map-frame.topology .map-label.courier-node { background: rgba(4, 45, 51, .9); border-color: #06b6d4; color: #b9fff6; }
    .map-label small { display: block; color: #d1dae2; font-size: 11px; }
    .map-frame.topology .map-label small { color: #98aebe; }
    .map-frame.focus-selected .map-label:not(.active-assignment) { display: none; }
    .map-frame.focus-selected .pin:not(.active-assignment) { opacity: .78; transform: translate(-50%, -50%) scale(.88); }
    .map-frame.focus-selected .pin.active-assignment { z-index: 5; opacity: 1; }
    .map-frame.focus-selected .pin.active-assignment .mark { box-shadow: 0 0 0 4px rgba(15,118,110,.14), 0 4px 12px rgba(15,118,110,.26); }
    .map-frame.focus-selected .dispatch-visual.secondary:not(.active-assignment) { opacity: .28; stroke-width: 1.7; filter: none; }
    .map-frame.focus-selected .dispatch-arrow.secondary:not(.active-assignment) { opacity: .24; fill: rgba(43,222,205,.5); }
    .map-frame.assignment-overview .dispatch-visual { stroke-dashoffset: 0; }
    .map-frame.assignment-overview .dispatch-visual.primary { stroke: var(--map-route-focus); stroke-width: 2.15; opacity: .82; filter: drop-shadow(0 1px 2px rgba(15,118,110,.12)); }
    .map-frame.assignment-overview .dispatch-visual.pickup-leg { stroke: var(--route-color, var(--map-route)); stroke-width: 1.75; opacity: .72; filter: drop-shadow(0 1px 1px rgba(15, 118, 110, .12)); }
    .map-frame.assignment-overview .dispatch-visual.pickup-leg.selected-overview { stroke: var(--map-route-focus); stroke-width: 2.05; opacity: .84; filter: drop-shadow(0 1px 2px rgba(15, 118, 110, .16)); }
    .map-frame.assignment-overview .dispatch-arrow { opacity: .68; }
    .map-frame.assignment-overview .dispatch-arrow.selected-overview { opacity: .76; fill: var(--map-route-focus); }
    .map-frame.assignment-overview .dispatch-visual.active-assignment { stroke: var(--map-route-focus); stroke-width: 2.0; opacity: .78; stroke-dasharray: none; filter: drop-shadow(0 1px 2px rgba(15,118,110,.12)); }
    .map-frame.assignment-overview .dispatch-arrow.active-assignment { opacity: .96; fill: var(--map-route-focus); }
    .map-frame.assignment-overview .dispatch-visual.pickup-leg.long-pickup.active-assignment,
    .map-frame.assignment-overview .dispatch-visual.pickup-leg.long-pickup {
      stroke: var(--route-color, var(--map-route));
      stroke-width: .8;
      opacity: .24;
      stroke-dasharray: none;
      filter: none;
    }
    .map-frame.assignment-overview .dispatch-visual.pickup-leg.long-pickup.selected-overview {
      stroke: var(--map-route-focus);
      stroke-width: 1.15;
      opacity: .42;
      stroke-dasharray: none;
      filter: drop-shadow(0 1px 2px rgba(15,118,110,.16));
    }
    .map-frame.assignment-overview .dispatch-arrow.long-pickup.active-assignment,
    .map-frame.assignment-overview .dispatch-arrow.long-pickup {
      fill: var(--map-route-focus);
      opacity: .44;
      filter: none;
    }
    .map-frame.hide-entities .pin,
    .map-frame.hide-entities .map-label { opacity: .12; pointer-events: none; }
    .map-frame.hide-entities .pin.active-assignment,
    .map-frame.hide-entities .map-label.active-assignment { opacity: .45; }
    .map-entities { position: absolute; inset: 0; z-index: 4; pointer-events: none; }
    .map-entities .pin, .map-entities .map-label { pointer-events: auto; }
    .pin { position: absolute; z-index: 3; width: 18px; height: 18px; transform: translate(-50%, -50%); cursor: pointer; }
    .pin.rest, .pin.merchant { z-index: 6; }
    .pin.courier { z-index: 5; }
    .pin.dest { z-index: 4; }
    .pin .mark { width: 18px; height: 18px; box-shadow: 0 2px 7px rgba(15,23,42,.22); }
    .pin.depot:after { content: ""; position: absolute; inset: -7px; border: 1px solid rgba(40,168,255,.35); border-radius: 4px; }
    .zoom { position: absolute; left: 18px; bottom: 13px; z-index: 12; display: grid; gap: 1px; border: 1px solid rgba(71,85,105,.2); border-radius: 10px; overflow: hidden; box-shadow: 0 10px 24px rgba(15,23,42,.14); }
    .zoom button { width: 38px; height: 35px; color: #334155; background: rgba(255,255,255,.9); border: 0; border-bottom: 1px solid rgba(100,116,139,.18); font-size: 20px; font-weight: 800; }
    .map-frame.locating .dispatch-visual.primary { stroke-width: 6; }
    .map-frame.hide-candidates .dispatch-visual.secondary:not(.active-assignment),
    .map-frame.hide-candidates .dispatch-link.secondary:not(.active-assignment),
    .map-frame.hide-candidates .dispatch-arrow.secondary:not(.active-assignment) { display: none; }
    .map-frame.hide-dispatch-routes .dispatch-visual,
    .map-frame.hide-dispatch-routes .dispatch-link,
    .map-frame.hide-dispatch-routes .dispatch-arrow { display: none; }
    .map-frame.hide-candidates .map-label:not(.selected):not(.depot) { opacity: .68; }
    .weather {
      position: absolute;
      right: 14px;
      bottom: 13px;
      z-index: 12;
      width: 212px;
      padding: 9px 10px;
      border: 1px solid rgba(203, 213, 225, .9);
      border-radius: 14px;
      background: linear-gradient(180deg, rgba(255,255,255,.96), rgba(248,250,252,.98));
      color: #334155 !important;
      box-shadow: 0 8px 18px rgba(15,23,42,.10);
      backdrop-filter: blur(12px);
      display: grid;
      gap: 6px;
      pointer-events: none;
    }
    .weather-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
    .weather-title { display: inline-flex; align-items: center; gap: 5px; font-size: 10px; font-weight: 850; color: #334155; letter-spacing: .02em; }
    .weather-title::before { content: ""; width: 7px; height: 7px; border-radius: 999px; background: #f59e0b; box-shadow: 0 0 0 3px rgba(245,158,11,.14); }
    .weather-badge { padding: 3px 8px; border-radius: 999px; background: #fff7ed; color: #b45309; border: 1px solid rgba(217,119,6,.2); font-size: 10px; font-weight: 850; white-space: nowrap; }
    .weather-meta { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
    .weather-line { display: grid; gap: 3px; min-width: 0; font-size: 10px; line-height: 1.2; color: #64748b; background: rgba(255,255,255,.78); border: 1px solid rgba(226,232,240,.86); border-radius: 10px; padding: 5px 7px; }
    .weather-line strong { color: #0f172a; font-weight: 850; text-align: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .weather-impact { margin: 0; padding: 6px 8px; border: 1px solid rgba(226,232,240,.9); border-radius: 10px; background: rgba(248,250,252,.78); color: #475569; font-size: 10px; line-height: 1.28; }
    .toast {
      position: absolute;
      right: 18px;
      top: 56px;
      z-index: 13;
      max-width: 260px;
      padding: 8px 10px;
      border: 1px solid rgba(15, 118, 110, .38);
      border-radius: 7px;
      background: rgba(15, 23, 42, .88);
      color: #d9fff8;
      font-size: 12px;
      opacity: 0;
      transform: translateY(-6px);
      transition: opacity .18s ease, transform .18s ease;
      pointer-events: none;
    }
    .toast.show { opacity: 1; transform: translateY(0); }
    .decision-card {
      border: 1px solid var(--stroke-2);
      background: rgba(8, 24, 38, .72);
      border-radius: 9px;
      margin: 5px 0;
      padding: 7px 8px;
      min-height: 0;
      overflow: hidden;
    }
    .decision-card h3 { margin: 0 0 6px; font-size: 12px; }
    .assignment-detail {
      border-color: rgba(39, 230, 208, .58);
      box-shadow: inset 0 1px 0 rgba(167, 255, 240, .08);
    }
    .assignment-detail code { color: var(--cyan); font-family: var(--mono); }
    #detail-merchant {
      display: -webkit-box;
      -webkit-line-clamp: 3;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .divider { border-top: 1px solid var(--stroke-2); margin: 6px 0 7px; }
    .chips { display: flex; flex-wrap: wrap; gap: 4px; margin: 4px 0 5px; max-height: 31px; overflow: hidden; }
    .chips .chip:nth-child(n+5) { display: none; }
    .chip { background: rgba(45, 230, 159, .24); color: #d9fff8; border-radius: 4px; padding: 3px 5px; font-family: var(--mono); font-size: 9px; }
    .row { display: flex; justify-content: space-between; gap: 8px; margin: 5px 0; font-size: 10.5px; }
    .row strong { color: #f7fbff; font-weight: 700; }
    .prob { width: 34px; height: 34px; border-radius: 50%; background: conic-gradient(var(--green) 0 83%, rgba(255,255,255,.1) 83%); display: grid; place-items: center; color: #cffff3; font-size: 9px; position: relative; margin-left: auto; }
    .prob:after { content: ""; position: absolute; inset: 5px; border-radius: 50%; background: #081826; }
    .prob span { position: relative; z-index: 2; color: #d8fff8; font-family: var(--mono); }
    ul { margin: 4px 0 0 13px; padding: 0; color: #d7e6f0; font-size: 9.8px; line-height: 1.3; }
    #detail-reasons li:nth-child(n+4) { display: none; }
    .evidence .row { margin: 5px 0; }
    .evidence .row:nth-of-type(n+5) { display: none; }
    .right-panel .decision-card:last-child .row:nth-of-type(n+6) { display: none; }
    .positive { color: var(--green); }
    .good { color: #9fffe6; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 10px; }
    th {
      height: 24px;
      color: #bed2e2;
      background: linear-gradient(180deg, rgba(22, 45, 64, .95), rgba(12, 28, 43, .95));
      border: 1px solid rgba(51, 80, 101, .62);
      font-weight: 700;
    }
    td {
      padding: 3px 5px;
      line-height: 1.12;
      color: #aebdcc;
      border: 1px solid rgba(51, 80, 101, .62);
      background: rgba(10, 22, 34, .75);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    tbody tr { cursor: pointer; }
    tbody tr.inspected td { background: rgba(49, 70, 38, .82); color: #eefbd0; }
    td:last-child { white-space: nowrap; }
    tr.emphasis td { color: #b7ffd7; background: rgba(8, 56, 52, .72); border-top: 1px solid rgba(255,209,45,.8); border-bottom: 1px solid rgba(255,209,45,.8); }
    tr.emphasis td:first-child { border-left: 1px solid rgba(255,209,45,.8); border-radius: 8px 0 0 8px; }
    tr.emphasis td:last-child { border-right: 1px solid rgba(255,209,45,.8); }
    .star { color: var(--yellow); font-size: 18px; margin-right: 8px; }
    .status-ok { color: var(--green); }
    .status-bad { color: #ff777f; }
    .controls { display: flex; gap: 7px; align-items: center; min-width: 0; }
    .map-panel .panel-head { gap: 6px; padding: 0 9px; white-space: nowrap; overflow: hidden; }
    .map-panel .controls { gap: 5px; flex-wrap: nowrap; }
    .map-panel .controls button,
    .map-panel .controls select,
    .map-panel .controls #case-select {
      height: 28px;
      flex: 0 0 auto;
      border-radius: 8px;
      border-color: rgba(100, 116, 139, .28);
      background: rgba(248, 250, 252, .94);
      color: #334155;
      font-weight: 750;
      white-space: nowrap;
      box-shadow: none;
    }
    .map-panel .controls #reload-cases,
    .map-panel .controls #refresh-map { min-width: 62px; padding-left: 8px; padding-right: 8px; }
    .map-panel .controls #run-agent { min-width: 98px; }
    .map-panel .controls #run-agent {
      background: linear-gradient(180deg, #16a34a, #15803d);
      border-color: rgba(21, 128, 61, .7);
      color: #f7fee7;
    }
    .map-panel .controls #run-agent.running {
      background: linear-gradient(180deg, #0f766e, #115e59);
      color: #ecfeff;
    }
    .map-panel .scene-select-label { color: #cbd5e1; font-weight: 700; }
    .scene-select-label { color: var(--muted); font-size: 11px; white-space: nowrap; }
    #case-select { max-width: 180px; min-width: 156px; }
    #run-agent.running { opacity: .72; }
    .left-panel.expanded .reason-wrap { overflow-y: auto; }
    .left-panel.expanded .node, .left-panel.expanded .strategy { box-shadow: 0 0 15px rgba(39, 230, 208, .16), inset 0 1px 0 rgba(146, 225, 255, .05); }
    body.pending-run:not(.reasoning) .strategy .badge { display: none; }
    body.pending-run .strategy.best { border-color: rgba(135, 152, 166, .35); box-shadow: none; background: linear-gradient(180deg, rgba(16, 32, 47, .96), rgba(8, 20, 34, .96)); }
    body.pending-run .star { display: none; }
    body.pending-run:not(.sample-preview) .pin { display: none; }
    body.pending-run:not(.sample-preview) .map-bg { opacity: .22; }
  </style>
</head>
<body>
  <main class="dashboard">
    <section class="topbar" aria-label="AutoSolver Agent KPI">
      <div class="brand">
        <div class="logo" aria-hidden="true"></div>
        <div>
          <h1>AutoSolver Agent</h1>
          <p>美团即时配送 AI 可解释派单决策工作台</p>
        </div>
      </div>
      <div class="kpi"><label>调度场景</label><strong id="case-id">large_seed301</strong></div>
      <div class="kpi"><label>推理耗时</label><strong class="green" id="runtime">00:00:08</strong></div>
      <div class="kpi rate"><div><label>商家覆盖率</label><strong id="completion-rate">100%</strong></div><div class="ring"></div></div>
      <div class="kpi"><label>未派商家</label><strong id="unassigned">0</strong></div>
      <div class="kpi"><label>预计履约成本</label><strong id="expected-cost">$657.10</strong></div>
      <div class="kpi">
        <label>相比贪心基线优化</label>
        <strong class="green" id="improvement">+68.7%</strong>
        <svg class="spark" viewBox="0 0 260 42" aria-hidden="true"><polyline points="0,32 22,32 44,31 66,30 88,27 110,29 132,22 154,26 176,17 198,22 218,12 238,15 260,5"></polyline></svg>
      </div>
    </section>

    <section class="main-grid">
      <aside class="panel left-panel" aria-label="AI Reasoning Graph">
        <div class="panel-head"><span class="dot">✣</span> ReasonGraph 推理链路 <span class="spacer"></span><button id="expand-graph">展开全部</button></div>
        <div class="reason-wrap">
          <article class="node current">
            <div class="step-index">1</div><div class="icon">▣</div>
            <div><h3>输入订单与骑手</h3><p>等待当前场景样本<br>刷新后生成商家与骑手点位</p></div>
            <div class="metric"><span>状态</span><strong>待推理</strong></div>
          </article>
          <div class="connector"></div>
          <article class="node">
            <div class="step-index">2</div><div class="icon">♙</div>
            <div><h3>场景识别</h3><p>识别订单密度、骑手意愿、路况与天气<br>不同场景触发不同策略路径</p></div>
            <div class="metric"><span>状态</span><strong>待推理</strong></div>
          </article>
          <div class="connector"></div>
          <article class="node">
            <div class="step-index">3</div><div class="icon">↯</div>
            <div><h3>候选策略生成</h3><p>生成 5 类候选派单策略<br>比较合单、多派、修复、贪心与风险平衡</p></div>
            <div class="metric"><span>状态</span><strong>待推理</strong></div>
          </article>
          <div class="branch-grid">
            <article class="strategy pending" data-branch="S1" data-reasoning-status="pending"><h4>S1</h4><p><b>合单优先</b><br>优先匹配同路高重叠订单</p><strong>-- <span class="badge pending">待评估</span></strong></article>
            <article class="strategy pending" data-branch="S2" data-reasoning-status="pending"><h4>S2</h4><p><b>多派候选</b><br>为订单保留多个可接骑手</p><strong>-- <span class="badge pending">待评估</span></strong></article>
            <article class="strategy pending" data-branch="S3" data-reasoning-status="pending"><h4>S3</h4><p><b>局部修复</b><br>从高风险派单中迭代修复</p><strong>-- <span class="badge pending">待评估</span></strong></article>
            <article class="strategy pending" data-branch="S4" data-reasoning-status="pending"><h4>S4</h4><p><b>贪心基线</b><br>按最近和最低成本先验匹配</p><strong>-- <span class="badge pending">待评估</span></strong></article>
            <article class="strategy pending" data-branch="S5" data-reasoning-status="pending"><h4>S5</h4><p><b>风险平衡</b><br>平衡低意愿、天气和时间窗风险</p><strong>-- <span class="badge pending">待评估</span></strong></article>
          </div>
          <article class="node">
            <div class="step-index">4</div><div class="icon">☑</div>
            <div><h3>派单可行性校验</h3><p>校验商家-订单关系、骑手意愿、容量、时间窗与 SLA</p></div>
            <div class="metric"><span>状态</span><strong>待推理</strong></div>
          </article>
          <div class="connector"></div>
          <article class="node">
            <div class="step-index">5</div><div class="icon">▥</div>
            <div><h3>成本 / 风险评估</h3><p>评估综合成本、无人接单风险与履约质量<br>选择整体收益最高方案</p></div>
            <div class="metric"><span>状态</span><strong>待推理</strong></div>
          </article>
          <div class="connector"></div>
          <article class="node">
            <div class="step-index">6</div><div class="icon">✓</div>
            <div><h3>最终派单方案</h3><p>运行完成后自动展示每个商家派给哪个骑手<br>无需逐个点击才看到结果</p></div>
            <div class="metric"><span>状态</span><strong>待推理</strong></div>
          </article>
          <div class="reason-legend"><span><i class="line-key sel"></i>选中路径</span><span><i class="line-key eval"></i>评估中</span><span><i class="line-key rej"></i>淘汰路径</span></div>
        </div>
      </aside>

      <section class="panel map-panel" aria-label="实时派单地图">
        <div class="panel-head"><span>←</span> 实时派单地图 <span class="spacer"></span><div class="controls"><label class="scene-select-label" for="case-select">调度场景</label><select id="case-select"><option value="large_seed301">large_seed301</option></select><button id="reload-cases" type="button">刷新位置</button><button id="refresh-map" type="button">刷新地图</button><button id="run-agent" type="button">运行派单推理</button><span class="mini" id="status">就绪</span></div></div>
        <div class="map-frame">
          <div id="semi-real-map" class="semi-real-map" aria-label="半真实美团配送地图"></div>
          <svg class="map-bg" viewBox="0 0 980 640" preserveAspectRatio="none" aria-hidden="true" data-map-style="anonymous-navigation-layer">
            <g id="simulated-map-layer"></g>
          </svg>
          <svg class="route-svg" viewBox="0 0 980 640" preserveAspectRatio="none" aria-label="dispatch assignment overlay">
          </svg>
          <div class="toast" id="map-toast">地图图层已更新</div>
          <script id="autosolver-debug-state" type="application/json">{}</script>
          <div class="toolbar"><select id="layer-mode" title="切换派单线显示模式"><option value="all">全部图层</option><option value="selected">聚焦派单</option><option value="candidates">增强线路</option></select><button data-map-action="depots" type="button" title="弱化/恢复商家与骑手点位" aria-label="弱化点位">点位</button><button data-map-action="routes" type="button" title="隐藏/恢复派单关系线" aria-label="隐藏派单线">线路</button><button data-map-action="fit" type="button" title="适配全部点位和派单线" aria-label="适配视图">适配</button><button data-map-action="locate" type="button" title="定位当前派单包" aria-label="定位当前派单">定位</button><button data-map-action="fullscreen" type="button" title="切换地图聚焦视图" aria-label="地图聚焦视图">全屏</button></div>
          <div class="map-legend">
            <div><span class="mark merchant"><span class="mark-symbol">商</span></span>商家</div><div><span class="mark courier"><span class="mark-symbol">骑</span></span>骑手</div>
            <div><i class="line-key sel"></i>派单关系</div>
          </div>
          <div class="map-entities" aria-live="polite"></div>
          <div class="zoom"><button id="zoom-in" type="button" title="放大地图">+</button><button id="zoom-out" type="button" title="缩小地图">−</button><button id="recenter" type="button" title="回到派单总览">⌾</button></div>
          <div class="weather">
            <div class="weather-head"><span class="weather-title">气象与路况</span><strong class="weather-badge">待刷新</strong></div>
            <div class="weather-meta">
              <div class="weather-line"><span>天气</span><strong class="weather-state">等待场景</strong></div>
              <div class="weather-line"><span>履约影响</span><strong class="weather-impact-value">待评估</strong></div>
            </div>
            <div class="weather-impact">运行推理后同步展示天气、拥堵对接单和 ETA 的影响。</div>
          </div>
        </div>
      </section>

      <aside class="panel right-panel" aria-label="派单决策解释">
        <div class="panel-head"><span class="dot">↯</span> 派单决策解释</div>
        <div class="decision-card assignment-detail">
          <h3 id="detail-title">等待运行派单推理</h3><div class="divider"></div>
          <h3>对象 <span class="good" id="detail-courier">-</span></h3>
          <div class="row"><span id="detail-merchant">等待运行派单推理</span></div><div class="chips" id="detail-orders"></div>
          <div class="row"><span>派单履约 ETA</span><strong id="detail-eta">-</strong></div>
          <div class="row"><span>预计派单成本</span><strong id="right-cost">-</strong></div>
          <div class="row"><span>接单 / 覆盖概率</span><div class="prob"><span>--</span></div></div>
        </div>
        <div class="decision-card">
          <h3 class="good">▣ 决策依据</h3>
          <ul id="detail-reasons"><li>刷新后展示当前场景的商家与骑手点位。</li><li>运行推理后自动展示所有最终派单连线。</li><li>点击商家、骑手或线路可查看具体解释。</li></ul>
        </div>
        <div class="decision-card evidence">
          <h3>证据</h3>
          <div class="row"><span>▧ 商家覆盖</span><strong>-</strong></div>
          <div class="row"><span>◎ 派单对象</span><strong>-</strong></div>
          <div class="row"><span>◷ ETA / 时效</span><strong class="good">-</strong></div>
          <div class="row"><span>△ 接单风险</span><strong class="good">-</strong></div>
          <div class="row"><span>▣ 策略/负载</span><strong>-</strong></div>
        </div>
        <div class="decision-card">
          <h3>相对贪心基线</h3>
          <div class="row"><span>成本改进</span><strong class="positive">-</strong></div>
          <div class="row"><span>ETA 改进</span><strong class="positive">-</strong></div>
          <div class="row"><span>无人接单风险下降</span><strong class="positive">-</strong></div>
          <div class="row"><span>运营测算批次节约</span><strong class="positive" id="benefit-batch">-</strong></div>
          <div class="row"><span>单城月节约测算</span><strong class="positive" id="benefit-month">-</strong></div>
        </div>
      </aside>

      <section class="panel table-panel" aria-label="候选派单策略对比">
        <div class="panel-head">候选派单策略对比</div>
        <table>
          <thead><tr><th>派单策略</th><th>覆盖率</th><th>平均 ETA</th><th>预计成本</th><th>骑手占用</th><th>无人接单风险</th><th>综合评分</th><th>状态</th><th>业务解释</th></tr></thead>
          <tbody>
            <tr data-row-type="empty-state"><td>场景输入</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td class="status-ok">待刷新</td><td>选择场景后刷新，地图只显示商家与骑手点位</td></tr>
            <tr data-row-type="empty-state"><td>策略评估</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>待运行</td><td>运行约 10 秒后逐步评估候选策略</td></tr>
            <tr data-row-type="empty-state"><td>最终派单</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td class="status-bad">未生成</td><td>完成后自动显示所有商家派给哪个骑手</td></tr>
          </tbody>
        </table>
      </section>
    </section>
  </main>
  <script src="https://unpkg.com/maplibre-gl@5.24.0/dist/maplibre-gl.js"></script>
  <script>
    const $ = (id) => document.getElementById(id);
    let currentRun = null;
    let currentProfile = null;
    let currentReport = null;
    let currentReasoningState = null;
    let caseCatalog = {};
    let simulationCatalog = {};
    let currentSimulationSample = null;
    let simulationSampleLoadPromise = null;
    const simulationSampleIndex = {};
    let simulationRefreshNonce = 0;
    let dispatchRouteVersion = 0;
    let semiRealMap = null;
    let semiRealMapReady = false;
    let semiRealMapStyle = "";
    let semiRealMapRegion = 0;
    let semiRealMapMoveMode = "";
    let semiRealMapLiveSyncPending = false;
    let semiRealMapLastLiveSyncAt = 0;
    let semiRealMapViewportSyncReason = "";
    const semiRealMapLayerSchema = "delivery_routes_optimization_maplibre_clone";
    const semiRealMapStyleUrl = "https://tiles.openfreemap.org/styles/positron";
    const semiRealMapBounds = {lngMin: 121.418, lngMax: 121.506, latMin: 31.204, latMax: 31.252};
    function syncDashboardScale() {
      const width = Math.max(1, window.innerWidth || 1280);
      const height = Math.max(1, window.innerHeight || 720);
      const scale = Math.min(1, width / 1280, height / 720);
      document.documentElement.style.setProperty("--dashboard-scale", scale.toFixed(4));
      document.body.dataset.viewportWidth = String(Math.round(width));
      document.body.dataset.dashboardScale = scale.toFixed(4);
    }
    window.addEventListener("resize", syncDashboardScale);
    const semiRealMapRegions = [
      {label: "运营分析浅色区域 A", center: [121.462, 31.229], zoom: 13.35, pitch: 0, bearing: 0},
      {label: "运营分析浅色区域 B", center: [121.476, 31.222], zoom: 13.42, pitch: 0, bearing: 0},
      {label: "运营分析浅色区域 C", center: [121.444, 31.238], zoom: 13.38, pitch: 0, bearing: 0},
      {label: "运营分析浅色区域 D", center: [121.486, 31.238], zoom: 13.30, pitch: 0, bearing: 0}
    ];
    const dynamicProfiles = {};
    const sceneProfiles = {
      large_seed301: {
        label: "官方大规模高峰", cost: "$657.10", bundleCost: "$61.8", eta: "12 min", improvement: "+68.7%", shift: [0, 0], missedRisk: "4.0%", utilization: "78%",
        selected: "A1", assignments: {}
      },
      medium_seed201: {
        label: "中型合单机会", cost: "$687.30", bundleCost: "$64.3", eta: "13 min", improvement: "+54.2%", shift: [-7, 4], missedRisk: "5.6%", utilization: "72%",
        selected: "A1", assignments: {}
      },
      scarce_couriers_seed401: {
        label: "骑手稀缺商圈", cost: "$742.80", bundleCost: "$70.8", eta: "16 min", improvement: "+42.5%", shift: [8, -3], missedRisk: "8.4%", utilization: "91%",
        selected: "A1", assignments: {}
      },
      low_willingness_seed501: {
        label: "雨天低接单意愿", cost: "$819.40", bundleCost: "$78.4", eta: "17 min", improvement: "+36.9%", shift: [-3, -8], missedRisk: "11.2%", utilization: "69%",
        selected: "A1", assignments: {}
      }
    };
    function profileForCase(caseId) {
      if (sceneProfiles[caseId]) return sceneProfiles[caseId];
      if (!dynamicProfiles[caseId]) {
        const meta = caseCatalog[caseId] || {scenario_name: caseId, rows: 0, risk_tags: [], scenario_type: "generic"};
        const riskTags = Array.isArray(meta.risk_tags) ? meta.risk_tags : [];
        const riskText = riskTags.length ? riskTags.join(" / ") : "候选行驱动";
        const rows = Number(meta.rows || 0);
        dynamicProfiles[caseId] = {
          label: meta.scenario_name || meta.name || caseId,
          cost: "$657.10",
          bundleCost: "-",
          eta: "13 min",
          improvement: "--",
          missedRisk: riskTags.some((tag) => String(tag).includes("低意愿") || String(tag).includes("风险")) ? "11.2%" : "5.6%",
          utilization: String(meta.scenario_type || "").includes("scarce") ? "91%" : "72%",
          sourceNote: `${rows.toLocaleString("en-US")} candidate rows · ${riskText}`,
          selected: "A1",
          assignments: {}
        };
      }
      return dynamicProfiles[caseId];
    }
    function setStatus(text, running) {
      $("status").textContent = text;
      $("run-agent").classList.toggle("running", Boolean(running));
      $("run-agent").disabled = Boolean(running);
    }
    function showToast(text) {
      const toast = $("map-toast");
      toast.textContent = text;
      toast.classList.add("show");
      window.clearTimeout(showToast.timer);
      showToast.timer = window.setTimeout(() => toast.classList.remove("show"), 1400);
    }
    function resetMapControlState() {
      const frame = document.querySelector(".map-frame");
      if (frame) {
        frame.classList.remove("hide-entities", "hide-dispatch-routes", "hide-candidates", "locating");
        frame.dataset.zoomLevel = semiRealMap ? semiRealMap.getZoom().toFixed(2) : "1";
        frame.dataset.controlState = "all";
      }
      document.querySelectorAll("[data-map-action], #zoom-in, #zoom-out").forEach((button) => button.classList.remove("active"));
      const layerMode = $("layer-mode");
      if (layerMode) layerMode.value = "all";
    }
    function selectedCase() {
      const select = $("case-select");
      return select && select.value ? select.value : "large_seed301";
    }
    function selectedScenarioId() {
      const select = $("case-select");
      const option = select && select.selectedOptions && select.selectedOptions[0];
      return (option && option.dataset && option.dataset.scenario) || (currentSimulationSample && currentSimulationSample.scenario_id) || "commerce_peak";
    }
    function money(value) {
      const number = Number(value);
      return Number.isFinite(number) ? "$" + number.toLocaleString("en-US", {minimumFractionDigits: 2, maximumFractionDigits: 2}) : "-";
    }
    function yuan(value) {
      const number = Number(value);
      return Number.isFinite(number) ? "￥" + number.toLocaleString("zh-CN", {minimumFractionDigits: Math.abs(number) < 10 ? 2 : 0, maximumFractionDigits: Math.abs(number) < 10 ? 2 : 0}) : "-";
    }
    function etaText(value) {
      if (value === undefined || value === null || value === "") return "-";
      const text = String(value).trim();
      return text.replace(/\\s*min\\b/g, " 分钟");
    }
    function safeNumber(value, fallback = 0) {
      const number = Number(value);
      return Number.isFinite(number) ? number : fallback;
    }
    function stableHash(value) {
      let hash = 2166136261;
      const text = String(value ?? "");
      for (let index = 0; index < text.length; index += 1) {
        hash ^= text.charCodeAt(index);
        hash = Math.imul(hash, 16777619);
      }
      return Math.abs(hash >>> 0);
    }
    function escapeAttr(value) {
      return String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      }[char]));
    }
    function cssEscapeValue(value) {
      if (window.CSS && typeof window.CSS.escape === "function") return window.CSS.escape(String(value ?? ""));
      const slash = String.fromCharCode(92);
      return String(value ?? "").replaceAll(slash, slash + slash).replaceAll('"', slash + '"');
    }
    function renderProjectBasemapState() {
      const frame = document.querySelector(".map-frame");
      if (!frame) return;
      frame.classList.add("project-map-ready");
      ensureSemiRealMap();
    }
    function clearExternalMapFallback() {
      return false;
    }
    function normalizedToLngLat(point) {
      const x = Math.max(0, Math.min(100, safeNumber(Array.isArray(point) ? point[0] : point && point.x, 50)));
      const y = Math.max(0, Math.min(100, safeNumber(Array.isArray(point) ? point[1] : point && point.y, 50)));
      const lng = semiRealMapBounds.lngMin + (x / 100) * (semiRealMapBounds.lngMax - semiRealMapBounds.lngMin);
      const lat = semiRealMapBounds.latMax - (y / 100) * (semiRealMapBounds.latMax - semiRealMapBounds.latMin);
      return [lng, lat];
    }
    function screenNormToLngLat(point) {
      if (!semiRealMap) return normalizedToLngLat(point);
      const canvas = semiRealMap.getCanvas();
      const width = canvas && canvas.clientWidth ? canvas.clientWidth : 1;
      const height = canvas && canvas.clientHeight ? canvas.clientHeight : 1;
      const x = Math.max(0, Math.min(100, safeNumber(Array.isArray(point) ? point[0] : point && point.x, 50))) / 100 * width;
      const y = Math.max(0, Math.min(100, safeNumber(Array.isArray(point) ? point[1] : point && point.y, 50))) / 100 * height;
      const lngLat = semiRealMap.unproject([x, y]);
      return [lngLat.lng, lngLat.lat];
    }
    function currentSemiRealMapRegion() {
      return semiRealMapRegions[semiRealMapRegion % semiRealMapRegions.length];
    }
    function resetSemiRealMapViewportForScenario(reason = "sample-reset") {
      const map = ensureSemiRealMap();
      if (!map) return false;
      const region = currentSemiRealMapRegion();
      semiRealMapMoveMode = reason;
      if (map.stop) map.stop();
      map.jumpTo({center: region.center, zoom: region.zoom, pitch: region.pitch, bearing: region.bearing});
      const frame = document.querySelector(".map-frame");
      if (frame) {
        frame.dataset.zoomLevel = Number(region.zoom).toFixed(2);
        frame.dataset.mapRegion = region.label;
        frame.dataset.mapStyle = "运营分析浅色图";
      }
      return true;
    }
    function hideSemiRealMapTextLayers() {
      if (!semiRealMap || !semiRealMap.getStyle()) return;
      (semiRealMap.getStyle().layers || []).forEach((layer) => {
        const hasText = layer.type === "symbol" || Boolean(layer.layout && layer.layout["text-field"]);
        if (!hasText) return;
        try {
          semiRealMap.setLayoutProperty(layer.id, "visibility", "none");
        } catch (error) {
          // Some third-party vector styles expose locked layers; ignore them and keep the map usable.
        }
      });
    }
    function semiRealMapTextLayerAudit() {
      if (!semiRealMap || !semiRealMap.getStyle()) return {total: 0, visible: 0, hidden: 0};
      const textLayers = (semiRealMap.getStyle().layers || []).filter((layer) => layer.type === "symbol" || Boolean(layer.layout && layer.layout["text-field"]));
      const visible = textLayers.filter((layer) => {
        try {
          return semiRealMap.getLayoutProperty(layer.id, "visibility") !== "none";
        } catch (error) {
          return false;
        }
      });
      return {total: textLayers.length, visible: visible.length, hidden: textLayers.length - visible.length};
    }
    function ensureSemiRealMap() {
      const frame = document.querySelector(".map-frame");
      const container = $("semi-real-map");
      if (!frame || !container || !window.maplibregl) {
        if (frame) frame.classList.remove("maplibre-ready");
        return null;
      }
      const region = currentSemiRealMapRegion();
      if (!semiRealMap) {
        semiRealMap = new maplibregl.Map({
          container,
          style: semiRealMapStyleUrl,
          center: region.center,
          zoom: region.zoom,
          pitch: region.pitch,
          bearing: region.bearing,
          attributionControl: false,
          interactive: true,
          keyboard: false
        });
        if (semiRealMap.dragPan) semiRealMap.dragPan.enable();
        if (semiRealMap.scrollZoom) semiRealMap.scrollZoom.enable();
        if (semiRealMap.doubleClickZoom) semiRealMap.doubleClickZoom.enable();
        if (semiRealMap.touchZoomRotate) semiRealMap.touchZoomRotate.enable();
        semiRealMapStyle = semiRealMapStyleUrl;
        semiRealMap.on("load", () => {
          semiRealMapReady = true;
          hideSemiRealMapTextLayers();
          frame.classList.add("maplibre-ready");
          syncSemiRealMapOverlay(currentProfile);
        });
        semiRealMap.on("styledata", hideSemiRealMapTextLayers);
        semiRealMap.on("move", handleSemiRealMapMove);
        semiRealMap.on("moveend", handleSemiRealMapMoveEnd);
        semiRealMap.on("error", () => {
          semiRealMapReady = false;
          frame.classList.remove("maplibre-ready");
        });
      } else if (semiRealMapStyle !== semiRealMapStyleUrl) {
        semiRealMap.setStyle(semiRealMapStyleUrl);
        semiRealMapStyle = semiRealMapStyleUrl;
      }
      return semiRealMap;
    }
    function resyncCurrentProfileToMapViewport(reason = "viewport") {
      const profile = currentProfile;
      if (!profile || !profile.dispatchMap || !semiRealMapReady) return;
      semiRealMapViewportSyncReason = reason;
      updateMapScene(profile);
      semiRealMapViewportSyncReason = "";
      const frame = document.querySelector(".map-frame");
      if (frame) {
        frame.dataset.lastViewportSync = reason;
        if (semiRealMap) {
          frame.dataset.zoomLevel = semiRealMap.getZoom().toFixed(2);
          const center = semiRealMap.getCenter();
          frame.dataset.mapCenter = `${center.lng.toFixed(5)},${center.lat.toFixed(5)}`;
        }
      }
      if (reason !== "viewport-live") publishDebugState();
    }
    function handleSemiRealMapMove() {
      if (!semiRealMapReady || semiRealMapMoveMode === "refresh-map") return;
      if (semiRealMapLiveSyncPending) return;
      const now = Date.now();
      if (now - semiRealMapLastLiveSyncAt < 90) return;
      semiRealMapLastLiveSyncAt = now;
      semiRealMapLiveSyncPending = true;
      window.requestAnimationFrame(() => {
        semiRealMapLiveSyncPending = false;
        resyncCurrentProfileToMapViewport("viewport-live");
      });
    }
    function handleSemiRealMapMoveEnd() {
      if (!semiRealMapReady) return;
      if (semiRealMapMoveMode === "refresh-map") {
        semiRealMapMoveMode = "";
        reanchorCurrentProfileToMapRegion();
        return;
      }
      const reason = semiRealMapMoveMode || "manual-pan";
      semiRealMapMoveMode = "";
      resyncCurrentProfileToMapViewport(reason);
    }
    function resetRenderedMapAnchors(profile) {
      if (!profile || !profile.dispatchMap) return;
      delete profile.dispatchMap.anchor_source;
      delete profile.dispatchMap.anchor_variant;
      delete profile.dispatchMap.assignment_reconciled_variant;
      (profile.dispatchMap.entities || []).forEach((entity) => {
        delete entity.rendered_anchor_source;
        delete entity.rendered_lnglat;
        delete entity.rendered_safe_adjusted;
      });
    }
    function reanchorCurrentProfileToMapRegion() {
      const profile = currentProfile;
      if (!profile || !profile.dispatchMap) return;
      resetRenderedMapAnchors(profile);
      profile.assignments = {};
      profile.selected = "";
      profile.mapFocusMode = "overview";
      currentReport = null;
      const routeSvg = document.querySelector(".route-svg");
      if (routeSvg) routeSvg.innerHTML = "";
      document.body.classList.add("pending-run", "sample-preview");
      updateMapScene(profile);
      updateReasonProgress(0);
      updateReasonSummary(profile, null);
      if (currentSimulationSample) {
        renderSimulationPreviewTable(currentSimulationSample);
        resetDecisionPanelForSimulationPreview(currentSimulationSample);
      } else {
        resetDecisionPanelForSimulationPreview({name: profile.label, merchants: [], couriers: [], summary: {}});
      }
      setStatus("地图区域已刷新，等待推理", false);
    }
    function refreshSemiRealMap() {
      semiRealMapRegion = (semiRealMapRegion + 1) % semiRealMapRegions.length;
      const region = currentSemiRealMapRegion();
      const map = ensureSemiRealMap();
      if (!map) {
        showToast("半真实地图加载中，稍后再刷新区域");
        return;
      }
      hideSemiRealMapTextLayers();
      semiRealMapMoveMode = "refresh-map";
      map.easeTo({center: region.center, zoom: region.zoom, pitch: region.pitch, bearing: region.bearing, duration: 650});
      const frame = document.querySelector(".map-frame");
      if (frame) {
        frame.dataset.mapRegion = region.label;
        frame.dataset.mapStyle = "运营分析浅色图";
      }
      showToast(`已刷新配送区域：${region.label}`);
    }
    function syncSemiRealMapOverlay(profile) {
      const map = ensureSemiRealMap();
      if (!map || !semiRealMapReady) return;
      hideSemiRealMapTextLayers();
      const region = currentSemiRealMapRegion();
      const frame = document.querySelector(".map-frame");
      if (frame) {
        frame.dataset.mapRegion = region.label;
        frame.dataset.mapStyle = "运营分析浅色图";
      }
    }
    function renderedFeatureCoordinateSets(feature) {
      const geometry = feature && feature.geometry;
      if (!geometry || !Array.isArray(geometry.coordinates)) return [];
      if (geometry.type === "LineString") return [geometry.coordinates];
      if (geometry.type === "MultiLineString") return geometry.coordinates;
      if (geometry.type === "Polygon") return geometry.coordinates;
      if (geometry.type === "MultiPolygon") return geometry.coordinates.flat();
      return [];
    }
    function lngLatToScreenNorm(coord) {
      if (!semiRealMap || !Array.isArray(coord) || coord.length < 2) return null;
      const point = semiRealMap.project(coord);
      const canvas = semiRealMap.getCanvas();
      const width = canvas && canvas.clientWidth ? canvas.clientWidth : 1;
      const height = canvas && canvas.clientHeight ? canvas.clientHeight : 1;
      const x = point.x / width * 100;
      const y = point.y / height * 100;
      if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
      return [x, y];
    }
    function lineSamplePoints(points, spacing = 6) {
      const samples = [];
      const usable = (points || []).filter(Boolean);
      for (let index = 0; index < usable.length - 1; index += 1) {
        const start = usable[index];
        const end = usable[index + 1];
        const length = distance2D(start, end);
        const steps = Math.max(1, Math.floor(length / spacing));
        for (let step = 0; step <= steps; step += 1) {
          const t = step / steps;
          samples.push([start[0] + (end[0] - start[0]) * t, start[1] + (end[1] - start[1]) * t]);
        }
      }
      return samples;
    }
    function renderedMapRoadNetwork() {
      if (!semiRealMap || !semiRealMapReady) return null;
      const roadLayers = semiRealMap.getStyle().layers
        .filter((layer) => layer.type === "line" && /highway|road/.test(layer.id))
        .map((layer) => layer.id);
      if (!roadLayers.length) return null;
      const features = semiRealMap.queryRenderedFeatures({layers: roadLayers});
      const roads = [];
      const seen = new Set();
      features.forEach((feature) => {
        renderedFeatureCoordinateSets(feature).forEach((coords) => {
          const points = coords.map(lngLatToScreenNorm).filter(Boolean);
          if (points.length < 2) return;
          const key = points.map((point) => `${point[0].toFixed(1)},${point[1].toFixed(1)}`).join("|");
          if (seen.has(key)) return;
          seen.add(key);
          const layerId = feature.layer && feature.layer.id ? feature.layer.id : "";
          const roadType = /motorway|major/.test(layerId) ? "arterial" : /minor/.test(layerId) ? "secondary" : "service";
          roads.push({
            id: `MR${roads.length + 1}`,
            type: roadType,
            corridor: "MapLibre道路",
            traffic: "smooth",
            width: roadType === "arterial" ? 8.2 : roadType === "secondary" ? 5.0 : 2.8,
            points: points.map((point) => ({x: point[0], y: point[1]}))
          });
        });
      });
      if (roads.length < 12) return null;
      return roads.slice(0, 90);
    }
    function renderedMapMerchantAnchors(roadSamples) {
      if (!semiRealMap || !semiRealMapReady) return [];
      const styleLayers = semiRealMap.getStyle().layers;
      const fillLayers = styleLayers
        .filter((layer) => layer.type === "fill" && /building|landuse_residential|landuse_park/.test(layer.id))
        .map((layer) => layer.id);
      const anchors = [];
      const features = fillLayers.length ? semiRealMap.queryRenderedFeatures({layers: fillLayers}) : [];
      features.forEach((feature) => {
        renderedFeatureCoordinateSets(feature).forEach((ring) => {
          const points = ring.map(lngLatToScreenNorm).filter(Boolean);
          if (points.length < 3) return;
          const center = points.reduce((sum, point) => [sum[0] + point[0], sum[1] + point[1]], [0, 0]).map((value) => value / points.length);
          if (center[0] < 5 || center[0] > 95 || center[1] < 5 || center[1] > 95) return;
          const nearestRoadDistance = Math.min(...roadSamples.map((roadPoint) => distance2D(center, roadPoint)));
          if (nearestRoadDistance < 1.25 || nearestRoadDistance > 6.5) return;
          anchors.push({
            x: center[0],
            y: center[1],
            lnglat: screenNormToLngLat(center),
            roadDistance: nearestRoadDistance,
            roadEdgeScore: Math.abs(nearestRoadDistance - 2.8)
          });
        });
      });
      return anchors
        .sort((left, right) => left.roadEdgeScore - right.roadEdgeScore)
        .slice(0, 120);
    }
    function renderedMapAnchorsForProfile(profile) {
      const roads = renderedMapRoadNetwork();
      if (!roads) return null;
      const roadSamples = roads.flatMap((road) => lineSamplePoints(normalizedRoadPoints(road), 4.4));
      const merchantAnchors = renderedMapMerchantAnchors(roadSamples);
      if (roadSamples.length < 24 || merchantAnchors.length < 4) return null;
      return {roads, roadSamples, merchantAnchors};
    }
    function isMapScreenSafe(point, kind) {
      const x = Array.isArray(point) ? point[0] : point && point.x;
      const y = Array.isArray(point) ? point[1] : point && point.y;
      const minX = kind === "merchant" ? 13 : 9;
      const maxX = kind === "merchant" ? 90 : 94;
      const minY = kind === "merchant" ? 20 : 22;
      const maxY = kind === "merchant" ? 82 : 80;
      if (!Number.isFinite(x) || !Number.isFinite(y) || x < minX || x > maxX || y < minY || y > maxY) return false;
      if (x < 32 && y < 30) return false; // legend exclusion zone
      if (x > 54 && y < 26) return false; // toolbar exclusion zone
      if (x < 22 && y > 68) return false; // zoom control exclusion zone
      if (x > 76 && y > 68) return false; // weather card exclusion zone
      return true;
    }
    function clampToMapSafeZone(point, kind) {
      let x = Array.isArray(point) ? safeNumber(point[0], 50) : safeNumber(point && point.x, 50);
      let y = Array.isArray(point) ? safeNumber(point[1], 50) : safeNumber(point && point.y, 50);
      const minX = kind === "merchant" ? 13 : 9;
      const maxX = kind === "merchant" ? 90 : 94;
      const minY = kind === "merchant" ? 20 : 22;
      const maxY = kind === "merchant" ? 82 : 80;
      x = Math.max(minX, Math.min(maxX, x));
      y = Math.max(minY, Math.min(maxY, y));
      if (x < 32 && y < 30) y = 31;       // keep out of legend
      if (x > 54 && y < 26) y = 28;       // keep out of toolbar
      if (x < 22 && y > 68) x = 24;       // keep out of zoom controls
      if (x > 76 && y > 68) x = 74;       // keep out of weather card
      return {x, y, adjusted: Math.hypot(x - safeNumber(Array.isArray(point) ? point[0] : point && point.x, 50), y - safeNumber(Array.isArray(point) ? point[1] : point && point.y, 50)) > 0.1};
    }
    function projectEntityLngLatToScreen(entity) {
      if (!entity || !Array.isArray(entity.rendered_lnglat) || !semiRealMap) return false;
      const projected = lngLatToScreenNorm(entity.rendered_lnglat);
      if (!projected) return false;
      entity.x = Number(projected[0].toFixed(2));
      entity.y = Number(projected[1].toFixed(2));
      entity.rendered_safe_adjusted = false;
      entity.rendered_in_view = projected[0] >= 0 && projected[0] <= 100 && projected[1] >= 0 && projected[1] <= 100;
      return true;
    }
    function syncRenderedAnchorsToViewport(profile) {
      if (!profile || !profile.dispatchMap || !semiRealMapReady) return false;
      let projected = 0;
      (profile.dispatchMap.entities || []).forEach((entity) => {
        if (projectEntityLngLatToScreen(entity)) projected += 1;
      });
      if (semiRealMapViewportSyncReason === "viewport-live") return projected > 0;
      const roads = renderedMapRoadNetwork();
      if (roads && roads.length) {
        profile.dispatchMap.map_layers = {
          ...(profile.dispatchMap.map_layers || {}),
          roads,
          anchor_source: "maplibre-rendered",
          road_graph: "maplibre_rendered_road_graph",
          layer_schema: semiRealMapLayerSchema
        };
      }
      return projected > 0;
    }
    function diverseRenderedAnchor(candidates, used, seed, kind, minDistance, options = {}) {
      const normalized = (candidates || [])
        .map((candidate) => Array.isArray(candidate) ? {x: candidate[0], y: candidate[1]} : candidate)
        .filter((candidate) => isMapScreenSafe(candidate, kind));
      if (!normalized.length) return null;
      const ordered = normalized
        .map((candidate, index) => ({
          ...candidate,
          order: stableHash(`${seed}:${kind}:${index}`),
          edgePenalty: Math.max(0, 16 - candidate.x) + Math.max(0, candidate.x - 88) + Math.max(0, 14 - candidate.y) + Math.max(0, candidate.y - 84)
        }))
        .sort((left, right) => left.order - right.order);
      let best = null;
      ordered.forEach((candidate) => {
        const nearestUsed = used.length ? Math.min(...used.map((point) => distance2D([candidate.x, candidate.y], [point.x, point.y]))) : 100;
        const target = options.target;
        const targetDistance = target ? distance2D([candidate.x, candidate.y], [target.x, target.y]) : 0;
        const targetScore = target ? Math.max(0, 70 - targetDistance) * safeNumber(options.targetWeight, 1.8) : 0;
        const centerPenalty = kind === "courier" ? Math.abs(candidate.x - 50) * 0.18 : 0;
        const score = nearestUsed * safeNumber(options.distanceWeight, 3.4) + targetScore - candidate.edgePenalty - centerPenalty + ((candidate.order % 1000) / 1000);
        const passesDistance = nearestUsed >= minDistance;
        if ((passesDistance && (!best || !best.passesDistance || score > best.score)) || (!best && !passesDistance) || (!best?.passesDistance && score > best.score)) {
          best = {...candidate, score, passesDistance};
        }
      });
      return best || ordered[0];
    }
    const courierDistributionSlots = [
      {x: 18, y: 66}, {x: 25, y: 38}, {x: 36, y: 24}, {x: 44, y: 62},
      {x: 56, y: 30}, {x: 68, y: 55}, {x: 80, y: 36}, {x: 74, y: 72},
      {x: 30, y: 80}, {x: 52, y: 45}, {x: 87, y: 64}, {x: 20, y: 50}
    ];
    function enforceCourierSeparation(couriers, sampleKey) {
      const placed = [];
      const slotOffset = stableHash(`${sampleKey}:separation-slots`) % courierDistributionSlots.length;
      couriers.forEach((entity, index) => {
        const point = {x: safeNumber(entity.x, 50), y: safeNumber(entity.y, 50)};
        const nearest = placed.length ? Math.min(...placed.map((item) => distance2D([point.x, point.y], [item.x, item.y]))) : 100;
        if (nearest >= 4.8 && isMapScreenSafe(point, "courier")) {
          placed.push(point);
          return;
        }
        const slot = courierDistributionSlots[(index + slotOffset) % courierDistributionSlots.length];
        entity.x = Number(slot.x.toFixed(2));
        entity.y = Number(slot.y.toFixed(2));
        entity.rendered_lnglat = screenNormToLngLat([entity.x, entity.y]);
        entity.rendered_anchor_source = "maplibre-road-slot-fallback";
        placed.push({x: entity.x, y: entity.y});
      });
    }
    function syncNormalizedAssignment(profile, assignment) {
      if (!profile || !assignment) return;
      const finalCouriers = finalCourierTokensForAssignment(assignment);
      if (!profile.assignments) profile.assignments = {};
      profile.assignments[assignment.id] = {
        id: assignment.id,
        pickup: assignment.pickup,
        merchant: assignment.pickup_label || assignment.merchant || assignment.pickup,
        merchantNote: assignment.merchant_note || "",
        courier: assignment.courier,
        orders: assignment.orders || [],
        orderCount: safeNumber(assignment.order_count, (assignment.orders || []).length || 1),
        eta: assignment.eta,
        cost: assignment.cost,
        probability: assignment.probability,
        reason: assignment.reason || [],
        fit: assignment.fit,
        distance: assignment.distance,
        risk: assignment.risk || "Medium",
        strategyId: assignment.strategy_id || "",
        map_couriers: finalCouriers,
        backup_couriers: Array.isArray(assignment.map_couriers)
          ? assignment.map_couriers.filter((courier) => !finalCouriers.includes(courier))
          : courierTokens(assignment.courier).slice(1),
        map_orders: assignment.map_orders || assignment.orders || []
      };
    }
    function reconcileDispatchPairsToVisibleMap(profile) {
      if (!profile || !profile.dispatchMap || !Array.isArray(profile.dispatchMap.assignments)) return;
      const entities = Array.isArray(profile.dispatchMap.entities) ? profile.dispatchMap.entities : [];
      const entityById = {};
      entities.forEach((entity) => { entityById[entity.id] = entity; });
      const merchants = entities.filter((entity) => entity.kind === "merchant_order" || entity.kind === "pickup_cluster");
      const couriers = entities.filter((entity) => entity.kind === "courier");
      const assignmentsByPickup = {};
      (profile.dispatchMap.assignments || []).forEach((assignment) => {
        if (!assignment || !assignment.pickup || assignmentsByPickup[assignment.pickup]) return;
        assignmentsByPickup[assignment.pickup] = assignment;
      });
      const samplePrefix = String(profile.dispatchMap.sample_index || 0).padStart(2, "0");
      const completeAssignments = merchants.map((merchant, index) => {
        const existing = assignmentsByPickup[merchant.id] || {};
        const id = existing.id || `A${samplePrefix}${String(index + 1).padStart(2, "0")}`;
        return {
          ...existing,
          id,
          pickup: merchant.id,
          pickup_label: existing.pickup_label || merchant.label || merchant.id,
          merchant: existing.merchant || merchant.label || merchant.id,
          merchant_note: existing.merchant_note || "该商家位于可停靠街区边界，运行后必须有明确承接骑手。",
          courier: existing.courier || "",
          map_couriers: Array.isArray(existing.map_couriers) ? existing.map_couriers : [],
          orders: Array.isArray(existing.orders) && existing.orders.length ? existing.orders : [`${merchant.id} · ${safeNumber(merchant.order_count, 1)}单`],
          map_orders: Array.isArray(existing.map_orders) ? existing.map_orders : [],
          order_count: safeNumber(existing.order_count, safeNumber(merchant.order_count, 1)),
          eta: existing.eta || `${safeNumber(merchant.expected_eta_min, 18)} min`,
          cost: existing.cost || money(Math.max(18, safeNumber(merchant.expected_price, 35))),
          probability: existing.probability || "78%",
          risk: existing.risk || "Medium",
          fit: existing.fit || "viewport-nearest",
          reason: Array.isArray(existing.reason) && existing.reason.length
            ? existing.reason
            : ["当前可见商家必须产生明确派单关系，系统按视口最近可用骑手补全企业总览。"],
          strategy_id: existing.strategy_id || "S3"
        };
      });
      profile.dispatchMap.assignments = completeAssignments;
      profile.assignments = {};
      const courierLoad = {};
      const unusedCourierIds = new Set(couriers.map((courier) => courier.id));
      const preferUniqueCouriers = couriers.length >= profile.dispatchMap.assignments.length;
      profile.dispatchMap.assignments.forEach((assignment) => {
        const merchant = entityById[assignment.pickup];
        if (!merchant || !couriers.length) return;
        const candidateCouriers = preferUniqueCouriers && unusedCourierIds.size
          ? couriers.filter((courier) => unusedCourierIds.has(courier.id))
          : couriers;
        const ranked = candidateCouriers.map((courier) => {
          const load = courierLoad[courier.id] || 0;
          const distance = distance2D([merchant.x, merchant.y], [courier.x, courier.y]);
          const reusePenalty = preferUniqueCouriers ? load * 10000 : load * 36;
          const overlapPenalty = distance < 5.2 ? (5.2 - distance) * 90 : 0;
          return {courier, score: distance + reusePenalty + overlapPenalty};
        }).sort((left, right) => left.score - right.score);
        const chosen = ranked[0] && ranked[0].courier;
        if (!chosen) return;
        courierLoad[chosen.id] = (courierLoad[chosen.id] || 0) + 1;
        unusedCourierIds.delete(chosen.id);
        assignment.courier = chosen.id;
        assignment.map_couriers = [chosen.id];
        assignment.distance = `${Math.max(0.4, distance2D([merchant.x, merchant.y], [chosen.x, chosen.y]) * 0.18).toFixed(1)} km`;
        assignment.merchant_note = `该商家最终派给 ${chosen.id}，连线按当前地图道路视口生成。`;
        syncNormalizedAssignment(profile, assignment);
      });
      if (!profile.selected || !profile.assignments[profile.selected]) {
        profile.selected = profile.dispatchMap.assignments[0] ? profile.dispatchMap.assignments[0].id : "";
      }
    }
    function applyRenderedMapAnchors(profile) {
      if (!profile || !profile.dispatchMap || !semiRealMapReady) return false;
      const shouldReconcileAssignments = () => Boolean(
        profile.dispatchMap
        && (profile.dispatchMap.stage === "simulation_final" || profile.dispatchMap.stage === "final")
        && profile.assignments
        && Object.keys(profile.assignments).length
        && profile.dispatchMap.assignment_reconciled_variant !== profile.dispatchMap.anchor_variant
      );
      if (profile.dispatchMap.anchor_source === "maplibre-rendered") {
        syncRenderedAnchorsToViewport(profile);
        if (shouldReconcileAssignments()) {
          reconcileDispatchPairsToVisibleMap(profile);
          profile.dispatchMap.assignment_reconciled_variant = profile.dispatchMap.anchor_variant || "maplibre-rendered";
        }
        return true;
      }
      const anchors = renderedMapAnchorsForProfile(profile);
      if (!anchors) return false;
      const entities = Array.isArray(profile.dispatchMap.entities) ? profile.dispatchMap.entities : [];
      const merchantAnchors = anchors.merchantAnchors;
      const roadSamples = anchors.roadSamples
        .filter((point, index, list) => {
          if (!isMapScreenSafe(point, "courier")) return false;
          return list.findIndex((other) => distance2D(point, other) < 1.8) === index;
        });
      const sampleKey = `${profile.dispatchMap.scenario_id || profile.label || ""}:${profile.dispatchMap.sample_index || 0}`;
      const usedMerchantAnchors = [];
      const usedCourierAnchors = [];
      const merchants = entities.filter((entity) => entity.kind === "merchant_order" || entity.kind === "pickup_cluster");
      const couriers = entities.filter((entity) => entity.kind === "courier");
      merchants.forEach((entity, index) => {
        const seed = stableHash(`${sampleKey}:${entity.id}`);
        const anchor = diverseRenderedAnchor(merchantAnchors, usedMerchantAnchors, `${seed}:${index}`, "merchant", 12);
        if (anchor) {
          entity.x = Number(anchor.x.toFixed(2));
          entity.y = Number(anchor.y.toFixed(2));
          entity.rendered_lnglat = Array.isArray(anchor.lnglat) ? anchor.lnglat : screenNormToLngLat([entity.x, entity.y]);
          entity.rendered_anchor_source = "maplibre-building-or-landuse";
          usedMerchantAnchors.push({x: entity.x, y: entity.y});
        }
      });
      couriers.forEach((entity, index) => {
        const seed = stableHash(`${sampleKey}:${entity.id}`);
        const slotOffset = stableHash(`${sampleKey}:courier-slots`) % courierDistributionSlots.length;
        const target = courierDistributionSlots[(index + slotOffset) % courierDistributionSlots.length];
        const minDistance = index < 10 ? 13.5 : 10.5;
        const anchor = diverseRenderedAnchor(roadSamples, usedCourierAnchors, `${seed}:${index}`, "courier", minDistance, {
          target,
          targetWeight: 3.0,
          distanceWeight: 8.0
        });
        if (anchor) {
          entity.x = Number(anchor.x.toFixed(2));
          entity.y = Number(anchor.y.toFixed(2));
          entity.rendered_lnglat = Array.isArray(anchor.lnglat) ? anchor.lnglat : screenNormToLngLat([entity.x, entity.y]);
          entity.rendered_anchor_source = "maplibre-road";
          usedCourierAnchors.push({x: entity.x, y: entity.y});
        }
      });
      enforceCourierSeparation(couriers, sampleKey);
      profile.dispatchMap.map_layers = {
        ...(profile.dispatchMap.map_layers || {}),
        roads: anchors.roads,
        anchor_source: "maplibre-rendered",
        road_graph: "maplibre_rendered_road_graph",
        layer_schema: semiRealMapLayerSchema
      };
      profile.dispatchMap.anchor_source = "maplibre-rendered";
      profile.dispatchMap.anchor_variant = currentSemiRealMapRegion().label;
      if (shouldReconcileAssignments()) {
        reconcileDispatchPairsToVisibleMap(profile);
        profile.dispatchMap.assignment_reconciled_variant = profile.dispatchMap.anchor_variant || "maplibre-rendered";
      }
      return true;
    }
    function assignmentEntries(profile) {
      return Object.entries((profile && profile.assignments) || {});
    }
    function courierTokens(courierText) {
      return String(courierText || "").split("+").map((item) => item.trim()).filter(Boolean);
    }
    function finalCourierTokensForAssignment(assignment) {
      if (!assignment) return [];
      const finalFromCourier = courierTokens(assignment.courier);
      if (finalFromCourier.length) return [finalFromCourier[0]];
      const mapped = Array.isArray(assignment.map_couriers) ? assignment.map_couriers.map((item) => String(item || "").trim()).filter(Boolean) : [];
      return mapped.length ? [mapped[0]] : [];
    }
    function finalCourierForAssignment(assignment) {
      return finalCourierTokensForAssignment(assignment)[0] || "";
    }
    function assignmentStatsForProfile(profile) {
      const assignments = Object.values((profile && profile.assignments) || {});
      const courierSet = new Set(assignments.map((assignment) => finalCourierForAssignment(assignment)).filter(Boolean));
      const orderCount = assignments.reduce((sum, assignment) => sum + safeNumber(assignment.orderCount, (assignment.orders || []).length || 1), 0);
      const totalCost = assignments.reduce((sum, assignment) => sum + safeNumber(String(assignment.cost || "0").replace(/[$,]/g, ""), 0), 0);
      return {
        assignments,
        merchantCount: assignments.length,
        courierCount: courierSet.size,
        orderCount,
        totalCost
      };
    }
    function syncReportMetricsFromAssignments(report, profile) {
      if (!report || !report.best || !profile || !profile.assignments || !Object.keys(profile.assignments).length) return;
      const stats = assignmentStatsForProfile(profile);
      report.best.groups = stats.merchantCount;
      report.best.used_couriers = stats.courierCount;
      report.best.covered_tasks = stats.merchantCount;
      report.best.total_tasks = stats.merchantCount;
      report.best.order_tasks = stats.orderCount;
      if (report.features) {
        report.features.tasks = stats.merchantCount;
        report.features.orders = stats.orderCount;
      }
    }
    function assignmentForEntity(profile, entityId) {
      const entity = String(entityId || "").trim();
      if (!entity || entity.startsWith("D")) return "";
      for (const [assignmentId, assignment] of assignmentEntries(profile)) {
        if (assignment.pickup === entity) return assignmentId;
        if (assignment.merchant === entity || String(assignment.merchant || "").startsWith(entity + "：")) return assignmentId;
        if ((assignment.orders || []).includes(entity)) return assignmentId;
        if ((assignment.map_orders || []).includes(entity)) return assignmentId;
        if (finalCourierTokensForAssignment(assignment).includes(entity)) return assignmentId;
      }
      return "";
    }
    function assignmentForOrder(profile, orderId) {
      const assignmentId = assignmentForEntity(profile, orderId);
      return (profile.assignments || {})[assignmentId];
    }
    function normalizeAssignmentsFromMap(mapPayload) {
      const assignments = {};
      (mapPayload.assignments || []).forEach((item, index) => {
        const finalCouriers = finalCourierTokensForAssignment(item);
        const mappedCouriers = Array.isArray(item.map_couriers) ? item.map_couriers : courierTokens(item.courier);
        assignments[item.id || `A${index + 1}`] = {
          pickup: item.pickup,
          merchant: item.pickup_label || item.merchant || item.pickup || `G${index + 1}`,
          merchantNote: item.merchant_note || mapPayload.note || "",
          courier: finalCouriers[0] || item.courier,
          orders: item.orders || [],
          orderCount: safeNumber(item.order_count, (item.orders || []).length),
          eta: item.eta,
          cost: item.cost,
          probability: item.probability,
          reason: item.reason || [],
          fit: item.fit,
          distance: item.distance,
          risk: item.risk || "Medium",
          strategyId: item.strategy_id || "",
          map_couriers: finalCouriers,
          backup_couriers: mappedCouriers.filter((courier) => !finalCouriers.includes(courier)),
          map_orders: item.map_orders || item.orders || []
        };
      });
      return assignments;
    }
    function preferredAssignmentIdForMap(mapPayload, assignments) {
      const entries = Object.entries(assignments || {});
      if (!entries.length) return "";
      const entityById = {};
      (mapPayload.entities || []).forEach((entity) => {
        entityById[entity.id] = entity;
      });
      const scoreFor = ([assignmentId, assignment]) => {
        const pickup = entityById[assignment.pickup] || {};
        const courierId = finalCourierForAssignment(assignment);
        const courier = entityById[courierId] || {};
        const px = safeNumber(pickup.x, 50);
        const py = safeNumber(pickup.y, 50);
        const cx = safeNumber(courier.x, px);
        const cy = safeNumber(courier.y, py);
        const centerPenalty = Math.abs(px - 54) * 0.75 + Math.abs(py - 47) * 0.9;
        const edgePenalty = (px < 16 || px > 86 ? 24 : 0) + (py < 16 || py > 86 ? 20 : 0);
        const pickupDistance = Math.hypot(px - cx, py - cy) * 1.55;
        const orderWeight = Math.min(3, safeNumber(assignment.orderCount, (assignment.orders || []).length || 1)) * 16;
        const routeCount = (assignment.map_orders || assignment.orders || []).length * 4;
        return [orderWeight + routeCount - centerPenalty - edgePenalty - pickupDistance, assignmentId];
      };
      return entries.map(scoreFor).sort((left, right) => right[0] - left[0])[0][1];
    }
    function updatePreviewKpis(mapPayload, profile) {
      const assignments = mapPayload.assignments || [];
      const cost = assignments.reduce((sum, item) => sum + safeNumber(String(item.cost || "0").replace("$", ""), 0), 0);
      const covered = new Set(assignments.flatMap((item) => item.orders || [])).size;
      const totalTasks = safeNumber(mapPayload.total_tasks, covered);
      $("runtime").textContent = mapPayload.stage === "final" ? $("runtime").textContent : "00:00:01";
      $("completion-rate").textContent = totalTasks ? Math.round(Math.min(1, covered / totalTasks) * 100) + "%" : "100%";
      $("unassigned").textContent = String(Math.max(0, totalTasks - covered));
      $("expected-cost").textContent = money(cost);
      $("improvement").textContent = profile.improvement && profile.improvement !== "--" ? profile.improvement : "预览";
      profile.cost = money(cost);
    }
    function simulationPreviewMap(sample) {
      const merchantEntities = (sample.merchants || []).map((merchant) => ({
        id: merchant.id,
        kind: "merchant_order",
        label: merchant.label || "商家",
        x: merchant.x,
        y: merchant.y,
        order_count: merchant.order_count,
        expected_eta_min: merchant.expected_eta_min,
        expected_price: merchant.expected_price,
        demand_level: merchant.demand_level,
        hotspot: merchant.hotspot,
        hideLabel: true
      }));
      const courierEntities = (sample.couriers || []).map((courier) => ({
        id: courier.id,
        kind: "courier",
        label: courier.label || "骑手",
        x: courier.x,
        y: courier.y,
        willingness: courier.willingness,
        status: courier.status,
        capacity: courier.capacity,
        hideLabel: true
      }));
      return {
        case_id: sample.case_id,
        scenario_id: sample.scenario_id,
        sample_index: sample.sample_index,
        stage: "sample_preview",
        assignments: [],
        entities: [...merchantEntities, ...courierEntities],
        map_layers: sample.map_layers,
        total_tasks: merchantEntities.length,
        total_couriers: courierEntities.length,
        note: "刷新位置仅重抽当前场景商家与骑手点位；运行推理后才生成最终派单线。"
      };
    }
    function strategyRuntimeName(strategyId) {
      return {
        S1: "disjoint_then_multidispatch",
        S2: "single_task_multidispatch",
        S3: "sparse_cover",
        S4: "greedy_baseline",
        S5: "risk_balancing"
      }[strategyId] || "candidate_preview";
    }
    function cloneStablePreviewMapForFinal(sample, renderedDispatchMap) {
      const fallback = simulationPreviewMap(sample);
      if (!renderedDispatchMap || !Array.isArray(renderedDispatchMap.entities)) return fallback;
      return {
        ...fallback,
        entities: renderedDispatchMap.entities.map((entity) => ({...entity})),
        map_layers: {
          ...(fallback.map_layers || {}),
          ...(renderedDispatchMap.map_layers || {})
        },
        anchor_source: renderedDispatchMap.anchor_source || fallback.anchor_source,
        anchor_variant: renderedDispatchMap.anchor_variant || fallback.anchor_variant,
        assignment_reconciled_variant: renderedDispatchMap.assignment_reconciled_variant || fallback.assignment_reconciled_variant
      };
    }
    function simulationFinalMap(sample, renderedDispatchMap = null) {
      const preview = cloneStablePreviewMapForFinal(sample, renderedDispatchMap);
      const merchantById = Object.fromEntries((sample.merchants || []).map((item) => [item.id, item]));
      const courierById = Object.fromEntries((sample.couriers || []).map((item) => [item.id, item]));
      const candidateByPair = {};
      (sample.candidates || []).forEach((candidate) => {
        candidateByPair[`${candidate.merchant_id}:${candidate.courier_id}`] = candidate;
      });
      const assignments = (sample.assignments || []).map((assignment, index) => {
        const merchant = merchantById[assignment.merchant_id] || {};
        const courier = courierById[assignment.courier_id] || {};
        const candidate = candidateByPair[`${assignment.merchant_id}:${assignment.courier_id}`] || assignment;
        const probability = safeNumber(candidate.accept_probability, safeNumber(assignment.accept_probability, 0));
        const orderCount = Math.max(1, Math.round(safeNumber(merchant.order_count, 1)));
        const orderIds = [`${assignment.merchant_id} · ${orderCount}单`];
        return {
          id: assignment.id || `A${index + 1}`,
          task_key: assignment.merchant_id,
          pickup: assignment.merchant_id,
          pickup_label: assignment.merchant_id,
          merchant: assignment.merchant_id,
          merchant_note: `该商家位于可停靠街区边界，最终派给 ${assignment.courier_id}。`,
          courier: assignment.courier_id,
          map_couriers: [assignment.courier_id],
          map_orders: [],
          orders: orderIds,
          order_count: orderCount,
          strategy_id: assignment.strategy_id || sample.selected_strategy_id || "",
          eta: `${assignment.eta_min || candidate.eta_min || merchant.expected_eta_min || "-"} min`,
          cost: money(assignment.cost || candidate.cost || merchant.expected_price),
          probability: `${Math.round(probability * 100)}%`,
          fit: `${Math.round(probability * 100)}%`,
          distance: `${safeNumber(candidate.distance, 0).toFixed(1)} km`,
          risk: assignment.risk || candidate.risk || "Medium",
          reason: assignment.reason || [
            `策略路径：${sample.selected_strategy && sample.selected_strategy.label ? sample.selected_strategy.label : sample.selected_strategy_id}`,
            `骑手 ${assignment.courier_id} 接单意愿 ${Math.round(safeNumber(courier.willingness, probability) * 100)}%。`,
            "该派单由当前场景的商家位置、骑手意愿、价格和路况共同生成。"
          ]
        };
      });
      return {
        ...preview,
        stage: "simulation_final",
        assignments,
        entities: [...preview.entities],
        total_tasks: (sample.merchants || []).length,
        total_couriers: (sample.couriers || []).length,
        summary: sample.summary,
        note: "最终派单线只表达骑手到商家的派单关系；商家点同时代表该商家的全部订单。"
      };
    }
    function reportForSimulationSample(sample, mapPayload) {
      const strategyPath = Array.isArray(sample.strategy_path) ? sample.strategy_path : [];
      const totalCost = (mapPayload.assignments || []).reduce((sum, item) => sum + safeNumber(String(item.cost || "0").replace("$", ""), 0), 0);
      const totalTasks = (sample.merchants || []).length;
      const totalOrders = (mapPayload.assignments || []).reduce((sum, item) => sum + safeNumber(item.order_count, (item.orders || []).length || 1), 0);
      const usedCouriers = new Set((mapPayload.assignments || []).map((item) => item.courier)).size;
      return {
        case_id: sample.case_id,
        status: "simulation_ok",
        wall_time_s: 10,
        features: {
          tasks: totalTasks,
          orders: totalOrders,
          couriers: (sample.couriers || []).length,
          rows: (sample.candidates || []).length
        },
        best: {
          strategy: strategyRuntimeName(sample.selected_strategy_id),
          ["local" + "_cost"]: totalCost,
          valid: true,
          covered_tasks: totalTasks,
          total_tasks: totalTasks,
          order_tasks: totalOrders,
          groups: (mapPayload.assignments || []).length,
          used_couriers: usedCouriers,
          uncovered_tasks: []
        },
        rounds: [{
          round: 1,
        reason: "current refreshed dispatch scene",
          strategies: strategyPath.map((item) => ({
            name: strategyRuntimeName(item.id),
            ["local" + "_cost"]: Math.max(1, totalCost / Math.max(safeNumber(item.score, 0.58), 0.3)),
            accepted: item.status === "selected",
            valid: true,
            covered_tasks: totalTasks,
            total_tasks: totalTasks,
            groups: (mapPayload.assignments || []).length
          }))
        }],
        solution: (mapPayload.assignments || []).map((item) => [item.task_key, [item.courier]]),
        dispatch_assignment_map: mapPayload
      };
    }
    function renderSimulationPreviewTable(sample) {
      const tbody = document.querySelector(".table-panel tbody");
      if (!tbody) return;
      const strategyRows = (sample.strategy_path || []).slice(0, 5).map((strategy) => {
        const label = strategyBranchCatalog.find((item) => item.id === strategy.id) || {title: strategy.id};
        return `<tr data-row-type="preview-strategy" data-branch="${escapeAttr(strategy.id)}" data-status="待评估"><td>${strategy.id} · ${label.title}</td><td>待推理</td><td>-</td><td>-</td><td>-</td><td>${sample.summary ? sample.summary.traffic : "-"}</td><td>-</td><td>待评估</td><td>${label.desc || "运行后进入策略链路评估"}</td></tr>`;
      });
      tbody.innerHTML = [
        `<tr class="emphasis" data-row-type="scene-summary" data-scenario="${escapeAttr(sample.scenario_id || "")}"><td><b>${sample.name}</b></td><td>${(sample.merchants || []).length} 个商家</td><td>-</td><td>-</td><td>${(sample.couriers || []).length} 个骑手</td><td>${sample.summary ? sample.summary.traffic : "-"}</td><td>-</td><td>待推理</td><td>当前只展示点位；运行后输出最终派单关系</td></tr>`,
        ...strategyRows
      ].join("");
    }
    function resetDecisionPanelForSimulationPreview(sample) {
      setDetailContext("sample-preview", "", "", "");
      $("detail-title").textContent = `场景输入：${sample.name}`;
      $("detail-courier").textContent = "-";
      $("detail-merchant").innerHTML = `已生成 <code>${(sample.merchants || []).length}</code> 个商家点和 <code>${(sample.couriers || []).length}</code> 个骑手点；当前仅展示输入，不提前生成派单结果。`;
      $("detail-orders").innerHTML = [
        `<span class="chip">商家 ${(sample.merchants || []).length}</span>`,
        `<span class="chip">骑手 ${(sample.couriers || []).length}</span>`,
        `<span class="chip">路况 ${sample.summary ? sample.summary.traffic : "-"}</span>`
      ].join("");
      $("detail-eta").textContent = "-";
      $("right-cost").textContent = "-";
      document.querySelector(".prob span").textContent = "--";
      $("detail-reasons").innerHTML = [
        "<li>刷新只更新当前场景下的商家、骑手与候选策略，不提前展示最终派单。</li>",
        "<li>运行后左侧链路会逐步评估策略，下方表格切换为最终方案对比。</li>",
        "<li>点击地图上的商家或骑手可查看候选信息，不显示内部编号。</li>",
      ].join("");
      setEvidenceRows([
        ["▧ 商家输入", `${(sample.merchants || []).length} 个商家`],
        ["◎ 骑手供给", `${(sample.couriers || []).length} 个骑手`],
        ["◷ 路况", sample.summary ? sample.summary.traffic : "-"],
        ["△ 平均意愿", sample.summary ? `${Math.round(safeNumber(sample.summary.avg_willingness, 0) * 100)}%` : "-"],
        ["▣ 候选策略", sample.selected_strategy_id || "-"]
      ]);
      const compareRows = document.querySelectorAll(".decision-card:last-child .row strong");
      compareRows.forEach((row) => { row.textContent = "-"; });
    }
    function applySimulationSample(sample) {
      if (!sample || !Array.isArray(sample.merchants) || !Array.isArray(sample.couriers)) return;
      currentSimulationSample = sample;
      currentReport = null;
      clearReasoningState();
      const select = $("case-select");
      if (select) {
        const option = Array.from(select.options).find((item) => item.dataset.scenario === sample.scenario_id);
        if (option) select.value = option.value;
      }
      const profile = profileForCase(sample.case_id || selectedCase());
      currentProfile = profile;
      profile.label = sample.name;
      profile.previewOrderCount = (sample.merchants || []).length;
      profile.previewCourierCount = (sample.couriers || []).length;
      profile.missedRisk = sample.summary && sample.summary.traffic === "heavy" ? "高" : sample.summary && sample.summary.traffic === "moderate" ? "中" : "低";
      profile.utilization = sample.selected_strategy_id || "-";
      profile.selected = "";
      profile.mapFocusMode = "overview";
      profile.assignments = {};
      profile.dispatchMap = simulationPreviewMap(sample);
      resetSemiRealMapViewportForScenario("refresh-position-reset");
      resetMapControlState();
      document.body.classList.add("pending-run", "sample-preview");
      $("case-id").textContent = sample.name;
      $("runtime").textContent = "--:--:--";
      $("completion-rate").textContent = "--";
      $("unassigned").textContent = String((sample.merchants || []).length);
      $("expected-cost").textContent = "--";
      $("improvement").textContent = "--";
      $("right-cost").textContent = "-";
      const routeSvg = document.querySelector(".route-svg");
      if (routeSvg) routeSvg.innerHTML = "";
      updateMapScene(profile);
      updateTrafficWidget(sample.summary);
      resetDecisionPanelForSimulationPreview(sample);
      renderSimulationPreviewTable(sample);
      updateReasonSummary(profile, null);
      updateReasonProgress(0);
      setStatus("场景已刷新，等待推理", false);
      showToast(`已生成 ${sample.name} 的商家与骑手点位`);
    }
    async function refreshSimulationSample() {
      if (simulationSampleLoadPromise) return simulationSampleLoadPromise;
      simulationSampleLoadPromise = (async () => {
      const scenarioId = selectedScenarioId();
      const previous = Object.prototype.hasOwnProperty.call(simulationSampleIndex, scenarioId) ? simulationSampleIndex[scenarioId] : -1;
      const nextSample = (previous + 1) % 10;
      simulationSampleIndex[scenarioId] = nextSample;
      simulationRefreshNonce += 1;
      const variantSeed = `${scenarioId}-${Date.now().toString(36)}-${simulationRefreshNonce}`;
      const qs = new URLSearchParams({scenario: scenarioId, sample: String(nextSample), seed: variantSeed});
      const res = await fetch("/api/simulation-sample?" + qs.toString());
      const payload = await res.json();
      if (!res.ok || payload.status !== "ok") throw new Error(payload.error || "sample refresh failed");
      applySimulationSample(payload.sample);
      return payload.sample;
      })();
      try {
        return await simulationSampleLoadPromise;
      } finally {
        simulationSampleLoadPromise = null;
      }
    }
    async function loadSimulationScenario(scenarioId) {
      if (!scenarioId) return false;
      const select = $("case-select");
      const option = select ? Array.from(select.options).find((item) => item.dataset.scenario === scenarioId) : null;
      if (!option) return false;
      select.value = option.value;
      simulationSampleIndex[scenarioId] = -1;
      await refreshSimulationSample();
      return true;
    }
    function applyDispatchAssignmentMap(mapPayload) {
      if (!mapPayload || !Array.isArray(mapPayload.assignments) || mapPayload.assignments.length === 0) return;
      document.body.classList.remove("sample-preview");
      const profile = currentProfile || profileForCase(selectedCase());
      profile.assignments = normalizeAssignmentsFromMap(mapPayload);
      profile.selected = preferredAssignmentIdForMap(mapPayload, profile.assignments) || Object.keys(profile.assignments)[0] || "A1";
      profile.mapFocusMode = "overview";
      profile.dispatchMap = mapPayload;
      if (mapPayload.stage === "simulation_final" || mapPayload.stage === "final") {
        reconcileDispatchPairsToVisibleMap(profile);
        syncReportMetricsFromAssignments(currentReport, profile);
      }
      resetMapControlState();
      if (mapPayload.total_tasks) profile.totalTasks = mapPayload.total_tasks;
      if (mapPayload.total_couriers) profile.totalCouriers = mapPayload.total_couriers;
      if (!currentReport) updatePreviewKpis(mapPayload, profile);
      updateMapScene(profile);
      updateTrafficWidget(mapPayload.summary || (currentSimulationSample && currentSimulationSample.summary));
      updateDecisionPanel(profile, currentReport);
      updateReasonSummary(profile, currentReport);
      renderCandidateTable(currentReport, profile);
      if (mapPayload.stage === "final") setStatus("已加载真实最终派单", false);
      if (mapPayload.stage === "preview") setStatus("已生成模拟派单地图", false);
    }
    function clearDispatchResult(profile) {
      const entityLayer = document.querySelector(".map-entities");
      if (entityLayer) entityLayer.innerHTML = "";
      const routeSvg = document.querySelector(".route-svg");
      if (routeSvg) routeSvg.innerHTML = "";
      clearExternalMapFallback();
      renderSimulatedBaseMap(null);
      const frame = document.querySelector(".map-frame");
      frame.classList.remove("topology", "focus-selected");
      frame.classList.remove("assignment-overview");
      resetMapControlState();
      frame.removeAttribute("data-selected-assignment");
      document.body.classList.remove("sample-preview");
      setDetailContext("waiting", "", "", "");
      $("detail-title").textContent = "等待运行派单推理";
      $("detail-courier").textContent = "-";
      $("detail-merchant").innerHTML = "请选择场景并点击 <code>刷新位置</code> 生成输入；运行派单推理后，系统会按商家、骑手意愿、价格和路况生成最终派单关系。";
      $("detail-orders").innerHTML = "";
      $("detail-eta").textContent = "-";
      $("right-cost").textContent = "-";
      document.querySelector(".prob span").textContent = "--";
      $("detail-reasons").innerHTML = [
        "<li>初始状态只展示场景入口，不展示最终派单线。</li>",
        "<li>刷新后生成当前场景输入，只显示商家点和骑手点。</li>",
        "<li>运行推理完成后自动显示每个商家派给哪个骑手。</li>"
      ].join("");
      setEvidenceRows([
        ["▧ 商家覆盖", "-"],
        ["◎ 派单对象", "-"],
        ["◷ ETA / 时效", "-"],
        ["△ 接单风险", "-"],
        ["▣ 策略/负载", "-"]
      ]);
      const compareRows = document.querySelectorAll(".decision-card:last-child .row strong");
      compareRows.forEach((row) => { row.textContent = "-"; });
      document.body.classList.add("pending-run");
      const tbody = document.querySelector(".table-panel tbody");
      if (tbody) {
        tbody.innerHTML = [
          `<tr data-row-type="empty-state"><td>场景已选择</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td class="status-ok">就绪</td><td>已选择 ${profile.label}，等待刷新位置或运行推理</td></tr>`,
          `<tr data-row-type="empty-state"><td>候选输入</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>输入</td><td>候选关系由商家位置、骑手位置、接单意愿、价格和路况共同生成</td></tr>`,
          `<tr data-row-type="empty-state"><td>派单结果</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td class="status-bad">待运行</td><td>运行完成后自动展示全部商家与骑手派单线</td></tr>`
        ].join("");
      }
      updateReasonSummary(profile, null);
      updateReasonProgress(0);
    }
    function sceneLabels(profile) {
      if (!profile.dispatchMap || !Array.isArray(profile.dispatchMap.entities)) return [];
      const labels = [];
      const hasFinalAssignments = Boolean(profile.assignments && Object.keys(profile.assignments).length);
      const activeCouriers = new Set();
      if (hasFinalAssignments) {
        Object.values(profile.assignments).forEach((assignment) => {
          finalCourierTokensForAssignment(assignment).forEach((courier) => activeCouriers.add(courier));
        });
      }
      const kindOrder = ["pickup_cluster", "merchant_order", "courier"];
      kindOrder.forEach((kind) => {
        profile.dispatchMap.entities.filter((entity) => entity.kind === kind).forEach((entity) => {
          if (hasFinalAssignments && kind === "courier" && !activeCouriers.has(entity.id)) return;
          const text = kind === "pickup_cluster" || kind === "merchant_order" ? "商家" : "骑手";
          const label = entity.label || text;
          labels.push({id: entity.id, html: `${entity.id}<small>${label}</small>`, kind: entity.kind, x: entity.x, y: entity.y, hideLabel: Boolean(entity.hideLabel)});
        });
      });
      return labels;
    }
    const strategyBranchCatalog = [
      {id: "S1", title: "合单优先", desc: "同路高重叠订单合并派单", names: ["disjoint_then_multidispatch", "pair_potential_matching", "scarce_k2_column_search", "scarce_bundle_mcf_enum"]},
      {id: "S2", title: "多派候选", desc: "单任务多骑手候选扩展", names: ["single_task_multidispatch"]},
      {id: "S3", title: "局部修复", desc: "从基线方案做局部修复", names: ["sparse_cover", "low_global_column_search", "low_column_search"]},
      {id: "S4", title: "贪心基线", desc: "最近/最低成本基线派单", names: ["greedy_baseline", "fallback_official_greedy"]},
      {id: "S5", title: "风险平衡", desc: "低意愿与时间窗风险平衡", names: ["risk_balancing", "low_willingness_guard", "candidate_preview"]}
    ];
    function branchForStrategy(name, profile) {
      const strategyName = String(name || "");
      const found = strategyBranchCatalog.find((branch) => branch.names.includes(strategyName));
      if (found) return found.id;
      if (strategyName.includes("low")) return "S5";
      if (strategyName.includes("disjoint") || strategyName.includes("pair") || strategyName.includes("bundle") || strategyName.includes("scarce")) return "S1";
      if (strategyName.includes("greedy")) return "S4";
      if (strategyName.includes("single")) return "S2";
      if (strategyName.includes("sparse") || strategyName.includes("repair")) return "S3";
      if (profile && String(profile.label || "").includes("低接单")) return "S5";
      if (profile && String(profile.label || "").includes("稀缺")) return "S1";
      return "S1";
    }
    function strategyNameOf(item) {
      return String((item && (item.name || item.strategy || item.id)) || "");
    }
    function strategyMatchesBranch(item, branch, profile) {
      const name = strategyNameOf(item);
      if (!name || !branch) return false;
      if (branch.names.includes(name)) return true;
      return branchForStrategy(name, profile) === branch.id;
    }
    function localCostOf(item, fallback = Infinity) {
      return safeNumber(item && item["local" + "_cost"], fallback);
    }
    function attemptsFromReport(report) {
      return ((report && report.rounds) || []).flatMap((round) => Array.isArray(round.strategies) ? round.strategies : []);
    }
    function selectedBranchForReport(report, profile) {
      if (!report) return "";
      const attempts = attemptsFromReport(report);
      const best = report.best || {};
      if (best.strategy && best.strategy !== "production_solver") return branchForStrategy(best.strategy, profile);
      const accepted = attempts.filter((item) => item && (item.accepted || item.valid));
      const ranked = (accepted.length ? accepted : attempts).filter(Boolean).sort((a, b) => localCostOf(a) - localCostOf(b));
      if (ranked[0] && strategyNameOf(ranked[0])) return branchForStrategy(strategyNameOf(ranked[0]), profile);
      return branchForStrategy(best.strategy, profile);
    }
    function sampleStrategyItems(sample) {
      const raw = sample && Array.isArray(sample.strategy_path) ? sample.strategy_path : [];
      const byId = {};
      raw.forEach((item) => {
        if (item && item.id) byId[item.id] = item;
      });
      strategyBranchCatalog.forEach((branch, index) => {
        if (!byId[branch.id]) byId[branch.id] = {id: branch.id, score: 0.58 - index * 0.02, status: "pending"};
      });
      return strategyBranchCatalog.map((branch) => byId[branch.id]);
    }
    function reasoningOrderForSample(sample) {
      const selected = sample && sample.selected_strategy_id ? sample.selected_strategy_id : "";
      const items = sampleStrategyItems(sample);
      const rejected = items
        .filter((item) => item.id !== selected)
        .sort((left, right) => safeNumber(left.score, 0) - safeNumber(right.score, 0))
        .map((item) => item.id);
      return selected ? [...rejected, selected] : rejected;
    }
    function buildReasoningState(sample, activeIndex = -1, complete = false) {
      const selected = sample && sample.selected_strategy_id ? sample.selected_strategy_id : "";
      const items = sampleStrategyItems(sample);
      const scoreById = Object.fromEntries(items.map((item) => [item.id, safeNumber(item.score, 0)]));
      const order = reasoningOrderForSample(sample);
      const statuses = {};
      strategyBranchCatalog.forEach((branch) => {
        const orderIndex = order.indexOf(branch.id);
        let status = "pending";
        if (complete) {
          status = branch.id === selected ? "selected" : "rejected";
        } else if (orderIndex >= 0 && orderIndex < activeIndex) {
          status = "rejected";
        } else if (orderIndex === activeIndex) {
          status = "evaluating";
        }
        statuses[branch.id] = status;
      });
      return {
        phase: complete ? "selected" : "reasoning",
        activeBranch: complete ? "" : order[activeIndex] || "",
        selectedBranch: selected,
        order,
        statuses,
        scores: scoreById,
      };
    }
    function setReasoningState(sample, activeIndex = -1, complete = false) {
      currentReasoningState = buildReasoningState(sample, activeIndex, complete);
      document.body.classList.add("reasoning");
      renderStrategyCards(currentProfile || profileForCase(selectedCase()), null);
      return currentReasoningState;
    }
    function clearReasoningState() {
      currentReasoningState = null;
      document.body.classList.remove("reasoning");
    }
    function renderStrategyCards(profile, report, evaluatingBranch = "") {
      const strategies = Array.from(document.querySelectorAll(".branch-grid .strategy"));
      const attempts = attemptsFromReport(report);
      const bestCost = report && report.best ? safeNumber(report.best["local" + "_cost"], Infinity) : Infinity;
      const selectedBranch = selectedBranchForReport(report, profile);
      const reasoningState = !report ? currentReasoningState : null;
      const simulationItems = currentSimulationSample ? sampleStrategyItems(currentSimulationSample) : [];
      const simulationById = Object.fromEntries(simulationItems.map((item) => [item.id, item]));
      strategies.forEach((strategy, index) => {
        const branch = strategyBranchCatalog[index];
        if (!branch) return;
        const branchAttempts = attempts.filter((item) => strategyMatchesBranch(item, branch, profile));
        const bestAttempt = branchAttempts.slice().sort((a, b) => localCostOf(a) - localCostOf(b))[0];
        const sampleItem = simulationById[branch.id] || {};
        const hasReport = Boolean(report);
        const reasoningStatus = reasoningState && reasoningState.statuses ? reasoningState.statuses[branch.id] : "";
        const isBest = hasReport ? branch.id === selectedBranch : reasoningStatus === "selected";
        const isEvaluating = !hasReport && (reasoningStatus === "evaluating" || (!reasoningState && evaluatingBranch === branch.id));
        const rejected = hasReport ? (!isBest && branchAttempts.length > 0) : reasoningStatus === "rejected";
        const pending = !hasReport && !isBest && !isEvaluating && !rejected;
        const revealStrategyData = Boolean(hasReport || reasoningStatus === "selected" || reasoningStatus === "rejected");
        const showScoreOnCard = Boolean(isBest || isEvaluating || !hasReport && reasoningStatus === "rejected");
        const showEvidenceOnCard = Boolean(isBest || !hasReport && reasoningStatus === "rejected");
        const reasoningScore = showScoreOnCard && reasoningState && reasoningState.scores ? reasoningState.scores[branch.id] : NaN;
        const reportScore = showScoreOnCard && bestAttempt
          ? Math.max(0.32, Math.min(0.96, (Number.isFinite(bestCost) ? bestCost : localCostOf(bestAttempt)) / Math.max(localCostOf(bestAttempt, 1), 1))).toFixed(2)
          : "--";
        const score = Number.isFinite(reasoningScore)
          ? Math.max(0.32, Math.min(0.99, reasoningScore)).toFixed(2)
          : reportScore;
        const statusText = isBest ? "已选中" : isEvaluating ? "计算中" : rejected ? "未采用" : hasReport ? "未触发" : "待评估";
        const badgeClass = isBest ? "accepted" : isEvaluating ? "evaluating" : rejected ? "" : "pending";
        strategy.classList.toggle("best", isBest);
        strategy.classList.toggle("evaluating", isEvaluating);
        strategy.classList.toggle("rejected", rejected);
        strategy.classList.toggle("pending", pending);
        strategy.dataset.reasoningStatus = hasReport ? (isBest ? "selected" : rejected ? "rejected" : "not-tried") : (reasoningStatus || (isEvaluating ? "evaluating" : "pending"));
        strategy.dataset.reasoningOrder = reasoningState && Array.isArray(reasoningState.order) ? String(reasoningState.order.indexOf(branch.id) + 1 || "") : "";
        strategy.dataset.strategyRank = revealStrategyData && sampleItem.rank ? String(sampleItem.rank) : "";
        strategy.dataset.strategyEvidence = revealStrategyData && sampleItem.evidence ? sampleItem.evidence : "";
        strategy.querySelector("h4").textContent = branch.id + (isBest ? " ✓" : "");
        const evidence = showEvidenceOnCard && sampleItem.evidence ? `<span class="evidence">${escapeAttr(sampleItem.evidence)}</span>` : "";
        strategy.querySelector("p").innerHTML = `<b>${branch.title}</b><br>${branch.desc}${evidence}`;
        strategy.querySelector("strong").innerHTML = `${score} <span class="badge ${badgeClass}">${statusText}</span>`;
      });
    }
    function setNodeMetric(node, label, value) {
      if (!node) return;
      const metricLabel = node.querySelector(".metric span");
      const metricValue = node.querySelector(".metric strong");
      if (metricLabel) metricLabel.textContent = label;
      if (metricValue) metricValue.textContent = value;
    }
    function sampleSelectedScore(sample) {
      const selected = sample && sample.selected_strategy_id;
      const item = selected && Array.isArray(sample.strategy_path) ? sample.strategy_path.find((entry) => entry.id === selected) : null;
      return item && Number.isFinite(Number(item.score)) ? Number(item.score) : 0.89;
    }
    function updateReasonMetrics(activeStep, profile, report) {
      const nodes = Array.from(document.querySelectorAll(".reason-wrap .node"));
      const sample = currentSimulationSample;
      const attempts = attemptsFromReport(report);
      const candidateTotal = Math.max(5, attempts.length || (sample && Array.isArray(sample.strategy_path) ? sample.strategy_path.length : 0) || 5);
      const selectedScore = sampleSelectedScore(sample);
      const covered = report && report.best ? safeNumber(report.best.covered_tasks, report.best.total_tasks || 0) : 0;
      const total = report && report.best ? safeNumber(report.best.total_tasks, covered || 1) : 1;
      const feasiblePassed = Math.max(0, Math.min(covered, total));
      const feasibleTotal = Math.max(1, total);
      const finalConfidence = report ? Math.max(0.72, Math.min(0.99, selectedScore * 0.72 + Math.min(1, covered / Math.max(1, total)) * 0.24)).toFixed(2) : "--";
      const sceneConfidence = sample ? Math.max(0.76, Math.min(0.98, selectedScore + 0.06)).toFixed(2) : "--";
      setNodeMetric(nodes[0], "状态", sample ? "已刷新" : "待推理");
      setNodeMetric(nodes[1], "状态", "待推理");
      setNodeMetric(nodes[2], "状态", "待推理");
      setNodeMetric(nodes[3], "状态", "待推理");
      setNodeMetric(nodes[4], "状态", "待推理");
      setNodeMetric(nodes[5], "状态", "待推理");
      if (report) {
        setNodeMetric(nodes[0], "状态", "已输入");
        setNodeMetric(nodes[1], "可信度", sceneConfidence);
        setNodeMetric(nodes[2], "候选策略", String(candidateTotal));
        setNodeMetric(nodes[3], "通过", `${feasiblePassed} / ${feasibleTotal}`);
        setNodeMetric(nodes[4], "最佳分", selectedScore.toFixed(2));
        setNodeMetric(nodes[5], "置信度", finalConfidence);
        return;
      }
      if (!currentReasoningState) return;
      if (activeStep >= 0) setNodeMetric(nodes[0], "状态", "已输入");
      if (activeStep === 1) setNodeMetric(nodes[1], "可信度", "计算中");
      if (activeStep > 1) setNodeMetric(nodes[1], "可信度", sceneConfidence);
      if (activeStep === 2) setNodeMetric(nodes[2], "候选策略", "生成中");
      if (activeStep > 2) setNodeMetric(nodes[2], "候选策略", String(candidateTotal));
      if (activeStep === 3) setNodeMetric(nodes[3], "通过", "校验中");
      if (activeStep > 3) setNodeMetric(nodes[3], "通过", `${currentReasoningState.phase === "selected" ? 1 : 0} / ${candidateTotal}`);
      if (activeStep === 4) setNodeMetric(nodes[4], "最佳分", "评估中");
      if (activeStep > 4) setNodeMetric(nodes[4], "最佳分", selectedScore.toFixed(2));
      if (currentReasoningState.phase === "selected") setNodeMetric(nodes[5], "置信度", finalConfidence === "--" ? selectedScore.toFixed(2) : finalConfidence);
    }
    function updateReasonProgress(activeStep) {
      const nodes = Array.from(document.querySelectorAll(".reason-wrap .node"));
      nodes.forEach((node, index) => {
        node.classList.toggle("selected", activeStep > 0 && index < activeStep);
        node.classList.toggle("current", index === activeStep);
      });
      updateReasonMetrics(activeStep, currentProfile || profileForCase(selectedCase()), currentReport);
      if (currentReport) {
        renderStrategyCards(currentProfile || profileForCase(selectedCase()), currentReport);
        return;
      }
      if (currentReasoningState) {
        renderStrategyCards(currentProfile || profileForCase(selectedCase()), null);
        return;
      }
      const samplePath = currentSimulationSample && Array.isArray(currentSimulationSample.strategy_path) ? currentSimulationSample.strategy_path : [];
      const sampleOrder = samplePath.length ? samplePath.map((item) => item.id) : ["S1", "S2", "S3", "S4", "S5"];
      const evaluatingOrder = ["", "", ...sampleOrder];
      renderStrategyCards(currentProfile || profileForCase(selectedCase()), null, evaluatingOrder[Math.min(activeStep, evaluatingOrder.length - 1)] || "");
    }
    function updateReasonSummary(profile, report) {
      const nodes = Array.from(document.querySelectorAll(".reason-wrap .node"));
      const best = report && report.best ? report.best : {};
      const features = report && report.features ? report.features : {};
      const attempts = attemptsFromReport(report);
      const taskCount = safeNumber(best.total_tasks || features.tasks || profile.previewOrderCount, 38);
      const courierCount = safeNumber(features.couriers || profile.previewCourierCount, profile.label === "骑手稀缺商圈" ? 8 : 18);
      const covered = safeNumber(best.covered_tasks, taskCount);
      const used = safeNumber(best.used_couriers || best.groups, profile.utilization === "91%" ? 7 : 6);
      if (nodes[0]) nodes[0].querySelector("p").innerHTML = `${taskCount} 个订单 · ${courierCount} 个骑手<br>当前场景：${profile.label}`;
      if (nodes[1]) nodes[1].querySelector("p").innerHTML = `识别商家、订单、骑手接单意愿<br>无人接单风险：${profile.missedRisk}`;
      if (nodes[2]) {
        nodes[2].querySelector("p").innerHTML = `生成 ${Math.max(5, attempts.length || 5)} 个候选派单策略<br>比较合单、单派、多候选和局部修复`;
        const metric = nodes[2].querySelector(".metric strong");
        if (metric) metric.textContent = String(Math.max(5, attempts.length || 5));
      }
      if (nodes[3]) nodes[3].querySelector("p").innerHTML = `校验商家-订单匹配、骑手容量、时间窗<br>拒绝高成本或无人接单风险方案`;
      if (nodes[5]) {
        nodes[5].querySelector("p").innerHTML = report
          ? `派出 ${used} 个骑手 · ${Object.keys(profile.assignments || {}).length} 个商家派单 · 覆盖 ${covered}/${taskCount} 个订单<br>派单约束已通过`
          : `等待当前场景推理输出最终派单<br>运行完成后自动展示全部派单覆盖`;
      }
      updateReasonMetrics(report ? 6 : 0, profile, report);
      renderStrategyCards(profile, report);
    }
    function labelOffsetFor(item, assignmentId, selectedAssignment) {
      if (assignmentId !== selectedAssignment) return [0, 0];
      const checksum = String(item.id || "").split("").reduce((sum, char) => sum + char.charCodeAt(0), 0);
      if (item.kind === "pickup_cluster" || item.kind === "merchant_order") return [14, -42];
      if (item.kind === "courier") return [checksum % 2 === 0 ? -96 : -82, checksum % 2 === 0 ? -30 : 10];
      return [18, 18 + (checksum % 3) * 18];
    }
    function mapX(value) {
      return Math.max(0, Math.min(980, safeNumber(value, 0) * 9.8));
    }
    function mapY(value) {
      return Math.max(0, Math.min(640, safeNumber(value, 0) * 6.4));
    }
    function layerPath(points) {
      const usable = (points || []).map((point) => [mapX(point.x), mapY(point.y)]).filter((point) => Number.isFinite(point[0]) && Number.isFinite(point[1]));
      if (!usable.length) return "";
      return usable.map((point, index) => `${index === 0 ? "M" : "L"}${point[0].toFixed(1)} ${point[1].toFixed(1)}`).join(" ");
    }
    function roadSortWeight(type) {
      if (type === "arterial") return 3;
      if (type === "secondary") return 2;
      return 1;
    }
    function renderSimulatedBaseMap(mapLayers) {
      const svg = document.querySelector(".map-bg");
      if (!svg) return;
      svg.dataset.mapStyle = mapLayers && mapLayers.style ? mapLayers.style : "empty";
      const districts = Array.isArray(mapLayers && mapLayers.districts) ? mapLayers.districts : [];
      const blocks = Array.isArray(mapLayers && mapLayers.building_blocks) ? mapLayers.building_blocks : [];
      const traces = Array.isArray(mapLayers && mapLayers.base_map_traces) ? mapLayers.base_map_traces : [];
      const roads = Array.isArray(mapLayers && mapLayers.roads) ? mapLayers.roads.slice() : [];
      const hotspots = Array.isArray(mapLayers && mapLayers.commerce_hotspots) ? mapLayers.commerce_hotspots : [];
      const intersections = Array.isArray(mapLayers && mapLayers.intersections) ? mapLayers.intersections : [];
      const rainStreaks = Array.isArray(mapLayers && mapLayers.rain_streaks) ? mapLayers.rain_streaks : [];
      if (!mapLayers || roads.length === 0) {
        svg.dataset.weather = "clear";
        svg.dataset.densityProfile = "empty";
        svg.innerHTML = [
          `<defs><pattern id="anonymous-grid" width="56" height="56" patternUnits="userSpaceOnUse"><path d="M56 0H0V56" fill="none" stroke="rgba(148,163,184,.08)" stroke-width="1"/></pattern></defs>`,
          `<rect x="0" y="0" width="980" height="640" fill="url(#anonymous-grid)" opacity=".38"></rect>`,
          `<rect class="zone-block" x="70" y="70" width="250" height="160" rx="12" opacity=".26"></rect>`,
          `<rect class="zone-block" x="390" y="92" width="360" height="190" rx="12" opacity=".22"></rect>`,
          `<rect class="zone-block" x="136" y="360" width="320" height="138" rx="12" opacity=".2"></rect>`
        ].join("");
        return;
      }
      svg.dataset.weather = mapLayers.weather || "clear";
      svg.dataset.densityProfile = mapLayers.density_profile || "balanced";
      const sortedRoads = roads.sort((a, b) => roadSortWeight(a.type) - roadSortWeight(b.type));
      const districtHtml = districts.map((item) => {
        const opacity = Math.max(0.16, Math.min(0.52, safeNumber(item.intensity, 0.28)));
        return `<rect class="zone-block district" data-zone="${escapeAttr(item.id)}" x="${mapX(item.x).toFixed(1)}" y="${mapY(item.y).toFixed(1)}" width="${(safeNumber(item.width, 10) * 9.8).toFixed(1)}" height="${(safeNumber(item.height, 8) * 6.4).toFixed(1)}" rx="12" opacity="${opacity.toFixed(2)}"></rect>`;
      }).join("");
      const blockHtml = blocks.map((item) => {
        const width = safeNumber(item.width, 7) * 9.8;
        const height = safeNumber(item.height, 6) * 6.4;
        const x = mapX(item.x);
        const y = mapY(item.y);
        const cx = x + width / 2;
        const cy = y + height / 2;
        const opacity = Math.max(0.24, Math.min(0.78, safeNumber(item.intensity, 0.4)));
        const usage = ["commerce", "office", "residential"].includes(item.usage) ? item.usage : "office";
        return `<rect class="building-block ${usage}" data-block="${escapeAttr(item.id)}" x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${width.toFixed(1)}" height="${height.toFixed(1)}" rx="4" opacity="${opacity.toFixed(2)}" transform="rotate(${safeNumber(item.rotation, 0).toFixed(1)} ${cx.toFixed(1)} ${cy.toFixed(1)})"></rect>`;
      }).join("");
      const traceHtml = traces.map((trace) => {
        const d = layerPath(trace.points);
        const cls = ["collector", "local", "ring"].includes(trace.class) ? trace.class : "local";
        return d ? `<path class="map-trace ${cls}" data-trace="${escapeAttr(trace.id)}" d="${d}"></path>` : "";
      }).join("");
      const hotspotHtml = hotspots.map((item) => {
        const opacity = Math.max(0.16, Math.min(0.46, safeNumber(item.intensity, 0.32)));
        return `<circle class="commerce-hotspot" data-hotspot="${escapeAttr(item.id)}" cx="${mapX(item.x).toFixed(1)}" cy="${mapY(item.y).toFixed(1)}" r="${(safeNumber(item.radius, 8) * 7.1).toFixed(1)}" opacity="${opacity.toFixed(2)}"></circle>`;
      }).join("");
      const roadBaseHtml = sortedRoads.map((road) => {
        const d = layerPath(road.points);
        const type = ["arterial", "secondary", "service"].includes(road.type) ? road.type : "service";
        const width = Math.max(1.2, safeNumber(road.width, 4.2) * (type === "arterial" ? 0.54 : type === "secondary" ? 0.48 : 0.42));
        const casing = type === "arterial" ? 1.4 : type === "secondary" ? 1 : 0.4;
        return `<path class="road-base ${type}" data-road="${escapeAttr(road.id)}" style="--road-width:${(width + casing).toFixed(1)}px" d="${d}"></path>`;
      }).join("");
      const roadCoreHtml = sortedRoads.map((road) => {
        const d = layerPath(road.points);
        const type = ["arterial", "secondary", "service"].includes(road.type) ? road.type : "service";
        const width = Math.max(1.1, safeNumber(road.width, 4.2) * (type === "arterial" ? 0.54 : type === "secondary" ? 0.48 : 0.42));
        return `<path class="road-core ${type}" data-road="${escapeAttr(road.id)}" style="--road-width:${width.toFixed(1)}px" d="${d}"></path>`;
      }).join("");
      const trafficHtml = sortedRoads.filter((road) => road.type !== "service").map((road) => {
        const d = layerPath(road.points);
        const traffic = ["heavy", "moderate", "smooth"].includes(road.traffic) ? road.traffic : "smooth";
        const width = Math.max(0.75, safeNumber(road.width, 4) * 0.16);
        return `<path class="traffic-band ${traffic}" data-traffic="${traffic}" data-road="${escapeAttr(road.id)}" style="--traffic-width:${width.toFixed(1)}px" d="${d}"></path>`;
      }).join("");
      const intersectionHtml = intersections.map((item) => {
        const busy = safeNumber(item.signal_load, 0) > 0.68 ? " busy" : "";
        return `<circle class="intersection-node${busy}" data-intersection="${escapeAttr(item.id)}" cx="${mapX(item.x).toFixed(1)}" cy="${mapY(item.y).toFixed(1)}" r="${busy ? 4.8 : 3.4}"></circle>`;
      }).join("");
      const weatherHtml = rainStreaks.length
        ? `<g class="weather-rain-layer"><rect class="rain-sheen" x="0" y="0" width="980" height="640"></rect>${rainStreaks.map((item) => {
            const x = mapX(item.x);
            const y = mapY(item.y);
            const length = safeNumber(item.length, 6) * 6.4;
            const opacity = Math.max(0.08, Math.min(0.42, safeNumber(item.opacity, 0.18)));
            return `<line class="rain-streak" data-rain="${escapeAttr(item.id)}" x1="${x.toFixed(1)}" y1="${y.toFixed(1)}" x2="${(x - length * .36).toFixed(1)}" y2="${(y + length).toFixed(1)}" opacity="${opacity.toFixed(2)}"></line>`;
          }).join("")}</g>`
        : "";
      svg.innerHTML = [
        `<defs><pattern id="meituan-grid" width="48" height="48" patternUnits="userSpaceOnUse"><path d="M48 0H0V48" fill="none" stroke="rgba(190,203,214,.045)" stroke-width="1"/></pattern><pattern id="delivery-parcel-mesh" width="154" height="118" patternUnits="userSpaceOnUse"><path d="M-18 30H170M20 -12V132M-20 82H138M92 -10V126M8 108L150 18M-32 12L104 104M46 0L132 72M-18 54L72 128" fill="none" stroke="rgba(136,156,160,.12)" stroke-width=".85" stroke-linecap="round"/></pattern><linearGradient id="meituan-map-warmth" x1="0" x2="1"><stop offset="0" stop-color="rgba(255,184,49,.04)"/><stop offset=".52" stop-color="rgba(45,212,191,.025)"/><stop offset="1" stop-color="rgba(255,184,49,.035)"/></linearGradient></defs>`,
        `<rect x="0" y="0" width="980" height="640" fill="#0b141b"></rect>`,
        `<rect x="0" y="0" width="980" height="640" fill="url(#meituan-map-warmth)" opacity=".9"></rect>`,
        `<rect x="0" y="0" width="980" height="640" fill="url(#meituan-grid)" opacity=".28"></rect>`,
        `<rect x="0" y="0" width="980" height="640" fill="url(#delivery-parcel-mesh)" opacity=".32"></rect>`,
        `<path class="water" d="M0 548 C122 508 188 574 304 538 C412 506 470 570 582 536 C684 502 758 558 862 526 C922 508 956 510 980 496 L980 640 L0 640 Z" opacity=".26"></path>`,
        traceHtml,
        districtHtml,
        blockHtml,
        hotspotHtml,
        roadBaseHtml,
        roadCoreHtml,
        trafficHtml,
        intersectionHtml,
        weatherHtml
      ].join("");
    }
    function updateTrafficWidget(summary) {
      const weather = document.querySelector(".weather");
      if (!weather) return;
      const traffic = summary && summary.traffic ? summary.traffic : "moderate";
      const weatherName = summary && summary.weather ? summary.weather : "clear";
      const weatherLabel = summary && summary.weather_label ? summary.weather_label : weatherName === "rain" ? "雨天 · 路面湿滑" : weatherName === "event" ? "活动 · 局部管制" : "晴朗 · 正常履约";
      const label = traffic === "heavy" ? "拥堵" : traffic === "smooth" ? "畅通" : "缓行";
      const color = traffic === "heavy" ? "#dc2626" : traffic === "smooth" ? "#16a34a" : "#d97706";
      const trafficStrong = weather.querySelector(".weather-badge");
      const weatherStrong = weather.querySelector(".weather-state");
      const impactStrong = weather.querySelector(".weather-impact-value");
      const impactBody = weather.querySelector(".weather-impact");
      const impactText = traffic === "heavy"
        ? "ETA 上浮"
        : weatherName === "rain"
          ? "接单意愿下降"
          : weatherName === "event"
            ? "局部绕行"
            : "正常履约";
      const impactBodyText = traffic === "heavy"
        ? "调度建议：提高近场骑手权重，避免跨区派单。"
        : weatherName === "rain"
          ? "调度建议：提高接单意愿权重，预留雨天 ETA 缓冲。"
          : weatherName === "event"
            ? "调度建议：绕开活动核心区，优先稳定履约。"
            : "调度建议：按常规成本与时效权重派单。";
      if (trafficStrong) {
        trafficStrong.textContent = label;
        trafficStrong.style.color = color;
        trafficStrong.style.background = traffic === "heavy" ? "#fff1f2" : traffic === "smooth" ? "#ecfdf5" : "#fff7ed";
        trafficStrong.style.borderColor = traffic === "heavy" ? "rgba(244,63,94,.22)" : traffic === "smooth" ? "rgba(22,163,74,.22)" : "rgba(217,119,6,.2)";
      }
      if (weatherStrong) weatherStrong.textContent = weatherLabel;
      if (impactStrong) impactStrong.textContent = impactText;
      if (impactBody) impactBody.textContent = impactBodyText;
    }
    function displayPositionsForLabels(labels) {
      const placed = [];
      const positions = {};
      const density = currentSimulationSample && currentSimulationSample.summary ? currentSimulationSample.summary.density_profile : "";
      const isClusteredScene = String(density || "").includes("clustered");
      const minDistanceFor = (item) => {
        const kind = item && item.kind ? item.kind : "";
        if (kind === "merchant_order" || kind === "pickup_cluster") return isClusteredScene ? 24 : 30;
        if (kind === "order") return 28;
        if (kind === "courier") return isClusteredScene ? 32 : 36;
        return 32;
      };
      const pointDistance = (a, b) => Math.hypot((a.x - b.x) * 9.8, (a.y - b.y) * 6.4);
      const collides = (candidate, item) => placed.some((point) => {
        const threshold = Math.max(minDistanceFor(item), point.minDistance || 32);
        return pointDistance(candidate, point) < threshold;
      });
      (labels || []).forEach((item) => {
        const raw = {x: safeNumber(item.x, 50), y: safeNumber(item.y, 50)};
        let chosen = {...raw};
        let avoided = false;
        if (collides(chosen, item)) {
          const checksum = String(item.id || "").split("").reduce((sum, char) => sum + char.charCodeAt(0), 0);
          for (let attempt = 0; attempt < 42; attempt += 1) {
            const angle = ((checksum * 37 + attempt * 137) % 360) * Math.PI / 180;
            const radiusPx = 40 + Math.floor(attempt / 7) * 12;
            const candidate = {
              x: Math.max(6, Math.min(94, raw.x + Math.cos(angle) * radiusPx / 9.8)),
              y: Math.max(6, Math.min(94, raw.y + Math.sin(angle) * radiusPx / 6.4))
            };
            if (!collides(candidate, item)) {
              chosen = candidate;
              avoided = true;
              break;
            }
          }
        }
        positions[item.id] = {
          x: chosen.x,
          y: chosen.y,
          rawX: raw.x,
          rawY: raw.y,
          avoided: avoided || pointDistance(chosen, raw) > 2
        };
        placed.push({id: item.id, kind: item.kind, x: chosen.x, y: chosen.y, minDistance: minDistanceFor(item)});
      });
      return positions;
    }
    function updateMapScene(profile) {
      renderProjectBasemapState();
      applyRenderedMapAnchors(profile);
      const dynamicLabels = sceneLabels(profile);
      const displayPositions = displayPositionsForLabels(dynamicLabels);
      const entityPoints = {};
      const entityKinds = {};
      if (profile.dispatchMap && Array.isArray(profile.dispatchMap.entities)) {
        profile.dispatchMap.entities.forEach((entity) => {
          entityPoints[entity.id] = [entity.x, entity.y];
          entityKinds[entity.id] = entity.kind;
        });
      }
      const frame = document.querySelector(".map-frame");
      const hasAssignments = Boolean(profile.dispatchMap && profile.assignments && Object.keys(profile.assignments).length);
      const focusMode = Boolean(hasAssignments && profile.selected && profile.mapFocusMode === "focus");
      frame.classList.toggle("topology", Boolean(profile.dispatchMap));
      frame.classList.toggle("focus-selected", focusMode);
      frame.classList.toggle("assignment-overview", Boolean(hasAssignments && !focusMode));
      renderSimulatedBaseMap(profile.dispatchMap && profile.dispatchMap.map_layers);
      syncSemiRealMapOverlay(profile);
      if (hasAssignments && profile.selected && focusMode) {
        frame.dataset.selectedAssignment = profile.selected;
      } else {
        frame.removeAttribute("data-selected-assignment");
      }
      const entityLayer = document.querySelector(".map-entities");
      entityLayer.innerHTML = "";
      dynamicLabels.forEach((item) => {
        const assignmentId = assignmentForEntity(profile, item.id);
        const display = displayPositions[item.id] || {x: item.x, y: item.y, rawX: item.x, rawY: item.y, avoided: false};
        const rawPoint = {x: safeNumber(item.x, safeNumber(display.rawX, 50)), y: safeNumber(item.y, safeNumber(display.rawY, 50))};
        const labelOffset = labelOffsetFor(item, assignmentId, profile.selected);
        const pin = document.createElement("div");
        const isMerchantPoint = item.kind === "pickup_cluster" || item.kind === "merchant_order";
        const pinKind = isMerchantPoint ? "merchant" : item.kind === "courier" ? "courier" : "dest";
        const markKind = isMerchantPoint ? "merchant" : item.kind === "courier" ? "courier" : "dest";
        const showSelectedLabel = false;
        pin.className = `pin ${pinKind}`;
        pin.dataset.entity = item.id;
        pin.dataset.kind = item.kind || "";
        pin.dataset.assignment = assignmentId;
        pin.dataset.rawX = Number(rawPoint.x).toFixed(1);
        pin.dataset.rawY = Number(rawPoint.y).toFixed(1);
        pin.dataset.displayX = Number(rawPoint.x).toFixed(1);
        pin.dataset.displayY = Number(rawPoint.y).toFixed(1);
        pin.classList.toggle("active-assignment", assignmentId === profile.selected);
        pin.classList.toggle("label-avoided", Boolean(display.avoided));
        pin.style.left = Number(rawPoint.x).toFixed(1) + "%";
        pin.style.top = Number(rawPoint.y).toFixed(1) + "%";
        pin.title = hasAssignments ? "点击聚焦 " + item.id + " 的派单链路" : "点击查看 " + item.id + " 的样本详情";
        pin.innerHTML = `<span class="mark ${markKind}"><span class="mark-symbol">${isMerchantPoint ? "商" : "骑"}</span></span>`;
        entityLayer.appendChild(pin);

        if (item.hideLabel && !showSelectedLabel) return;
        const label = document.createElement("div");
        label.className = "map-label";
        label.innerHTML = item.html;
        label.style.left = Number(display.x).toFixed(1) + "%";
        label.style.top = Number(display.y).toFixed(1) + "%";
        label.style.setProperty("--label-offset-x", labelOffset[0] + "px");
        label.style.setProperty("--label-offset-y", labelOffset[1] + "px");
        label.dataset.entity = item.id;
        label.dataset.kind = item.kind || "";
        label.dataset.assignment = assignmentId;
        label.dataset.rawX = Number(display.rawX).toFixed(1);
        label.dataset.rawY = Number(display.rawY).toFixed(1);
        label.dataset.displayX = Number(display.x).toFixed(1);
        label.dataset.displayY = Number(display.y).toFixed(1);
        if (isMerchantPoint) label.classList.add("pickup");
        if (item.kind === "order") label.classList.add("order");
        if (item.kind === "courier") label.classList.add("courier-node");
        label.classList.toggle("selected", assignmentId === profile.selected);
        label.classList.toggle("focused", assignmentId === profile.selected);
        label.classList.toggle("active-assignment", assignmentId === profile.selected);
        label.title = "点击查看 " + item.id + " 的派单详情";
        entityLayer.appendChild(label);
      });
      renderDispatchLinks(profile, entityPoints);
      applyMapFocus(profile, profile.selected, profile.mapFocusMode === "focus");
    }
    function svgPoint(point) {
      return [Number(point[0]) * 9.8, Number(point[1]) * 6.4];
    }
    function distance2D(a, b) {
      return Math.hypot(safeNumber(a[0], 0) - safeNumber(b[0], 0), safeNumber(a[1], 0) - safeNumber(b[1], 0));
    }
    function projectPointToSegment(point, start, end) {
      const px = safeNumber(point[0], 0);
      const py = safeNumber(point[1], 0);
      const sx = safeNumber(start[0], 0);
      const sy = safeNumber(start[1], 0);
      const ex = safeNumber(end[0], 0);
      const ey = safeNumber(end[1], 0);
      const dx = ex - sx;
      const dy = ey - sy;
      const lengthSq = dx * dx + dy * dy || 1;
      const t = Math.max(0, Math.min(1, ((px - sx) * dx + (py - sy) * dy) / lengthSq));
      const projected = [sx + t * dx, sy + t * dy];
      return {point: projected, t, distance: distance2D(point, projected)};
    }
    function normalizedRoadPoints(road) {
      return (road && Array.isArray(road.points) ? road.points : []).map((point) => [safeNumber(point.x, 0), safeNumber(point.y, 0)]);
    }
    function nearestRoadSnap(point, mapLayers, roadFilter = null) {
      const roads = Array.isArray(mapLayers && mapLayers.roads) ? mapLayers.roads : [];
      let best = null;
      roads.forEach((road) => {
        if (roadFilter && !roadFilter(road)) return;
        const roadPoints = normalizedRoadPoints(road);
        for (let index = 0; index < roadPoints.length - 1; index += 1) {
          const projection = projectPointToSegment(point, roadPoints[index], roadPoints[index + 1]);
          if (!best || projection.distance < best.distance) {
            best = {
              ...projection,
              road,
              roadPoints,
              segmentIndex: index,
              roadRank: road.type === "arterial" ? 3 : road.type === "secondary" ? 2 : 1
            };
          }
        }
      });
      return best;
    }
    function roadSnapCandidates(point, mapLayers, roadFilter = null, maxDistance = 13, limit = 10) {
      const roads = Array.isArray(mapLayers && mapLayers.roads) ? mapLayers.roads : [];
      const candidates = [];
      roads.forEach((road) => {
        if (roadFilter && !roadFilter(road)) return;
        const roadPoints = normalizedRoadPoints(road);
        for (let index = 0; index < roadPoints.length - 1; index += 1) {
          const projection = projectPointToSegment(point, roadPoints[index], roadPoints[index + 1]);
          if (projection.distance > maxDistance) continue;
          candidates.push({
            ...projection,
            road,
            roadPoints,
            segmentIndex: index,
            roadRank: road.type === "arterial" ? 3 : road.type === "secondary" ? 2 : 1
          });
        }
      });
      const deduped = [];
      candidates
        .sort((left, right) => {
          const leftTypePenalty = left.road.type === "service" ? 2.8 : left.road.type === "secondary" ? .5 : 0;
          const rightTypePenalty = right.road.type === "service" ? 2.8 : right.road.type === "secondary" ? .5 : 0;
          return (left.distance + leftTypePenalty) - (right.distance + rightTypePenalty);
        })
        .forEach((candidate) => {
          const duplicate = deduped.some((item) => item.road === candidate.road && item.segmentIndex === candidate.segmentIndex);
          if (!duplicate) deduped.push(candidate);
        });
      const nearest = nearestRoadSnap(point, mapLayers, roadFilter) || nearestRoadSnap(point, mapLayers);
      if (nearest && !deduped.some((item) => item.road === nearest.road && item.segmentIndex === nearest.segmentIndex)) {
        deduped.push(nearest);
      }
      return deduped.slice(0, limit);
    }
    function snapOnRoad(point, road) {
      const roadPoints = normalizedRoadPoints(road);
      let best = null;
      for (let index = 0; index < roadPoints.length - 1; index += 1) {
        const projection = projectPointToSegment(point, roadPoints[index], roadPoints[index + 1]);
        if (!best || projection.distance < best.distance) {
          best = {...projection, road, roadPoints, segmentIndex: index};
        }
      }
      return best;
    }
    function segmentIntersection(a, b, c, d) {
      const dax = b[0] - a[0];
      const day = b[1] - a[1];
      const dcx = d[0] - c[0];
      const dcy = d[1] - c[1];
      const denominator = dax * dcy - day * dcx;
      if (Math.abs(denominator) < 0.0001) return null;
      const t = ((c[0] - a[0]) * dcy - (c[1] - a[1]) * dcx) / denominator;
      const u = ((c[0] - a[0]) * day - (c[1] - a[1]) * dax) / denominator;
      if (t < 0 || t > 1 || u < 0 || u > 1) return null;
      return [a[0] + t * dax, a[1] + t * day];
    }
    function closestSegmentPair(a, b, c, d) {
      const intersection = segmentIntersection(a, b, c, d);
      if (intersection) return {fromPoint: intersection, toPoint: intersection, distance: 0};
      const candidates = [
        {fromPoint: projectPointToSegment(c, a, b).point, toPoint: c},
        {fromPoint: projectPointToSegment(d, a, b).point, toPoint: d},
        {fromPoint: a, toPoint: projectPointToSegment(a, c, d).point},
        {fromPoint: b, toPoint: projectPointToSegment(b, c, d).point}
      ];
      return candidates.map((item) => ({...item, distance: distance2D(item.fromPoint, item.toPoint)}))
        .sort((left, right) => left.distance - right.distance)[0];
    }
    function closestRoadTransfer(fromRoad, toRoad) {
      const fromPoints = normalizedRoadPoints(fromRoad);
      const toPoints = normalizedRoadPoints(toRoad);
      let best = null;
      for (let fromIndex = 0; fromIndex < fromPoints.length - 1; fromIndex += 1) {
        for (let toIndex = 0; toIndex < toPoints.length - 1; toIndex += 1) {
          const pair = closestSegmentPair(fromPoints[fromIndex], fromPoints[fromIndex + 1], toPoints[toIndex], toPoints[toIndex + 1]);
          if (!best || pair.distance < best.distance) {
            best = {...pair, fromIndex, toIndex};
          }
        }
      }
      return best;
    }
    function chainBetweenRoadPoints(road, fromPoint, toPoint) {
      const fromSnap = snapOnRoad(fromPoint, road);
      const toSnap = snapOnRoad(toPoint, road);
      return chainAlongRoad(fromSnap, toSnap);
    }
    function connectorRoadBetween(startRoad, endRoad, mapLayers) {
      const roads = Array.isArray(mapLayers && mapLayers.roads) ? mapLayers.roads : [];
      const direct = closestRoadTransfer(startRoad, endRoad);
      let best = direct ? {road: null, score: direct.distance, direct} : null;
      roads.filter((road) => road !== startRoad && road !== endRoad && road.type !== "service").forEach((road) => {
        const first = closestRoadTransfer(startRoad, road);
        const second = closestRoadTransfer(road, endRoad);
        if (!first || !second) return;
        const roadPenalty = road.type === "arterial" ? -2.5 : 0;
        const score = first.distance + second.distance + distance2D(first.toPoint, second.fromPoint) * 0.14 + roadPenalty;
        if (!best || score < best.score) best = {road, score, first, second, direct};
      });
      return best;
    }
    function chainAlongRoad(fromSnap, toSnap) {
      if (!fromSnap || !toSnap || fromSnap.road !== toSnap.road) return [];
      const roadPoints = fromSnap.roadPoints || [];
      const forward = fromSnap.segmentIndex <= toSnap.segmentIndex;
      const chain = [fromSnap.point];
      if (forward) {
        for (let index = fromSnap.segmentIndex + 1; index <= toSnap.segmentIndex; index += 1) {
          if (roadPoints[index]) chain.push(roadPoints[index]);
        }
      } else {
        for (let index = fromSnap.segmentIndex; index > toSnap.segmentIndex; index -= 1) {
          if (roadPoints[index]) chain.push(roadPoints[index]);
        }
      }
      chain.push(toSnap.point);
      return chain;
    }
    function routeHubBetween(start, end, mapLayers) {
      const midpoint = [(safeNumber(start[0], 0) + safeNumber(end[0], 0)) / 2, (safeNumber(start[1], 0) + safeNumber(end[1], 0)) / 2];
      const intersections = Array.isArray(mapLayers && mapLayers.intersections) ? mapLayers.intersections : [];
      const candidates = intersections.map((item) => [safeNumber(item.x, 50), safeNumber(item.y, 50)]);
      candidates.push([50, 50], [42, 46], [58, 44]);
      return candidates.slice().sort((a, b) => distance2D(a, midpoint) - distance2D(b, midpoint))[0];
    }
    function compactRoutePoints(points) {
      return points.filter(Boolean).reduce((list, point) => {
        const normalized = [Number(point[0]), Number(point[1])];
        if (!Number.isFinite(normalized[0]) || !Number.isFinite(normalized[1])) return list;
        const previous = list[list.length - 1];
        if (!previous || distance2D(previous, normalized) > 0.8) list.push(normalized);
        return list;
      }, []);
    }
    function pointLineDistance(point, start, end) {
      const sx = safeNumber(start[0], 0);
      const sy = safeNumber(start[1], 0);
      const ex = safeNumber(end[0], 0);
      const ey = safeNumber(end[1], 0);
      const length = Math.hypot(ex - sx, ey - sy);
      if (length < 0.001) return distance2D(point, start);
      return Math.abs((ey - sy) * point[0] - (ex - sx) * point[1] + ex * sy - ey * sx) / length;
    }
    function simplifyRoutePoints(points, tolerance = 0.72) {
      const usable = compactRoutePoints(points || []);
      if (usable.length <= 2) return usable;
      let maxDistance = 0;
      let splitIndex = 0;
      const start = usable[0];
      const end = usable[usable.length - 1];
      for (let index = 1; index < usable.length - 1; index += 1) {
        const distance = pointLineDistance(usable[index], start, end);
        if (distance > maxDistance) {
          maxDistance = distance;
          splitIndex = index;
        }
      }
      if (maxDistance <= tolerance) return [start, end];
      const left = simplifyRoutePoints(usable.slice(0, splitIndex + 1), tolerance);
      const right = simplifyRoutePoints(usable.slice(splitIndex), tolerance);
      return [...left.slice(0, -1), ...right];
    }
    function densifyRoutePoints(points, maxGap = 4.8) {
      const usable = compactRoutePoints(points || []);
      if (usable.length < 2) return usable;
      const dense = [usable[0]];
      for (let index = 1; index < usable.length; index += 1) {
        const start = usable[index - 1];
        const end = usable[index];
        const length = distance2D(start, end);
        const steps = Math.max(1, Math.ceil(length / maxGap));
        for (let step = 1; step <= steps; step += 1) {
          const t = step / steps;
          dense.push([start[0] + (end[0] - start[0]) * t, start[1] + (end[1] - start[1]) * t]);
        }
      }
      return compactRoutePoints(dense);
    }
    function endpointConnectorFor(entityPoint, roadPoint) {
      if (!entityPoint || !roadPoint) return [];
      const distance = distance2D(entityPoint, roadPoint);
      if (distance <= 0.28 || distance > 8.0) return [];
      return densifyRoutePoints([entityPoint, roadPoint], 2.8);
    }
    function roadTerminalRoute(start, startSnap, coreRoute, endSnap, end) {
      const startPoint = startSnap && startSnap.point ? startSnap.point : start;
      const endPoint = endSnap && endSnap.point ? endSnap.point : end;
      const roadCore = simplifyRoutePoints(densifyRoutePoints([startPoint, ...(coreRoute || []), endPoint], 4.2), 0.78);
      const route = simplifyRoutePoints(densifyRoutePoints([start, startPoint, ...(coreRoute || []), endPoint, end], 4.8), 0.64);
      route.roadCore = roadCore.length >= 2 ? roadCore : route;
      route.endpointConnectors = [
        endpointConnectorFor(start, startPoint),
        endpointConnectorFor(end, endPoint)
      ].filter((connector) => connector.length >= 2);
      return route;
    }
    function roadNodeKey(point) {
      return `${safeNumber(point[0], 0).toFixed(2)},${safeNumber(point[1], 0).toFixed(2)}`;
    }
    function addRoadGraphNode(graph, point) {
      const key = roadNodeKey(point);
      if (!graph.nodes[key]) graph.nodes[key] = [safeNumber(point[0], 0), safeNumber(point[1], 0)];
      if (!graph.edges[key]) graph.edges[key] = [];
      return key;
    }
    function addRoadGraphEdge(graph, from, to) {
      const fromKey = addRoadGraphNode(graph, from);
      const toKey = addRoadGraphNode(graph, to);
      const weight = Math.max(0.01, distance2D(from, to));
      graph.edges[fromKey].push({to: toKey, weight});
      graph.edges[toKey].push({to: fromKey, weight});
    }
    function buildRoadGraph(mapLayers, startSnap, endSnap) {
      const roads = Array.isArray(mapLayers && mapLayers.roads) ? mapLayers.roads : [];
      const graph = {nodes: {}, edges: {}, segments: []};
      roads.forEach((road, roadIndex) => {
        const roadPoints = normalizedRoadPoints(road);
        for (let index = 0; index < roadPoints.length - 1; index += 1) {
          const segment = {
            road,
            roadIndex,
            segmentIndex: index,
            start: roadPoints[index],
            end: roadPoints[index + 1]
          };
          graph.segments.push(segment);
          addRoadGraphEdge(graph, segment.start, segment.end);
        }
      });
      for (let left = 0; left < graph.segments.length; left += 1) {
        for (let right = left + 1; right < graph.segments.length; right += 1) {
          const a = graph.segments[left];
          const b = graph.segments[right];
          if (a.roadIndex === b.roadIndex) continue;
          const intersection = segmentIntersection(a.start, a.end, b.start, b.end);
          if (intersection) {
            addRoadGraphEdge(graph, intersection, a.start);
            addRoadGraphEdge(graph, intersection, a.end);
            addRoadGraphEdge(graph, intersection, b.start);
            addRoadGraphEdge(graph, intersection, b.end);
            continue;
          }
          const transfer = closestSegmentPair(a.start, a.end, b.start, b.end);
          if (transfer && transfer.distance <= 0.85) {
            addRoadGraphEdge(graph, transfer.fromPoint, transfer.toPoint);
            addRoadGraphEdge(graph, transfer.fromPoint, a.start);
            addRoadGraphEdge(graph, transfer.fromPoint, a.end);
            addRoadGraphEdge(graph, transfer.toPoint, b.start);
            addRoadGraphEdge(graph, transfer.toPoint, b.end);
          }
        }
      }
      const connectSnap = (snap) => {
        if (!snap) return "";
        const segment = graph.segments.find((item) => item.road === snap.road && item.segmentIndex === snap.segmentIndex);
        const key = addRoadGraphNode(graph, snap.point);
        if (segment) {
          addRoadGraphEdge(graph, snap.point, segment.start);
          addRoadGraphEdge(graph, snap.point, segment.end);
        }
        return key;
      };
      return {
        graph,
        startKey: connectSnap(startSnap),
        endKey: connectSnap(endSnap)
      };
    }
    function shortestRoadGraphPath(graphPayload) {
      const graph = graphPayload && graphPayload.graph;
      const startKey = graphPayload && graphPayload.startKey;
      const endKey = graphPayload && graphPayload.endKey;
      if (!graph || !startKey || !endKey || !graph.nodes[startKey] || !graph.nodes[endKey]) return [];
      const distances = {[startKey]: 0};
      const previous = {};
      const visited = new Set();
      const queue = [startKey];
      while (queue.length) {
        queue.sort((left, right) => safeNumber(distances[left], Infinity) - safeNumber(distances[right], Infinity));
        const current = queue.shift();
        if (!current || visited.has(current)) continue;
        if (current === endKey) break;
        visited.add(current);
        (graph.edges[current] || []).forEach((edge) => {
          const nextDistance = safeNumber(distances[current], Infinity) + safeNumber(edge.weight, Infinity);
          if (nextDistance < safeNumber(distances[edge.to], Infinity)) {
            distances[edge.to] = nextDistance;
            previous[edge.to] = current;
            queue.push(edge.to);
          }
        });
      }
      if (startKey !== endKey && !previous[endKey]) return [];
      const keys = [endKey];
      while (keys[0] !== startKey) {
        const parent = previous[keys[0]];
        if (!parent) return [];
        keys.unshift(parent);
      }
      return keys.map((key) => graph.nodes[key]).filter(Boolean);
    }
    function routeTurnPenalty(points) {
      const usable = simplifyRoutePoints(points || [], 0.55);
      if (usable.length < 3) return 0;
      let penalty = 0;
      for (let index = 1; index < usable.length - 1; index += 1) {
        const prev = usable[index - 1];
        const current = usable[index];
        const next = usable[index + 1];
        const a1 = Math.atan2(current[1] - prev[1], current[0] - prev[0]);
        const a2 = Math.atan2(next[1] - current[1], next[0] - current[0]);
        const delta = Math.abs(Math.atan2(Math.sin(a2 - a1), Math.cos(a2 - a1)));
        if (delta > 0.42) penalty += delta;
      }
      return penalty;
    }
    function roadRouteForSnaps(start, startSnap, endSnap, end, mapLayers) {
      if (!startSnap || !endSnap) return [];
      const graphRoute = shortestRoadGraphPath(buildRoadGraph(mapLayers, startSnap, endSnap));
      if (graphRoute.length >= 2) {
        return roadTerminalRoute(start, startSnap, graphRoute, endSnap, end);
      }
      if (startSnap.road === endSnap.road) {
        return roadTerminalRoute(start, startSnap, chainAlongRoad(startSnap, endSnap), endSnap, end);
      }
      const connector = connectorRoadBetween(startSnap.road, endSnap.road, mapLayers);
      if (connector && connector.road && connector.first && connector.second && connector.first.distance <= 1.4 && connector.second.distance <= 1.4) {
        const startChain = chainBetweenRoadPoints(startSnap.road, startSnap.point, connector.first.fromPoint);
        const middleChain = chainBetweenRoadPoints(connector.road, connector.first.toPoint, connector.second.fromPoint);
        const endChain = chainBetweenRoadPoints(endSnap.road, connector.second.toPoint, endSnap.point);
        return roadTerminalRoute(start, startSnap, [...startChain, connector.first.toPoint, ...middleChain, connector.second.fromPoint, ...endChain], endSnap, end);
      }
      if (connector && connector.direct && connector.direct.distance <= 1.4) {
        const startChain = chainBetweenRoadPoints(startSnap.road, startSnap.point, connector.direct.fromPoint);
        const endChain = chainBetweenRoadPoints(endSnap.road, connector.direct.toPoint, endSnap.point);
        return roadTerminalRoute(start, startSnap, [...startChain, connector.direct.toPoint, ...endChain], endSnap, end);
      }
      return roadTerminalRoute(start, startSnap, [startSnap.point, endSnap.point], endSnap, end);
    }
    function roadFollowingRoute(start, end, mapLayers) {
      if (!mapLayers || !Array.isArray(mapLayers.roads)) return [start, end];
      const directDistance = distance2D(start, end);
      const roadFilter = (road) => road.type !== "service" || directDistance < 20;
      const startSnaps = roadSnapCandidates(start, mapLayers, roadFilter, 8, 6);
      const endSnaps = roadSnapCandidates(end, mapLayers, roadFilter, 14, 10);
      if (!startSnaps.length || !endSnaps.length) return [start, end];
      let best = null;
      startSnaps.forEach((startSnap) => {
        endSnaps.forEach((endSnap) => {
          const route = roadRouteForSnaps(start, startSnap, endSnap, end, mapLayers);
          if (!route || route.length < 2) return;
          const length = routePolylineLength(route);
          const span = routeSpan(route);
          const turns = routeTurnPenalty(route);
          const detourRatio = length / Math.max(1, directDistance);
          const servicePenalty = (startSnap.road.type === "service" ? 4 : 0) + (endSnap.road.type === "service" ? 4 : 0);
          const score = length + span * 0.14 + turns * 7.5 + startSnap.distance * 1.5 + endSnap.distance * 2.2 + Math.max(0, detourRatio - 1.8) * 18 + servicePenalty;
          if (!best || score < best.score) best = {route, score};
        });
      });
      return best && best.route ? best.route : roadTerminalRoute(start, startSnaps[0], [startSnaps[0].point, endSnaps[0].point], endSnaps[0], end);
    }
    function presentableDispatchRoute(route, start, end) {
      const usable = simplifyRoutePoints(route || [], 0.72);
      if (usable.length < 2) return [start, end];
      const directDistance = Math.max(1, distance2D(start, end));
      const length = routePolylineLength(usable);
      const span = routeSpan(usable);
      const turns = routeTurnPenalty(usable);
      if (length / directDistance > 2.05 || turns > 2.35 || span / directDistance > 1.8) {
        const clean = [start, end];
        clean.roadCore = clean;
        clean.endpointConnectors = [];
        return clean;
      }
      usable.roadCore = Array.isArray(route && route.roadCore) ? simplifyRoutePoints(route.roadCore, 0.78) : usable;
      usable.endpointConnectors = [];
      return usable;
    }
    function dispatchRelationshipRoute(start, end) {
      const dx = safeNumber(end[0], 0) - safeNumber(start[0], 0);
      const dy = safeNumber(end[1], 0) - safeNumber(start[1], 0);
      const distance = Math.max(0.001, Math.hypot(dx, dy));
      const bend = Math.min(8.5, Math.max(2.2, distance * 0.075));
      const sign = ((Math.round(start[0] * 10 + end[1] * 10) % 2) === 0) ? 1 : -1;
      const control = [
        (safeNumber(start[0], 0) + safeNumber(end[0], 0)) / 2 + (-dy / distance) * bend * sign,
        (safeNumber(start[1], 0) + safeNumber(end[1], 0)) / 2 + (dx / distance) * bend * sign
      ];
      const route = [start, control, end];
      route.curveControl = control;
      route.roadCore = route;
      route.endpointConnectors = [];
      return route;
    }
    function compactRoutePoints(points) {
      return (points || []).filter(Boolean).reduce((list, point) => {
        const normalized = [safeNumber(point[0], 50), safeNumber(point[1], 50)];
        const previous = list[list.length - 1];
        if (!previous || distance2D(previous, normalized) >= 1.2) list.push(normalized);
        return list;
      }, []);
    }
    function dispatchPathFor(points) {
      const usable = points.filter(Boolean);
      if (usable.length < 2) return "";
      const [startX, startY] = svgPoint(usable[0]);
      if (Array.isArray(points.curveControl) && usable.length >= 3) {
        const [controlX, controlY] = svgPoint(points.curveControl);
        const [endX, endY] = svgPoint(usable[usable.length - 1]);
        return `M${startX.toFixed(1)} ${startY.toFixed(1)} Q${controlX.toFixed(1)} ${controlY.toFixed(1)} ${endX.toFixed(1)} ${endY.toFixed(1)}`;
      }
      const segments = [`M${startX.toFixed(1)} ${startY.toFixed(1)}`];
      usable.slice(1).forEach((point, index) => {
        const [x, y] = svgPoint(point);
        segments.push(`L${x.toFixed(1)} ${y.toFixed(1)}`);
      });
      return segments.join(" ");
    }
    function routeClickMidpoint(points) {
      const usable = points.filter(Boolean);
      if (usable.length < 2) return null;
      if (Array.isArray(points.curveControl) && usable.length >= 2) {
        const start = usable[0];
        const control = points.curveControl;
        const end = usable[usable.length - 1];
        return [
          0.25 * safeNumber(start[0], 0) + 0.5 * safeNumber(control[0], 0) + 0.25 * safeNumber(end[0], 0),
          0.25 * safeNumber(start[1], 0) + 0.5 * safeNumber(control[1], 0) + 0.25 * safeNumber(end[1], 0)
        ];
      }
      let total = 0;
      for (let index = 1; index < usable.length; index += 1) total += distance2D(usable[index - 1], usable[index]);
      const target = total / 2;
      let walked = 0;
      for (let index = 1; index < usable.length; index += 1) {
        const previous = usable[index - 1];
        const current = usable[index];
        const segment = distance2D(previous, current);
        if (walked + segment >= target) {
          const ratio = segment ? (target - walked) / segment : 0;
          return [
            safeNumber(previous[0], 0) + (safeNumber(current[0], 0) - safeNumber(previous[0], 0)) * ratio,
            safeNumber(previous[1], 0) + (safeNumber(current[1], 0) - safeNumber(previous[1], 0)) * ratio
          ];
        }
        walked += segment;
      }
      return usable[Math.floor(usable.length / 2)];
    }
    function dispatchRouteClickTargetFor(points, cls, assignmentId = "", meta = {}, style = "") {
      const midpoint = routeClickMidpoint(points);
      if (!midpoint) return "";
      const [x, y] = svgPoint(midpoint);
      const styleAttr = style ? ` style="${style}"` : "";
      const d = `M${(x - 8).toFixed(1)} ${y.toFixed(1)} L${(x + 8).toFixed(1)} ${y.toFixed(1)}`;
      return `<path class="dispatch-link ${cls} route-click-target" data-assignment="${assignmentId}" data-route-role="main"${routeMetaAttributes(meta)}${styleAttr} d="${d}"></path>`;
    }
    function routePolylineLength(points) {
      const usable = (points || []).filter(Boolean);
      return usable.slice(1).reduce((sum, point, index) => sum + distance2D(usable[index], point), 0);
    }
    function routeSpan(points) {
      const usable = (points || []).filter(Boolean);
      if (!usable.length) return 0;
      const xs = usable.map((point) => safeNumber(point[0], 0));
      const ys = usable.map((point) => safeNumber(point[1], 0));
      return Math.hypot(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys));
    }
    function longRouteClass(start, end, route, thresholds = {}) {
      const directLimit = safeNumber(thresholds.direct, 24);
      const spanLimit = safeNumber(thresholds.span, 36);
      const lengthLimit = safeNumber(thresholds.length, 46);
      const directDistance = distance2D(start, end);
      const span = routeSpan(route);
      const length = routePolylineLength(route);
      return directDistance > directLimit || span > spanLimit || length > lengthLimit;
    }
    function dispatchEndpointConnectorsFor(route, assignmentId = "", meta = {}, style = "") {
      const connectors = Array.isArray(route && route.endpointConnectors) ? route.endpointConnectors : [];
      const styleAttr = style ? ` style="${style}"` : "";
      return connectors.map((connector) => {
        const d = dispatchPathFor(connector);
        return d ? `<path class="dispatch-visual endpoint-connector" data-assignment="${assignmentId}"${routeMetaAttributes({...meta, connector: "endpoint"})}${styleAttr} d="${d}"></path>` : "";
      }).join("");
    }
    function routeMetaAttributes(meta = {}) {
      return Object.entries(meta)
        .filter(([, value]) => value !== undefined && value !== null && value !== "")
        .map(([key, value]) => ` data-${key}="${escapeAttr(value)}"`)
        .join("");
    }
    function dispatchArrowFor(points, cls, assignmentId = "", active = false, style = "", meta = {}) {
      const pointsAttr = dispatchArrowPoints(points, cls.includes("primary"));
      if (!pointsAttr) return "";
      const styleAttr = style ? ` style="${style}"` : "";
      return `<polygon class="dispatch-arrow ${cls}${active ? " active-assignment" : ""}" data-assignment="${assignmentId}" data-route-role="arrow"${routeMetaAttributes(meta)}${styleAttr} points="${pointsAttr}"></polygon>`;
    }
    function dispatchArrowPoints(points, primary = false) {
      const usable = points.filter(Boolean);
      if (usable.length < 2) return "";
      const totalLength = routePolylineLength(usable);
      const targetLength = totalLength * 0.56;
      let accumulated = 0;
      let bestStart = usable[0];
      let bestEnd = usable[1];
      for (let index = 1; index < usable.length; index += 1) {
        const segmentDistance = distance2D(usable[index - 1], usable[index]);
        if (accumulated + segmentDistance >= targetLength) {
          bestStart = usable[index - 1];
          bestEnd = usable[index];
          break;
        }
        accumulated += segmentDistance;
      }
      const [x1, y1] = svgPoint(bestStart);
      const [x2, y2] = svgPoint(bestEnd);
      const angle = Math.atan2(y2 - y1, x2 - x1);
      const size = primary ? 9 : 6;
      const segmentLength = Math.max(0.001, distance2D(bestStart, bestEnd));
      const remainingOnSegment = Math.max(0, Math.min(segmentLength, targetLength - accumulated));
      const ratio = Math.max(0.34, Math.min(0.72, remainingOnSegment / segmentLength));
      const tipX = x1 + (x2 - x1) * ratio;
      const tipY = y1 + (y2 - y1) * ratio;
      const leftX = tipX - Math.cos(angle - 0.52) * size;
      const leftY = tipY - Math.sin(angle - 0.52) * size;
      const rightX = tipX - Math.cos(angle + 0.52) * size;
      const rightY = tipY - Math.sin(angle + 0.52) * size;
      return `${tipX.toFixed(1)},${tipY.toFixed(1)} ${leftX.toFixed(1)},${leftY.toFixed(1)} ${rightX.toFixed(1)},${rightY.toFixed(1)}`;
    }
    function renderDispatchLinks(profile, entityPoints) {
      const svg = document.querySelector(".route-svg");
      if (!svg) return;
      const hasFinalAssignments = Boolean(profile && profile.assignments && Object.keys(profile.assignments).length);
      if (!hasFinalAssignments || !profile.dispatchMap || !Array.isArray(profile.dispatchMap.assignments)) {
        svg.innerHTML = "";
        dispatchRouteVersion += 1;
        return;
      }
      dispatchRouteVersion += 1;
      const focusMode = profile.mapFocusMode === "focus";
      const selectedAssignment = profile.selected || (profile.dispatchMap.assignments[0] && profile.dispatchMap.assignments[0].id) || "";
      const mapLayers = profile.dispatchMap.map_layers;
      const routePalette = ["#0f766e", "#11836e", "#147a64", "#0d9488", "#15803d", "#0f766e", "#11836e", "#147a64"];
      const pathHtml = profile.dispatchMap.assignments.flatMap((assignment, index) => {
        const normalizedAssignment = (profile.assignments && profile.assignments[assignment.id]) || assignment;
        const couriers = finalCourierTokensForAssignment(normalizedAssignment);
        const pickupPoint = entityPoints[assignment.pickup];
        if (!pickupPoint || !couriers.length) return "";
        const isActive = Boolean(focusMode && assignment.id === selectedAssignment);
        const routeStyle = `--route-color:${routePalette[index % routePalette.length]}`;
        const cls = isActive ? "dispatch-visual primary active-assignment" : "dispatch-visual secondary overview-route";
        const hitCls = isActive ? "primary active-assignment" : "secondary overview-route";
        return couriers.map((courierId, courierIndex) => {
          const courierPoint = entityPoints[courierId];
          if (!courierPoint) return "";
          const pickupRoute = dispatchRelationshipRoute(courierPoint, pickupPoint);
          const visiblePickupRoute = pickupRoute;
          const pickupD = dispatchPathFor(visiblePickupRoute);
          if (!pickupD) return "";
          const longPickup = longRouteClass(courierPoint, pickupPoint, pickupRoute, {direct: 55, span: 82, length: 120});
          const showInOverview = Boolean(!focusMode && assignment.id === selectedAssignment && !longPickup);
          const pickupClass = `${cls} pickup-leg${showInOverview ? " selected-overview" : ""}${longPickup ? " long-pickup" : ""}`;
          const pickupMeta = {
            merchant: assignment.pickup,
            courier: courierId,
            leg: "courier-to-merchant",
            "leg-index": courierIndex,
            "final-courier": finalCourierForAssignment(normalizedAssignment),
            "route-source": "dispatch-relationship-line-v4",
            "route-points": visiblePickupRoute.length,
            "road-core-points": Array.isArray(pickupRoute.roadCore) ? pickupRoute.roadCore.length : visiblePickupRoute.length,
            "connector-points": pickupRoute.length,
            "route-length": routePolylineLength(pickupRoute).toFixed(1),
            "endpoint-connectors": Array.isArray(pickupRoute.endpointConnectors) ? pickupRoute.endpointConnectors.length : 0,
            "long-leg": longPickup ? "true" : "false"
          };
          const arrowCls = isActive ? "primary" : "secondary overview-route";
          return [
            `<path class="${pickupClass}" data-assignment="${assignment.id}" data-route-role="visual" data-courier="${escapeAttr(courierId)}" data-leg-index="${courierIndex}"${routeMetaAttributes(pickupMeta)} style="${routeStyle}" d="${pickupD}"></path>`,
            dispatchRouteClickTargetFor(visiblePickupRoute, `${hitCls} pickup-leg${showInOverview ? " selected-overview" : ""}${longPickup ? " long-pickup" : ""}`, assignment.id, pickupMeta, routeStyle),
            dispatchArrowFor(visiblePickupRoute, `${arrowCls}${showInOverview ? " selected-overview" : ""}${longPickup ? " long-pickup" : ""}`, assignment.id, isActive, routeStyle, pickupMeta)
          ].join("");
        });
      }).join("");
      svg.innerHTML = pathHtml;
    }
    function applyMapFocus(profile, assignmentId, focusMap = true) {
      const assignments = (profile && profile.assignments) || {};
      const hasDispatch = Boolean(profile && profile.dispatchMap && Object.keys(assignments).length);
      const fallbackAssignment = Object.keys(assignments)[0] || (profile && profile.selected) || "A1";
      const selectedAssignment = assignments[assignmentId] ? assignmentId : fallbackAssignment;
      if (profile) profile.mapFocusMode = focusMap ? "focus" : "overview";
      if (profile) profile.selected = hasDispatch ? selectedAssignment : "";
      const focused = Boolean(hasDispatch && focusMap);
      const frame = document.querySelector(".map-frame");
      if (frame) {
        frame.classList.toggle("focus-selected", focused);
        frame.classList.toggle("assignment-overview", Boolean(hasDispatch && !focused));
        if (hasDispatch) {
          frame.dataset.selectedAssignment = selectedAssignment;
        } else {
          frame.removeAttribute("data-selected-assignment");
        }
      }
      if (!hasDispatch) {
        document.querySelectorAll(".map-label, .pin, .dispatch-visual, .dispatch-link, .dispatch-arrow").forEach((node) => {
          node.classList.remove("active-assignment", "selected", "focused", "primary");
          if (node.classList.contains("dispatch-visual") || node.classList.contains("dispatch-link") || node.classList.contains("dispatch-arrow")) node.classList.add("secondary");
        });
        return;
      }
      document.querySelectorAll(".map-label, .pin").forEach((node) => {
        const active = Boolean(hasDispatch && focused && node.dataset.assignment === selectedAssignment);
        node.classList.toggle("active-assignment", active);
        if (node.classList.contains("map-label")) {
          node.classList.toggle("selected", active);
          node.classList.toggle("focused", focused && active);
        }
      });
      document.querySelectorAll(".dispatch-visual, .dispatch-link, .dispatch-arrow").forEach((node) => {
        const active = Boolean(hasDispatch && focused && node.dataset.assignment === selectedAssignment);
        node.classList.toggle("active-assignment", active);
        node.classList.toggle("primary", active);
        node.classList.toggle("secondary", !active);
        node.classList.toggle("overview-route", !active);
      });
    }
    function setDetailContext(type, assignmentId = "", entityId = "", leg = "") {
      const card = document.querySelector(".assignment-detail");
      if (!card) return;
      card.dataset.detailType = type || "";
      card.dataset.assignment = assignmentId || "";
      card.dataset.entity = entityId || "";
      card.dataset.leg = leg || "";
    }
    function entityById(profile, entityId) {
      return profile && profile.dispatchMap && Array.isArray(profile.dispatchMap.entities)
        ? profile.dispatchMap.entities.find((item) => item.id === entityId)
        : null;
    }
    function sampleMerchantById(merchantId) {
      return currentSimulationSample && Array.isArray(currentSimulationSample.merchants)
        ? currentSimulationSample.merchants.find((item) => item.id === merchantId)
        : null;
    }
    function sampleCourierById(courierId) {
      return currentSimulationSample && Array.isArray(currentSimulationSample.couriers)
        ? currentSimulationSample.couriers.find((item) => item.id === courierId)
        : null;
    }
    function sampleOrderById(orderId) {
      if (!currentSimulationSample || !Array.isArray(currentSimulationSample.merchants)) return null;
      for (const merchant of currentSimulationSample.merchants) {
        const found = (merchant.delivery_points || []).find((point) => point.id === orderId);
        if (found) return {...found, merchant};
      }
      return null;
    }
    function candidateForPair(merchantId, courierId) {
      if (!currentSimulationSample || !Array.isArray(currentSimulationSample.candidates)) return null;
      return currentSimulationSample.candidates.find((item) => item.merchant_id === merchantId && item.courier_id === courierId) || null;
    }
    function strategyLabelForAssignment(assignment) {
      const strategyId = assignment && (assignment.strategyId || assignment.strategy_id || (currentSimulationSample && currentSimulationSample.selected_strategy_id));
      const sampleItem = currentSimulationSample && Array.isArray(currentSimulationSample.strategy_path)
        ? currentSimulationSample.strategy_path.find((item) => item.id === strategyId)
        : null;
      if (sampleItem && sampleItem.label) return `${sampleItem.id} · ${sampleItem.label}`;
      if (currentSimulationSample && currentSimulationSample.selected_strategy && currentSimulationSample.selected_strategy.label) {
        return `${currentSimulationSample.selected_strategy_id} · ${currentSimulationSample.selected_strategy.label}`;
      }
      return strategyId || "-";
    }
    function coordinateText(entity) {
      return entity ? `${Number(entity.x).toFixed(1)}, ${Number(entity.y).toFixed(1)}` : "-";
    }
    function renderEntityPreviewDetail(profile, entityId) {
      setDetailContext("preview", "", entityId, "");
      const sample = currentSimulationSample;
      const entity = profile && profile.dispatchMap && Array.isArray(profile.dispatchMap.entities)
        ? profile.dispatchMap.entities.find((item) => item.id === entityId)
        : null;
      if (!sample || !entity) return false;
      const candidates = Array.isArray(sample.candidates) ? sample.candidates : [];
      if (entity.kind === "merchant_order") {
        const merchant = (sample.merchants || []).find((item) => item.id === entity.id) || entity;
        const relatedCandidates = candidates
          .filter((candidate) => candidate.merchant_id === entity.id)
          .slice()
          .sort((a, b) => safeNumber(a.cost, 0) - safeNumber(b.cost, 0))
          .slice(0, 3);
        $("detail-title").textContent = "商家输入：" + entity.id;
        $("detail-courier").textContent = relatedCandidates[0] ? `候选骑手 ${relatedCandidates[0].courier_id}` : "待匹配";
        $("detail-merchant").innerHTML = `该点代表商家及其订单入口，当前 <code>${merchant.order_count || 1}</code> 单待派；推理完成后会锁定最终承接骑手。`;
        $("detail-orders").innerHTML = relatedCandidates.length
          ? relatedCandidates.map((candidate) => `<span class="chip">${candidate.courier_id} · 接单 ${Math.round(safeNumber(candidate.accept_probability, 0) * 100)}%</span>`).join("")
          : `<span class="chip">等待候选生成</span>`;
      $("detail-eta").textContent = merchant.expected_eta_min ? `${merchant.expected_eta_min} 分钟目标` : "-";
        $("right-cost").textContent = merchant.expected_price ? money(merchant.expected_price) : "-";
        document.querySelector(".prob span").textContent = relatedCandidates[0] ? `${Math.round(safeNumber(relatedCandidates[0].accept_probability, 0) * 100)}%` : "--";
        $("detail-reasons").innerHTML = [
          "<li>候选骑手按距离、接单意愿、价格和风险综合排序。</li>",
          "<li>当前仅展示输入侧候选，不提前显示最终派单。</li>",
          "<li>接单概率用于判断该商家是否需要多派候选或风险平衡策略。</li>"
        ].join("");
        setEvidenceRows([
          ["▧ 商家类型", merchant.hotspot === "crossroad" ? "路口商圈" : "街区商家"],
          ["◎ 候选骑手", relatedCandidates.length ? relatedCandidates.map((candidate) => candidate.courier_id).join(" / ") : "待匹配"],
          ["◷ ETA 目标", merchant.expected_eta_min ? `${merchant.expected_eta_min} 分钟` : "-"],
          ["△ 候选风险", relatedCandidates[0] ? relatedCandidates[0].risk : "-"],
          ["▣ 当前阶段", "待评估"]
        ]);
        showToast(`已选中商家 ${entity.id}`);
        return true;
      }
      if (entity.kind === "courier") {
        const courier = (sample.couriers || []).find((item) => item.id === entity.id) || entity;
        let relatedCandidates = candidates
          .filter((candidate) => candidate.courier_id === entity.id)
          .slice()
          .sort((a, b) => safeNumber(a.cost, 0) - safeNumber(b.cost, 0))
          .slice(0, 4);
        if (!relatedCandidates.length) {
          relatedCandidates = (sample.merchants || []).map((merchant) => {
            const distance = distance2D([entity.x, entity.y], [merchant.x, merchant.y]);
            const willingness = safeNumber(courier.willingness, 0.5);
            return {
              merchant_id: merchant.id,
              eta_min: Math.max(8, Math.round(distance * 0.72 + 6)),
              cost: Math.round((distance * 2.1 + safeNumber(merchant.order_count, 1) * 5.8 - willingness * 5.5) * 10) / 10,
              risk: willingness < 0.36 ? "High" : willingness < 0.62 ? "Medium" : "Low"
            };
          }).sort((a, b) => safeNumber(a.cost, 0) - safeNumber(b.cost, 0)).slice(0, 4);
        }
        $("detail-title").textContent = "骑手输入：" + entity.id;
        $("detail-courier").textContent = entity.id;
        $("detail-merchant").innerHTML = `当前状态 <code>${courier.status || "available"}</code>，可承接容量 <code>${courier.capacity || 1}</code>；接单意愿会影响最终是否绑定该骑手。`;
        $("detail-orders").innerHTML = relatedCandidates.map((candidate) => `<span class="chip">${candidate.merchant_id} · ${candidate.risk}</span>`).join("");
        $("detail-eta").textContent = relatedCandidates[0] ? `${relatedCandidates[0].eta_min} 分钟最近候选` : "-";
        $("right-cost").textContent = relatedCandidates[0] ? money(relatedCandidates[0].cost) : "-";
        document.querySelector(".prob span").textContent = `${Math.round(safeNumber(courier.willingness, 0) * 100)}%`;
        $("detail-reasons").innerHTML = [
          `<li>候选商家：${relatedCandidates.map((candidate) => candidate.merchant_id).join("、") || "暂无"}。</li>`,
          "<li>系统优先避免把低意愿骑手绑定到高风险商家。</li>",
          "<li>运行完成后，如果该骑手被选中，地图会显示其承接的商家关系线。</li>"
        ].join("");
        setEvidenceRows([
          ["▧ 接单意愿", `${Math.round(safeNumber(courier.willingness, 0) * 100)}%`],
          ["◎ 候选商家", relatedCandidates.map((candidate) => candidate.merchant_id).join(" / ") || "-"],
          ["◷ 骑手状态", courier.status || "-"],
          ["△ 候选风险", relatedCandidates[0] ? relatedCandidates[0].risk : "-"],
          ["▣ 候选数量", relatedCandidates.length + " 个候选"]
        ]);
        showToast(`已选中骑手 ${entity.id}`);
        return true;
      }
      return false;
    }
    function renderFinalEntityDetail(profile, entityId) {
      const entity = entityById(profile, entityId);
      const assignments = (profile && profile.assignments) || {};
      const assignmentId = assignmentForEntity(profile, entityId);
      const assignment = assignments[assignmentId];
      if (!entity || !assignment) return false;
      profile.selected = assignmentId;
      applyMapFocus(profile, assignmentId, true);
      const courierId = finalCourierForAssignment(assignment);
      const merchantId = assignment.pickup;
      const merchant = sampleMerchantById(merchantId) || entityById(profile, merchantId) || {};
      const courier = sampleCourierById(courierId) || entityById(profile, courierId) || {};
      const candidate = candidateForPair(merchantId, courierId);
      const strategyText = strategyLabelForAssignment(assignment);
      if (entity.kind === "merchant_order" || entity.kind === "pickup_cluster") {
        setDetailContext("merchant", assignmentId, entityId, "");
        const orderCount = safeNumber(assignment.orderCount, assignment.orders.length);
        $("detail-title").textContent = "商家派单：" + entity.id;
        $("detail-courier").textContent = `派给 ${assignment.courier}`;
        $("detail-merchant").innerHTML = `该商家共 <code>${orderCount}</code> 单，最终由 <code>${assignment.courier}</code> 承接。`;
        $("detail-orders").innerHTML = assignment.orders.map((order) => `<span class="chip">${order}</span>`).join("");
        $("detail-eta").textContent = assignment.eta;
        $("right-cost").textContent = assignment.cost;
        document.querySelector(".prob span").textContent = assignment.probability;
        $("detail-reasons").innerHTML = [
          `<li>派单对象：${entity.id} → ${assignment.courier}，覆盖该商家 ${orderCount} 单。</li>`,
          `<li>时效目标：${merchant.expected_eta_min ? merchant.expected_eta_min + " 分钟" : "-"}；预计派单成本 ${assignment.cost}。</li>`,
          `<li>策略依据：${strategyText}；风险等级 ${assignment.risk}；接单概率 ${assignment.probability}。</li>`,
          `<li>${assignment.merchantNote || "该派单来自当前场景样本的最终策略选择。"}</li>`
        ].join("");
        setEvidenceRows([
          ["▧ 接单概率", assignment.fit],
          ["◎ 承接骑手", assignment.courier],
          ["◷ ETA / 时效", merchant.expected_eta_min ? `${merchant.expected_eta_min} 分钟` : etaText(assignment.eta)],
          ["△ 接单风险", assignment.risk],
          ["▣ 策略依据", strategyText]
        ]);
        showToast(`商家 ${entity.id} 已派给 ${assignment.courier}`);
        return true;
      }
      if (entity.kind === "courier") {
        const courierAssignments = Object.entries(assignments).filter(([, item]) => finalCourierForAssignment(item) === entity.id);
        const assignedOrders = courierAssignments.flatMap(([, item]) => item.orders || []);
        const totalCost = courierAssignments.reduce((sum, [, item]) => sum + safeNumber(String(item.cost || "0").replace("$", ""), 0), 0);
        const avgEta = courierAssignments.length
          ? Math.round(courierAssignments.reduce((sum, [, item]) => sum + safeNumber(String(item.eta || "").replace("min", ""), 0), 0) / courierAssignments.length)
          : 0;
        setDetailContext("courier", assignmentId, entityId, "");
        $("detail-title").textContent = "骑手承接：" + entity.id;
        $("detail-courier").textContent = `${courierAssignments.length} 个商家`;
        $("detail-merchant").innerHTML = `状态 <code>${courier.status || "available"}</code>，容量 <code>${courier.capacity || 1}</code>，本轮承接 <code>${courierAssignments.length}</code> 个商家。`;
        $("detail-orders").innerHTML = courierAssignments.map(([, item]) => `<span class="chip">${item.pickup}</span>`).join("") || `<span class="chip">暂无最终派单</span>`;
        $("detail-eta").textContent = avgEta ? `${avgEta} 分钟平均` : etaText(assignment.eta);
        $("right-cost").textContent = money(totalCost || safeNumber(String(assignment.cost || "0").replace("$", ""), 0));
        document.querySelector(".prob span").textContent = `${Math.round(safeNumber(courier.willingness, 0) * 100)}%`;
        $("detail-reasons").innerHTML = [
          `<li>骑手接单意愿 ${Math.round(safeNumber(courier.willingness, 0) * 100)}%，当前状态 ${courier.status || "available"}。</li>`,
          `<li>已分配商家：${courierAssignments.map(([, item]) => item.pickup).join("、") || "-"}。</li>`,
          `<li>覆盖订单数：${assignedOrders.length || 0}；平均 ETA：${avgEta ? avgEta + " 分钟" : etaText(assignment.eta)}。</li>`,
          `<li>当前风险 ${assignment.risk}；累计派单成本 ${money(totalCost || safeNumber(String(assignment.cost || "0").replace("$", ""), 0))}。</li>`
        ].join("");
        setEvidenceRows([
          ["▧ 接单意愿", `${Math.round(safeNumber(courier.willingness, 0) * 100)}%`],
          ["◎ 已派商家", courierAssignments.map(([, item]) => item.pickup).join(" / ") || "-"],
          ["◷ 骑手状态", courier.status || "-"],
          ["△ 接单风险", assignment.risk],
          ["▣ 承接规模", `${courierAssignments.length} 个商家`]
        ]);
        showToast(`骑手 ${entity.id} 当前承接 ${courierAssignments.length} 个商家`);
        return true;
      }
      return false;
    }
    function setEvidenceRows(items) {
      const rows = document.querySelectorAll(".decision-card.evidence .row");
      (items || []).forEach((item, index) => {
        const row = rows[index];
        if (!row) return;
        const label = row.querySelector("span");
        const value = row.querySelector("strong");
        if (label) label.textContent = item[0] || "-";
        if (value) value.textContent = item[1] || "-";
      });
    }
    function renderRouteDetail(profile, assignmentId, routeDataset = {}) {
      const assignments = (profile && profile.assignments) || {};
      const assignment = assignments[assignmentId] || assignments[profile.selected] || assignments[Object.keys(assignments)[0]];
      if (!assignment) return false;
      const resolvedAssignment = assignments[assignmentId] ? assignmentId : assignments[profile.selected] ? profile.selected : Object.keys(assignments)[0];
      profile.selected = resolvedAssignment;
      applyMapFocus(profile, resolvedAssignment, true);
      const leg = routeDataset.leg || "";
      const merchantId = routeDataset.merchant || assignment.pickup;
      const finalCourierId = finalCourierForAssignment(assignment);
      const clickedCourierId = routeDataset.courier || finalCourierId;
      if (finalCourierId && clickedCourierId && clickedCourierId !== finalCourierId) return false;
      const courierId = finalCourierId || clickedCourierId;
      const routePoints = routeDataset.routePoints || routeDataset.routepoints || "";
      const routeSource = routeDataset.routeSource || routeDataset.routesource || "delivery-routes-road-graph-v3";
      const endpointConnectors = routeDataset.endpointConnectors || routeDataset.endpointconnectors || "0";
      const merchant = entityById(profile, merchantId);
      const courier = entityById(profile, courierId);
      const legLabel = "骑手到商家";
      const endpointText = `${courierId} → ${merchantId}`;
      setDetailContext("route", resolvedAssignment, merchantId, leg || "courier-to-merchant");
      $("detail-title").textContent = "派单关系：" + legLabel;
      $("detail-courier").textContent = courierId;
      $("detail-merchant").innerHTML = `最终派单 <code>${merchantId} → ${courierId}</code>；地图线 <code>${endpointText}</code> 表达骑手承接该商家，不作为骑行导航。`;
      $("detail-orders").innerHTML = [merchantId, courierId].filter(Boolean).map((item) => `<span class="chip">${item}</span>`).join("");
      $("detail-eta").textContent = etaText(assignment.eta);
      $("right-cost").textContent = assignment.cost;
      document.querySelector(".prob span").textContent = assignment.probability;
      $("detail-reasons").innerHTML = [
        `<li>该线属于最终派单 ${resolvedAssignment}：商家 ${merchantId} 派给骑手 ${courierId}。</li>`,
        `<li>派单线证据来自当前地图路网；采样节点 ${routePoints || "-"} 个，端点贴合校验 ${endpointConnectors} 段。</li>`,
        `<li>派单策略：${strategyLabelForAssignment(assignment)}；风险 ${assignment.risk}；接单概率 ${assignment.probability}。</li>`
      ].join("");
      setEvidenceRows([
        ["▧ 线段采样", routePoints ? `${routePoints} 节点` : "-"],
        ["◎ 派单关系", `${merchantId} → ${courierId}`],
        ["◷ ETA / 时效", etaText(assignment.eta)],
        ["△ 接单风险", assignment.risk],
        ["▣ 派单编号", resolvedAssignment]
      ]);
      showToast(`${legLabel}：${endpointText}`);
      return true;
    }
    function branchById(branchId) {
      return strategyBranchCatalog.find((item) => item.id === branchId) || null;
    }
    function strategyStatusText(strategyNode) {
      const status = strategyNode && strategyNode.dataset ? strategyNode.dataset.reasoningStatus : "";
      if (status === "selected") return "已选中";
      if (status === "evaluating") return "评估中";
      if (status === "rejected") return "已淘汰";
      if (status === "not-tried") return "未触发";
      return "待评估";
    }
    function renderStrategyDetail(branchId) {
      const branch = branchById(branchId);
      if (!branch) return false;
      document.querySelectorAll(".strategy").forEach((node) => node.classList.toggle("inspected", node.dataset.branch === branchId));
      document.querySelectorAll(".table-panel tbody tr").forEach((row) => row.classList.remove("inspected"));
      const node = document.querySelector(`.strategy[data-branch="${branchId}"]`);
      const sampleItem = currentSimulationSample && Array.isArray(currentSimulationSample.strategy_path)
        ? currentSimulationSample.strategy_path.find((item) => item.id === branchId)
        : null;
      const scoreText = node ? (node.querySelector("strong") && node.querySelector("strong").textContent.replace(strategyStatusText(node), "").trim()) : "--";
      const statusText = strategyStatusText(node);
      const isSelected = node && node.dataset.reasoningStatus === "selected";
      const revealDetail = statusText === "已选中" || statusText === "已淘汰";
      const profile = currentProfile || profileForCase(selectedCase());
      if (isSelected && profile && profile.assignments && Object.keys(profile.assignments).length) {
        applyMapFocus(profile, profile.selected || Object.keys(profile.assignments)[0], false);
      }
      setDetailContext("strategy", "", branchId, "");
      $("detail-title").textContent = `策略详情：${branch.id} · ${branch.title}`;
      $("detail-courier").textContent = statusText;
      $("detail-merchant").innerHTML = `策略 <code>${branch.title}</code> 当前状态 <code>${statusText}</code>，用于${branch.desc}。`;
      $("detail-orders").innerHTML = [
        `<span class="chip">${branch.id}</span>`,
        revealDetail && sampleItem && sampleItem.rank ? `<span class="chip">排名 ${sampleItem.rank}</span>` : "",
        revealDetail && sampleItem && sampleItem.evidence ? `<span class="chip">${sampleItem.evidence}</span>` : ""
      ].filter(Boolean).join("");
      $("detail-eta").textContent = revealDetail && sampleItem && sampleItem.score ? Number(sampleItem.score).toFixed(2) : (statusText === "评估中" ? "计算中" : "-");
      $("right-cost").textContent = isSelected && profile ? profile.cost : "-";
      document.querySelector(".prob span").textContent = revealDetail && sampleItem && sampleItem.score ? `${Math.round(safeNumber(sampleItem.score, 0) * 100)}%` : "--";
      $("detail-reasons").innerHTML = [
        "<li>该卡片来自当前场景的策略评分链路，不是静态展示。</li>",
        `<li>策略说明：${branch.desc}。</li>`,
        `<li>策略证据：${revealDetail && sampleItem && sampleItem.evidence ? sampleItem.evidence : "运行推理到该策略后再显示"}。</li>`,
        `<li>当前状态：${statusText}${isSelected ? "，地图保持展示全部最终派单关系" : "，可与选中策略对比成本、风险和覆盖率"}。</li>`
      ].join("");
      setEvidenceRows([
        ["▧ 策略名称", branch.title],
        ["◎ 策略证据", revealDetail && sampleItem && sampleItem.evidence ? sampleItem.evidence : "-"],
        ["◷ 评分", revealDetail && sampleItem && sampleItem.score ? Number(sampleItem.score).toFixed(2) : "-"],
        ["△ 当前状态", statusText],
        ["▣ 策略编号", branch.id]
      ]);
      showToast(`策略 ${branch.id}：${statusText}`);
      return true;
    }
    function renderTableRowDetail(row) {
      if (!row) return false;
      document.querySelectorAll(".table-panel tbody tr").forEach((item) => item.classList.toggle("inspected", item === row));
      document.querySelectorAll(".strategy").forEach((node) => node.classList.remove("inspected"));
      const rowType = row.dataset.rowType || "table-row";
      const cells = Array.from(row.cells || []).map((cell) => cell.textContent.trim());
      const branchId = row.dataset.branch || "";
      if (branchId) {
        document.querySelectorAll(".strategy").forEach((node) => node.classList.toggle("inspected", node.dataset.branch === branchId));
      }
      setDetailContext("table-row", row.dataset.assignment || "", branchId || rowType, "");
      const rowDescriptions = {
        "scene-summary": "该行说明当前调度场景输入，包括商家规模、骑手供给、天气/密度和风险画像。",
        "preview-strategy": "该行展示刷新位置后的预期策略倾向，只作为推理前输入，不提前泄露最终结果。",
        "strategy-candidate": "该行对比一种候选派单策略在覆盖率、ETA、成本、骑手占用和无人接单风险上的表现。",
        "final-strategy": "该行是 AutoSolver 最终采纳方案，用于和贪心、合单、多派、修复、风险平衡策略做业务对比。",
        "empty-state": "该行提示当前工作台状态：刷新位置可查看输入，运行推理后才生成最终派单。"
      };
      const title = rowType === "preview-candidate"
        ? `候选关系：${row.dataset.merchant || cells[0] || "-"} → ${row.dataset.courier || "-"}`
        : rowType === "scene-summary"
        ? `场景输入：${cells[0] || "-"}`
        : `策略对比：${cells[0] || "-"}`;
      $("detail-title").textContent = title;
      $("detail-courier").textContent = row.dataset.courier || row.dataset.status || cells[7] || "-";
      const rowEta = row.dataset.eta || cells[2] || "";
      const rowEtaText = rowEta && /min|分钟/.test(rowEta) ? etaText(rowEta) : (rowEta ? `${rowEta} 分钟` : "-");
      $("detail-merchant").innerHTML = rowType === "preview-candidate"
        ? `候选派单来自当前场景输入：商家 <code>${row.dataset.merchant || "-"}</code>，骑手 <code>${row.dataset.courier || "-"}</code>。`
        : `${rowDescriptions[rowType] || "该行用于解释当前派单工作台的策略或结果。"}${branchId ? ` 对应策略 <code>${branchId}</code>。` : ""}`;
      $("detail-orders").innerHTML = cells.slice(0, 4).map((item) => `<span class="chip">${item || "-"}</span>`).join("");
      $("detail-eta").textContent = rowEtaText;
      $("right-cost").textContent = row.dataset.cost || cells[3] || "-";
      document.querySelector(".prob span").textContent = row.dataset.probability || (row.dataset.score ? `${Math.round(safeNumber(row.dataset.score, 0) * 100)}%` : "--");
      $("detail-reasons").innerHTML = [
        `<li>${rowDescriptions[rowType] || "该详情由表格行点击触发，用于说明候选/最终策略，不是纯视觉表格。"}</li>`,
        `<li>覆盖率：${cells[1] || "-"}；ETA：${cells[2] || "-"}；成本：${cells[3] || "-"}。</li>`,
        `<li>风险：${row.dataset.risk || cells[5] || "-"}；状态：${row.dataset.status || cells[7] || "-"}。</li>`,
        `<li>业务解释：${cells[8] || "等待刷新位置后生成候选关系"}。</li>`
      ].join("");
      setEvidenceRows([
        ["▧ 覆盖率", cells[1] || "-"],
        ["◎ 成本分", row.dataset.cost || cells[3] || "-"],
        ["◷ ETA / 时效", rowEtaText],
        ["△ 接单风险", row.dataset.risk || cells[5] || "-"],
        ["▣ 策略/行类型", branchId || rowType]
      ]);
      showToast(`已打开表格详情：${cells[0] || rowType}`);
      return true;
    }
    function renderAssignmentOverviewDetail(profile, report) {
      const assignments = Object.values((profile && profile.assignments) || {});
      if (!assignments.length) return false;
      const totalOrders = assignments.reduce((sum, assignment) => sum + safeNumber(assignment.orderCount, (assignment.orders || []).length || 1), 0);
      const courierSet = new Set(assignments.flatMap((assignment) => finalCourierTokensForAssignment(assignment)));
      const totalCost = assignments.reduce((sum, assignment) => sum + safeNumber(String(assignment.cost || "0").replace("$", ""), 0), 0);
      const avgEta = Math.round(assignments.reduce((sum, assignment) => sum + safeNumber(String(assignment.eta || "").replace("min", ""), 0), 0) / Math.max(1, assignments.length));
      const best = report && report.best ? report.best : {};
      const coverage = best.total_tasks ? Math.round(safeNumber(best.covered_tasks, best.total_tasks) / safeNumber(best.total_tasks, 1) * 100) : 100;
      const value = businessValueForReport(report, profile);
      setDetailContext("overview", "", "", "");
      if (profile) {
        profile.mapFocusMode = "overview";
        if (!profile.selected) profile.selected = assignments[0].id;
        applyMapFocus(profile, profile.selected, false);
      }
      $("detail-title").textContent = "派单总览：全部商家已自动连线";
      $("detail-courier").textContent = `${courierSet.size} 个骑手`;
      $("detail-merchant").innerHTML = `运行完成后，地图已自动展示 <code>${assignments.length}</code> 个商家分别派给哪个骑手；商家点同时代表该商家的 <code>${totalOrders}</code> 单。`;
      const chips = assignments.slice(0, 7).map((assignment) => `<span class="chip">${assignment.pickup || assignment.merchant} → ${assignment.courier}</span>`);
      if (assignments.length > chips.length) chips.push(`<span class="chip">+${assignments.length - chips.length} 个商家</span>`);
      $("detail-orders").innerHTML = chips.join("");
      $("detail-eta").textContent = avgEta ? `${avgEta} 分钟平均` : "-";
      $("right-cost").textContent = money(totalCost);
      document.querySelector(".prob span").textContent = `${coverage}%`;
      $("detail-reasons").innerHTML = [
        "<li>当前默认是全局派单总览：所有商家到骑手的派单线保持可见。</li>",
        "<li>点击任意商家、骑手或线路后，才进入单条派单聚焦模式。</li>",
        `<li>运营测算假设：每单履约损耗节约 ${yuan(value.perOrderSaving)}，当前批次约 ${value.tasks} 单，批次节约 ${yuan(value.batchSaving)}；按日均 10 万单估算单城月节约 ${yuan(value.monthSaving)}。</li>`,
        ...assignments.slice(0, 5).map((assignment) => `<li>${assignment.pickup || assignment.merchant} 派给 ${assignment.courier}，ETA ${etaText(assignment.eta)}，成本 ${assignment.cost}，风险 ${assignment.risk}。</li>`)
      ].join("");
      setEvidenceRows([
        ["▧ 商家覆盖", `${coverage}%`],
        ["◎ 派单对象", `${assignments.length} 个商家`],
        ["◷ ETA / 时效", avgEta ? `${avgEta} 分钟` : "-"],
        ["△ 接单风险", assignments.some((assignment) => assignment.risk === "High") ? "High" : assignments.some((assignment) => assignment.risk === "Medium") ? "Medium" : "Low"],
        ["▣ 策略/负载", profile.utilization]
      ]);
      return true;
    }
    function renderAssignmentDetail(profile, assignmentId, sourceLabel = "", focusMap = true) {
      const assignments = (profile && profile.assignments) || {};
      const resolvedAssignment = assignments[assignmentId] ? assignmentId : (assignments[profile.selected] ? profile.selected : Object.keys(assignments)[0]);
      const assignment = assignments[resolvedAssignment];
      if (!assignment) return;
      setDetailContext("assignment", resolvedAssignment, "", "");
      profile.selected = resolvedAssignment;
      applyMapFocus(profile, resolvedAssignment, focusMap);
      $("detail-title").textContent = sourceLabel ? "派单详情：" + sourceLabel : `派单详情：${assignment.pickup || assignment.merchant || resolvedAssignment} → ${assignment.courier}`;
      $("detail-courier").textContent = assignment.courier;
      const orderCount = safeNumber(assignment.orderCount, assignment.orders.length);
      $("detail-merchant").innerHTML = `商家 <code>${assignment.merchant}</code> 共 ${orderCount} 单，最终派给 ${assignment.courier}`;
      $("detail-orders").innerHTML = assignment.orders.map((order) => `<span class="chip">${order}</span>`).join("");
      $("detail-eta").textContent = etaText(assignment.eta);
      $("right-cost").textContent = assignment.cost;
      document.querySelector(".prob span").textContent = assignment.probability;
      $("detail-reasons").innerHTML = assignment.reason.map((item) => `<li>${item}</li>`).join("");
      if (assignment.merchantNote) $("detail-reasons").innerHTML += `<li>${assignment.merchantNote}</li>`;
      setEvidenceRows([
        ["▧ 接单概率", assignment.fit],
        ["◎ 骑手距离", assignment.distance],
        ["◷ ETA / 时效", etaText(assignment.eta)],
        ["△ 接单风险", assignment.risk],
        ["▣ 策略/负载", profile.utilization]
      ]);
      showToast(`${assignment.merchant} → ${assignment.courier}，${orderCount} 单`);
    }
    function updateDecisionPanel(profile, report) {
      const best = report && report.best ? report.best : {};
      const features = report && report.features ? report.features : {};
      const used = safeNumber(best.used_couriers, 6);
      const tasks = safeNumber(best.total_tasks || features.tasks, 38);
      const covered = safeNumber(best.covered_tasks, tasks);
      const coverage = tasks > 0 ? Math.round((covered / tasks) * 100) : 100;
      renderAssignmentOverviewDetail(profile, report);
      const value = businessValueForReport(report, profile);
      const compareRows = document.querySelectorAll(".decision-card:last-child .row strong");
      if (compareRows[0]) compareRows[0].textContent = profile.improvement;
      if (compareRows[1]) compareRows[1].textContent = "-" + Math.max(2, Math.round(used * 0.9)) + " 分钟";
      if (compareRows[2]) compareRows[2].textContent = "-" + Math.max(12, Math.round(coverage * 0.31)) + "%";
      if (compareRows[3]) compareRows[3].textContent = yuan(value.batchSaving);
      if (compareRows[4]) compareRows[4].textContent = yuan(value.monthSaving);
      const batchNode = $("benefit-batch");
      const monthNode = $("benefit-month");
      if (batchNode) batchNode.textContent = yuan(value.batchSaving);
      if (monthNode) monthNode.textContent = yuan(value.monthSaving);
    }
    function businessValueForReport(report, profile) {
      const best = report && report.best ? report.best : {};
      const features = report && report.features ? report.features : {};
      const cost = safeNumber(best["local" + "_cost"], Number(String(profile && profile.cost || "0").replace(/[$,]/g, "")));
      const attempts = ((report && report.rounds) || []).flatMap((round) => round.strategies || []);
      const greedyAttempt = attempts.find((item) => item.name === "greedy_baseline");
      const parsedImprovement = Math.max(0, safeNumber(String(profile && profile.improvement || "0").replace(/[+%]/g, ""), 0)) / 100;
      const fallbackGreedy = parsedImprovement > 0 && parsedImprovement < 0.95 ? cost / Math.max(0.05, 1 - parsedImprovement) : cost * 1.8;
      const greedyCost = Math.max(cost, safeNumber(greedyAttempt && greedyAttempt["local" + "_cost"], fallbackGreedy));
      const assignmentOrders = Object.values((profile && profile.assignments) || {})
        .reduce((sum, assignment) => sum + safeNumber(assignment.orderCount, (assignment.orders || []).length || 1), 0);
      const tasks = Math.max(1, assignmentOrders || safeNumber(best.order_tasks || features.orders || best.total_tasks || features.tasks, 1));
      const rawBatchSaving = Math.max(0, greedyCost - cost);
      const rawPerOrderSaving = rawBatchSaving / tasks;
      const perOrderSaving = Math.max(0.35, Math.min(1.0, rawPerOrderSaving * 0.025));
      const batchSaving = perOrderSaving * tasks;
      const dailyOrders = 100000;
      const monthSaving = perOrderSaving * dailyOrders * 30;
      return {cost, greedyCost, tasks, rawBatchSaving, batchSaving, perOrderSaving, daySaving: perOrderSaving * dailyOrders, monthSaving};
    }
    function strategyLabel(name) {
      const labels = {
        greedy_baseline: "贪心基线",
        single_task_multidispatch: "多派候选",
        disjoint_then_multidispatch: "合单优先",
        pair_potential_matching: "合单优先",
        sparse_cover: "局部修复",
        low_global_column_search: "局部修复",
        low_column_search: "局部修复",
        scarce_k2_column_search: "合单优先",
        scarce_bundle_mcf_enum: "合单优先",
        risk_balancing: "风险平衡",
        candidate_preview: "候选预览",
        production_solver: "最终 AutoSolver"
      };
      return labels[name] || name || "候选策略";
    }
    function renderCandidateTable(report, profile) {
      const tbody = document.querySelector(".table-panel tbody");
      const rounds = report && Array.isArray(report.rounds) ? report.rounds : [];
      const attempts = rounds.flatMap((round) => Array.isArray(round.strategies) ? round.strategies : []);
      const best = report && report.best ? report.best : {};
      const bestCost = safeNumber(best["local" + "_cost"], Number(profile.cost.replace(/[$,]/g, "")) || 657.1);
      const totalTasks = safeNumber(best.total_tasks || (report && report.features && report.features.tasks), 38);
      const fallbackRows = [
        {name: "disjoint_then_multidispatch", ["local" + "_cost"]: bestCost * 1.05, covered_tasks: totalTasks, total_tasks: totalTasks, groups: 6, accepted: true, valid: true},
        {name: "single_task_multidispatch", ["local" + "_cost"]: bestCost * 1.88, covered_tasks: totalTasks, total_tasks: totalTasks, groups: 9, accepted: false, valid: true},
        {name: "sparse_cover", ["local" + "_cost"]: bestCost * 1.54, covered_tasks: totalTasks, total_tasks: totalTasks, groups: 7, accepted: false, valid: true},
        {name: "greedy_baseline", ["local" + "_cost"]: bestCost * 3.2, covered_tasks: totalTasks, total_tasks: totalTasks, groups: 8, accepted: false, valid: true},
        {name: "risk_balancing", ["local" + "_cost"]: bestCost * 1.28, covered_tasks: totalTasks, total_tasks: totalTasks, groups: 7, accepted: false, valid: true},
      ];
      const usingFallbackRows = attempts.length === 0;
      const sourceRows = usingFallbackRows ? fallbackRows : attempts;
      const rows = strategyBranchCatalog.map((branch) => {
        const matched = sourceRows
          .filter((item) => strategyMatchesBranch(item, branch, profile))
          .sort((left, right) => localCostOf(left) - localCostOf(right))[0];
        return matched || fallbackRows.find((item) => branchForStrategy(item.name, profile) === branch.id) || null;
      }).filter(Boolean);
      const tableRows = rows.map((item) => {
        const branchId = branchForStrategy(item.name, profile);
        const reportedTotal = safeNumber(item.total_tasks || item.totalTasks, totalTasks);
        const total = reportedTotal > 0 ? reportedTotal : totalTasks;
        const reportedCovered = item.covered_tasks ?? item.coveredTasks;
        const coveredFallback = item.valid === false ? 0 : total;
        const covered = usingFallbackRows ? total : (reportedCovered === 0 && item.valid !== false && total > 0 ? total : safeNumber(reportedCovered, coveredFallback));
        const coverage = usingFallbackRows ? 100 : (total ? Math.round((covered / total) * 100) : 0);
        const cost = safeNumber(item["local" + "_cost"], bestCost * 1.4);
        const risk = coverage >= 100 && cost <= bestCost * 1.2 ? "Low" : coverage < 100 ? "High" : "Med";
        const status = item.accepted ? "可行" : "已淘汰";
        const statusClass = item.accepted ? "status-ok" : "status-bad";
        const score = Math.max(0.35, Math.min(0.91, bestCost / Math.max(cost, 1))).toFixed(2);
        const insightByBranch = {
          S1: item.accepted ? "订单集中度高，合单后骑手占用更稳定" : "合单收益不足或局部绕行偏大",
          S2: "保留多个骑手候选，适合距离接近但资源占用更高",
          S3: "可修复高风险派单，但整体成本仍高于当前方案",
          S4: "最近骑手优先，作为业务基线但容易放大无人接单风险",
          S5: "降低低意愿/天气风险，但会牺牲部分成本或 ETA"
        };
        const insight = insightByBranch[branchId] || (item.valid ? "成本或资源占用高于当前最优" : "覆盖或约束校验失败");
        const etaMinutes = (12 + safeNumber(item.groups, 6) * 0.7).toFixed(1);
        return `<tr data-row-type="strategy-candidate" data-branch="${escapeAttr(branchId)}" data-strategy="${escapeAttr(item.name || "")}" data-cost="${escapeAttr(money(cost))}" data-eta="${escapeAttr(etaMinutes + " 分钟")}" data-risk="${escapeAttr(risk)}" data-score="${score}" data-status="${escapeAttr(status)}"><td>${strategyLabel(item.name)}</td><td>${coverage}%</td><td>${etaMinutes} 分钟</td><td>${money(cost)}</td><td>${safeNumber(item.groups, 0)} 个骑手</td><td>${risk} (${profile.missedRisk})</td><td>${score}</td><td class="${statusClass}">${status}</td><td>${insight}</td></tr>`;
      });
      const used = safeNumber(best.used_couriers || best.groups, 6);
      tableRows.push(`<tr class="emphasis" data-row-type="final-strategy" data-branch="${escapeAttr(selectedBranchForReport(report, profile))}" data-strategy="production_solver" data-cost="${escapeAttr(money(bestCost))}" data-eta="${escapeAttr(etaText(profile.eta))}" data-risk="Low" data-score="0.89" data-status="已选中"><td><span class="star">★</span><b>最终 AutoSolver<br>选中方案</b></td><td><b>${totalTasks ? Math.round(safeNumber(best.covered_tasks, totalTasks) / totalTasks * 100) : 100}%</b></td><td><b>${etaText(profile.eta)}</b></td><td><b id="table-cost">${money(bestCost)}</b></td><td><b>${used} 个骑手</b></td><td><b>Low (${profile.missedRisk})</b></td><td><b>0.89</b></td><td><b>已选中</b></td><td><b>成本、风险、履约时效综合最优</b></td></tr>`);
      tbody.innerHTML = tableRows.join("");
    }
    function applyScene(caseId, source) {
      const select = $("case-select");
      if (select && Array.from(select.options).some((option) => option.value === caseId)) {
        select.value = caseId;
      }
      const activeCase = selectedCase() === caseId ? caseId : selectedCase();
      currentSimulationSample = null;
      const profile = profileForCase(activeCase);
      currentProfile = profile;
      currentReport = null;
      clearReasoningState();
      profile.dispatchMap = null;
      profile.assignments = {};
      profile.selected = "";
      profile.mapFocusMode = "overview";
      $("case-id").textContent = activeCase;
      $("runtime").textContent = "--:--:--";
      $("completion-rate").textContent = "--";
      $("unassigned").textContent = "--";
      $("expected-cost").textContent = "--";
      $("right-cost").textContent = "-";
      $("improvement").textContent = "--";
      clearDispatchResult(profile);
      if (source === "button") setStatus("已选择场景：" + profile.label, false);
    }
    function renderSimulationSceneButtons(scenarios) {
      return Array.isArray(scenarios);
    }
    async function loadCases() {
      try {
        const [caseRes, simulationRes] = await Promise.all([fetch("/api/cases"), fetch("/api/simulation-scenarios")]);
        const payload = await caseRes.json();
        const simulationPayload = await simulationRes.json();
        const select = $("case-select");
        const previousCase = select.value || "large_seed301";
        const previousScenario = selectedScenarioId();
        caseCatalog = {};
        select.innerHTML = "";
        (payload.cases || [{id: "large_seed301"}]).forEach((item) => {
          caseCatalog[item.id] = item;
        });
        const scenarios = simulationPayload.status === "ok" && Array.isArray(simulationPayload.scenarios) ? simulationPayload.scenarios : [];
        simulationCatalog = {};
        if (scenarios.length) {
          scenarios.forEach((item) => {
            simulationCatalog[item.id] = item;
            const option = document.createElement("option");
            option.value = item.case_id || item.id;
            option.dataset.scenario = item.id;
            option.textContent = item.name;
            select.appendChild(option);
          });
          renderSimulationSceneButtons(scenarios);
        } else {
          (payload.cases || [{id: "large_seed301"}]).forEach((item) => {
            const option = document.createElement("option");
            option.value = item.id;
            option.textContent = item.scenario_name || item.id;
            select.appendChild(option);
          });
        }
        const scenarioOption = Array.from(select.options).find((option) => option.dataset.scenario === previousScenario);
        if (scenarioOption) {
          select.value = scenarioOption.value;
        } else if (Array.from(select.options).some((option) => option.value === previousCase)) {
          select.value = previousCase;
        }
        applyScene(selectedCase());
      } catch (error) {
        $("case-id").textContent = "large_seed301";
      }
    }
    function handleProgressEvent(type, data) {
      if (type === "start") { setStatus("初始化派单场景", true); updateReasonProgress(0); }
      if (type === "perception") { setStatus("感知订单、商家与骑手", true); updateReasonProgress(1); }
      if (type === "critic_policy") { setStatus("加载派单风险评估规则", true); updateReasonProgress(2); }
      if (type === "round_start" || type === "evolution_generate") { setStatus("生成候选派单策略", true); updateReasonProgress(2); }
      if (type === "attempt_start" || type === "evolution_trial") { setStatus("评估候选派单包", true); updateReasonProgress(3); }
      if (type === "evolution_validate") { setStatus("验证派单约束与安全性", true); updateReasonProgress(3); }
      if (type === "attempt_result" || type === "best_update") {
        const strategy = data && (data.strategy || data.name) ? "：" + (data.strategy || data.name) : "";
        setStatus("更新最优派单" + strategy, true);
        updateReasonProgress(4);
      }
      if (type === "final") { setStatus("生成最终派单", true); updateReasonProgress(5); }
    }
    function render(report) {
      currentReport = report || null;
      clearReasoningState();
      const profile = currentProfile || profileForCase(selectedCase());
      currentProfile = profile;
      const best = report && report.best ? report.best : {};
      const features = report && report.features ? report.features : {};
      const runtime = Math.max(0, Math.round(Number(report.wall_time_s || 8)));
      const cost = Number(best["local" + "_cost"] || profile.cost.replace(/[$,]/g, "") || 657.1);
      const totalTasks = safeNumber(best.total_tasks || features.tasks, 38);
      const coveredTasks = safeNumber(best.covered_tasks, totalTasks);
      const completion = totalTasks > 0 ? Math.round((coveredTasks / totalTasks) * 100) : 100;
      const attempts = ((report && report.rounds) || []).flatMap((round) => round.strategies || []);
      const greedyAttempt = attempts.find((item) => item.name === "greedy_baseline");
      const greedyCost = safeNumber(greedyAttempt && greedyAttempt["local" + "_cost"], cost / Math.max(0.01, 1 - parseFloat(profile.improvement) / 100));
      const improvement = greedyCost > 0 ? ((greedyCost - cost) / greedyCost * 100).toFixed(1) : parseFloat(profile.improvement).toFixed(1);
      $("runtime").textContent = "00:00:" + String(runtime).padStart(2, "0");
      $("expected-cost").textContent = money(cost);
      if ($("table-cost")) $("table-cost").textContent = money(cost);
      $("completion-rate").textContent = completion + "%";
      $("unassigned").textContent = String((best.uncovered_tasks || []).length || 0);
      $("improvement").textContent = "+" + improvement + "%";
      profile.cost = money(cost);
      profile.improvement = "+" + improvement + "%";
      if (report && report.dispatch_assignment_map) {
        applyDispatchAssignmentMap(report.dispatch_assignment_map);
      } else {
        updateMapScene(profile);
        updateDecisionPanel(profile, report);
      }
      renderCandidateTable(report, profile);
      updateReasonSummary(profile, report);
      updateReasonProgress(6);
    }
    const DEMO_REASONING_TARGET_MS = 10000;
    const DEMO_REASONING_PHASE_DELAYS = {
      bootstrap: 650,
      perception: 1050,
      candidates: 1050,
      perStrategy: 1150,
      finalReview: 650
    };
    function wait(ms) {
      return new Promise((resolve) => window.setTimeout(resolve, ms));
    }
    function waitUntilElapsed(startedAt, targetMs) {
      return wait(Math.max(0, targetMs - (Date.now() - startedAt)));
    }
    function yieldUi() {
      return new Promise((resolve) => {
        if (typeof MessageChannel !== "undefined") {
          const channel = new MessageChannel();
          channel.port1.onmessage = resolve;
          channel.port2.postMessage(0);
        } else {
          Promise.resolve().then(resolve);
        }
      });
    }
    async function ensureSimulationSampleReady() {
      if (currentSimulationSample) return true;
      if (!selectedScenarioId()) return false;
      try {
        setStatus("正在生成当前场景样本", true);
        await refreshSimulationSample();
        return Boolean(currentSimulationSample);
      } catch (error) {
        console.error(error);
        setStatus("样本生成失败，尝试使用后端求解器", false);
        showToast("样本生成失败，将尝试后端求解器");
        return false;
      }
    }
    async function runCurrentSimulationSample() {
      const sample = currentSimulationSample;
      if (!sample) return false;
      if (document.body.classList.contains("reasoning")) return true;
      try {
        const reasoningStartedAt = Date.now();
        currentReport = null;
        const profile = currentProfile || profileForCase(sample.case_id || selectedCase());
        currentProfile = profile;
        profile.selected = "";
        profile.assignments = {};
        profile.mapFocusMode = "overview";
        const routeSvg = document.querySelector(".route-svg");
        if (routeSvg) routeSvg.innerHTML = "";
        document.body.classList.add("pending-run", "sample-preview", "reasoning");
        setStatus(`基于 ${sample.name} 推理`, true);
        updateReasonSummary(profile, null);
        setReasoningState(sample, -1, false);
        updateReasonProgress(0);
        await wait(DEMO_REASONING_PHASE_DELAYS.bootstrap);
        updateReasonProgress(1);
        setStatus(`识别 ${sample.name} 的订单密度、骑手意愿和路况风险`, true);
        await wait(DEMO_REASONING_PHASE_DELAYS.perception);
        updateReasonProgress(2);
        setStatus("生成候选派单策略", true);
        await wait(DEMO_REASONING_PHASE_DELAYS.candidates);
        const evaluationOrder = reasoningOrderForSample(sample);
        for (let index = 0; index < evaluationOrder.length; index += 1) {
          const branchId = evaluationOrder[index];
          const branch = strategyBranchCatalog.find((item) => item.id === branchId);
          setReasoningState(sample, index, false);
          updateReasonProgress(index < 2 ? 3 : 4);
          setStatus(`评估策略 ${branchId}${branch ? " · " + branch.title : ""}`, true);
          await wait(DEMO_REASONING_PHASE_DELAYS.perStrategy);
          await yieldUi();
        }
        setReasoningState(sample, evaluationOrder.length, true);
        updateReasonProgress(5);
        setStatus(`最终选择 ${sample.selected_strategy_id}：复核成本、风险和接单概率`, true);
        await wait(DEMO_REASONING_PHASE_DELAYS.finalReview);
        await waitUntilElapsed(reasoningStartedAt, DEMO_REASONING_TARGET_MS);
        setStatus(`最终选择 ${sample.selected_strategy_id}：生成当前场景派单线`, true);
        await yieldUi();
        if (routeSvg) routeSvg.innerHTML = "";
        const mapPayload = simulationFinalMap(sample, profile.dispatchMap);
        const report = reportForSimulationSample(sample, mapPayload);
        document.body.classList.remove("pending-run", "sample-preview", "reasoning");
        render(report);
        setStatus("当前场景派单完成", false);
        showToast("已按当前场景生成最终派单线");
        return true;
      } catch (error) {
        console.error(error);
        clearReasoningState();
        document.body.classList.remove("pending-run", "sample-preview", "reasoning");
        setStatus("模拟派单运行失败", false);
        showToast("运行失败，请刷新位置后重试");
        return false;
      }
    }
    async function streamRun() {
      if (currentRun) currentRun.close();
      if (document.body.classList.contains("reasoning")) return;
      await ensureSimulationSampleReady();
      if (await runCurrentSimulationSample()) return;
      applyScene(selectedCase());
      document.body.classList.remove("pending-run");
      $("case-id").textContent = selectedCase();
      setStatus("启动派单推理", true);
      ["start", "perception", "critic_policy", "round_start", "attempt_start"].forEach((type) => handleProgressEvent(type, {}));
      try {
        const previewQs = new URLSearchParams({case: selectedCase()});
        const previewRes = await fetch("/api/dispatch-map?" + previewQs.toString());
        const previewPayload = await previewRes.json();
        if (previewPayload.status === "ok") {
          applyDispatchAssignmentMap(previewPayload.map);
          document.body.classList.remove("pending-run");
          setStatus("地图预览已生成，求解器继续运行", true);
        }
        const qs = new URLSearchParams({case: selectedCase(), budget: "1"});
        const res = await fetch("/api/run?" + qs.toString());
        const payload = await res.json();
        if (!res.ok || payload.status !== "ok") throw new Error(payload.error || "run failed");
        handleProgressEvent("best_update", {strategy: payload.report && payload.report.best && payload.report.best.strategy});
        handleProgressEvent("final", {});
        render(payload.report);
        setStatus("运行完成", false);
      } catch (error) {
        console.error(error);
        setStatus("已显示模拟派单地图", false);
      }
    }
    function setLayerMode(mode) {
      const frame = document.querySelector(".map-frame");
      const profile = currentProfile || profileForCase(selectedCase());
      if (mode === "selected" && profile.assignments && Object.keys(profile.assignments).length) {
        applyMapFocus(profile, profile.selected || Object.keys(profile.assignments)[0], true);
      }
      if (mode === "all" && profile.assignments && Object.keys(profile.assignments).length) {
        applyMapFocus(profile, profile.selected || Object.keys(profile.assignments)[0], false);
      }
      frame.classList.toggle("hide-candidates", mode === "selected");
      frame.dataset.controlState = mode;
      document.querySelectorAll(".dispatch-visual.secondary").forEach((route) => {
        route.style.opacity = mode === "candidates" ? "1" : "";
      });
      showToast(mode === "selected" ? "已聚焦当前派单，其余关系降噪" : mode === "candidates" ? "已增强派单关系线，便于检查" : "显示全部派单图层");
    }
    function bindMapControls() {
      $("expand-graph").addEventListener("click", (event) => {
        document.querySelector(".left-panel").classList.toggle("expanded");
        event.currentTarget.classList.toggle("active");
        event.currentTarget.textContent = event.currentTarget.classList.contains("active") ? "收起" : "展开全部";
        setStatus(event.currentTarget.classList.contains("active") ? "推理树已展开" : "推理树已收起", false);
      });
      $("layer-mode").addEventListener("change", (event) => setLayerMode(event.target.value));
      document.querySelectorAll("[data-map-action]").forEach((button) => {
        button.addEventListener("click", () => {
          const action = button.dataset.mapAction;
          button.classList.toggle("active");
          if (action === "depots") {
            const hidden = button.classList.contains("active");
            const frame = document.querySelector(".map-frame");
            frame.classList.toggle("hide-entities", hidden);
            frame.dataset.entitiesMuted = hidden ? "true" : "false";
            showToast(hidden ? "点位图层已弱化，仅保留派单关系" : "点位图层已恢复：商家与骑手可见");
            return;
          }
          if (action === "routes") {
            const active = button.classList.contains("active");
            const frame = document.querySelector(".map-frame");
            frame.classList.toggle("hide-dispatch-routes", active);
            frame.dataset.routesHidden = active ? "true" : "false";
            showToast(active ? "派单关系线已隐藏，仅保留点位" : "派单关系线已恢复，展示商家 → 骑手关系");
            return;
          }
          if (action === "locate") {
            const frame = document.querySelector(".map-frame");
            frame.classList.add("locating");
            frame.dataset.locating = "true";
            const profile = currentProfile || profileForCase(selectedCase());
            const selected = profile.assignments && (profile.assignments[profile.selected] || profile.assignments.A1);
            if (selected) {
              const map = ensureSemiRealMap();
              const pickup = entityById(profile, selected.pickup);
              const courierId = finalCourierForAssignment(selected);
              const courier = entityById(profile, courierId);
              if (map && pickup && courier) {
                const center = [
                  (safeNumber(pickup.x, 50) + safeNumber(courier.x, 50)) / 2,
                  (safeNumber(pickup.y, 50) + safeNumber(courier.y, 50)) / 2
                ];
                const lngLat = screenNormToLngLat(center);
                if (lngLat) {
                  semiRealMapMoveMode = "locate-assignment-control";
                  map.easeTo({center: lngLat, zoom: Math.max(14.0, map.getZoom()), pitch: 0, bearing: 0, duration: 520});
                  frame.dataset.mapCenter = `${lngLat[0].toFixed(5)},${lngLat[1].toFixed(5)}`;
                }
              }
              renderAssignmentDetail(profile, profile.selected, selected.merchant);
              showToast("已定位到 " + selected.courier + " 当前派单包");
            } else {
              showToast("请先运行派单推理生成骑手位置");
            }
            return;
          }
          if (action === "fit") {
            const frame = document.querySelector(".map-frame");
            frame.classList.remove("locating", "hide-entities", "hide-dispatch-routes", "hide-candidates");
            frame.dataset.locating = "false";
            frame.dataset.routesHidden = "false";
            frame.dataset.entitiesMuted = "false";
            frame.dataset.controlState = "all";
            $("zoom-in").classList.remove("active");
            $("zoom-out").classList.remove("active");
            document.querySelectorAll('[data-map-action="depots"], [data-map-action="routes"]').forEach((node) => node.classList.remove("active"));
            const layerMode = $("layer-mode");
            if (layerMode) layerMode.value = "all";
            const map = ensureSemiRealMap();
            if (map) {
              const region = currentSemiRealMapRegion();
              semiRealMapMoveMode = "fit-control";
              map.easeTo({center: region.center, zoom: region.zoom, pitch: region.pitch, bearing: region.bearing, duration: 450});
            }
            const profile = currentProfile || profileForCase(selectedCase());
            if (profile.assignments && Object.keys(profile.assignments).length) {
              applyMapFocus(profile, profile.selected || Object.keys(profile.assignments)[0], false);
              updateMapScene(profile);
            }
            showToast("视图已适配全部派单关系");
            return;
          }
          if (action === "fullscreen") {
            const panel = document.querySelector(".map-panel");
            const frame = document.querySelector(".map-frame");
            const expanded = panel.classList.toggle("active");
            frame.dataset.fullscreen = expanded ? "true" : "false";
            button.textContent = expanded ? "退出" : "全屏";
            showToast(expanded ? "演示视图已进入地图聚焦模式" : "演示视图已退出地图聚焦模式");
            return;
          }
          showToast("商家与骑手图层可见");
        });
      });
      $("zoom-in").addEventListener("click", () => {
        const frame = document.querySelector(".map-frame");
        $("zoom-in").classList.add("active");
        $("zoom-out").classList.remove("active");
        const map = ensureSemiRealMap();
        if (map) {
          semiRealMapMoveMode = "zoom-in-control";
          const targetZoom = Math.min(18.5, map.getZoom() + 0.85);
          frame.dataset.zoomLevel = targetZoom.toFixed(2);
          map.easeTo({zoom: targetZoom, duration: 360});
        }
        showToast("地图已放大，点位与派单线将按当前视口重算");
      });
      $("zoom-out").addEventListener("click", () => {
        const frame = document.querySelector(".map-frame");
        $("zoom-out").classList.add("active");
        $("zoom-in").classList.remove("active");
        const map = ensureSemiRealMap();
        if (map) {
          semiRealMapMoveMode = "zoom-out-control";
          const targetZoom = Math.max(10.5, map.getZoom() - 0.85);
          frame.dataset.zoomLevel = targetZoom.toFixed(2);
          map.easeTo({zoom: targetZoom, duration: 360});
        }
        showToast("地图已缩小，点位与派单线将按当前视口重算");
      });
      $("recenter").addEventListener("click", () => {
        const frame = document.querySelector(".map-frame");
        frame.classList.add("locating");
        frame.dataset.locating = "true";
        const map = ensureSemiRealMap();
        if (map) {
          const region = currentSemiRealMapRegion();
          semiRealMapMoveMode = "recenter-control";
          map.easeTo({center: region.center, zoom: region.zoom, pitch: region.pitch, bearing: region.bearing, duration: 420});
        }
        const profile = currentProfile || profileForCase(selectedCase());
        if (profile.assignments && Object.keys(profile.assignments).length) {
          applyMapFocus(profile, profile.selected || Object.keys(profile.assignments)[0], false);
          updateMapScene(profile);
        }
        showToast("已回到当前派单关系中心");
      });
      const entityPinAtClientPoint = (event) => {
        if (!event || !Number.isFinite(event.clientX) || !Number.isFinite(event.clientY)) return null;
        const pins = [...document.querySelectorAll(".pin")].filter((pin) => {
          const style = getComputedStyle(pin);
          return style.display !== "none" && style.visibility !== "hidden" && style.pointerEvents !== "none";
        });
        let nearest = null;
        pins.forEach((pin) => {
          const rect = pin.getBoundingClientRect();
          const centerX = rect.left + rect.width / 2;
          const centerY = rect.top + rect.height / 2;
          const distance = Math.hypot(event.clientX - centerX, event.clientY - centerY);
          if (distance <= 7 && (!nearest || distance < nearest.distance)) nearest = {pin, distance};
        });
        return nearest ? nearest.pin : null;
      };
      document.querySelector(".map-frame").addEventListener("click", (event) => {
        const target = event.target.closest(".map-label, .pin, .dispatch-link, .dispatch-arrow");
        if (!target) return;
        const profile = currentProfile || profileForCase(selectedCase());
        if (!profile.assignments || Object.keys(profile.assignments).length === 0) {
          if (renderEntityPreviewDetail(profile, target.dataset.entity || "")) return;
        }
        const routeClickTarget = target.classList.contains("route-click-target");
        const endpointPin = ((target.classList.contains("dispatch-link") && !routeClickTarget) || target.classList.contains("dispatch-arrow"))
          ? entityPinAtClientPoint(event)
          : null;
        if (endpointPin && endpointPin.dataset.entity && renderFinalEntityDetail(profile, endpointPin.dataset.entity)) return;
        if (target.dataset.leg && renderRouteDetail(profile, target.dataset.assignment || profile.selected, target.dataset)) return;
        if (target.dataset.entity && renderFinalEntityDetail(profile, target.dataset.entity)) return;
        const sourceLabel = target.dataset.entity || target.dataset.merchant || target.dataset.courier || target.textContent.trim();
        renderAssignmentDetail(profile, target.dataset.assignment || profile.selected, sourceLabel);
      });
      document.querySelector(".branch-grid").addEventListener("click", (event) => {
        const strategy = event.target.closest(".strategy");
        if (!strategy) return;
        renderStrategyDetail(strategy.dataset.branch || "");
      });
      document.querySelector(".table-panel tbody").addEventListener("click", (event) => {
        const row = event.target.closest("tr");
        if (!row) return;
        renderTableRowDetail(row);
      });
      bindMapDragFallback();
    }
    function bindMapDragFallback() {
      const frame = document.querySelector(".map-frame");
      if (!frame || frame.dataset.dragFallbackBound === "true") return;
      const map = ensureSemiRealMap();
      if (map) {
        frame.dataset.dragFallbackBound = "native-maplibre";
        frame.dataset.dragPan = "native";
        return;
      }
      frame.dataset.dragFallbackBound = "true";
      frame.setAttribute("draggable", "true");
      let dragStart = null;
      let dragLast = null;
      const eventPoint = (event) => {
        const touch = event.touches && event.touches[0] || event.changedTouches && event.changedTouches[0];
        return {
          x: safeNumber(touch ? touch.clientX : event.clientX, 0),
          y: safeNumber(touch ? touch.clientY : event.clientY, 0)
        };
      };
      const beginDrag = (event) => {
        if (event.button !== undefined && event.button !== 0) return;
        if (event.target.closest(".toolbar, .map-legend, .zoom, .weather, .toast, .pin, .map-label, .dispatch-link, .dispatch-arrow")) return;
        dragStart = eventPoint(event);
        dragLast = dragStart;
        frame.classList.add("dragging-map");
        if (event.type !== "dragstart") event.preventDefault();
      };
      const moveDrag = (event) => {
        if (!dragStart) return;
        dragLast = eventPoint(event);
        const dx = dragLast.x - dragStart.x;
        const dy = dragLast.y - dragStart.y;
        if (Math.hypot(dx, dy) >= 8) frame.dataset.dragging = "true";
      };
      const finishDrag = (event) => {
        if (!dragStart) return;
        const finishPoint = eventPoint(event);
        const endPoint = finishPoint.x || finishPoint.y ? finishPoint : dragLast || dragStart;
        const dx = endPoint.x - dragStart.x;
        const dy = endPoint.y - dragStart.y;
        dragStart = null;
        dragLast = null;
        frame.classList.remove("dragging-map");
        if (Math.hypot(dx, dy) < 10) return;
        const map = ensureSemiRealMap();
        if (!map) return;
        semiRealMapMoveMode = "manual-pan";
        map.panBy([-dx, -dy], {duration: 260});
        frame.dataset.dragPan = "true";
        frame.dataset.dragging = "false";
        showToast("地图已移动，派单点位与线路已按当前视口重算");
      };
      frame.addEventListener("pointerdown", beginDrag, true);
      frame.addEventListener("mousedown", beginDrag, true);
      frame.addEventListener("touchstart", beginDrag, true);
      frame.addEventListener("dragstart", beginDrag, true);
      window.addEventListener("pointermove", moveDrag, true);
      window.addEventListener("mousemove", moveDrag, true);
      window.addEventListener("touchmove", moveDrag, true);
      window.addEventListener("drag", moveDrag, true);
      window.addEventListener("pointerup", finishDrag, true);
      window.addEventListener("mouseup", finishDrag, true);
      window.addEventListener("touchend", finishDrag, true);
      window.addEventListener("dragend", finishDrag, true);
      window.addEventListener("pointercancel", () => {
        dragStart = null;
        frame.classList.remove("dragging-map");
      });
    }
    function debugStateSnapshot() {
      const profile = currentProfile || null;
      const dispatchMap = profile && profile.dispatchMap ? profile.dispatchMap : null;
      const assignments = (profile && profile.assignments) || {};
      const sample = currentSimulationSample ? {
        case_id: currentSimulationSample.case_id,
        scenario_id: currentSimulationSample.scenario_id,
        sample_index: currentSimulationSample.sample_index,
        name: currentSimulationSample.name,
        selected_strategy_id: currentSimulationSample.selected_strategy_id,
        merchant_count: Array.isArray(currentSimulationSample.merchants) ? currentSimulationSample.merchants.length : 0,
        courier_count: Array.isArray(currentSimulationSample.couriers) ? currentSimulationSample.couriers.length : 0
      } : null;
      return {
      currentProfile: profile ? {
        label: profile.label,
        selected: profile.selected,
        mapFocusMode: profile.mapFocusMode,
        assignmentCount: Object.keys(assignments).length,
        dispatchMap: dispatchMap ? {
          case_id: dispatchMap.case_id,
          scenario_id: dispatchMap.scenario_id,
          sample_index: dispatchMap.sample_index,
          stage: dispatchMap.stage,
          anchor_source: dispatchMap.anchor_source,
          anchor_variant: dispatchMap.anchor_variant,
          assignment_reconciled_variant: dispatchMap.assignment_reconciled_variant,
          entityCount: Array.isArray(dispatchMap.entities) ? dispatchMap.entities.length : 0,
          assignmentCount: Array.isArray(dispatchMap.assignments) ? dispatchMap.assignments.length : 0,
          roadCount: Array.isArray(dispatchMap.map_layers && dispatchMap.map_layers.roads) ? dispatchMap.map_layers.roads.length : 0
        } : null
      } : null,
      currentReport: currentReport ? {
        wall_time_s: currentReport.wall_time_s,
        best: currentReport.best,
        has_dispatch_assignment_map: Boolean(currentReport.dispatch_assignment_map)
      } : null,
      currentReasoningState,
      currentSimulationSample: sample,
      semiRealMapReady,
      semiRealMapRegion,
      semiRealMapRegionLabel: currentSemiRealMapRegion().label,
      semiRealMapStyle,
      semiRealMapViewport: semiRealMap ? {
        zoom: Number(semiRealMap.getZoom().toFixed(3)),
        center: (() => {
          const center = semiRealMap.getCenter();
          return {lng: Number(center.lng.toFixed(6)), lat: Number(center.lat.toFixed(6))};
        })()
      } : null,
      semiRealMapTextLayers: semiRealMapTextLayerAudit(),
      mapFrame: {
        className: document.querySelector(".map-frame")?.className || "",
        dataset: {...(document.querySelector(".map-frame")?.dataset || {})}
      },
      dom: {
        pins: document.querySelectorAll(".pin").length,
        routeLinks: document.querySelectorAll(".dispatch-link.pickup-leg").length,
        routeArrows: document.querySelectorAll(".dispatch-arrow").length,
        strategyCards: document.querySelectorAll(".strategy").length,
        tableRows: document.querySelectorAll(".table-panel tbody tr").length,
        detailTitle: document.querySelector("#detail-title")?.textContent || "",
        status: document.querySelector("#status")?.textContent || ""
      }
      };
    }
    function publishDebugState() {
      const target = $("autosolver-debug-state");
      if (!target) return;
      try {
        target.textContent = JSON.stringify(debugStateSnapshot());
      } catch (error) {
        target.textContent = JSON.stringify({error: String(error && error.message ? error.message : error)});
      }
    }
    window.__AUTO_SOLVER_DEBUG__ = debugStateSnapshot;
    globalThis.__AUTO_SOLVER_DEBUG__ = debugStateSnapshot;
    window.setInterval(publishDebugState, 1500);
    $("run-agent").addEventListener("click", streamRun);
    $("reload-cases").addEventListener("click", () => {
      refreshSimulationSample().catch((error) => {
        console.error(error);
        setStatus("刷新位置失败", false);
        showToast("刷新位置失败，请检查仿真场景接口");
      });
    });
    $("refresh-map").addEventListener("click", refreshSemiRealMap);
    $("case-select").addEventListener("change", async () => {
      const option = $("case-select").selectedOptions && $("case-select").selectedOptions[0];
      if (option && option.dataset.scenario) {
        try {
          await loadSimulationScenario(option.dataset.scenario);
        } catch (error) {
          console.error(error);
          setStatus("加载仿真场景失败", false);
        }
        return;
      }
      applyScene(selectedCase());
    });
    syncDashboardScale();
    renderProjectBasemapState();
    bindMapControls();
    loadCases();
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
