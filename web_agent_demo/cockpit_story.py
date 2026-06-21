"""
cockpit_story.py
================
即时履约智能调度指挥舱 · 故事/Payload 合成层 (iteration-1)

把 run_blind_solve 的真实 report + cockpit_baseline 的真值，映射成单页指挥舱
前端要消费的 payload；并做**确定性位置合成**（seed=20260620）：
  - 任务按候选「共现」聚成 6–8 个商圈中心；
  - 骑手放在它高意愿候选任务的质心附近，抖动避重叠；
  - 坐标只进可视化、绝不进任何指标计算（方案 §2.3 铁律）。

诚实边界（方案 §7）：
  - 真实字段（派单/意愿/分数/成本/感知/覆盖/证书）：is_demo=False。
  - 演示合成层（坐标/距离/ETA/天气/金额/商圈名/风险色）：is_demo=True，UI 挂
    "演示·seed20260620" 角标。
  - 本模块不宣称 706 泛化 / 自进化提分；gap 只用 r1（直接透传 report.certificate）。

本模块只读、不改任何后端。
"""
from __future__ import annotations

import hashlib
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.agent_trace_demo import parse_candidates

SEED = 20260620
DEMO_TAG = "演示·seed20260620"

# 画布逻辑坐标系（前端 SVG viewBox 0..1000 x 0..640）
CANVAS_W = 1000
CANVAS_H = 640


# --------------------------------------------------------------------------- #
# 确定性哈希工具                                                              #
# --------------------------------------------------------------------------- #
def _h(*parts: Any) -> int:
    raw = (str(SEED) + "|" + "|".join(str(p) for p in parts)).encode("utf-8")
    return int(hashlib.sha1(raw).hexdigest(), 16)


def _hf(*parts: Any) -> float:
    """0..1 确定性浮点。"""
    return (_h(*parts) % 1_000_000) / 1_000_000.0


