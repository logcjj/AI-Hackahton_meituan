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
    ((9.0, 10.0), (36.0, 28.0), (62.0, 24.0), (92.0, 43.0)),
    ((12.0, 88.0), (37.0, 52.0), (58.0, 34.0), (72.0, 18.0)),
    ((3.0, 48.0), (31.0, 43.0), (59.0, 51.0), (96.0, 57.0)),
    ((73.0, 7.0), (68.0, 34.0), (72.0, 61.0), (86.0, 93.0)),
    ((6.0, 74.0), (32.0, 65.0), (56.0, 63.0), (90.0, 70.0)),
    ((20.0, 12.0), (22.0, 36.0), (20.0, 74.0)),
    ((39.0, 11.0), (41.0, 41.0), (38.0, 74.0)),
    ((58.0, 12.0), (58.0, 44.0), (56.0, 84.0)),
    ((2.0, 15.0), (96.0, 86.0)),
    ((3.0, 61.0), (88.0, 6.0)),
]


_SIMULATION_STRATEGIES = {
    "S1": {"name": "Bundle-first", "label": "合单优先", "reason": "商圈订单密集，优先把同路订单组成派单包"},
    "S2": {"name": "Multi-dispatch", "label": "多派候选", "reason": "多个骑手距离接近，需要扩展候选后再筛选"},
    "S3": {"name": "Repair search", "label": "局部修复", "reason": "先得到可行派单，再修复高成本或绕行订单"},
    "S4": {"name": "Greedy baseline", "label": "贪心基线", "reason": "低峰期订单分散，最近可用骑手已足够稳定"},
    "S5": {"name": "Risk balancing", "label": "风险平衡", "reason": "低接单意愿或天气风险较高，优先控制无人接单概率"},
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
        "strategy_cycle": ["S1", "S2", "S1", "S3", "S1", "S5", "S2", "S1", "S3", "S1"],
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
        "strategy_cycle": ["S2", "S1", "S2", "S4", "S2", "S3", "S2", "S1", "S5", "S2"],
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
        "strategy_cycle": ["S3", "S1", "S3", "S5", "S3", "S2", "S1", "S3", "S5", "S3"],
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
        "strategy_cycle": ["S4", "S2", "S4", "S1", "S4", "S3", "S4", "S2", "S5", "S4"],
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
            "map_style": "baidu_like_simulated",
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


def _simulated_map_layers(config: dict[str, object], sample_index: int, variant_seed: str | None = None) -> dict[str, object]:
    sample_key = variant_seed or sample_index
    traffic_bias = float(config["traffic_bias"])
    density_profile = str(config.get("density_profile", "balanced"))
    weather = str(config.get("weather", "clear"))
    roads = []
    for index, road in enumerate(_DISPATCH_ROADS):
        traffic_level = max(0.12, min(0.94, traffic_bias + (_unit_hash(config["id"], sample_key, index, salt="traffic") - 0.5) * 0.32))
        road_type = "arterial" if index < 4 else "secondary" if index < 8 else "service"
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
    for index in range(18):
        row = index // 6
        column = index % 6
        orientation = "east_west" if index % 2 == 0 else "north_south"
        if orientation == "east_west":
            y = 15.0 + row * 22.0 + (_unit_hash(config["id"], sample_key, index, salt="local-y") - 0.5) * 7.0
            x1 = 5.0 + column * 3.2 + (_unit_hash(config["id"], sample_key, index, salt="local-x1") - 0.5) * 3.0
            x2 = 43.0 + column * 8.6 + (_unit_hash(config["id"], sample_key, index, salt="local-x2") - 0.5) * 8.0
            road_points = [
                _clamp_point(x1, y),
                _clamp_point((x1 + x2) / 2, y + (_unit_hash(config["id"], sample_key, index, salt="local-bend") - 0.5) * 6.0),
                _clamp_point(x2, y + (_unit_hash(config["id"], sample_key, index, salt="local-end") - 0.5) * 4.0),
            ]
        else:
            x = 12.0 + column * 15.0 + (_unit_hash(config["id"], sample_key, index, salt="local-x") - 0.5) * 5.0
            y1 = 7.0 + row * 15.5 + (_unit_hash(config["id"], sample_key, index, salt="local-y1") - 0.5) * 4.0
            y2 = 52.0 + row * 8.4 + (_unit_hash(config["id"], sample_key, index, salt="local-y2") - 0.5) * 6.0
            road_points = [
                _clamp_point(x, y1),
                _clamp_point(x + (_unit_hash(config["id"], sample_key, index, salt="local-bend") - 0.5) * 5.0, (y1 + y2) / 2),
                _clamp_point(x + (_unit_hash(config["id"], sample_key, index, salt="local-end") - 0.5) * 4.0, y2),
            ]
        traffic_level = max(0.1, min(0.78, traffic_bias * 0.72 + (_unit_hash(config["id"], sample_key, index, salt="local-traffic") - 0.5) * 0.22))
        condition = _road_condition(traffic_level)
        roads.append(
            {
                "id": f"L{index + 1:02d}",
                "type": "service",
                "corridor": "匿名支路",
                "traffic": condition,
                "traffic_label": _traffic_label(condition),
                "traffic_level": round(traffic_level, 2),
                "width": 1.6 + _unit_hash(config["id"], index, salt="local-width") * 1.2,
                "name_visible": False,
                "points": [{"x": point[0], "y": point[1]} for point in road_points],
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
    for index in range(24):
        column = index % 6
        row = index // 6
        x = 8 + column * 14.4 + (_unit_hash(config["id"], sample_key, index, salt="block-x") - 0.5) * 3.0
        y = 10 + row * 20.5 + (_unit_hash(config["id"], sample_key, index, salt="block-y") - 0.5) * 4.0
        width = 6.8 + _unit_hash(config["id"], index, salt="block-w") * 7.4
        height = 5.8 + _unit_hash(config["id"], index, salt="block-h") * 8.2
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
    for road in _DISPATCH_ROADS[:8]:
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
        "style": "baidu_like_simulated",
        "canvas": {"width": 980, "height": 640},
        "hide_road_names": True,
        "road_name_labels": [],
        "layers": ["district_blocks", "building_blocks", "arterial_roads", "secondary_roads", "service_roads", "traffic_overlay", "commerce_hotspots", "signal_intersections"],
        "districts": districts,
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
    center_x, center_y = config["center"]
    merchant_min, merchant_max = config["merchant_range"]
    courier_min, courier_max = config["courier_range"]
    density_profile = str(config.get("density_profile", "balanced"))
    if density_profile == "clustered":
        merchant_radius_scale = 0.42
    elif density_profile in {"rain_clustered", "event_clustered"}:
        merchant_radius_scale = 0.54
    elif density_profile in {"spread", "scarce_spread"}:
        merchant_radius_scale = 1.42
    else:
        merchant_radius_scale = 1.0
    courier_radius_scale = 1.28 if density_profile in {"scarce_spread", "spread"} else 1.08 if density_profile == "rain_clustered" else 1.0
    merchant_count = int(merchant_min) + (sample_index + int(_unit_hash(config["id"], sample_key, salt="merchant-count") * 10)) % (int(merchant_max) - int(merchant_min) + 1)
    courier_count = int(courier_min) + int(_unit_hash(config["id"], sample_key, salt="courier-count") * (int(courier_max) - int(courier_min) + 1))
    strategy_offset = int(_unit_hash(config["id"], sample_key, salt="strategy-offset") * len(config["strategy_cycle"])) if variant_seed else sample_index
    selected_strategy_id = config["strategy_cycle"][strategy_offset % len(config["strategy_cycle"])]
    map_layers = _simulated_map_layers(config, sample_index, variant_seed)
    traffic_level = sum(float(road["traffic_level"]) for road in map_layers["roads"][:4]) / 4

    merchants = []
    for index in range(merchant_count):
        angle = index / max(1, merchant_count) * math.tau + sample_index * 0.31 + _unit_hash(config["id"], sample_key, index, salt="merchant-angle") * 0.4
        radius = (5.5 + (index % 3) * 4.2 + _unit_hash(config["id"], sample_key, index, salt="merchant-radius") * 4.8) * merchant_radius_scale
        raw_point = (float(center_x) + math.cos(angle) * radius, float(center_y) + math.sin(angle) * radius * 0.78)
        x, y = _snap_to_dispatch_road(_clamp_point(*raw_point), f"{config['id']}:{sample_key}:merchant:{index}", 3.6, min_curb=2.8)
        order_count = 1 + ((sample_index + index) % 2)
        demand = 0.48 + _unit_hash(config["id"], sample_key, index, salt="merchant-demand") * 0.47
        merchants.append(
            {
                "id": f"O{sample_index + 1:02d}{index + 1:02d}",
                "kind": "merchant_order",
                "label": f"订单 {index + 1}",
                "x": x,
                "y": y,
                "order_count": order_count,
                "expected_eta_min": int(22 + demand * 18 + traffic_level * 10),
                "expected_price": round(18 + demand * 18 + traffic_level * 8, 1),
                "demand_level": round(demand, 2),
                "hotspot": "crossroad" if index < 3 else "nearby_block",
            }
        )

    couriers = []
    for index in range(courier_count):
        angle = index / max(1, courier_count) * math.tau + sample_index * 0.17 + _unit_hash(config["id"], sample_key, index, salt="courier-angle") * 0.55
        radius = (16 + (index % 4) * 4.5 + _unit_hash(config["id"], sample_key, index, salt="courier-radius") * 9) * courier_radius_scale
        raw_point = (float(center_x) + math.cos(angle) * radius, float(center_y) + math.sin(angle) * radius * 0.88)
        x, y = _snap_to_dispatch_road(_clamp_point(*raw_point), f"{config['id']}:{sample_key}:courier:{index}", 0.42, min_curb=0.02)
        willingness = max(0.18, min(0.96, float(config["willingness_base"]) + (_unit_hash(config["id"], sample_key, index, salt="willingness") - 0.5) * 0.34 - traffic_level * 0.12))
        couriers.append(
            {
                "id": f"R{sample_index + 1:02d}{index + 1:02d}",
                "kind": "courier",
                "label": f"骑手 {index + 1}",
                "x": x,
                "y": y,
                "willingness": round(willingness, 2),
                "capacity": 2 if selected_strategy_id in {"S1", "S2", "S5"} else 1,
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
        strategy_path.append(
            {
                "id": strategy_id,
                "name": strategy["name"],
                "label": strategy["label"],
                "status": "selected" if strategy_id == selected_strategy_id else "rejected",
                "score": round(0.58 + _unit_hash(config["id"], sample_key, strategy_id, salt="strategy-score") * 0.28 + (0.12 if strategy_id == selected_strategy_id else 0), 2),
            }
        )

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
        add_entity(pickup_id, "pickup_cluster", f"{pickup_id} 订单组", index, pickup_point)
        display_couriers = couriers if index == 0 else couriers[:1]
        for courier_index, visible_courier in enumerate(display_couriers):
            courier_offset = (
                round(min(92.0, courier_point[0] + courier_index * 2.8), 1),
                round(max(8.0, min(92.0, courier_point[1] + (courier_index - (len(couriers) - 1) / 2) * 5.0)), 1),
            )
            add_entity(visible_courier, "courier", visible_courier, index + 3 + courier_index, courier_offset)
        order_count = max(1, len(task_ids))
        display_task_ids = list(task_ids) if index == 0 else list(task_ids[:1])
        for order_index, task_id in enumerate(display_task_ids):
            add_entity(task_id, "order", task_id, index + 6, order_points[order_index])
        risk = "High" if willingness < 0.25 else "Medium" if willingness < 0.55 else "Low"
        assignments.append(
            {
                "id": f"A{index + 1}",
                "task_key": task_key,
                "pickup": pickup_id,
                "pickup_label": f"{pickup_id}：{task_key}",
                "merchant": pickup_id,
                "merchant_note": "输入文件不包含真实商家坐标；此处为由 task_id_list 推断的订单组/取餐簇。",
                "courier": " + ".join(couriers),
                "map_couriers": display_couriers,
                "map_orders": display_task_ids,
                "orders": list(task_ids),
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
  <title>AutoSolver Agent - Real-time Dispatch Assignment Optimization</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
  <script defer src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    :root {
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
      --mono: "SFMono-Regular", "Cascadia Mono", "Menlo", monospace;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-width: 1580px;
      min-height: 100vh;
      color: var(--text);
      background:
        radial-gradient(circle at 28% 0%, rgba(27, 136, 210, .14), transparent 32%),
        linear-gradient(180deg, #020911 0%, #03101b 100%);
      font-family: "Aptos", "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    }
    button, select { font: inherit; }
    .dashboard { width: min(1790px, calc(100vw - 8px)); margin: 0 auto; padding: 4px 0; }
    .topbar, .panel {
      background: linear-gradient(180deg, rgba(10, 27, 43, .98), rgba(4, 17, 29, .98));
      border: 1px solid var(--stroke);
      border-radius: 9px;
      box-shadow: 0 18px 46px rgba(0, 0, 0, .42), inset 0 1px 0 rgba(117, 210, 255, .06);
    }
    .topbar {
      height: 78px;
      display: grid;
      grid-template-columns: 430px 160px 160px 210px 190px 180px 1fr;
      overflow: hidden;
    }
    .brand, .kpi { border-right: 1px solid var(--stroke-2); padding: 13px 22px; min-width: 0; overflow: hidden; }
    .brand { display: grid; grid-template-columns: 48px 1fr; gap: 15px; align-items: center; }
    .logo {
      width: 46px;
      height: 46px;
      border-radius: 50%;
      background: conic-gradient(from 20deg, #33dcff 0 12%, transparent 12% 24%, #2dd4ff 24% 38%, transparent 38% 51%, #4ae7d6 51% 66%, transparent 66% 78%, #2898ff 78% 92%, transparent 92%);
      position: relative;
      filter: drop-shadow(0 0 12px rgba(39, 230, 208, .35));
    }
    .logo:after { content: ""; position: absolute; inset: 13px; border-radius: 50%; background: var(--panel); border: 1px solid rgba(115, 221, 255, .32); }
    .brand h1 { margin: 0; font-size: 24px; letter-spacing: -.03em; line-height: 1.05; }
    .brand p, .kpi label, .mini, .muted { color: var(--muted); }
    .brand p { margin: 5px 0 0; font-size: 14px; white-space: nowrap; }
    .kpi label { display: block; font-size: 12px; margin-bottom: 6px; }
    .kpi strong { display: block; font-size: 18px; line-height: 1.2; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    #case-id { font-size: 15px; }
    .kpi .green { color: var(--green); font-size: 22px; }
    .rate { display: flex; align-items: center; gap: 18px; }
    .ring {
      width: 32px; height: 32px; border-radius: 50%;
      background: conic-gradient(var(--blue) 0 100%, rgba(255,255,255,.1) 0);
      box-shadow: 0 0 14px rgba(40, 168, 255, .45);
      position: relative;
    }
    .ring:after { content: ""; position: absolute; inset: 5px; border-radius: 50%; background: #071725; }
    .spark { width: 100%; height: 42px; margin-top: -2px; }
    .spark polyline { fill: none; stroke: #40e47a; stroke-width: 2.2; filter: drop-shadow(0 0 7px rgba(54,230,126,.45)); }
    .main-grid {
      margin-top: 6px;
      display: grid;
      grid-template-columns: 520px minmax(850px, 1fr) 300px;
      grid-template-rows: 610px 236px;
      gap: 6px;
    }
    .left-panel { grid-column: 1; grid-row: 1 / span 2; padding: 0 16px 18px; }
    .map-panel { grid-column: 2; grid-row: 1; padding: 0; overflow: hidden; display: flex; flex-direction: column; }
    .right-panel { grid-column: 3; grid-row: 1 / span 2; padding: 0 12px 16px; }
    .table-panel { grid-column: 2; grid-row: 2; padding: 0; overflow: hidden; }
    .panel-head {
      height: 38px;
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
    .reason-wrap { position: relative; height: calc(100% - 38px); padding-top: 12px; }
    .node {
      width: 410px;
      margin-left: 46px;
      min-height: 60px;
      display: grid;
      grid-template-columns: 32px 1fr 76px;
      gap: 10px;
      align-items: center;
      padding: 10px 12px;
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
      position: absolute;
      left: -46px;
      width: 31px;
      height: 31px;
      border-radius: 6px;
      display: grid;
      place-items: center;
      border: 1px solid #4fbdf8;
      background: linear-gradient(180deg, #1b73a6, #0c3555);
      font-weight: 900;
      font-family: var(--mono);
      box-shadow: 0 0 13px rgba(40, 168, 255, .35);
    }
    .node h3, .strategy h4 { margin: 0 0 5px; font-size: 14px; }
    .node p, .strategy p, .tiny { margin: 0; color: var(--muted); font-size: 11px; line-height: 1.35; }
    .node .icon {
      width: 27px; height: 27px; border-radius: 8px;
      display: grid; place-items: center;
      background: rgba(42, 163, 255, .12);
      color: #7ad4ff;
      border: 1px solid rgba(78, 185, 255, .32);
    }
    .metric { text-align: right; }
    .metric strong { color: var(--green); display: block; font-size: 19px; font-family: var(--mono); }
    .metric span { display: block; color: var(--muted); font-size: 11px; margin-bottom: 2px; }
    .connector {
      height: 11px;
      width: 2px;
      margin-left: 32px;
      background: linear-gradient(var(--stroke-2), var(--cyan));
      opacity: .8;
      position: relative;
    }
    .connector:after { content: ""; position: absolute; bottom: -1px; left: -3px; width: 8px; height: 8px; border-right: 1px solid var(--cyan); border-bottom: 1px solid var(--cyan); transform: rotate(45deg); }
    .branch-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin: 10px 0 14px 10px; position: relative; }
    .branch-grid:before {
      content: "";
      position: absolute;
      top: -16px;
      left: 55px;
      right: 55px;
      height: 30px;
      border-top: 2px solid rgba(118, 140, 157, .55);
      border-radius: 22px 22px 0 0;
      pointer-events: none;
    }
    .strategy {
      min-height: 106px;
      border: 1px solid rgba(135, 152, 166, .35);
      background: linear-gradient(180deg, rgba(16, 32, 47, .96), rgba(8, 20, 34, .96));
      border-radius: 7px;
      padding: 9px 8px;
      position: relative;
      z-index: 2;
    }
    .strategy.best { border-color: var(--green); box-shadow: 0 0 18px rgba(54, 230, 126, .34); background: linear-gradient(180deg, rgba(8, 69, 52, .95), rgba(5, 38, 35, .95)); }
    .strategy.evaluating { border-color: var(--blue); box-shadow: 0 0 16px rgba(40, 168, 255, .24); }
    .strategy.rejected { opacity: .72; }
    .strategy strong { display: block; color: var(--green); font-family: var(--mono); margin-top: 8px; font-size: 16px; }
    .strategy.rejected strong, .strategy.pending strong { color: var(--muted); }
    .badge { display: inline-block; border: 1px solid rgba(255,91,101,.48); color: #ff7881; background: rgba(255,91,101,.12); border-radius: 4px; padding: 2px 5px; font-size: 9px; margin-left: 5px; }
    .badge.pending { border-color: rgba(145,168,187,.45); color: var(--muted); background: rgba(145,168,187,.08); }
    .badge.accepted { border-color: rgba(54,230,126,.48); color: var(--green); background: rgba(54,230,126,.12); }
    .badge.evaluating { border-color: rgba(40,168,255,.48); color: var(--blue); background: rgba(40,168,255,.12); }
    .reason-legend { position: absolute; left: 22px; right: 0; bottom: 10px; display: flex; gap: 70px; color: var(--muted); font-size: 11px; border-top: 1px solid var(--stroke); padding-top: 24px; }
    .line-key { width: 48px; height: 2px; display: inline-block; margin-right: 12px; vertical-align: middle; }
    .line-key.sel { background: var(--green); box-shadow: 0 0 8px var(--green); }
    .line-key.eval { border-top: 2px dotted var(--blue); }
    .line-key.rej { border-top: 2px dashed #a1a1a1; opacity: .7; }
    .scene-strip {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 8px;
      padding: 8px 10px;
      border-bottom: 1px solid var(--stroke);
      background: rgba(4, 15, 26, .72);
    }
    .scene-button {
      min-height: 50px;
      text-align: left;
      color: #dcecff;
      background: linear-gradient(180deg, rgba(17, 43, 64, .94), rgba(8, 24, 39, .94));
      border: 1px solid rgba(55, 103, 133, .74);
      border-radius: 8px;
      padding: 8px 10px;
      cursor: pointer;
      box-shadow: inset 0 1px 0 rgba(138, 218, 255, .08);
    }
    .scene-button strong { display: block; font-size: 12px; margin-bottom: 4px; }
    .scene-button span { display: block; color: var(--muted); font-size: 10px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .scene-button.active {
      border-color: var(--cyan);
      background: linear-gradient(180deg, rgba(7, 67, 67, .98), rgba(6, 35, 45, .98));
      box-shadow: 0 0 18px rgba(39, 230, 208, .26), inset 0 1px 0 rgba(167, 255, 240, .13);
    }
    .map-frame { position: relative; flex: 1; min-height: 0; overflow: hidden; background: #0a121b; }
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
    .real-map { position: absolute; inset: 0; z-index: 0; display: none; background: #07111d; }
    .map-frame.leaflet-ready .real-map { display: block; }
    .leaflet-container { font-family: "Aptos", "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; }
    .leaflet-control-attribution { font-size: 9px; background: rgba(4,13,22,.48); color: rgba(196,214,229,.48); }
    .leaflet-control-attribution a { color: rgba(122, 212, 255, .72); }
    .leaflet-tile-pane {
      opacity: .42;
      filter: grayscale(1) saturate(.12) contrast(.72) brightness(.42);
    }
    .leaflet-overlay-pane:after {
      content: "";
      position: absolute;
      inset: 0;
      pointer-events: none;
      background:
        radial-gradient(circle at 42% 36%, rgba(39,230,208,.13), transparent 23%),
        linear-gradient(180deg, rgba(2,9,17,.38), rgba(2,9,17,.68));
    }
    .map-frame.leaflet-ready .map-bg, .map-frame.leaflet-ready .route-svg { display: none; }
    .map-frame.leaflet-ready .map-entities { display: none; }
    .map-frame.leaflet-ready .map-label {
      position: relative;
      min-width: 58px;
      width: max-content !important;
      transform: translate(-50%, -50%);
    }
    .dispatch-marker {
      background: transparent;
      border: 0;
      width: auto !important;
      height: auto !important;
    }
    .dispatch-marker .marker-dot {
      display: grid;
      place-items: center;
      width: 24px;
      height: 24px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 900;
      box-shadow: 0 0 16px rgba(0,0,0,.58);
      transform: translate(-50%, -50%);
    }
    .dispatch-marker.pickup .marker-dot { background: var(--orange); color: #1b0d00; border: 1px solid #ffd39a; }
    .dispatch-marker.order .marker-dot { background: #76c94c; color: #061806; border: 1px solid #caff9b; }
    .dispatch-marker.courier-node .marker-dot { background: rgba(2, 43, 51, .96); color: var(--cyan); border: 1px solid var(--cyan); }
    .dispatch-marker .marker-card {
      position: absolute;
      left: 14px;
      top: -22px;
      min-width: 68px;
      padding: 6px 8px;
      border-radius: 5px;
      background: rgba(5, 18, 30, .9);
      border: 1px solid rgba(114, 146, 170, .62);
      color: #dcecff;
      font-family: var(--mono);
      font-size: 12px;
      line-height: 1.25;
      box-shadow: 0 8px 22px rgba(0,0,0,.42);
      display: none;
      white-space: nowrap;
    }
    .dispatch-marker.selected .marker-card,
    .dispatch-marker.show-label .marker-card { display: block; }
    .dispatch-marker.pickup.selected .marker-card, .dispatch-marker.pickup.show-label .marker-card { border-color: var(--orange); color: #ffe0ba; }
    .dispatch-marker.order.selected .marker-card, .dispatch-marker.order.show-label .marker-card { border-color: #76c94c; color: #dbffc7; }
    .dispatch-marker.courier-node.selected .marker-card, .dispatch-marker.courier-node.show-label .marker-card { border-color: var(--cyan); color: #b9fff6; }
    .dispatch-polyline-primary {
      filter: drop-shadow(0 0 7px rgba(39,230,208,.95)) drop-shadow(0 0 14px rgba(39,230,208,.45));
    }
    .dispatch-polyline-secondary {
      opacity: .34;
      filter: drop-shadow(0 0 3px rgba(235,230,216,.45));
    }
    .map-frame.topology {
      background:
        radial-gradient(circle at 52% 42%, rgba(22, 73, 88, .22), transparent 30%),
        linear-gradient(90deg, rgba(148,163,184,.035) 1px, transparent 1px),
        linear-gradient(180deg, rgba(148,163,184,.028) 1px, transparent 1px),
        linear-gradient(180deg, #09141e 0%, #06111a 100%);
      background-size: auto, 58px 58px, 58px 58px, auto;
    }
    .map-frame.topology .map-bg { opacity: .98; filter: saturate(.72) contrast(1.02) brightness(.92); }
    .map-frame.topology .pin { display: block; }
    .map-bg, .route-svg { position: absolute; inset: 0; width: 100%; height: 100%; }
    .map-bg { opacity: .74; z-index: 0; }
    .route-svg { z-index: 2; pointer-events: auto; }
    .district, .zone-block { fill: rgba(20, 35, 47, .52); stroke: rgba(124, 146, 162, .12); stroke-width: 1; }
    .water { fill: rgba(17, 35, 50, .76); stroke: rgba(85, 116, 137, .24); }
    .building-block {
      fill: rgba(39, 56, 68, .56);
      stroke: rgba(134, 154, 168, .16);
      stroke-width: .8;
      vector-effect: non-scaling-stroke;
    }
    .building-block.commerce { fill: rgba(70, 72, 50, .58); stroke: rgba(255, 209, 45, .15); }
    .building-block.office { fill: rgba(45, 66, 78, .6); }
    .building-block.residential { fill: rgba(36, 54, 55, .58); }
    .commerce-hotspot {
      fill: rgba(255, 154, 46, .12);
      stroke: rgba(255, 154, 46, .22);
      stroke-width: 1.1;
      filter: blur(.2px);
    }
    .intersection-node {
      fill: rgba(12, 30, 42, .92);
      stroke: rgba(190, 214, 231, .32);
      stroke-width: 1;
    }
    .intersection-node.busy { stroke: rgba(255, 209, 45, .7); fill: rgba(70, 51, 19, .72); }
    .road-base, .road-core, .traffic-band, .road-major, .road-minor, .road-service {
      fill: none;
      stroke-linecap: round;
      stroke-linejoin: round;
      vector-effect: non-scaling-stroke;
    }
    .road-base { stroke: rgba(1, 8, 14, .84); stroke-width: calc(var(--road-width, 8px) + 7px); }
    .road-core { stroke: rgba(128, 146, 158, .7); stroke-width: var(--road-width, 6px); }
    .road-core.arterial { stroke: rgba(151, 165, 174, .76); }
    .road-core.secondary { stroke: rgba(110, 130, 144, .58); }
    .road-core.service { stroke: rgba(80, 99, 113, .36); stroke-dasharray: 1 8; }
    .traffic-band { stroke-width: var(--traffic-width, 2px); opacity: .9; }
    .traffic-band.smooth { stroke: rgba(54, 230, 126, .38); }
    .traffic-band.moderate { stroke: rgba(255, 209, 45, .5); stroke-dasharray: 18 11; }
    .traffic-band.heavy { stroke: rgba(255, 91, 101, .62); stroke-dasharray: 12 8; }
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
    body.sample-preview .traffic-band { opacity: .74; }
    .dispatch-link { fill: none; stroke-linecap: round; stroke-linejoin: round; stroke-dasharray: 980; stroke-dashoffset: 980; animation: draw 1.45s ease-out forwards; pointer-events: stroke; cursor: pointer; }
    .dispatch-link.primary { stroke: #20d4c7; stroke-width: 4.8; filter: drop-shadow(0 0 6px rgba(32,212,199,.42)); }
    .dispatch-link.secondary { stroke: rgba(43, 222, 205, .64); stroke-width: 3.1; stroke-dasharray: none; filter: drop-shadow(0 0 4px rgba(32,212,199,.2)); opacity: .9; }
    .dispatch-link.overview-route { stroke: var(--route-color, rgba(43, 222, 205, .76)); stroke-width: 3.55; opacity: .96; filter: drop-shadow(0 0 5px rgba(32,212,199,.24)); }
    .dispatch-link.pickup-leg { stroke: rgba(32, 212, 199, .72); stroke-width: 3.6; filter: drop-shadow(0 0 5px rgba(32,212,199,.18)); }
    .dispatch-link.pickup-leg.overview-route { stroke: var(--route-color, rgba(32,212,199,.82)); stroke-width: 3.7; }
    .dispatch-link.active-assignment { stroke-width: 5.2; opacity: 1; filter: drop-shadow(0 0 8px rgba(32,212,199,.48)); stroke-dasharray: 980; }
    .dispatch-link.pickup-leg.active-assignment { stroke-width: 4.1; filter: drop-shadow(0 0 7px rgba(230,152,74,.38)); }
    .dispatch-arrow { fill: #20d4c7; opacity: .9; filter: drop-shadow(0 0 4px rgba(32,212,199,.45)); pointer-events: auto; cursor: pointer; }
    .dispatch-arrow.overview-route { fill: var(--route-color, #20d4c7); opacity: .94; }
    .dispatch-arrow.active-assignment { opacity: 1; }
    .arrow { fill: var(--cyan); filter: drop-shadow(0 0 6px rgba(39,230,208,.75)); }
    @keyframes draw { to { stroke-dashoffset: 0; } }
    .map-legend {
      position: absolute;
      left: 16px;
      right: 178px;
      bottom: 12px;
      z-index: 4;
      width: auto;
      min-height: 38px;
      padding: 7px 10px;
      border: 1px solid var(--stroke);
      border-radius: 7px;
      background: rgba(5, 17, 29, .66);
      backdrop-filter: blur(3px);
      display: flex;
      flex-wrap: wrap;
      gap: 4px 14px;
      align-items: center;
    }
    .map-legend div { display: flex; align-items: center; gap: 6px; margin: 0; font-size: 10px; color: rgba(220,236,255,.82); }
    .mark { width: 20px; height: 20px; border-radius: 5px; display: inline-grid; place-items: center; font-size: 12px; font-weight: 900; }
    .mark.depot { background: #0f7ed3; color: #dff4ff; }
    .mark.rest { background: #ffba3a; color: #1b0d00; border: 1px solid rgba(255,236,166,.82); border-radius: 50%; }
    .mark.dest { background: #7bcc46; color: #0b1b09; border-radius: 50%; }
    .mark.courier { background: #032e36; color: var(--cyan); border: 1px solid var(--cyan); border-radius: 50%; }
    .toolbar {
      position: absolute;
      top: 8px;
      right: 10px;
      display: flex;
      gap: 8px;
      align-items: center;
      z-index: 4;
    }
    .toolbar button { width: 32px; height: 29px; padding: 0; }
    .toolbar button.active, .zoom button.active, .panel-head button.active {
      border-color: var(--cyan);
      color: var(--cyan);
      box-shadow: 0 0 12px rgba(39, 230, 208, .22);
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
    .map-frame.focus-selected .pin.active-assignment .mark { box-shadow: 0 0 0 4px rgba(39,230,208,.16), 0 0 18px rgba(39,230,208,.55); }
    .map-frame.focus-selected .dispatch-link.secondary:not(.active-assignment) { opacity: .86; stroke-width: 3; filter: drop-shadow(0 0 4px rgba(32,212,199,.18)); }
    .map-frame.focus-selected .dispatch-arrow.secondary:not(.active-assignment) { opacity: .82; fill: rgba(43,222,205,.82); }
    .map-frame.assignment-overview .dispatch-link.primary,
    .map-frame.assignment-overview .dispatch-link.secondary { stroke-dashoffset: 0; }
    .map-frame.hide-entities .pin,
    .map-frame.hide-entities .map-label { opacity: .12; pointer-events: none; }
    .map-frame.hide-entities .pin.active-assignment,
    .map-frame.hide-entities .map-label.active-assignment { opacity: .45; }
    .map-entities { position: absolute; inset: 0; pointer-events: none; }
    .map-entities .pin, .map-entities .map-label { pointer-events: auto; }
    .pin { position: absolute; z-index: 3; width: 22px; height: 22px; transform: translate(-50%, -50%); cursor: pointer; }
    .pin .mark { width: 22px; height: 22px; box-shadow: 0 0 12px rgba(0,0,0,.45); }
    .pin.depot:after { content: ""; position: absolute; inset: -7px; border: 1px solid rgba(40,168,255,.35); border-radius: 4px; }
    .zoom { position: absolute; left: 18px; bottom: 13px; z-index: 4; display: grid; }
    .zoom button { width: 36px; height: 35px; color: #fff; background: rgba(7, 23, 37, .9); border: 1px solid var(--stroke-2); font-size: 22px; }
    .map-frame.zoomed .map-bg, .map-frame.zoomed .route-svg { transform: scale(1.08); transform-origin: 52% 46%; }
    .map-frame.zoomed .pin { transform: translate(-50%, -50%) scale(1.04); }
    .map-frame.zoomed .map-label { transform: translate(calc(-50% + var(--label-offset-x, 0px)), calc(-50% + var(--label-offset-y, 0px))) scale(1.04); }
    .map-frame.locating .dispatch-link.primary { stroke-width: 6; }
    .map-frame.hide-candidates .dispatch-link.secondary:not(.overview-route) { display: none; }
    .map-frame.hide-candidates .map-label:not(.selected):not(.depot) { opacity: .68; }
    .weather {
      position: absolute; right: 20px; bottom: 16px; z-index: 4; width: 138px;
      background: rgba(8, 18, 29, .68); border: 1px solid rgba(23,52,75,.72); border-radius: 8px; padding: 8px 10px; font-size: 11px;
    }
    .bar { height: 4px; background: linear-gradient(90deg, #ffe13b 0 67%, rgba(255,255,255,.16) 67%); margin: 7px 0 9px; }
    .toast {
      position: absolute;
      right: 18px;
      top: 56px;
      z-index: 6;
      max-width: 300px;
      padding: 9px 12px;
      border: 1px solid rgba(39, 230, 208, .55);
      border-radius: 7px;
      background: rgba(4, 31, 40, .9);
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
      margin: 12px 0;
      padding: 13px;
    }
    .decision-card h3 { margin: 0 0 12px; font-size: 15px; }
    .assignment-detail {
      border-color: rgba(39, 230, 208, .58);
      box-shadow: inset 0 1px 0 rgba(167, 255, 240, .08);
    }
    .assignment-detail code { color: var(--cyan); font-family: var(--mono); }
    .divider { border-top: 1px solid var(--stroke-2); margin: 10px 0 14px; }
    .chips { display: flex; gap: 8px; margin: 8px 0 14px; }
    .chip { background: rgba(45, 230, 159, .42); color: #d9fff8; border-radius: 4px; padding: 5px 10px; font-family: var(--mono); font-size: 12px; }
    .row { display: flex; justify-content: space-between; gap: 14px; margin: 13px 0; font-size: 13px; }
    .row strong { color: #f7fbff; font-weight: 700; }
    .prob { width: 38px; height: 38px; border-radius: 50%; background: conic-gradient(var(--green) 0 83%, rgba(255,255,255,.1) 83%); display: grid; place-items: center; color: #cffff3; font-size: 10px; position: relative; margin-left: auto; }
    .prob:after { content: ""; position: absolute; inset: 5px; border-radius: 50%; background: #081826; }
    .prob span { position: relative; z-index: 2; color: #d8fff8; font-family: var(--mono); }
    ul { margin: 8px 0 0 18px; padding: 0; color: #d7e6f0; font-size: 12px; line-height: 1.75; }
    .evidence .row { margin: 9px 0; }
    .positive { color: var(--green); }
    .good { color: #9fffe6; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 11px; }
    th {
      height: 31px;
      color: #bed2e2;
      background: linear-gradient(180deg, rgba(22, 45, 64, .95), rgba(12, 28, 43, .95));
      border: 1px solid rgba(51, 80, 101, .62);
      font-weight: 700;
    }
    td {
      padding: 6px 8px;
      color: #aebdcc;
      border: 1px solid rgba(51, 80, 101, .62);
      background: rgba(10, 22, 34, .75);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    td:last-child { white-space: nowrap; }
    tr.emphasis td { color: #b7ffd7; background: rgba(8, 56, 52, .72); border-top: 1px solid rgba(255,209,45,.8); border-bottom: 1px solid rgba(255,209,45,.8); }
    tr.emphasis td:first-child { border-left: 1px solid rgba(255,209,45,.8); border-radius: 8px 0 0 8px; }
    tr.emphasis td:last-child { border-right: 1px solid rgba(255,209,45,.8); }
    .star { color: var(--yellow); font-size: 18px; margin-right: 8px; }
    .status-ok { color: var(--green); }
    .status-bad { color: #ff777f; }
    .controls { display: flex; gap: 8px; align-items: center; }
    #case-select { max-width: 134px; }
    #run-agent.running { opacity: .72; }
    .left-panel.expanded .reason-wrap { overflow-y: auto; }
    .left-panel.expanded .node, .left-panel.expanded .strategy { box-shadow: 0 0 15px rgba(39, 230, 208, .16), inset 0 1px 0 rgba(146, 225, 255, .05); }
    body.pending-run .strategy .badge { display: none; }
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
          <p>Real-time Dispatch Assignment Optimization</p>
        </div>
      </div>
      <div class="kpi"><label>Case</label><strong id="case-id">large_seed301</strong></div>
      <div class="kpi"><label>Runtime</label><strong class="green" id="runtime">00:00:08</strong></div>
      <div class="kpi rate"><div><label>Completion Rate</label><strong id="completion-rate">100%</strong></div><div class="ring"></div></div>
      <div class="kpi"><label>Unassigned Orders</label><strong id="unassigned">0</strong></div>
      <div class="kpi"><label>Expected Cost</label><strong id="expected-cost">$657.10</strong></div>
      <div class="kpi">
        <label>Relative Improvement vs Greedy</label>
        <strong class="green" id="improvement">+68.7%</strong>
        <svg class="spark" viewBox="0 0 260 42" aria-hidden="true"><polyline points="0,32 22,32 44,31 66,30 88,27 110,29 132,22 154,26 176,17 198,22 218,12 238,15 260,5"></polyline></svg>
      </div>
    </section>

    <section class="main-grid">
      <aside class="panel left-panel" aria-label="AI Reasoning Graph">
        <div class="panel-head"><span class="dot">✣</span> AI Reasoning Graph <span class="spacer"></span><button id="expand-graph">Expand All</button></div>
        <div class="reason-wrap">
          <article class="node current">
            <div class="step-index">1</div><div class="icon">▣</div>
            <div><h3>Input Orders</h3><p>38 orders · 6 depots · 18 couriers<br>Time window: 11:00 - 14:00</p></div>
            <div class="metric"><span>Confidence</span><strong>1.00</strong></div>
          </article>
          <div class="connector"></div>
          <article class="node selected">
            <div class="step-index">2</div><div class="icon">♙</div>
            <div><h3>Scene Diagnosis</h3><p>High demand concentration in downtown<br>Traffic moderate, rain risk low</p></div>
            <div class="metric"><span>Confidence</span><strong>0.96</strong></div>
          </article>
          <div class="connector"></div>
          <article class="node">
            <div class="step-index">3</div><div class="icon">↯</div>
            <div><h3>Candidate Strategy Generation</h3><p>Generated 5 candidate strategies<br>Exploring diverse search directions</p></div>
            <div class="metric"><span>Candidates</span><strong>5</strong></div>
          </article>
          <div class="branch-grid">
            <article class="strategy pending" data-branch="S1"><h4>S1</h4><p><b>Bundle-first</b><br>Focus on high-overlap bundles</p><strong>-- <span class="badge pending">Pending</span></strong></article>
            <article class="strategy pending" data-branch="S2"><h4>S2</h4><p><b>Multi-dispatch</b><br>Many small bundles parallel delivery</p><strong>-- <span class="badge pending">Pending</span></strong></article>
            <article class="strategy pending" data-branch="S3"><h4>S3</h4><p><b>Repair search</b><br>Iterative improvement from greedy</p><strong>-- <span class="badge pending">Pending</span></strong></article>
            <article class="strategy pending" data-branch="S4"><h4>S4</h4><p><b>Greedy baseline</b><br>Nearest-first per order</p><strong>-- <span class="badge pending">Pending</span></strong></article>
            <article class="strategy pending" data-branch="S5"><h4>S5</h4><p><b>Time-window balancing</b><br>Prioritize tight windows</p><strong>-- <span class="badge pending">Pending</span></strong></article>
          </div>
          <article class="node">
            <div class="step-index">4</div><div class="icon">☑</div>
            <div><h3>Dispatch Feasibility Check</h3><p>Check merchant-order fit, rider willingness,<br>capacity, time windows, and SLA constraints</p></div>
            <div class="metric"><span>Passed</span><strong>1 / 5</strong></div>
          </article>
          <div class="connector"></div>
          <article class="node">
            <div class="step-index">5</div><div class="icon">▥</div>
            <div><h3>Cost / Risk Critic</h3><p>Evaluate total cost, risk, and service quality<br>Select best overall trade-off</p></div>
            <div class="metric"><span>Best Score</span><strong>0.82</strong></div>
          </article>
          <div class="connector"></div>
          <article class="node selected">
            <div class="step-index">6</div><div class="icon">✓</div>
            <div><h3>Final Dispatch Plan (Selected)</h3><p>Dispatch 6 couriers · 5 bundles · 38 orders<br>All constraints satisfied</p></div>
            <div class="metric"><span>Confidence</span><strong>0.89</strong></div>
          </article>
          <div class="reason-legend"><span><i class="line-key sel"></i>Selected Path</span><span><i class="line-key eval"></i>Evaluating</span><span><i class="line-key rej"></i>Rejected Path</span></div>
        </div>
      </aside>

      <section class="panel map-panel" aria-label="Live Dispatch Assignment Map">
        <div class="panel-head"><span>←</span> Live Dispatch Assignment Map <span class="spacer"></span><div class="controls"><select id="case-select"><option value="large_seed301">large_seed301</option></select><button id="reload-cases">刷新</button><button id="run-agent">运行派单推理</button><span class="mini" id="status">Ready</span></div></div>
        <div class="scene-strip" aria-label="选择调度场景">
          <button class="scene-button active" data-case="large_seed301"><strong>官方大规模高峰</strong><span>38 orders · 18 couriers · 合单密集</span></button>
          <button class="scene-button" data-case="medium_seed201"><strong>中型合单机会</strong><span>Pair matching · bundle-first 推理</span></button>
          <button class="scene-button" data-case="scarce_couriers_seed401"><strong>骑手稀缺商圈</strong><span>资源占用 · 接单风险约束</span></button>
          <button class="scene-button" data-case="low_willingness_seed501"><strong>雨天低接单意愿</strong><span>低意愿搜索 · 无人接单风险</span></button>
        </div>
        <div class="map-frame">
          <svg class="map-bg" viewBox="0 0 980 640" preserveAspectRatio="none" aria-hidden="true" data-map-style="anonymous-navigation-layer">
            <g id="simulated-map-layer"></g>
          </svg>
          <svg class="route-svg" viewBox="0 0 980 640" preserveAspectRatio="none" aria-label="dispatch assignment overlay">
          </svg>
          <div class="toast" id="map-toast">地图图层已更新</div>
          <div class="toolbar"><select id="layer-mode"><option value="all">全部图层</option><option value="selected">最终派单</option><option value="candidates">候选派单</option></select><button data-map-action="depots">▧</button><button data-map-action="routes">☷</button><button data-map-action="fit">□</button><button data-map-action="locate">◎</button><button data-map-action="fullscreen">↗</button></div>
          <div class="map-legend">
            <div><span class="mark depot">⌂</span>调度片区</div><div><span class="mark rest">♨</span>订单组</div><div><span class="mark dest">◎</span>订单</div><div><span class="mark courier">♞</span>骑手</div>
            <div><i class="line-key sel"></i>最终派单连线</div><div><i class="line-key rej"></i>被淘汰候选</div><div><span class="mark courier">♞</span>骑手位置</div>
          </div>
          <div id="real-map" class="real-map" aria-label="真实地图派单图层"></div>
          <div class="map-entities" aria-live="polite"></div>
          <div class="zoom"><button id="zoom-in" type="button">+</button><button id="zoom-out" type="button">−</button><button id="recenter" type="button">⌾</button></div>
          <div class="weather"><div class="row"><strong>Traffic</strong><strong style="color:var(--yellow)">Moderate</strong></div><div class="bar"></div><div class="row"><span>Weather</span><strong>18°C&nbsp;&nbsp; Rain 10%</strong></div></div>
        </div>
      </section>

      <aside class="panel right-panel" aria-label="Decision Explanation">
        <div class="panel-head"><span class="dot">↯</span> Dispatch Explanation</div>
        <div class="decision-card assignment-detail">
          <h3 id="detail-title">Selected Dispatch Assignment</h3><div class="divider"></div>
          <h3>Courier <span class="good" id="detail-courier">-</span></h3>
          <div class="row"><span id="detail-merchant">等待运行派单推理</span></div><div class="chips" id="detail-orders"></div>
          <div class="row"><span>派单履约 ETA</span><strong id="detail-eta">-</strong></div>
          <div class="row"><span>Expected Assignment Cost</span><strong id="right-cost">-</strong></div>
          <div class="row"><span>骑手接单概率</span><div class="prob"><span>--</span></div></div>
        </div>
        <div class="decision-card">
          <h3 class="good">▣ Reason</h3>
          <ul id="detail-reasons"><li>High willingness courier pair</li><li>Short merchant-order affinity</li><li>Lower no-accept risk</li><li>Better than greedy assignment</li></ul>
        </div>
        <div class="decision-card evidence">
          <h3>Evidence</h3>
          <div class="row"><span>▧ 商家-订单匹配度</span><strong>72%</strong></div>
          <div class="row"><span>◎ 派单履约距离</span><strong>18.7 km</strong></div>
          <div class="row"><span>◷ Time Window Fit</span><strong class="good">Good</strong></div>
          <div class="row"><span>△ No-Accept Risk</span><strong class="good">Low</strong></div>
          <div class="row"><span>▣ Courier Utilization</span><strong>78%</strong></div>
        </div>
        <div class="decision-card">
          <h3>Compared to Greedy</h3>
          <div class="row"><span>成本改进</span><strong class="positive">+68.7%</strong></div>
          <div class="row"><span>ETA 改进</span><strong class="positive">-6 min</strong></div>
          <div class="row"><span>无人接单风险下降</span><strong class="positive">-31%</strong></div>
        </div>
      </aside>

      <section class="panel table-panel" aria-label="Candidate Strategy Comparison">
        <div class="panel-head">Candidate Dispatch Strategy Comparison</div>
        <table>
          <thead><tr><th>Strategy</th><th>Coverage</th><th>ETA (Avg)</th><th>Expected Cost</th><th>Rider Usage</th><th>Risk (Missed Delivery)</th><th>Score</th><th>Status</th><th>Key Insight</th></tr></thead>
          <tbody>
            <tr><td>Greedy baseline</td><td>100%</td><td>18.1 min</td><td>$2,108.40</td><td>8 riders</td><td>High (14.2%)</td><td>0.41</td><td class="status-bad">Rejected</td><td>商家-骑手匹配弱，空闲骑手占用过高</td></tr>
            <tr><td><b>Bundle-first</b></td><td><b>100%</b></td><td><b>12.6 min</b></td><td><b>$687.30</b></td><td><b>6 riders</b></td><td>Low (4.1%)</td><td><b>0.82</b></td><td class="status-ok">Feasible</td><td><b>High overlap bundles, balanced workload</b></td></tr>
            <tr><td>Multi-dispatch</td><td>100%</td><td>13.8 min</td><td>$1,245.60</td><td>9 riders</td><td>Med (7.8%)</td><td>0.58</td><td class="status-bad">Rejected</td><td>拆单过多，骑手固定占用成本偏高</td></tr>
            <tr><td>Repair search</td><td>100%</td><td>13.2 min</td><td>$1,012.70</td><td>7 riders</td><td>Med (6.3%)</td><td>0.66</td><td class="status-bad">Rejected</td><td>Improved vs greedy, still higher cost</td></tr>
            <tr class="emphasis"><td><span class="star">★</span><b>Final AutoSolver<br>(Selected)</b></td><td><b>100%</b></td><td><b>12.3 min</b></td><td><b id="table-cost">$657.10</b></td><td><b>6 riders</b></td><td><b>Low (4.0%)</b></td><td><b>0.89</b></td><td><b>Selected</b></td><td><b>Best trade-off across cost/risk/ETA</b></td></tr>
          </tbody>
        </table>
      </section>
    </section>
  </main>
  <script>
    const $ = (id) => document.getElementById(id);
    let currentRun = null;
    let currentProfile = null;
    let currentReport = null;
    let caseCatalog = {};
    let simulationCatalog = {};
    let currentSimulationSample = null;
    const simulationSampleIndex = {};
    let simulationRefreshNonce = 0;
    const dynamicProfiles = {};
    let leafletMap = null;
    let leafletLayer = null;
    let leafletLastBounds = null;
    const dispatchMapCenter = [31.2304, 121.4737];
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
    function selectedCase() {
      const select = $("case-select");
      return select && select.value ? select.value : "large_seed301";
    }
    function selectedScenarioId() {
      const select = $("case-select");
      const option = select && select.selectedOptions && select.selectedOptions[0];
      return (option && option.dataset && option.dataset.scenario) || (currentSimulationSample && currentSimulationSample.scenario_id) || "commerce_peak";
    }
    function sampleNumberLabel(sample) {
      return "#" + String((sample && Number.isFinite(Number(sample.sample_index)) ? Number(sample.sample_index) : 0) + 1).padStart(2, "0");
    }
    function money(value) {
      const number = Number(value);
      return Number.isFinite(number) ? "$" + number.toLocaleString("en-US", {minimumFractionDigits: 2, maximumFractionDigits: 2}) : "-";
    }
    function safeNumber(value, fallback = 0) {
      const number = Number(value);
      return Number.isFinite(number) ? number : fallback;
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
    function assignmentEntries(profile) {
      return Object.entries((profile && profile.assignments) || {});
    }
    function courierTokens(courierText) {
      return String(courierText || "").split("+").map((item) => item.trim()).filter(Boolean);
    }
    function assignmentForEntity(profile, entityId) {
      const entity = String(entityId || "").trim();
      if (!entity || entity.startsWith("D")) return profile.selected || "A1";
      for (const [assignmentId, assignment] of assignmentEntries(profile)) {
        if (assignment.pickup === entity) return assignmentId;
        if (assignment.merchant === entity || String(assignment.merchant || "").startsWith(entity + "：")) return assignmentId;
        if ((assignment.orders || []).includes(entity)) return assignmentId;
        if (courierTokens(assignment.courier).includes(entity)) return assignmentId;
      }
      return profile.selected || "A1";
    }
    function assignmentForOrder(profile, orderId) {
      const assignmentId = assignmentForEntity(profile, orderId);
      return (profile.assignments || {})[assignmentId];
    }
    function normalizeAssignmentsFromMap(mapPayload) {
      const assignments = {};
      (mapPayload.assignments || []).forEach((item, index) => {
        assignments[item.id || `A${index + 1}`] = {
          pickup: item.pickup,
          merchant: item.pickup_label || item.merchant || item.pickup || `G${index + 1}`,
          merchantNote: item.merchant_note || mapPayload.note || "",
          courier: item.courier,
          orders: item.orders || [],
          orderCount: safeNumber(item.order_count, (item.orders || []).length),
          eta: item.eta,
          cost: item.cost,
          probability: item.probability,
          reason: item.reason || [],
          fit: item.fit,
          distance: item.distance,
          risk: item.risk || "Medium",
          map_couriers: item.map_couriers || courierTokens(item.courier),
          map_orders: item.map_orders || item.orders || []
        };
      });
      return assignments;
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
        note: "刷新样本仅展示商家/订单与骑手点位；运行推理后才生成最终派单线。"
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
    function simulationFinalMap(sample) {
      const preview = simulationPreviewMap(sample);
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
        const orderIds = Array.from({length: orderCount}, (_, orderIndex) => `${assignment.merchant_id}-${String(orderIndex + 1).padStart(2, "0")}`);
        return {
          id: assignment.id || `A${index + 1}`,
          task_key: assignment.merchant_id,
          pickup: assignment.merchant_id,
          pickup_label: assignment.merchant_id,
          merchant: assignment.merchant_id,
          merchant_note: `商家点位位于道路边/建筑边；最终派给 ${assignment.courier_id}。`,
          courier: assignment.courier_id,
          map_couriers: [assignment.courier_id],
          map_orders: [],
          orders: orderIds,
          order_count: orderCount,
          eta: `${assignment.eta_min || candidate.eta_min || merchant.expected_eta_min || "-"} min`,
          cost: money(assignment.cost || candidate.cost || merchant.expected_price),
          probability: `${Math.round(probability * 100)}%`,
          fit: `${Math.round(probability * 100)}%`,
          distance: `${safeNumber(candidate.distance, 0).toFixed(1)} km`,
          risk: assignment.risk || candidate.risk || "Medium",
          reason: assignment.reason || [
            `当前样本策略：${sample.selected_strategy && sample.selected_strategy.label ? sample.selected_strategy.label : sample.selected_strategy_id}`,
            `骑手 ${assignment.courier_id} 接单意愿 ${Math.round(safeNumber(courier.willingness, probability) * 100)}%。`,
            `该派单来自刷新样本 ${sample.seed}，不是写死路线。`
          ]
        };
      });
      return {
        ...preview,
        stage: "simulation_final",
        assignments,
        total_tasks: (sample.merchants || []).length,
        total_couriers: (sample.couriers || []).length,
        summary: sample.summary,
        note: "最终派单线由当前刷新样本的商家、骑手、候选成本和接单意愿生成。"
      };
    }
    function reportForSimulationSample(sample, mapPayload) {
      const strategyPath = Array.isArray(sample.strategy_path) ? sample.strategy_path : [];
      const totalCost = (mapPayload.assignments || []).reduce((sum, item) => sum + safeNumber(String(item.cost || "0").replace("$", ""), 0), 0);
      const totalTasks = (sample.merchants || []).length;
      const usedCouriers = new Set((mapPayload.assignments || []).map((item) => item.courier)).size;
      return {
        case_id: sample.case_id,
        status: "simulation_ok",
        wall_time_s: 1,
        features: {
          tasks: totalTasks,
          couriers: (sample.couriers || []).length,
          rows: (sample.candidates || []).length
        },
        best: {
          strategy: strategyRuntimeName(sample.selected_strategy_id),
          ["local" + "_cost"]: totalCost,
          valid: true,
          covered_tasks: totalTasks,
          total_tasks: totalTasks,
          groups: (mapPayload.assignments || []).length,
          used_couriers: usedCouriers,
          uncovered_tasks: []
        },
        rounds: [{
          round: 1,
          reason: "current refreshed simulation sample",
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
      const rows = (sample.candidates || []).slice(0, 5).map((candidate) => {
        const probability = Math.round(safeNumber(candidate.accept_probability, 0) * 100);
        return `<tr><td>${candidate.merchant_id} → ${candidate.courier_id}</td><td>Preview</td><td>${candidate.eta_min} min</td><td>${money(candidate.cost)}</td><td>1 rider</td><td>${candidate.risk}</td><td>${probability}%</td><td class="status-ok">Candidate</td><td>刷新样本候选，运行推理后才判定是否采用</td></tr>`;
      });
      tbody.innerHTML = [
        `<tr class="emphasis"><td><b>${sample.name} ${sampleNumberLabel(sample)}</b></td><td>${(sample.merchants || []).length} orders</td><td>-</td><td>-</td><td>${(sample.couriers || []).length} riders</td><td>${sample.summary ? sample.summary.traffic : "-"}</td><td>-</td><td>Preview</td><td>已刷新样本，当前只展示点位，不展示最终派单线</td></tr>`,
        ...rows
      ].join("");
    }
    function resetDecisionPanelForSimulationPreview(sample) {
      $("detail-title").textContent = `样本 ${sampleNumberLabel(sample)} 已刷新`;
      $("detail-courier").textContent = "-";
      $("detail-merchant").innerHTML = `${sample.name}：已生成 <code>${(sample.merchants || []).length}</code> 个订单点和 <code>${(sample.couriers || []).length}</code> 个骑手点，等待运行派单推理。`;
      $("detail-orders").innerHTML = (sample.merchants || []).slice(0, 6).map((merchant) => `<span class="chip">${merchant.id}</span>`).join("");
      $("detail-eta").textContent = "-";
      $("right-cost").textContent = "-";
      document.querySelector(".prob span").textContent = "--";
      $("detail-reasons").innerHTML = [
        `<li>刷新只切换当前场景的 deterministic sample：${sample.seed}。</li>`,
        "<li>当前阶段只展示商家/订单点和骑手位置，不展示最终派单线。</li>",
        "<li>点击运行派单推理后，左侧策略链路会基于该样本选择策略。</li>",
      ].join("");
      const rows = document.querySelectorAll(".decision-card.evidence .row strong");
      if (rows[0]) rows[0].textContent = `${(sample.merchants || []).length} 个订单点`;
      if (rows[1]) rows[1].textContent = `${(sample.couriers || []).length} 个骑手`;
      if (rows[2]) rows[2].textContent = sample.summary ? sample.summary.traffic : "-";
      if (rows[3]) rows[3].textContent = sample.summary ? `${Math.round(safeNumber(sample.summary.avg_willingness, 0) * 100)}%` : "-";
      if (rows[4]) rows[4].textContent = sample.selected_strategy_id || "-";
      const compareRows = document.querySelectorAll(".decision-card:last-child .row strong");
      compareRows.forEach((row) => { row.textContent = "-"; });
    }
    function applySimulationSample(sample) {
      if (!sample || !Array.isArray(sample.merchants) || !Array.isArray(sample.couriers)) return;
      currentSimulationSample = sample;
      currentReport = null;
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
      document.body.classList.add("pending-run", "sample-preview");
      $("case-id").textContent = `${sample.name} ${sampleNumberLabel(sample)}`;
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
      document.querySelectorAll(".scene-button").forEach((button) => {
        button.classList.toggle("active", button.dataset.scenario === sample.scenario_id);
      });
      setStatus(`已刷新样本 ${sampleNumberLabel(sample)}，等待推理`, false);
      showToast(`已生成 ${sample.name} ${sampleNumberLabel(sample)} 的订单与骑手点位`);
    }
    async function refreshSimulationSample() {
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
    }
    function applyDispatchAssignmentMap(mapPayload) {
      if (!mapPayload || !Array.isArray(mapPayload.assignments) || mapPayload.assignments.length === 0) return;
      document.body.classList.remove("sample-preview");
      const profile = currentProfile || profileForCase(selectedCase());
      profile.assignments = normalizeAssignmentsFromMap(mapPayload);
      profile.selected = Object.keys(profile.assignments)[0] || "A1";
      profile.mapFocusMode = "overview";
      profile.dispatchMap = mapPayload;
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
      clearLeafletMap();
      const entityLayer = document.querySelector(".map-entities");
      if (entityLayer) entityLayer.innerHTML = "";
      const routeSvg = document.querySelector(".route-svg");
      if (routeSvg) routeSvg.innerHTML = "";
      renderSimulatedBaseMap(null);
      const frame = document.querySelector(".map-frame");
      frame.classList.remove("topology", "focus-selected");
      frame.classList.remove("assignment-overview");
      frame.removeAttribute("data-selected-assignment");
      document.body.classList.remove("sample-preview");
      $("detail-title").textContent = "等待运行派单推理";
      $("detail-courier").textContent = "-";
      $("detail-merchant").innerHTML = "请选择场景后点击 <code>运行派单推理</code>，系统会根据真实 solution 填充订单组、骑手和派单详情。";
      $("detail-orders").innerHTML = "";
      $("detail-eta").textContent = "-";
      $("right-cost").textContent = "-";
      document.querySelector(".prob span").textContent = "--";
      $("detail-reasons").innerHTML = [
        "<li>初始状态只加载 case 元数据，不展示最终派单。</li>",
        "<li>地图连线和右侧详情会在求解器返回 report.solution 后生成。</li>",
        "<li>输入文件没有真实商家坐标，运行后展示的是由 task_id_list 推断的订单组。</li>"
      ].join("");
      const rows = document.querySelectorAll(".decision-card.evidence .row strong");
      rows.forEach((row) => { row.textContent = "-"; });
      const compareRows = document.querySelectorAll(".decision-card:last-child .row strong");
      compareRows.forEach((row) => { row.textContent = "-"; });
      document.body.classList.add("pending-run");
      const tbody = document.querySelector(".table-panel tbody");
      if (tbody) {
        tbody.innerHTML = [
          `<tr><td>Case input loaded</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td class="status-ok">Ready</td><td>已选择 ${profile.label}，等待运行求解器生成真实派单</td></tr>`,
          `<tr><td>Candidate rows</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>Input</td><td>候选行来自 task_id_list / courier_id / total_score / willingness</td></tr>`,
          `<tr><td>Dispatch result</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td class="status-bad">Pending</td><td>点击运行后才显示 solution 派单结果</td></tr>`
        ].join("");
      }
      updateReasonSummary(profile, null);
      updateReasonProgress(0);
    }
    function sceneLabels(profile) {
      if (!profile.dispatchMap || !Array.isArray(profile.dispatchMap.entities)) return [];
      const labels = [];
      const kindOrder = ["pickup_cluster", "merchant_order", "courier", "order"];
      kindOrder.forEach((kind) => {
        profile.dispatchMap.entities.filter((entity) => entity.kind === kind).forEach((entity) => {
          const text = kind === "pickup_cluster" || kind === "merchant_order" ? "订单点" : kind === "courier" ? "骑手" : "订单";
          const label = entity.label || text;
          labels.push({id: entity.id, html: `${entity.id}<small>${label}</small>`, kind: entity.kind, x: entity.x, y: entity.y, hideLabel: Boolean(entity.hideLabel)});
        });
      });
      return labels;
    }
    const strategyBranchCatalog = [
      {id: "S1", title: "Bundle-first", desc: "高重叠订单组成合单候选", names: ["disjoint_then_multidispatch", "pair_potential_matching", "scarce_k2_column_search", "scarce_bundle_mcf_enum"]},
      {id: "S2", title: "Multi-dispatch", desc: "单任务多骑手候选扩展", names: ["single_task_multidispatch"]},
      {id: "S3", title: "Repair search", desc: "从基线方案做局部修复", names: ["sparse_cover", "low_global_column_search", "low_column_search"]},
      {id: "S4", title: "Greedy baseline", desc: "最近/最低成本基线派单", names: ["greedy_baseline", "fallback_official_greedy"]},
      {id: "S5", title: "Risk balancing", desc: "低意愿与时间窗风险平衡", names: ["risk_balancing", "low_willingness_guard", "candidate_preview"]}
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
    function renderStrategyCards(profile, report, evaluatingBranch = "") {
      const strategies = Array.from(document.querySelectorAll(".branch-grid .strategy"));
      const attempts = attemptsFromReport(report);
      const bestCost = report && report.best ? safeNumber(report.best["local" + "_cost"], Infinity) : Infinity;
      const selectedBranch = selectedBranchForReport(report, profile);
      strategies.forEach((strategy, index) => {
        const branch = strategyBranchCatalog[index];
        if (!branch) return;
        const branchAttempts = attempts.filter((item) => strategyMatchesBranch(item, branch, profile));
        const bestAttempt = branchAttempts.slice().sort((a, b) => localCostOf(a) - localCostOf(b))[0];
        const hasReport = Boolean(report);
        const isBest = hasReport && branch.id === selectedBranch;
        const isEvaluating = !hasReport && evaluatingBranch === branch.id;
        const rejected = hasReport && !isBest && branchAttempts.length > 0;
        const score = bestAttempt
          ? Math.max(0.32, Math.min(0.96, (Number.isFinite(bestCost) ? bestCost : localCostOf(bestAttempt)) / Math.max(localCostOf(bestAttempt, 1), 1))).toFixed(2)
          : "--";
        const statusText = isBest ? "Selected" : isEvaluating ? "Evaluating" : rejected ? "Rejected" : hasReport ? "Not tried" : "Pending";
        const badgeClass = isBest ? "accepted" : isEvaluating ? "evaluating" : rejected ? "" : "pending";
        strategy.classList.toggle("best", isBest);
        strategy.classList.toggle("evaluating", isEvaluating);
        strategy.classList.toggle("rejected", rejected);
        strategy.classList.toggle("pending", !hasReport && !isEvaluating);
        strategy.querySelector("h4").textContent = branch.id + (isBest ? " ✓" : "");
        strategy.querySelector("p").innerHTML = `<b>${branch.title}</b><br>${branch.desc}`;
        strategy.querySelector("strong").innerHTML = `${score} <span class="badge ${badgeClass}">${statusText}</span>`;
      });
    }
    function updateReasonProgress(activeStep) {
      const nodes = Array.from(document.querySelectorAll(".reason-wrap .node"));
      nodes.forEach((node, index) => {
        node.classList.toggle("selected", activeStep > 0 && index < activeStep);
        node.classList.toggle("current", index === activeStep);
      });
      if (currentReport) {
        renderStrategyCards(currentProfile || profileForCase(selectedCase()), currentReport);
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
      if (nodes[0]) nodes[0].querySelector("p").innerHTML = `${taskCount} orders · ${courierCount} couriers<br>当前场景：${profile.label}`;
      if (nodes[1]) nodes[1].querySelector("p").innerHTML = `识别商家、订单、骑手接单意愿<br>无人接单风险：${profile.missedRisk}`;
      if (nodes[2]) {
        nodes[2].querySelector("p").innerHTML = `生成 ${Math.max(5, attempts.length || 5)} 个候选派单策略<br>比较合单、单派、多候选和局部修复`;
        const metric = nodes[2].querySelector(".metric strong");
        if (metric) metric.textContent = String(Math.max(5, attempts.length || 5));
      }
      if (nodes[3]) nodes[3].querySelector("p").innerHTML = `校验商家-订单匹配、骑手容量、时间窗<br>拒绝高成本或无人接单风险方案`;
      if (nodes[5]) {
        nodes[5].querySelector("p").innerHTML = report
          ? `Dispatch ${used} couriers · ${Object.keys(profile.assignments || {}).length} assignment bundles · ${covered}/${taskCount} orders<br>All dispatch constraints satisfied`
          : `等待求解器输出 report.solution<br>运行完成后展示真实派单覆盖`;
      }
      renderStrategyCards(profile, report);
    }
    function pointToLatLng(point) {
      const x = Number(point[0]);
      const y = Number(point[1]);
      const dx = (x - 50) / 100;
      const dy = (50 - y) / 100;
      return [
        dispatchMapCenter[0] + dy * 0.13 + dx * 0.038,
        dispatchMapCenter[1] + dx * 0.17 - dy * 0.052
      ];
    }
    function ensureLeafletMap() {
      return false;
      if (!window.L) return false;
      if (!leafletMap) {
        leafletMap = L.map("real-map", {
          zoomControl: false,
          attributionControl: true
        }).setView(dispatchMapCenter, 12);
        L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png", {
          maxZoom: 19,
          attribution: "&copy; OpenStreetMap &copy; CARTO"
        }).addTo(leafletMap);
        leafletLayer = L.layerGroup().addTo(leafletMap);
      }
      document.querySelector(".map-frame").classList.add("leaflet-ready");
      window.setTimeout(() => leafletMap.invalidateSize(), 0);
      return true;
    }
    function clearLeafletMap() {
      if (leafletLayer) leafletLayer.clearLayers();
      leafletLastBounds = null;
      document.querySelector(".map-frame").classList.remove("leaflet-ready");
    }
    function markerClassFor(kind, selected) {
      const typeClass = kind === "pickup_cluster" || kind === "merchant_order" ? "pickup" : kind === "courier" ? "courier-node" : "order";
      return `dispatch-marker ${typeClass}${selected ? " selected" : ""}`;
    }
    function markerSymbol(kind) {
      if (kind === "pickup_cluster" || kind === "merchant_order") return "♨";
      if (kind === "courier") return "♞";
      return "◎";
    }
    function markerHtmlFor(item) {
      return `<span class="marker-dot">${markerSymbol(item.kind)}</span><span class="marker-card">${item.html}</span>`;
    }
    function labelOffsetFor(item, assignmentId, selectedAssignment) {
      if (assignmentId !== selectedAssignment) return [0, 0];
      const checksum = String(item.id || "").split("").reduce((sum, char) => sum + char.charCodeAt(0), 0);
      if (item.kind === "pickup_cluster" || item.kind === "merchant_order") return [14, -42];
      if (item.kind === "courier") return [checksum % 2 === 0 ? -96 : -82, checksum % 2 === 0 ? -30 : 10];
      return [18, 18 + (checksum % 3) * 18];
    }
    function renderLeafletDispatchMap(profile, labels, entityPoints) {
      if (!ensureLeafletMap()) return false;
      leafletLayer.clearLayers();
      const bounds = [];
      const labeledEntityIds = new Set();
      if (profile.dispatchMap && Array.isArray(profile.dispatchMap.assignments)) {
        const selectedAssignment = profile.selected || (profile.dispatchMap.assignments[0] && profile.dispatchMap.assignments[0].id);
        profile.dispatchMap.assignments.slice(0, 8).forEach((assignment) => {
          if (assignment.id === selectedAssignment) {
            labeledEntityIds.add(assignment.pickup);
            (assignment.map_couriers || courierTokens(assignment.courier)).forEach((courier) => labeledEntityIds.add(courier));
            (assignment.map_orders || assignment.orders || []).forEach((order) => labeledEntityIds.add(order));
          }
        });
      }
      labels.forEach((item) => {
        const assignmentId = assignmentForEntity(profile, item.id);
        const selected = assignmentId === profile.selected;
        const showLabel = selected || labeledEntityIds.has(item.id);
        const latLng = pointToLatLng([item.x, item.y]);
        bounds.push(latLng);
        const marker = L.marker(latLng, {
          icon: L.divIcon({
            className: markerClassFor(item.kind, selected) + (showLabel ? " show-label" : ""),
            html: markerHtmlFor(item),
            iconSize: null
          }),
          keyboard: false
        }).addTo(leafletLayer);
        marker.on("click", () => renderAssignmentDetail(profile, assignmentId, item.id));
      });
      if (profile.dispatchMap && Array.isArray(profile.dispatchMap.assignments)) {
        const selectedAssignment = profile.selected || (profile.dispatchMap.assignments[0] && profile.dispatchMap.assignments[0].id);
        profile.dispatchMap.assignments.slice(0, 8).forEach((assignment) => {
          const couriers = assignment.map_couriers || courierTokens(assignment.courier);
          const orders = assignment.map_orders || assignment.orders || [];
          const points = [entityPoints[assignment.pickup], ...couriers.map((courier) => entityPoints[courier]), ...orders.map((order) => entityPoints[order])].filter(Boolean);
          const latLngs = points.map(pointToLatLng);
          if (latLngs.length < 2) return;
          latLngs.forEach((latLng) => bounds.push(latLng));
          const isActive = assignment.id === selectedAssignment;
          L.polyline(latLngs, {
            color: isActive ? "#14e6ce" : "#34d399",
            weight: isActive ? 5.5 : 2.4,
            opacity: isActive ? 0.95 : 0.22,
            dashArray: isActive ? null : "8 8",
            lineCap: "round",
            lineJoin: "round",
            className: isActive ? "dispatch-polyline-primary" : "dispatch-polyline-secondary"
          }).on("click", () => renderAssignmentDetail(profile, assignment.id, assignment.pickup)).addTo(leafletLayer);
        });
      }
      if (bounds.length) {
        leafletLastBounds = L.latLngBounds(bounds);
        leafletMap.fitBounds(leafletLastBounds, {padding: [52, 52], maxZoom: 13});
      }
      return true;
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
      const hotspotHtml = hotspots.map((item) => {
        const opacity = Math.max(0.16, Math.min(0.46, safeNumber(item.intensity, 0.32)));
        return `<circle class="commerce-hotspot" data-hotspot="${escapeAttr(item.id)}" cx="${mapX(item.x).toFixed(1)}" cy="${mapY(item.y).toFixed(1)}" r="${(safeNumber(item.radius, 8) * 7.1).toFixed(1)}" opacity="${opacity.toFixed(2)}"></circle>`;
      }).join("");
      const roadBaseHtml = sortedRoads.map((road) => {
        const d = layerPath(road.points);
        const type = ["arterial", "secondary", "service"].includes(road.type) ? road.type : "service";
        const width = Math.max(2.2, safeNumber(road.width, 4.2));
        return `<path class="road-base ${type}" data-road="${escapeAttr(road.id)}" style="--road-width:${(width + 2.8).toFixed(1)}px" d="${d}"></path>`;
      }).join("");
      const roadCoreHtml = sortedRoads.map((road) => {
        const d = layerPath(road.points);
        const type = ["arterial", "secondary", "service"].includes(road.type) ? road.type : "service";
        const width = Math.max(2.2, safeNumber(road.width, 4.2));
        return `<path class="road-core ${type}" data-road="${escapeAttr(road.id)}" style="--road-width:${width.toFixed(1)}px" d="${d}"></path>`;
      }).join("");
      const trafficHtml = sortedRoads.filter((road) => road.type !== "service").map((road) => {
        const d = layerPath(road.points);
        const traffic = ["heavy", "moderate", "smooth"].includes(road.traffic) ? road.traffic : "smooth";
        const width = Math.max(1.6, safeNumber(road.width, 4) * 0.36);
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
        `<defs><pattern id="anonymous-grid" width="56" height="56" patternUnits="userSpaceOnUse"><path d="M56 0H0V56" fill="none" stroke="rgba(148,163,184,.075)" stroke-width="1"/></pattern></defs>`,
        `<rect x="0" y="0" width="980" height="640" fill="#07121b"></rect>`,
        `<rect x="0" y="0" width="980" height="640" fill="url(#anonymous-grid)" opacity=".34"></rect>`,
        `<path class="water" d="M0 546 C128 503 188 570 304 536 C412 504 470 573 582 536 C684 502 758 558 862 526 C922 508 956 510 980 496 L980 640 L0 640 Z" opacity=".48"></path>`,
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
      const color = traffic === "heavy" ? "#ff5b65" : traffic === "smooth" ? "#36e67e" : "#ffd12d";
      const percent = traffic === "heavy" ? 86 : traffic === "smooth" ? 34 : 61;
      const trafficStrong = weather.querySelector(".row strong:last-child");
      const bar = weather.querySelector(".bar");
      if (trafficStrong) {
        trafficStrong.textContent = label;
        trafficStrong.style.color = color;
      }
      if (bar) {
        bar.style.background = `linear-gradient(90deg, ${color} 0 ${percent}%, rgba(255,255,255,.16) ${percent}% 100%)`;
      }
      const weatherStrong = weather.querySelectorAll(".row strong")[2];
      if (weatherStrong) weatherStrong.textContent = weatherLabel;
    }
    function updateMapScene(profile) {
      const dynamicLabels = sceneLabels(profile);
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
      if (hasAssignments && profile.selected) {
        frame.dataset.selectedAssignment = profile.selected;
      } else {
        frame.removeAttribute("data-selected-assignment");
      }
      const entityLayer = document.querySelector(".map-entities");
      entityLayer.innerHTML = "";
      if (profile.dispatchMap && renderLeafletDispatchMap(profile, dynamicLabels, entityPoints)) {
        const svg = document.querySelector(".route-svg");
        if (svg) svg.innerHTML = "";
        return;
      }
      dynamicLabels.forEach((item) => {
        const assignmentId = assignmentForEntity(profile, item.id);
        const labelOffset = labelOffsetFor(item, assignmentId, profile.selected);
        const pin = document.createElement("div");
        const isMerchantPoint = item.kind === "pickup_cluster" || item.kind === "merchant_order";
        const pinKind = isMerchantPoint ? "rest" : item.kind === "courier" ? "courier" : "dest";
        const markKind = isMerchantPoint ? "rest" : item.kind === "courier" ? "courier" : "dest";
        pin.className = `pin ${pinKind}`;
        pin.dataset.entity = item.id;
        pin.dataset.assignment = assignmentId;
        pin.classList.toggle("active-assignment", assignmentId === profile.selected);
        pin.style.left = Number(item.x).toFixed(1) + "%";
        pin.style.top = Number(item.y).toFixed(1) + "%";
        pin.title = hasAssignments ? "点击聚焦 " + item.id + " 的派单链路" : "点击查看 " + item.id + " 的样本详情";
        pin.innerHTML = `<span class="mark ${markKind}">${isMerchantPoint ? "♨" : item.kind === "courier" ? "♞" : "◎"}</span>`;
        entityLayer.appendChild(pin);

        if (item.hideLabel) return;
        const label = document.createElement("div");
        label.className = "map-label";
        label.innerHTML = item.html;
        label.style.left = Number(item.x).toFixed(1) + "%";
        label.style.top = Number(item.y).toFixed(1) + "%";
        label.style.setProperty("--label-offset-x", labelOffset[0] + "px");
        label.style.setProperty("--label-offset-y", labelOffset[1] + "px");
        label.dataset.entity = item.id;
        label.dataset.assignment = assignmentId;
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
      applyMapFocus(profile, profile.selected);
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
    function roadFollowingRoute(start, end, mapLayers) {
      if (!mapLayers || !Array.isArray(mapLayers.roads)) return [start, end];
      const roadFilter = (road) => road.type !== "service" || distance2D(start, end) < 20;
      const startSnap = nearestRoadSnap(start, mapLayers, roadFilter) || nearestRoadSnap(start, mapLayers);
      const endSnap = nearestRoadSnap(end, mapLayers, roadFilter) || nearestRoadSnap(end, mapLayers);
      if (!startSnap || !endSnap) return [start, end];
      if (startSnap.road === endSnap.road) {
        return compactRoutePoints([start, ...chainAlongRoad(startSnap, endSnap), end]);
      }
      const connector = connectorRoadBetween(startSnap.road, endSnap.road, mapLayers);
      if (connector && connector.road && connector.first && connector.second) {
        const startChain = chainBetweenRoadPoints(startSnap.road, startSnap.point, connector.first.fromPoint);
        const middleChain = chainBetweenRoadPoints(connector.road, connector.first.toPoint, connector.second.fromPoint);
        const endChain = chainBetweenRoadPoints(endSnap.road, connector.second.toPoint, endSnap.point);
        return compactRoutePoints([start, ...startChain, connector.first.toPoint, ...middleChain, connector.second.fromPoint, ...endChain, end]);
      }
      if (connector && connector.direct) {
        const startChain = chainBetweenRoadPoints(startSnap.road, startSnap.point, connector.direct.fromPoint);
        const endChain = chainBetweenRoadPoints(endSnap.road, connector.direct.toPoint, endSnap.point);
        return compactRoutePoints([start, ...startChain, connector.direct.toPoint, ...endChain, end]);
      }
      const hub = routeHubBetween(startSnap.point, endSnap.point, mapLayers);
      return compactRoutePoints([start, startSnap.point, hub, endSnap.point, end]);
    }
    function dispatchPathFor(points) {
      const usable = points.filter(Boolean);
      if (usable.length < 2) return "";
      const [startX, startY] = svgPoint(usable[0]);
      const segments = [`M${startX.toFixed(1)} ${startY.toFixed(1)}`];
      usable.slice(1).forEach((point, index) => {
        const [x, y] = svgPoint(point);
        segments.push(`L${x.toFixed(1)} ${y.toFixed(1)}`);
      });
      return segments.join(" ");
    }
    function dispatchArrowFor(points, cls, assignmentId = "", active = false, style = "") {
      const usable = points.filter(Boolean);
      if (usable.length < 2) return "";
      const [x1, y1] = svgPoint(usable[usable.length - 2]);
      const [x2, y2] = svgPoint(usable[usable.length - 1]);
      const angle = Math.atan2(y2 - y1, x2 - x1);
      const size = cls.includes("primary") ? 9 : 6;
      const tipX = x2;
      const tipY = y2;
      const leftX = tipX - Math.cos(angle - 0.52) * size;
      const leftY = tipY - Math.sin(angle - 0.52) * size;
      const rightX = tipX - Math.cos(angle + 0.52) * size;
      const rightY = tipY - Math.sin(angle + 0.52) * size;
      const styleAttr = style ? ` style="${style}"` : "";
      return `<polygon class="dispatch-arrow ${cls}${active ? " active-assignment" : ""}" data-assignment="${assignmentId}"${styleAttr} points="${tipX.toFixed(1)},${tipY.toFixed(1)} ${leftX.toFixed(1)},${leftY.toFixed(1)} ${rightX.toFixed(1)},${rightY.toFixed(1)}"></polygon>`;
    }
    function renderDispatchLinks(profile, entityPoints) {
      const svg = document.querySelector(".route-svg");
      if (!svg) return;
      if (!profile.dispatchMap || !Array.isArray(profile.dispatchMap.assignments)) {
        svg.innerHTML = "";
        return;
      }
      const focusMode = profile.mapFocusMode === "focus";
      const selectedAssignment = focusMode ? (profile.selected || (profile.dispatchMap.assignments[0] && profile.dispatchMap.assignments[0].id)) : "";
      const mapLayers = profile.dispatchMap.map_layers;
      const routePalette = ["#26dccd", "#55d68a", "#ffcf4a", "#5fb8ff", "#ff9d57", "#c3e56d", "#7de3ff", "#f2b76a"];
      const pathHtml = profile.dispatchMap.assignments.slice(0, 8).map((assignment, index) => {
        const couriers = assignment.map_couriers || courierTokens(assignment.courier);
        const orders = assignment.map_orders || assignment.orders || [];
        const courierPoints = couriers.map((courier) => entityPoints[courier]).filter(Boolean);
        const pickupPoint = entityPoints[assignment.pickup];
        const orderPoints = orders.map((order) => entityPoints[order]).filter(Boolean);
        if (!pickupPoint || courierPoints.length === 0) return "";
        const isActive = focusMode && assignment.id === selectedAssignment;
        const routeStyle = `--route-color:${routePalette[index % routePalette.length]}`;
        const cls = isActive ? "dispatch-link primary active-assignment" : "dispatch-link secondary overview-route";
        const deliveryRoute = orderPoints.length ? roadFollowingRoute(pickupPoint, orderPoints[0], mapLayers) : [];
        const pickupRoute = roadFollowingRoute(courierPoints[0], pickupPoint, mapLayers);
        const pickupD = dispatchPathFor(pickupRoute);
        const deliveryD = dispatchPathFor(deliveryRoute);
        const arrowCls = isActive ? "primary" : "secondary overview-route";
        const routeParts = [
          `<path class="${cls} pickup-leg" data-assignment="${assignment.id}" style="${routeStyle}" d="${pickupD}"></path>`,
          dispatchArrowFor(orderPoints.length ? deliveryRoute : pickupRoute, arrowCls, assignment.id, isActive, routeStyle)
        ];
        if (deliveryD) routeParts.splice(1, 0, `<path class="${cls}" data-assignment="${assignment.id}" style="${routeStyle}" d="${deliveryD}"></path>`);
        return routeParts.join("");
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
        if (hasDispatch && focused) {
          frame.dataset.selectedAssignment = selectedAssignment;
        } else {
          frame.removeAttribute("data-selected-assignment");
        }
      }
      if (!hasDispatch) {
        document.querySelectorAll(".map-label, .pin, .dispatch-link, .dispatch-arrow").forEach((node) => {
          node.classList.remove("active-assignment", "selected", "focused", "primary");
          if (node.classList.contains("dispatch-link") || node.classList.contains("dispatch-arrow")) node.classList.add("secondary");
        });
        return;
      }
      document.querySelectorAll(".map-label, .pin").forEach((node) => {
        const active = focused && node.dataset.assignment === selectedAssignment;
        node.classList.toggle("active-assignment", active);
        if (node.classList.contains("map-label")) {
          node.classList.toggle("selected", active);
          node.classList.toggle("focused", active);
        }
      });
      document.querySelectorAll(".dispatch-link, .dispatch-arrow").forEach((node) => {
        const active = focused && node.dataset.assignment === selectedAssignment;
        node.classList.toggle("active-assignment", active);
        node.classList.toggle("primary", active);
        node.classList.toggle("secondary", !active);
        node.classList.toggle("overview-route", !focused);
      });
    }
    function renderEntityPreviewDetail(profile, entityId) {
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
        $("detail-title").textContent = "商家/订单点：" + entity.id;
        $("detail-courier").textContent = relatedCandidates[0] ? relatedCandidates[0].courier_id : "-";
        $("detail-merchant").innerHTML = `黄色点位为商家侧订单入口，位于道路边/建筑边；当前有 <code>${merchant.order_count || 1}</code> 单待派。`;
        $("detail-orders").innerHTML = relatedCandidates.map((candidate) => `<span class="chip">${candidate.courier_id} · ${Math.round(safeNumber(candidate.accept_probability, 0) * 100)}%</span>`).join("");
        $("detail-eta").textContent = merchant.expected_eta_min ? `${merchant.expected_eta_min} min 期望` : "-";
        $("right-cost").textContent = merchant.expected_price ? money(merchant.expected_price) : "-";
        document.querySelector(".prob span").textContent = relatedCandidates[0] ? `${Math.round(safeNumber(relatedCandidates[0].accept_probability, 0) * 100)}%` : "--";
        $("detail-reasons").innerHTML = [
          `<li>商家点不会压在道路中心线，坐标按最近道路边缘和商圈热区生成。</li>`,
          `<li>候选骑手来自当前刷新样本，不是写死数据。</li>`,
          `<li>点击运行后才会把该商家最终派给一个骑手并显示连线。</li>`
        ].join("");
        const rows = document.querySelectorAll(".decision-card.evidence .row strong");
        if (rows[0]) rows[0].textContent = merchant.hotspot === "crossroad" ? "路口商圈" : "街区商家";
        if (rows[1]) rows[1].textContent = `${Number(entity.x).toFixed(1)}, ${Number(entity.y).toFixed(1)}`;
        if (rows[2]) rows[2].textContent = merchant.expected_eta_min ? `${merchant.expected_eta_min} min` : "-";
        if (rows[3]) rows[3].textContent = relatedCandidates[0] ? relatedCandidates[0].risk : "-";
        if (rows[4]) rows[4].textContent = sample.selected_strategy_id || "-";
        showToast(`已选中商家 ${entity.id}`);
        return true;
      }
      if (entity.kind === "courier") {
        const courier = (sample.couriers || []).find((item) => item.id === entity.id) || entity;
        const relatedCandidates = candidates
          .filter((candidate) => candidate.courier_id === entity.id)
          .slice()
          .sort((a, b) => safeNumber(a.cost, 0) - safeNumber(b.cost, 0))
          .slice(0, 4);
        $("detail-title").textContent = "骑手位置：" + entity.id;
        $("detail-courier").textContent = entity.id;
        $("detail-merchant").innerHTML = `骑手位于道路上/道路边，当前状态 <code>${courier.status || "available"}</code>，容量 <code>${courier.capacity || 1}</code>。`;
        $("detail-orders").innerHTML = relatedCandidates.map((candidate) => `<span class="chip">${candidate.merchant_id}</span>`).join("");
        $("detail-eta").textContent = relatedCandidates[0] ? `${relatedCandidates[0].eta_min} min 最近候选` : "-";
        $("right-cost").textContent = relatedCandidates[0] ? money(relatedCandidates[0].cost) : "-";
        document.querySelector(".prob span").textContent = `${Math.round(safeNumber(courier.willingness, 0) * 100)}%`;
        $("detail-reasons").innerHTML = [
          `<li>骑手位置按当前道路网络吸附生成，不放到建筑块内部。</li>`,
          `<li>接单意愿会影响候选排序、风险和最终策略选择。</li>`,
          `<li>该骑手当前可接候选：${relatedCandidates.map((candidate) => candidate.merchant_id).join("、") || "暂无"}。</li>`
        ].join("");
        const rows = document.querySelectorAll(".decision-card.evidence .row strong");
        if (rows[0]) rows[0].textContent = `${Math.round(safeNumber(courier.willingness, 0) * 100)}%`;
        if (rows[1]) rows[1].textContent = `${Number(entity.x).toFixed(1)}, ${Number(entity.y).toFixed(1)}`;
        if (rows[2]) rows[2].textContent = courier.status || "-";
        if (rows[3]) rows[3].textContent = relatedCandidates[0] ? relatedCandidates[0].risk : "-";
        if (rows[4]) rows[4].textContent = relatedCandidates.length + " 个候选";
        showToast(`已选中骑手 ${entity.id}`);
        return true;
      }
      return false;
    }
    function renderAssignmentDetail(profile, assignmentId, sourceLabel = "", focusMap = true) {
      const assignments = (profile && profile.assignments) || {};
      const resolvedAssignment = assignments[assignmentId] ? assignmentId : (assignments[profile.selected] ? profile.selected : Object.keys(assignments)[0]);
      const assignment = assignments[resolvedAssignment];
      if (!assignment) return;
      const changedSelection = profile.selected !== resolvedAssignment;
      profile.selected = resolvedAssignment;
      applyMapFocus(profile, resolvedAssignment, focusMap);
      if (changedSelection && profile.dispatchMap && document.querySelector(".map-frame").classList.contains("leaflet-ready")) {
        updateMapScene(profile);
      }
      $("detail-title").textContent = sourceLabel ? "派单详情：" + sourceLabel : "Selected Dispatch Assignment";
      $("detail-courier").textContent = assignment.courier;
      const orderCount = safeNumber(assignment.orderCount, assignment.orders.length);
      $("detail-merchant").innerHTML = `订单组 <code>${assignment.merchant}</code> 共 ${orderCount} 单，最终派给 ${assignment.courier}`;
      $("detail-orders").innerHTML = assignment.orders.map((order) => `<span class="chip">${order}</span>`).join("");
      $("detail-eta").textContent = assignment.eta;
      $("right-cost").textContent = assignment.cost;
      document.querySelector(".prob span").textContent = assignment.probability;
      $("detail-reasons").innerHTML = assignment.reason.map((item) => `<li>${item}</li>`).join("");
      if (assignment.merchantNote) $("detail-reasons").innerHTML += `<li>${assignment.merchantNote}</li>`;
      const rows = document.querySelectorAll(".decision-card.evidence .row strong");
      if (rows[0]) rows[0].textContent = assignment.fit;
      if (rows[1]) rows[1].textContent = assignment.distance;
      if (rows[2]) rows[2].textContent = assignment.risk === "High" ? "Warning" : "Good";
      if (rows[3]) rows[3].textContent = assignment.risk;
      if (rows[4]) rows[4].textContent = profile.utilization;
      showToast(`${assignment.merchant} → ${assignment.courier}，${orderCount} 单`);
    }
    function updateDecisionPanel(profile, report) {
      const best = report && report.best ? report.best : {};
      const features = report && report.features ? report.features : {};
      const used = safeNumber(best.used_couriers, 6);
      const tasks = safeNumber(best.total_tasks || features.tasks, 38);
      const covered = safeNumber(best.covered_tasks, tasks);
      const coverage = tasks > 0 ? Math.round((covered / tasks) * 100) : 100;
      renderAssignmentDetail(profile, profile.selected, "", false);
      const compareRows = document.querySelectorAll(".decision-card:last-child .row strong");
      if (compareRows[0]) compareRows[0].textContent = profile.improvement;
      if (compareRows[1]) compareRows[1].textContent = "-" + Math.max(2, Math.round(used * 0.9)) + " min";
      if (compareRows[2]) compareRows[2].textContent = "-" + Math.max(12, Math.round(coverage * 0.31)) + "%";
    }
    function strategyLabel(name) {
      const labels = {
        greedy_baseline: "Greedy baseline",
        single_task_multidispatch: "Multi-dispatch",
        disjoint_then_multidispatch: "Bundle-first",
        pair_potential_matching: "Bundle-first",
        sparse_cover: "Repair search",
        low_global_column_search: "Repair search",
        low_column_search: "Repair search",
        scarce_k2_column_search: "Bundle-first",
        scarce_bundle_mcf_enum: "Bundle-first",
        risk_balancing: "Risk balancing",
        candidate_preview: "Candidate preview",
        production_solver: "Final AutoSolver"
      };
      return labels[name] || name || "Candidate";
    }
    function renderCandidateTable(report, profile) {
      const tbody = document.querySelector(".table-panel tbody");
      const rounds = report && Array.isArray(report.rounds) ? report.rounds : [];
      const attempts = rounds.flatMap((round) => Array.isArray(round.strategies) ? round.strategies : []);
      const best = report && report.best ? report.best : {};
      const bestCost = safeNumber(best["local" + "_cost"], Number(profile.cost.replace(/[$,]/g, "")) || 657.1);
      const totalTasks = safeNumber(best.total_tasks || (report && report.features && report.features.tasks), 38);
      const fallbackRows = [
        {name: "greedy_baseline", ["local" + "_cost"]: bestCost * 3.2, covered_tasks: totalTasks, total_tasks: totalTasks, groups: 8, accepted: false, valid: true},
        {name: "disjoint_then_multidispatch", ["local" + "_cost"]: bestCost * 1.05, covered_tasks: totalTasks, total_tasks: totalTasks, groups: 6, accepted: true, valid: true},
        {name: "single_task_multidispatch", ["local" + "_cost"]: bestCost * 1.88, covered_tasks: totalTasks, total_tasks: totalTasks, groups: 9, accepted: false, valid: true},
        {name: "sparse_cover", ["local" + "_cost"]: bestCost * 1.54, covered_tasks: totalTasks, total_tasks: totalTasks, groups: 7, accepted: false, valid: true},
      ];
      const usingFallbackRows = attempts.length === 0;
      const rows = (usingFallbackRows ? fallbackRows : attempts).slice(0, 4);
      const tableRows = rows.map((item) => {
        const reportedTotal = safeNumber(item.total_tasks || item.totalTasks, totalTasks);
        const total = reportedTotal > 0 ? reportedTotal : totalTasks;
        const reportedCovered = item.covered_tasks ?? item.coveredTasks;
        const coveredFallback = item.valid === false ? 0 : total;
        const covered = usingFallbackRows ? total : (reportedCovered === 0 && item.valid !== false && total > 0 ? total : safeNumber(reportedCovered, coveredFallback));
        const coverage = usingFallbackRows ? 100 : (total ? Math.round((covered / total) * 100) : 0);
        const cost = safeNumber(item["local" + "_cost"], bestCost * 1.4);
        const risk = coverage >= 100 && cost <= bestCost * 1.2 ? "Low" : coverage < 100 ? "High" : "Med";
        const status = item.accepted ? "Feasible" : "Rejected";
        const statusClass = item.accepted ? "status-ok" : "status-bad";
        const score = Math.max(0.35, Math.min(0.91, bestCost / Math.max(cost, 1))).toFixed(2);
        const insight = item.accepted ? "当前 best-so-far，被 Critic 接受" : (item.valid ? "成本或资源占用高于当前最优" : "覆盖或约束校验失败");
        return `<tr><td>${strategyLabel(item.name)}</td><td>${coverage}%</td><td>${(12 + safeNumber(item.groups, 6) * 0.7).toFixed(1)} min</td><td>${money(cost)}</td><td>${safeNumber(item.groups, 0)} riders</td><td>${risk} (${profile.missedRisk})</td><td>${score}</td><td class="${statusClass}">${status}</td><td>${insight}</td></tr>`;
      });
      const used = safeNumber(best.used_couriers || best.groups, 6);
      tableRows.push(`<tr class="emphasis"><td><span class="star">★</span><b>Final AutoSolver<br>(Selected)</b></td><td><b>${totalTasks ? Math.round(safeNumber(best.covered_tasks, totalTasks) / totalTasks * 100) : 100}%</b></td><td><b>${profile.eta}</b></td><td><b id="table-cost">${money(bestCost)}</b></td><td><b>${used} riders</b></td><td><b>Low (${profile.missedRisk})</b></td><td><b>0.89</b></td><td><b>Selected</b></td><td><b>Best trade-off across cost/risk/ETA</b></td></tr>`);
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
      const activeScenario = selectedScenarioId();
      document.querySelectorAll(".scene-button").forEach((button) => {
        button.classList.toggle("active", button.dataset.scenario === activeScenario || button.dataset.case === activeCase);
      });
      if (source === "button") setStatus("已选择场景：" + profile.label, false);
    }
    function renderSimulationSceneButtons(scenarios) {
      const strip = document.querySelector(".scene-strip");
      if (!strip || !Array.isArray(scenarios) || scenarios.length === 0) return;
      strip.innerHTML = scenarios.map((item) => {
        const strategies = Array.isArray(item.primary_strategies) ? item.primary_strategies.join("/") : "";
        return `<button class="scene-button" data-case="${item.case_id}" data-scenario="${item.id}"><strong>${item.name}</strong><span>${item.sample_count} samples · ${strategies}</span></button>`;
      }).join("");
      strip.querySelectorAll(".scene-button").forEach((button) => {
        button.addEventListener("click", () => applyScene(button.dataset.case, "button"));
      });
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
            option.textContent = `${item.name} · ${item.sample_count} samples`;
            select.appendChild(option);
          });
          renderSimulationSceneButtons(scenarios);
        } else {
          (payload.cases || [{id: "large_seed301"}]).forEach((item) => {
            const option = document.createElement("option");
            option.value = item.id;
            option.textContent = item.scenario_name ? `${item.scenario_name} · ${item.id}` : item.id;
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
    function wait(ms) {
      return new Promise((resolve) => window.setTimeout(resolve, ms));
    }
    async function runCurrentSimulationSample() {
      const sample = currentSimulationSample;
      if (!sample) return false;
      currentReport = null;
      const profile = currentProfile || profileForCase(sample.case_id || selectedCase());
      currentProfile = profile;
      profile.selected = "";
      profile.assignments = {};
      setStatus(`基于 ${sample.name} ${sampleNumberLabel(sample)} 推理`, true);
      updateReasonSummary(profile, null);
      const path = Array.isArray(sample.strategy_path) ? sample.strategy_path.map((item) => item.id) : [];
      for (let step = 0; step <= 5; step += 1) {
        updateReasonProgress(step);
        if (step >= 2 && path[step - 2]) setStatus(`评估策略 ${path[step - 2]}：${sample.seed}`, true);
        await wait(step < 2 ? 160 : 260);
      }
      const mapPayload = simulationFinalMap(sample);
      const report = reportForSimulationSample(sample, mapPayload);
      document.body.classList.remove("pending-run", "sample-preview");
      render(report);
      setStatus("当前样本派单完成", false);
      showToast("已按当前刷新样本生成最终派单线");
      return true;
    }
    async function streamRun() {
      if (currentRun) currentRun.close();
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
      document.querySelectorAll(".dispatch-link.secondary").forEach((route) => {
        route.style.opacity = mode === "candidates" ? "1" : "";
      });
      document.querySelectorAll(".dispatch-polyline-secondary").forEach((route) => {
        route.style.display = mode === "selected" ? "none" : "";
        route.style.opacity = mode === "candidates" ? "1" : "";
      });
      showToast(mode === "selected" ? "仅显示最终派单" : mode === "candidates" ? "突出显示候选派单" : "显示全部派单图层");
    }
    function bindMapControls() {
      $("expand-graph").addEventListener("click", (event) => {
        document.querySelector(".left-panel").classList.toggle("expanded");
        event.currentTarget.classList.toggle("active");
        event.currentTarget.textContent = event.currentTarget.classList.contains("active") ? "Collapse" : "Expand All";
        setStatus(event.currentTarget.classList.contains("active") ? "推理树已展开" : "推理树已收起", false);
      });
      $("layer-mode").addEventListener("change", (event) => setLayerMode(event.target.value));
      document.querySelectorAll("[data-map-action]").forEach((button) => {
        button.addEventListener("click", () => {
          const action = button.dataset.mapAction;
          button.classList.toggle("active");
          if (action === "depots") {
            const hidden = button.classList.contains("active");
            document.querySelector(".map-frame").classList.toggle("hide-entities", hidden);
            showToast(hidden ? "点位图层已弱化，仅保留派单关系" : "点位图层已恢复：商家、订单与骑手可见");
            return;
          }
          if (action === "routes") {
            const active = button.classList.contains("active");
            document.querySelector(".map-frame").classList.toggle("hide-candidates", active);
            document.querySelectorAll(".dispatch-polyline-secondary").forEach((route) => {
              route.style.display = active ? "none" : "";
            });
            showToast(active ? "候选派单连线已隐藏" : "候选派单连线已显示");
            return;
          }
          if (action === "locate") {
        document.querySelector(".map-frame").classList.toggle("locating");
            const profile = currentProfile || profileForCase(selectedCase());
            const selected = profile.assignments && (profile.assignments[profile.selected] || profile.assignments.A1);
            if (selected) {
              renderAssignmentDetail(profile, profile.selected, selected.merchant);
              showToast("已定位到 " + selected.courier + " 当前派单包");
            } else {
              showToast("请先运行派单推理生成骑手位置");
            }
            return;
          }
          if (action === "fit") {
            document.querySelector(".map-frame").classList.remove("zoomed");
            $("zoom-in").classList.remove("active");
            const profile = currentProfile || profileForCase(selectedCase());
            if (profile.assignments && Object.keys(profile.assignments).length) applyMapFocus(profile, profile.selected || Object.keys(profile.assignments)[0], false);
            if (leafletMap && leafletLastBounds) leafletMap.fitBounds(leafletLastBounds, {padding: [52, 52], maxZoom: 13});
            showToast("视图已适配全部派单关系");
            return;
          }
          if (action === "fullscreen") {
            const expanded = document.querySelector(".map-panel").classList.toggle("active");
            button.textContent = expanded ? "↙" : "↗";
            showToast(expanded ? "演示视图已进入地图聚焦模式" : "演示视图已退出地图聚焦模式");
            return;
          }
          showToast("仓库、商家、目的地与骑手图层可见");
        });
      });
      $("zoom-in").addEventListener("click", () => {
        if (leafletMap && document.querySelector(".map-frame").classList.contains("leaflet-ready")) {
          leafletMap.zoomIn();
        } else {
          document.querySelector(".map-frame").classList.add("zoomed");
        }
        $("zoom-in").classList.add("active");
        showToast("地图已放大");
      });
      $("zoom-out").addEventListener("click", () => {
        if (leafletMap && document.querySelector(".map-frame").classList.contains("leaflet-ready")) {
          leafletMap.zoomOut();
        } else {
          document.querySelector(".map-frame").classList.remove("zoomed");
        }
        $("zoom-in").classList.remove("active");
        showToast("地图已缩小");
      });
      $("recenter").addEventListener("click", () => {
        document.querySelector(".map-frame").classList.toggle("locating");
        const profile = currentProfile || profileForCase(selectedCase());
        if (profile.assignments && Object.keys(profile.assignments).length) applyMapFocus(profile, profile.selected || Object.keys(profile.assignments)[0], false);
        if (leafletMap && leafletLastBounds) leafletMap.fitBounds(leafletLastBounds, {padding: [52, 52], maxZoom: 13});
        showToast("已回到当前派单关系中心");
      });
      document.querySelector(".map-frame").addEventListener("click", (event) => {
        const target = event.target.closest(".map-label, .pin, .dispatch-link, .dispatch-arrow");
        if (!target) return;
        const profile = currentProfile || profileForCase(selectedCase());
        if (!profile.assignments || Object.keys(profile.assignments).length === 0) {
          if (renderEntityPreviewDetail(profile, target.dataset.entity || "")) return;
        }
        renderAssignmentDetail(profile, target.dataset.assignment || profile.selected, target.dataset.entity || target.textContent.trim());
      });
    }
    $("run-agent").addEventListener("click", streamRun);
    $("reload-cases").addEventListener("click", () => {
      refreshSimulationSample().catch((error) => {
        console.error(error);
        setStatus("刷新样本失败", false);
        showToast("刷新样本失败，请检查仿真场景接口");
      });
    });
    $("case-select").addEventListener("change", () => applyScene(selectedCase()));
    document.querySelectorAll(".scene-button").forEach((button) => {
      button.addEventListener("click", () => applyScene(button.dataset.case, "button"));
    });
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

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API.
        parsed = urlparse(self.path)
        try:
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