# --------------------------------------------------------------------------- #
# 1. 商圈聚类（任务共现）                                                      #
# --------------------------------------------------------------------------- #
def _cluster_tasks(candidates, all_tasks, n_clusters: int = 7) -> dict[str, int]:
    """把任务确定性聚成 n_clusters 个商圈簇。

    用「共现」信号：两个任务越常出现在同一候选行（合单），越靠近。large_seed301
    有 30,580 合单行，共现极丰富。这里用简易确定性方法：
      1) 统计每个任务的共现计数向量；
      2) 选 n_clusters 个种子任务（按共现度最高且互相共现最少，确定性挑选）；
      3) 每个任务并入与它共现最多的种子簇。
    """
    tasks = sorted(all_tasks)
    if not tasks:
        return {}
    n_clusters = max(1, min(n_clusters, len(tasks)))

    cooc: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    deg: dict[str, int] = defaultdict(int)
    for row in candidates:
        tids = row[1]
        if len(tids) < 2:
            continue
        for i in range(len(tids)):
            for j in range(i + 1, len(tids)):
                a, b = tids[i], tids[j]
                cooc[a][b] += 1
                cooc[b][a] += 1
                deg[a] += 1
                deg[b] += 1

    # 种子：按共现度降序确定性取，且与已选种子共现弱者优先（贪心 farthest-ish）。
    by_deg = sorted(tasks, key=lambda t: (-deg.get(t, 0), t))
    seeds: list[str] = []
    for t in by_deg:
        if len(seeds) >= n_clusters:
            break
        # 与已有种子共现总和（越小越独立）
        overlap = sum(cooc[t].get(s, 0) for s in seeds)
        # 第一个直接取；之后若与已有种子共现过强则跳过一次（确定性放宽）
        if not seeds or overlap <= max(1, deg.get(t, 0) // 3):
            seeds.append(t)
    # 补齐种子
    for t in by_deg:
        if len(seeds) >= n_clusters:
            break
        if t not in seeds:
            seeds.append(t)

    assign: dict[str, int] = {}
    for t in tasks:
        if t in seeds:
            assign[t] = seeds.index(t)
            continue
        # 并入共现最多的种子；并列用确定性 hash 打破
        best_idx, best_val = 0, -1
        for idx, s in enumerate(seeds):
            v = cooc[t].get(s, 0)
            tiebreak = v * 1000 + (_h(t, s) % 1000)
            if tiebreak > best_val:
                best_val = tiebreak
                best_idx = idx
        assign[t] = best_idx
    return assign


def _cluster_centers(n_clusters: int) -> list[tuple[float, float]]:
    """商圈中心确定性散布在画布上（环形 + 抖动，避免贴边）。

    iter-3(P0-2)：把簇心拉得更开（占满画面宽度、簇间留白更明显），让每个商圈成为
    一个**紧致独立的簇**（配合下方更小的 jitter 半径），贴近目标稿「一簇一商圈」观感。
    """
    centers = []
    cx, cy = CANVAS_W / 2, CANVAS_H * 0.50
    # 用更大的椭圆半径占满画布（x 拉宽到 0.40，y 压扁到 0.30 留出上下空隙）
    rad_x = CANVAS_W * 0.40
    rad_y = CANVAS_H * 0.36
    for k in range(n_clusters):
        ang = 2 * math.pi * k / max(1, n_clusters) + _hf("center-ang", k) * 0.45
        rr = 0.78 + 0.22 * _hf("center-r", k)
        x = cx + rad_x * rr * math.cos(ang) + (_hf("cx", k) - 0.5) * 36
        y = cy + rad_y * rr * math.sin(ang) + (_hf("cy", k) - 0.5) * 30
        # 收进安全框，避免簇心贴边导致节点溢出
        x = max(120, min(CANVAS_W - 120, x))
        y = max(110, min(CANVAS_H - 90, y))
        centers.append((round(x, 1), round(y, 1)))
    return centers


def _jitter_point(cx: float, cy: float, key: str, radius: float = 38.0) -> tuple[float, float]:
    """簇内抖动：iter-3 收紧半径（默认 38），让簇内节点更靠拢成「一坨」。"""
    ang = _hf("ja", key) * 2 * math.pi
    # 平方根分布让点更均匀地铺在圆盘内（避免全挤在圆心或全在外环）
    r = radius * math.sqrt(0.18 + 0.82 * _hf("jr", key))
    x = max(24, min(CANVAS_W - 24, cx + r * math.cos(ang)))
    y = max(24, min(CANVAS_H - 24, cy + r * math.sin(ang)))
    return round(x, 1), round(y, 1)


# --------------------------------------------------------------------------- #
# 2. 合成地图布局                                                              #
# --------------------------------------------------------------------------- #
_DISTRICT_NAMES = [
    "中关村商圈", "国贸 CBD", "望京科技园", "三里屯", "西二旗", "金融街",
    "五道口", "亦庄开发区",
]


def synth_layout(text: str, report: dict[str, Any]) -> dict[str, Any]:
    """合成地图布局：商圈/任务/骑手坐标 + 连线（候选虚线 vs 采纳实线）+ 合单圈。

    全部 is_demo=True（坐标演示）；连线的「采纳」关系来自真实 solution。
    """
    candidates, all_tasks = parse_candidates(text)
    perc = report.get("perception", {})
    tasks_sorted = sorted(all_tasks)
    n_tasks = len(tasks_sorted)

    # 候选元数据索引：每个 (task_key,courier) 行的 willingness/score
    row_meta: dict[tuple[str, str], tuple[float, float]] = {}
    courier_best: dict[str, list[tuple[float, str]]] = defaultdict(list)
    for row in candidates:
        task_key, tids, cid, score, will, _idx = row
        row_meta[(task_key, cid)] = (will, score)
        # 骑手对单任务的意愿（用于放置质心）
        for t in tids:
            courier_best[cid].append((will, t))

    n_clusters = max(6, min(8, max(1, round(n_tasks / 6))))
    if n_tasks <= 8:
        n_clusters = max(1, min(n_tasks, 4))
    assign = _cluster_tasks(candidates, all_tasks, n_clusters)
    centers = _cluster_centers(n_clusters)

    # 任务点
    task_nodes: dict[str, dict[str, Any]] = {}
    # 每个任务的代表 willingness（取该任务所有候选 will 的中位 ~ 决定红/黄风险）
    task_will: dict[str, list[float]] = defaultdict(list)
    for row in candidates:
        for t in row[1]:
            task_will[t].append(row[4])
    for t in tasks_sorted:
        cl = assign.get(t, 0)
        cx, cy = centers[cl] if cl < len(centers) else centers[0]
        x, y = _jitter_point(cx, cy, "task-" + t, radius=42)
        ws = task_will.get(t, [0.4])
        w_med = sorted(ws)[len(ws) // 2]
        risk = "high" if w_med < 0.3 else ("mid" if w_med < 0.55 else "low")
        task_nodes[t] = {
            "id": t, "x": x, "y": y, "cluster": cl,
            "willingness_repr": round(w_med, 3),   # 真值派生
            "risk": risk,                           # 真值派生(意愿)
        }

    # 商圈节点
    district_nodes = []
    for k in range(n_clusters):
        cx, cy = centers[k]
        members = [t for t in tasks_sorted if assign.get(t) == k]
        district_nodes.append({
            "id": f"D{k+1:02d}",
            "name": _DISTRICT_NAMES[k % len(_DISTRICT_NAMES)],  # 演示
            "x": round(cx, 1), "y": round(cy, 1),
            "tasks": members,
        })

    # 采纳解：task_key -> couriers
    solution = report.get("solution") or []
    sol_map: dict[str, list[str]] = {}
    for task_key, couriers in solution:
        sol_map[task_key] = list(couriers)

    used_couriers = set()
    for cs in sol_map.values():
        used_couriers.update(cs)

    # 骑手点：放在「它已被采纳服务的任务质心」附近；未被采纳的骑手放高意愿候选质心
    courier_nodes: dict[str, dict[str, Any]] = {}

    # 先算每个采纳骑手服务的任务集合
    courier_tasks: dict[str, set[str]] = defaultdict(set)
    for task_key, couriers in solution:
        # task_key 可能是 "T0001,T0002"
        tids = [x for x in task_key.split(",") if x]
        for c in couriers:
            courier_tasks[c].update(tids)

    def _courier_centroid(cid: str) -> tuple[float, float]:
        tset = courier_tasks.get(cid)
        if tset:
            pts = [(task_nodes[t]["x"], task_nodes[t]["y"]) for t in tset if t in task_nodes]
        else:
            # 高意愿候选任务质心
            best = sorted(courier_best.get(cid, []), reverse=True)[:3]
            pts = [(task_nodes[t]["x"], task_nodes[t]["y"]) for _w, t in best if t in task_nodes]
        if not pts:
            return CANVAS_W / 2, CANVAS_H / 2
        mx = sum(p[0] for p in pts) / len(pts)
        my = sum(p[1] for p in pts) / len(pts)
        return mx, my

    all_courier_ids = sorted({row[2] for row in candidates})
    for cid in all_courier_ids:
        mx, my = _courier_centroid(cid)
        x, y = _jitter_point(mx, my, "courier-" + cid, radius=30)
        courier_nodes[cid] = {
            "id": cid, "x": x, "y": y,
            "active": cid in used_couriers,   # 真值（是否被采纳）
        }

    # 连线：采纳=实线（真）；候选虚线=每个任务取若干高意愿候选行（演示采样，标注）
    accepted_edges = []
    for task_key, couriers in solution:
        tids = [x for x in task_key.split(",") if x]
        # 边的锚点 = 该组任务质心
        if tids:
            ax = sum(task_nodes[t]["x"] for t in tids if t in task_nodes) / max(1, len([t for t in tids if t in task_nodes]))
            ay = sum(task_nodes[t]["y"] for t in tids if t in task_nodes) / max(1, len([t for t in tids if t in task_nodes]))
        else:
            ax, ay = CANVAS_W / 2, CANVAS_H / 2
        for c in couriers:
            cn = courier_nodes.get(c)
            if not cn:
                continue
            will, score = row_meta.get((task_key, c), (None, None))
            accepted_edges.append({
                "task_key": task_key, "tasks": tids, "courier": c,
                "x1": cn["x"], "y1": cn["y"], "x2": round(ax, 1), "y2": round(ay, 1),
                "willingness": round(will, 3) if will is not None else None,  # 真
                "score": round(score, 3) if score is not None else None,       # 真
            })

    # 候选虚线（演示采样）：每个任务取候选 willingness 最高的 2 行（非采纳的）作为
    # 「可能选择的派单策略」虚线，营造收敛感。仅可视化。
    candidate_edges = []
    accepted_pairs = {(e["task_key"], e["courier"]) for e in accepted_edges}
    per_task_cands: dict[str, list[tuple[float, str, str]]] = defaultdict(list)
    for row in candidates:
        task_key, tids, cid, score, will, _idx = row
        per_task_cands[task_key].append((will, cid, task_key))
    cand_count = 0
    for task_key, lst in per_task_cands.items():
        tids = [x for x in task_key.split(",") if x]
        if tids:
            valid = [t for t in tids if t in task_nodes]
            if not valid:
                continue
            ax = sum(task_nodes[t]["x"] for t in valid) / len(valid)
            ay = sum(task_nodes[t]["y"] for t in valid) / len(valid)
        else:
            continue
        top = sorted(lst, reverse=True)[:2]
        for will, cid, _tk in top:
            if (task_key, cid) in accepted_pairs:
                continue
            cn = courier_nodes.get(cid)
            if not cn:
                continue
            candidate_edges.append({
                "task_key": task_key, "courier": cid,
                "x1": cn["x"], "y1": cn["y"], "x2": round(ax, 1), "y2": round(ay, 1),
            })
            cand_count += 1
            if cand_count >= 60:   # 限量，避免满屏乱穿
                break
        if cand_count >= 60:
            break

    # 圈：① 真合单组(任务数>1) 标「N单合单」；② 多骑手兜底组(单任务但≥2骑手)标
    # 「N骑手兜底」。两者都是 solution 真值（large_seed301 上 v4 解为多骑手兜底，
    # 故大量出现兜底圈，与决策「双骑手兜底」叙事自洽；绝不伪造任务合单）。
    bundles = []
    for task_key, couriers in solution:
        tids = [x for x in task_key.split(",") if x]
        couriers = list(couriers)
        is_task_bundle = len(tids) > 1
        is_multi_courier = len(couriers) > 1
        if not (is_task_bundle or is_multi_courier):
            continue
        pts = [(task_nodes[t]["x"], task_nodes[t]["y"]) for t in tids if t in task_nodes]
        if not pts:
            continue
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        spread = max((abs(p[0] - cx) + abs(p[1] - cy)) for p in pts) if len(pts) > 1 else 0
        # iter-3：节点收紧后聚合圈也收紧（更像目标稿那种贴着节点的紧致发光圈）
        r = max(22, spread * 0.6 + 22)
        if is_task_bundle:
            label = f"{len(tids)}单合单"
            kind = "task_bundle"
        else:
            label = f"{len(couriers)}骑手兜底"
            kind = "multi_courier"
        bundles.append({
            "task_key": task_key, "tasks": tids, "couriers": couriers,
            "cx": round(cx, 1), "cy": round(cy, 1), "r": round(r, 1),
            "label": label, "kind": kind,  # 真值
        })

    # iter-3(P0-2)：挑一个**代表性任务组**做默认显示的 G-028 风格浮卡。
    # 优先真合单组(任务数最多)；无则取骑手数最多的多骑手兜底组。group_id 与右侧
    # 决策卡同口径(G-+sha1[:4])，浮卡字段：订单数/预计送达/无人接单风险/候选方案数。
    featured_group = None
    if bundles:
        def _rank(b):
            return (len(b["tasks"]) > 1, len(b["tasks"]), len(b["couriers"]))
        fb = max(bundles, key=_rank)
        f_tids = fb["tasks"]
        f_is_bundle = len(f_tids) > 1
        # 该组无人接单风险：取组内任务最低意愿派生（越低风险越高）
        f_wills = [task_nodes[t]["willingness_repr"] for t in f_tids if t in task_nodes]
        wmin = min(f_wills) if f_wills else 0.4
        f_risk = "中高" if wmin < 0.3 else ("中" if wmin < 0.55 else "低")
        # 候选方案数：该组在候选虚线/候选行里出现的不同骑手数(≥2 时叙事=多候选)
        f_cands = len({row[2] for row in candidates if row[0] == fb["task_key"]})
        featured_group = {
            "group_id": "G-" + (hashlib.sha1(fb["task_key"].encode()).hexdigest()[:4].upper()),
            "task_key": fb["task_key"],
            "cx": fb["cx"], "cy": fb["cy"], "r": fb["r"],
            "n_tasks": len(f_tids),
            "n_couriers": len(fb["couriers"]),
            "is_bundle": f_is_bundle,
            "eta_min": 12 if f_is_bundle else 22,          # 演示
            "risk_text": f_risk,                            # 真值意愿派生
            "n_candidates": max(2, min(f_cands, 5)),        # 真值候选骑手数(裁切叙事区间)
            "district": (district_nodes[0]["name"] if district_nodes else None),  # 演示
            "is_demo": True,
        }

    return {
        "is_demo": True,
        "demo_tag": DEMO_TAG,
        "canvas": {"w": CANVAS_W, "h": CANVAS_H},
        "regime": perc.get("regime"),
        "districts": district_nodes,
        "tasks": list(task_nodes.values()),
        "couriers": list(courier_nodes.values()),
        "accepted_edges": accepted_edges,
        "candidate_edges": candidate_edges,
        "bundles": bundles,
        "featured_group": featured_group,
        "note": (
            "脱敏可视化沙盘：派单/意愿/分数来自赛题真实数据 large_seed301；"
            "地理坐标为确定性合成(seed=20260620，赛题数据不含位置)，非真实 GPS。"
        ),
    }


# --------------------------------------------------------------------------- #
# 3. 顶栏场景芯片（真实派生 + 叙事百分比）                                     #
# --------------------------------------------------------------------------- #
def synth_chips(report: dict[str, Any]) -> list[dict[str, Any]]:
    perc = report.get("perception", {})
    w_mean = perc.get("willingness_mean")
    d = perc.get("density_ratio")
    bf = perc.get("bundle_fraction")
    chips = []
    # 意愿芯片（真值 w_mean，叙事百分比）
    if w_mean is not None:
        chips.append({
            "icon": "☔", "title": "接单意愿",
            "value": f"w̄={w_mean}", "delta": "意愿偏低" if w_mean < 0.45 else "意愿正常",
            "real": {"willingness_mean": w_mean}, "is_demo": False, "narrative": True,
        })
    if d is not None:
        chips.append({
            "icon": "🧍", "title": "骑手供给",
            "value": f"d={d}", "delta": "骑手充裕" if d >= 1.8 else ("均衡" if d > 1.0 else "骑手紧张"),
            "real": {"density_ratio": d}, "is_demo": False, "narrative": True,
        })
    if bf is not None:
        # iter-2(P0-3)：large_seed301 上 v4 解为「多骑手兜底」非任务合单，故措辞改为
        # 「合单/兜底潜力」，与满屏兜底圈自洽，绝不伪造任务合单。
        chips.append({
            "icon": "🗂", "title": "合单/兜底潜力",
            "value": f"潜力占比 {round(bf*100,1)}%", "delta": "合单/兜底机会密集" if bf >= 0.35 else "机会一般",
            "real": {"bundle_fraction": bf}, "is_demo": False, "narrative": True,
        })
    return chips


# --------------------------------------------------------------------------- #
# 4. 6 KPI（真值 + 演示换算）                                                  #
# --------------------------------------------------------------------------- #
def synth_kpis(report: dict[str, Any], baseline: dict[str, Any]) -> list[dict[str, Any]]:
    summ = report.get("solution_summary", {})
    covered = summ.get("covered_tasks") or 0
    total = summ.get("total_tasks") or 0
    used = summ.get("used_couriers")
    completion = round(covered / total * 100, 1) if total else None
    unserved = (total - covered) if total else None
    a_cost = (baseline.get("autosolver") or {}).get("expected_cost")
    g_cost = (baseline.get("greedy") or {}).get("expected_cost")
    cost_pct = (baseline.get("improvement") or {}).get("cost_pct")

    kpis = []
    kpis.append({
        "key": "completion", "label": "预计完成率",
        "value": completion, "unit": "%", "is_demo": False,
        "good": "up", "sub": f"{covered}/{total} 覆盖",
    })
    kpis.append({
        "key": "unserved", "label": "预计无人接单数",
        "value": unserved, "unit": "单", "is_demo": False,
        "good": "down", "sub": "未覆盖任务数(真)",
    })
    # 履约成本指数：以贪心=100 归一化（演示换算）
    cost_index = round(a_cost / g_cost * 100, 1) if (a_cost is not None and g_cost) else None
    kpis.append({
        "key": "cost_index", "label": "履约成本指数",
        "value": cost_index, "unit": "", "is_demo": True,
        "good": "down", "sub": "贪心=100 归一化(演示换算)",
    })
    kpis.append({
        "key": "couriers", "label": "骑手占用数",
        "value": used, "unit": "人", "is_demo": False,
        "good": "neutral", "sub": "投入产能(中性，非越低越好)",
    })
    kpis.append({
        "key": "improve", "label": "相对省心基线改善",
        "value": cost_pct, "unit": "%", "is_demo": False,
        "good": "up", "sub": "成本口径(真) vs 纯贪心",
    })
    # 商业收益：ROI 公式演示换算
    roi_daily = None
    if cost_pct is not None:
        # 与 ROI 模拟器默认口径一致：示例城市量×下降比例×单位亏损×覆盖率
        roi_daily = round(500000 * (cost_pct / 100.0) * 15 * 0.5)
    kpis.append({
        "key": "revenue", "label": "预计商业收益",
        "value": roi_daily, "unit": "¥/日", "is_demo": True,
        "good": "up", "sub": "ROI 公式演示换算",
    })
    return kpis


# --------------------------------------------------------------------------- #
# 5. 风险画像 / 推荐策略（感知真值派生）                                       #
# --------------------------------------------------------------------------- #
def synth_risk(report: dict[str, Any]) -> list[dict[str, Any]]:
    perc = report.get("perception", {})
    w = perc.get("willingness_mean", 0.4)
    d = perc.get("density_ratio", 1.5)
    bf = perc.get("bundle_fraction", 0.0)
    quant = perc.get("willingness", {})
    spread = (quant.get("p90", 0) - quant.get("p10", 0)) if quant else 0
    risks = []
    risks.append({
        "name": "接单意愿低",
        "level": "high" if w < 0.3 else ("mid" if w < 0.5 else "low"),
        "basis": f"w̄={w}", "is_demo": False,
    })
    risks.append({
        "name": "骑手供给不足",
        "level": "high" if d <= 1.0 else ("mid" if d < 1.6 else "low"),
        "basis": f"d={d}", "is_demo": False,
    })
    risks.append({
        "name": "订单分布不均",
        "level": "high" if spread > 0.6 else ("mid" if spread > 0.4 else "low"),
        "basis": f"意愿 p90-p10={round(spread,3)}", "is_demo": False,
    })
    risks.append({
        "name": "合单机会密集",
        "level": "low" if bf >= 0.35 else "mid",
        "basis": f"合单占比={bf}", "is_demo": False,
    })
    return risks


def synth_strategy(report: dict[str, Any]) -> dict[str, Any]:
    planner = report.get("planner", {})
    chain = planner.get("chain", "")
    parts = [p.strip() for p in chain.replace("+", "·").split("·") if p.strip()] if chain else []
    return {
        "regime": planner.get("regime"),
        "chain": chain,
        "steps": parts,
        "why": planner.get("why", ""),
        "is_mirror_read": planner.get("is_mirror_read", True),
        "is_demo": False,
        "narrative": True,  # Planner 镜像解读(叙事)
    }


# --------------------------------------------------------------------------- #
# 6. 候选 A/B/C 评估                                                           #
# --------------------------------------------------------------------------- #
def synth_candidates(report: dict[str, Any], baseline: dict[str, Any]) -> list[dict[str, Any]]:
    g = baseline.get("greedy", {})
    a = baseline.get("autosolver", {})
    pareto = (report.get("stakeholders") or {}).get("pareto_front") or []
    cands = []

    def _row(label, tag, src, cost, covered, total, used, picked, reason, is_demo=False):
        completion = round(covered / total * 100, 1) if (total and covered is not None) else None
        return {
            "label": label, "tag": tag, "source": src,
            "completion": completion, "unserved": (total - covered) if (total and covered is not None) else None,
            "cost": cost, "used_couriers": used,
            "picked": picked, "reason": reason, "is_demo": is_demo,
        }

    cands.append(_row(
        "方案A 传统就近/贪心", "已淘汰", g.get("solver_used", "greedy"),
        g.get("expected_cost"), g.get("covered"), g.get("total"), g.get("used_couriers"),
        False, "纯贪心基线：期望成本高，多派/合单收益未挖掘", is_demo=False,
    ))
    cands.append(_row(
        "方案B AutoSolver", "已选用", a.get("solver_used", "solver_v4.py"),
        a.get("expected_cost"), a.get("covered"), a.get("total"), a.get("used_couriers"),
        True, "列搜索+MCF重组+v4余量精修：期望成本最低，覆盖不更差", is_demo=False,
    ))
    # 方案C：取 pareto_front 现成 α 解（不新求解）
    if pareto:
        # 取一个非 best 的折衷 α（如成本居中）
        srt = sorted(pareto, key=lambda p: p.get("expected_cost", 0))
        pick = srt[len(srt) // 2] if len(srt) > 1 else srt[0]
        total = (report.get("solution_summary") or {}).get("total_tasks")
        cands.append({
            "label": "方案C 公平折衷(Pareto α)", "tag": "已淘汰",
            "source": f"stakeholders.pareto_front α={pick.get('alpha')}",
            "completion": round(pick.get("fulfillment_rate", 0) * 100, 1) if pick.get("fulfillment_rate") is not None else None,
            "unserved": None,
            "cost": round(pick.get("expected_cost"), 3) if pick.get("expected_cost") is not None else None,
            "used_couriers": None,
            "picked": False,
            "reason": f"四方折衷解(α={pick.get('alpha')})：rider Gini={pick.get('rider_income_gini')}，成本高于B",
            "is_demo": False,
        })
    return cands


# --------------------------------------------------------------------------- #
# 7. 决策解释（聚焦第一个合单组，真值 + 演示距离/ETA）                          #
# --------------------------------------------------------------------------- #
def synth_decision(text: str, report: dict[str, Any], layout: dict[str, Any]) -> dict[str, Any]:
    candidates, _all = parse_candidates(text)
    row_meta: dict[tuple[str, str], tuple[float, float]] = {}
    for row in candidates:
        row_meta[(row[0], row[2])] = (row[4], row[3])
    bundles = layout.get("bundles", [])
    solution = report.get("solution") or []
    # 选第一个合单组；没有则取第一个有骑手的组
    # 优先选「真合单组」；无则选「多骑手兜底组」；再无则任意有骑手组。
    target = None
    for tk, couriers in solution:
        if "," in tk and couriers:
            target = (tk, list(couriers)); break
    if target is None:
        for tk, couriers in solution:
            if len(list(couriers)) > 1:
                target = (tk, list(couriers)); break
    if target is None:
        for tk, couriers in solution:
            if couriers:
                target = (tk, list(couriers)); break
    if target is None:
        return {"available": False}
    task_key, couriers = target
    tids = [x for x in task_key.split(",") if x]
    riders = []
    for c in couriers:
        will, score = row_meta.get((task_key, c), (None, None))
        riders.append({
            "id": c,
            "willingness": round(will, 3) if will is not None else None,  # 真
            "score": round(score, 3) if score is not None else None,       # 真
            "distance_km": round(0.8 + _hf("dist", task_key, c) * 3.0, 1),  # 演示
            "is_demo_distance": True,
        })
    is_bundle = len(tids) > 1            # 任务合单（真）
    is_multi = len(couriers) > 1         # 多骑手兜底（真）
    mode = "task_bundle" if is_bundle else ("multi_courier" if is_multi else "single")
    return {
        "available": True,
        "group_id": "G-" + (hashlib.sha1(task_key.encode()).hexdigest()[:4].upper()),
        "task_key": task_key,
        "tasks": tids,
        "is_bundle": is_bundle,
        "is_multi_courier": is_multi,
        "mode": mode,
        "n_tasks": len(tids),
        "n_couriers": len(couriers),
        "district": (layout.get("districts") or [{}])[0].get("name") if layout.get("districts") else None,  # 演示
        "eta_min": 12 if is_bundle else (18 if is_multi else 22),   # 演示
        "distance_km": round(2.0 + _hf("gdist", task_key) * 3.0, 1),  # 演示
        "riders": riders,
        "reasons": [
            ("该区域接单意愿派生自真实 willingness，选择"
             + ("合单优先" if is_bundle else ("多骑手兜底" if is_multi else "单骑手")) + "策略"),
            ("两名骑手分摊兜底，对冲低意愿拒单风险" if is_multi else
             ("合单后单位履约成本下降" if is_bundle else "单骑手直派，路径最短")),
            "AutoSolver 期望成本口径下为该组最优派单",
        ],
        "use_bundle": is_bundle,
        "is_demo": True,  # 含演示 ETA/距离/商圈
        "real_fields": ["task/courier 派单", "willingness", "score", "是否合单", "兜底骑手数"],
    }


# --------------------------------------------------------------------------- #
# 7b. 自进化面板（透传 report.evolution 真值；拿不到的子字段直接删，不造假）    #
# --------------------------------------------------------------------------- #
def synth_evolution(report: dict[str, Any]) -> dict[str, Any]:
    """把 run_blind_solve 的 **真实** report["evolution"] 提炼成前端面板数据。

    iteration-2 修「自进化假占位」雷：旧前端把实验策略 #18-21 写死。本函数改为
    **只透传真值**：
      - promoted_card：真实 promoted 策略（gen01_M1_003 / operator / parent /
        directive / safety_passed / held-out 改进量 Δ）。
      - registry_summary：注册表真实条数 + accepted 真实条数 + directive 直方图。
      - causal_demo：同一 parent + 不同 ReEvo lesson directive → 生成不同 rank
        代码（distinct_final_lines / causal_proven / 各 variant 的 final_key_line）。
    任一子字段拿不到则置 None，前端据此**删掉该段**（绝不补假数据），只保留
    「5 步机制流程图 + 真实注册表条数 + 诚实声明」。

    诚实声明铁律（方案 §7 / 红线）：机制可验证、对最终派单成绩零贡献、stub 无
    live LLM；改进量 Δ 为机制内部 held-out 指标，非派单成绩。
    """
    evo = report.get("evolution") or {}
    card = evo.get("promoted_card") or {}
    summ = evo.get("registry_summary") or {}
    demo = evo.get("causal_demo") or {}

    # promoted_card 真值（只挑展示需要、确定存在的字段；available=False 时降级）
    promoted = None
    if card.get("available") and card.get("status"):
        promoted = {
            "strategy_id": card.get("strategy_id"),
            "status": card.get("status"),
            "operator": card.get("operator"),
            "generation": card.get("generation"),
            "parent": card.get("parent"),
            "target_regime": card.get("target_regime"),
            "directive": card.get("directive"),
            "safety_passed": card.get("safety_passed"),
            "safety_reason": card.get("safety_reason"),
            "last_decision": card.get("last_decision"),
            "last_reason": card.get("last_reason"),
            "heldout_mean": card.get("heldout_mean"),
            "baseline_heldout_mean": card.get("baseline_heldout_mean"),
            "improvement_vs_baseline": card.get("improvement_vs_baseline"),
            "source": card.get("source"),
        }

    # registry_summary 真值（条数 + directive 直方图）
    registry = None
    if summ:
        registry = {
            "total_strategies": summ.get("total_strategies"),
            "promoted": summ.get("promoted") or [],
            "accepted_or_better": summ.get("accepted_or_better") or [],
            "n_accepted": len(summ.get("accepted_or_better") or []),
            "directive_histogram": summ.get("directive_histogram") or {},
            "source": summ.get("source"),
        }

    # causal_demo 真值（同 parent / 不同 directive → 不同 rank 代码）
    causal = None
    variants = demo.get("variants") or []
    if variants:
        # P1-6：report.evolution.causal_demo 顶层未带 parent（None），但同一批 variant
        # 的真实 parent 与 promoted_card.parent 同源（gen01_E1_001）。这里**回填真实
        # parent**（优先 causal 自带 → variant 自带 → promoted_card.parent），让前端不再
        # 兜底显示「—」。仍是真值（mechanism live runnable probe 的真实 parent）。
        causal_parent = (
            demo.get("parent")
            or next((v.get("parent") for v in variants if v.get("parent")), None)
            or card.get("parent")
        )
        causal = {
            "distinct_final_lines": demo.get("distinct_final_lines"),
            "causal_proven": demo.get("causal_proven"),
            "directives_contrasted": demo.get("directives_contrasted") or [],
            "parent": causal_parent,
            "variants": [
                {
                    "directive": v.get("directive"),
                    "final_key_line": v.get("final_key_line"),
                }
                for v in variants
            ],
            "mechanism": demo.get("mechanism", ""),
        }

    return {
        "is_demo": False,            # 机制真值（非演示合成）
        "is_mechanism_only": True,   # 但对最终派单成绩零贡献
        "live_llm": False,           # stub 生成，无 live LLM
        "promoted_card": promoted,   # None → 前端删该段
        "registry_summary": registry,
        "causal_demo": causal,       # None → 前端删该段
        "honesty": (
            "机制可验证·对最终派单成绩零贡献·stub 无 live LLM；"
            "改进量 Δ 为机制内部 held-out 指标，非派单成绩。"
        ),
    }


# --------------------------------------------------------------------------- #
# 主入口：把 report + baseline → 完整指挥舱 payload                            #
# --------------------------------------------------------------------------- #
def build_story(text: str, report: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    layout = synth_layout(text, report)
    return {
        "chips": synth_chips(report),
        "kpis": synth_kpis(report, baseline),
        "risk": synth_risk(report),
        "strategy": synth_strategy(report),
        "regime_verdict": {
            "regime": report.get("perception", {}).get("regime"),
            "rules": report.get("perception", {}).get("rules", []),
            "is_demo": False,
        },
        "map": layout,
        "decision": synth_decision(text, report, layout),
        "candidates": synth_candidates(report, baseline),
        "certificate": report.get("certificate", {}),   # r1，真值透传
        "evolution": synth_evolution(report),            # iter-2：透传真值，删假占位
        "baseline": baseline,
        "solution_summary": report.get("solution_summary", {}),
        "solve_time_s": report.get("solve_time_s"),
        "wall_time_s": report.get("wall_time_s"),
        "solver_used": report.get("solver_used"),
        "perception": report.get("perception", {}),
        "data_boundary": (
            "真实字段来自 solver_v4/感知/证书/四方/进化真实输出 + 纯贪心真跑；"
            "地图坐标·距离·ETA·天气·商圈·金额为演示合成层(seed=20260620)，非真实 GPS/财务。"
        ),
    }


if __name__ == "__main__":
    import json
    from web_agent_demo import blind_test_orchestrator_v3 as orch
    from web_agent_demo import cockpit_baseline as cb
    txt = (ROOT / "data" / "official_cases" / "large_seed301.txt").read_text(encoding="utf-8")
    rep = orch.run_blind_solve(txt, case_label="large_seed301")
    bl = cb.compute_baseline(txt, autosolver_solution=rep.get("solution"),
                             autosolver_solve_time_s=rep.get("solve_time_s"))
    story = build_story(txt, rep, bl)
    print(json.dumps({k: (v if not isinstance(v, (list, dict)) else f"<{type(v).__name__} len={len(v)}>")
                      for k, v in story.items()}, ensure_ascii=False, indent=2))
