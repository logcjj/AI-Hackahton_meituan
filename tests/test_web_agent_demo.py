from __future__ import annotations

import json
import math
import unittest
from types import SimpleNamespace
from unittest import mock


class WebAgentDemoTest(unittest.TestCase):
    def test_home_page_contains_dispatch_workbench_shell(self):
        from web_agent_demo.server import render_index

        html = render_index()

        required_markers = [
            "外卖配送智能调度工作台",
            "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",
            "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js",
            'integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="',
            'integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="',
            'crossorigin="anonymous"',
            'id="dispatch-workbench-shell"',
            'data-shell="dispatch-workbench-shell"',
            'data-visual-system="enterprise-dispatch-v2"',
            'data-density="high-information"',
            'data-product-reference="kandbox-dispatch"',
            'id="dispatch-workbench-bootstrap"',
            'id="route-nav"',
            'id="route-view"',
            'id="topbar-stats"',
            "#/live",
            "#/decisions",
            "#/memory",
            "#/orders",
            "#/riders",
            "实时推理",
            "决策过程",
            "长期记忆",
            "订单池",
            "骑手运力",
            "主控台",
            "可追溯",
            "需求视图",
            "供给视图",
            "看系统自动推演、地图动作和累计优势。",
            "看每一轮为什么这样派、放弃了什么。",
            "看系统沉淀、召回和验证的调度经验。",
            "看全天订单、时段、风险和进入推理状态。",
            "看骑手班次、位置、负载和任务链。",
            "data-route-role",
            "data-kandbox-module",
            "data-page-identity",
            "data-page-module",
            "data-page-role-strip",
            'aria-label="当前页面说明"',
            "工作台导览",
            "先看实时推理优势",
            "地图推演",
            "推导链路",
            "经验沉淀",
            "订单池",
            "运力池",
            "实时推理",
            "决策过程",
            "长期记忆",
            "骑手运力",
            "开始推理",
            "暂停/继续",
            "1x",
            "2x",
            "4x",
            "当前算法",
            "对比",
            "叠加",
            "实时累计对比栏",
            "决策轮次时间线",
            'data-decision-route="reasoning"',
            'id="decision-timeline"',
            'id="decision-reasoning-canvas"',
            'id="decision-context-pane"',
            "算法推理过程",
            "本轮推理说明",
            "本轮输入与输出",
            "本轮结论",
            'data-reasoning-surface="advantage-first"',
            'id="decision-step-flow"',
            'data-reasoning-pattern="plain-six-step"',
            'id="decision-plan-comparison"',
            'data-reasoning-pattern="accepted-and-rejected"',
            'id="decision-proof-panel"',
            "为什么触发这一轮",
            "看哪些订单",
            "候选骑手怎么选",
            "先过滤不可行方案",
            "再给可行方案打分",
            "输出派单并回写记忆",
            "采纳方案",
            "放弃方案",
            "评分对比",
            "decision-trigger-time",
            "decision-trigger-reason",
            "decision-input-orders",
            "decision-candidate-riders",
            "decision-filtering-process",
            "decision-scoring-process",
            "decision-final-actions",
            "decision-abandoned-actions",
            "decision-round-result",
            "decision-result-writeback",
            "decision-context-input",
            "decision-output-result",
            "decision-round-summary",
            "新沉淀记忆",
            'data-memory-route="hermes-long-term"',
            'data-memory-model="global-profile-recall-feedback"',
            'id="memory-command-center"',
            'id="memory-overview"',
            'id="memory-layer-board"',
            'id="memory-profile-board"',
            'id="memory-recall-chain"',
            'id="memory-writeback-loop"',
            "已整理记忆",
            "当前命中的记忆",
            "记忆效果反馈",
            "长期记忆中心",
            "长期记忆中枢",
            "不是日志列表、资产表或文档中心",
            "全局记忆",
            "画像记忆",
            "召回链",
            "回写反馈",
            "记忆层结构",
            "全局策略记忆",
            "骑手画像记忆",
            "商圈/需求画像",
            "订单风险画像",
            "骑手供给画像",
            "商圈压力画像",
            "长期记忆总量",
            "当前召回链路",
            "触发场景",
            "上下文摘要",
            "策略摘要",
            "决策结果",
            "效果反馈",
            "置信度",
            "召回次数",
            "最近命中时间",
            "全天订单全集",
            'data-orders-route="jobs-input"',
            "订单池看板",
            'id="orders-input-command"',
            'data-orders-surface="demand-risk-input"',
            'id="orders-priority-panel"',
            'id="orders-priority-list"',
            "订单池视图",
            "需关注订单",
            "订单全集明细",
            'data-evidence-role="secondary"',
            'id="orders-overview"',
            'id="orders-filter-bar"',
            'id="orders-filter-time"',
            'id="orders-filter-area"',
            'id="orders-filter-status"',
            'id="orders-filter-risk"',
            'id="orders-result-count"',
            'id="orders-table-body"',
            'id="orders-context-panel"',
            "订单池概览",
            "全天释放节奏",
            "基线算法结果",
            "我方算法结果",
            "全天骑手资源",
            'data-riders-route="workers-resource"',
            "骑手运力看板",
            'id="riders-resource-command"',
            'data-riders-surface="capacity-coverage"',
            'id="riders-capacity-panel"',
            'id="riders-capacity-list"',
            "运力覆盖视图",
            "可调度运力焦点",
            'id="riders-overview"',
            'id="riders-filter-bar"',
            'id="riders-filter-area"',
            'id="riders-filter-state"',
            'id="riders-result-count"',
            'id="rider-resource-board"',
            'id="rider-context-panel"',
            "运力覆盖上下文",
            "区域供给覆盖",
            "骑手编号",
            "当前任务链",
            "预计空闲时间",
            "历史表现摘要",
            'id="start-inference"',
            'id="pause-inference"',
            'id="playback-speed"',
            'id="inference-mode"',
            'id="inference-clock"',
            'id="inference-state-label"',
            'id="inference-progress-bar"',
            'id="live-advantage-hero"',
            'data-live-priority="advantage-first"',
            'id="live-advantage-headline"',
            'id="live-advantage-copy"',
            'data-score-role="dominant-advantage"',
            "实时推演总览",
            "等待开始推理",
            "开始后累计验证",
            "全日结论暂不展示",
            "推演完成",
            'id="live-event-flow"',
            'id="live-score-stack"',
            'id="live-round-summary"',
            'id="live-cumulative-metrics"',
            'id="cumulative-metrics-caption"',
            'id="live-map-stage"',
            'id="map-action-status"',
            'id="leaflet-live-map"',
            'data-real-map-provider="leaflet"',
            'data-tile-layer="cartodb-light-nolabels"',
            'data-fallback-map="screen-coordinate"',
            "leafletRouteCount",
            "leafletMarkerCount",
            'window.L.control.zoom({ position: "bottomright" }).addTo(map)',
            "scrollWheelZoom: true",
            "cartodb-light-nolabels",
            "匿名无标签真实地图",
            "移动中",
            "metric-time-delta",
            "metric-money-delta",
            "metric-timeout-delta",
            "metric-empty-mileage-delta",
            "metric-profit-delta",
            'id="round-final-actions"',
            'id="round-abandoned-actions"',
            'id="round-writeback"',
            'id="round-metric-impact"',
            "event-type-score_update",
            "event-type-decision_round",
            "event-tag",
            "metric-chip",
            "--shadow-tight",
            "--shadow-float",
            "--focus-ring",
            "--route-accent",
            "page-role-card",
            "page-role-strip",
            "nav-hint",
            "nav-module",
            "button:focus-visible",
            "prefers-reduced-motion",
            "live-ops-shell",
            "live-side-rail",
            "live-run-panel",
            'data-inference-runtime="status"',
            "map-mode-chip",
            "map-legend",
            "legend-swatch",
            'data-lane="difference"',
            'data-lane="previous"',
            'data-lane="baseline"',
            "data-release",
            "data-motion",
            "function bootstrapDispatchWorkbench",
            "function routeFromHash",
            "function setRoute",
            "function renderRoute",
            "function hydrateLivePage",
            "function bindLiveControls",
            "function startInference",
            "function toggleInferencePause",
            "function setInferenceSpeed",
            "function setInferenceMode",
            "function stopLiveRuntime",
            "function scheduleInferenceTick",
            "function advanceInferenceTick",
            "function setInferenceTime",
            "function renderLiveRuntimeState",
            "function liveAdvantageHeadline",
            "function liveAdvantageCopy",
            "function renderAdvantageTargetRow",
            "function preDispatchScore",
            "function preDispatchDecision",
            "function preDispatchFrame",
            "function fmtSavedDistance",
            "function renderLiveCumulativeMetrics",
            "function scoreForTime",
            "function decisionForTime",
            "function releasedEvents",
            "function frameForTime",
            "function previousFrameFor",
            "function routeRowsForFrame",
            "function differentialOrderIds",
            "function mapRouteRows",
            "function ordersForMap",
            "function riderPositionsForFrame",
            "function movingRiderPositions",
            "function trackPositionAt",
            "function renderLiveMapLayer",
            "function renderMapActionStatus",
            "function activeProgressRoutes",
            "function progressPolylineForRoute",
            "function queueLiveMapHydration",
            "function destroyLiveMap",
            "function hydrateLiveMap",
            "function updateLiveLeafletOverlay",
            "function mapEntityLabel",
            "function mapEntityTitle",
            "function renderLeafletMapLayers",
            "function renderLeafletMarkers",
            "function renderLeafletRoutes",
            "function renderLeafletMarker",
            "function renderMapLegend",
            "function renderLivePage",
            "function renderDecisionsPage",
            "function renderDecisionTimeline",
            "function renderDecisionReasoning",
            "function renderDecisionContext",
            "function renderDecisionAdvantageHero",
            "function renderDecisionStepFlow",
            "function renderDecisionPlanComparison",
            "function hydrateDecisionPage",
            "function selectDecisionRound",
            "function renderMemoryPage",
            "function memoryStats",
            "function memoryItemsForSection",
            "function renderMemoryLayerCard",
            "function renderMemoryProfile",
            "function renderMemoryRecallStep",
            "function renderMemoryWritebackStep",
            "function renderMemoryEvidenceItem",
            "function renderMemoryRecallCard",
            "function renderMemoryItem",
            "function renderOrdersPage",
            "function hydrateOrdersPage",
            "function updateOrdersView",
            "function filteredOrders",
            "function renderOrderFocusList",
            "function renderOrdersOverview",
            "function renderOrdersContext",
            "function renderRidersPage",
            "function hydrateRidersPage",
            "function updateRidersView",
            "function filteredRiders",
            "function renderCoverageCards",
            "function renderRiderFocusList",
            "function renderRidersOverview",
            "function renderRidersContext",
            "window.__DISPATCH_WORKBENCH__",
            "data-route-link",
            "data-route-view",
            "data-control-strip",
            "data-filter-bar",
            "data-map-ref",
            "data-memory-section",
            "data-secret-handling",
            "env-only-redacted",
        ]
        for marker in required_markers:
            self.assertIn(marker, html)

        for endpoint in [
            "/api/day-simulation/scenarios",
            "/api/day-simulation/engines",
            "/api/day-simulation/run",
            "/api/day-simulation/frame",
            "/api/day-simulation/memory",
        ]:
            self.assertIn(endpoint, html)

        for forbidden in [
            'id="day-replay-shell"',
            'id="side-by-side-replay"',
            'id="greedy-map-panel"',
            'id="autosolver-map-panel"',
            'id="greedy-map-stage"',
            'id="autosolver-map-stage"',
            "function bootstrapDayReplayShell",
            "window.__AUTO_SOLVER_DAY_REPLAY__",
            "Pure Greedy Replay",
            "AutoSolver Agent Replay",
            'id="simulation-sandbox"',
            'id="simulation-map"',
            'id="algorithm-compare-table"',
            'id="memory-current-recall"',
            "memory-section-grid",
            "memory-card",
            'id="run-compare"',
            "/api/simulation/session",
            "/api/simulation/tick",
            "/api/compare/run",
            "/api/memory/recall",
            "/api/predictor/rank",
            "maplibre-with-offline-schematic-fallback",
            "ReasonGraph 推理链路",
            "真实策略尝试流",
            "策略族汇总",
            'data-branch="S1"',
            'data-branch="S2"',
            'id="run-agent"',
            "运行派单推理",
            "function updateReasonMetrics",
            "function renderStrategyStream",
            "function reasoningOrderForSample",
            "调度输入上下文",
            "资源盘点上下文",
            "let simulationSampleLoadPromise = null",
            "/api/simulation-sample?",
            "candidate_preview",
            "官方成绩",
            "Proxy score",
            "Real-time Dispatch Assignment Optimization",
            "Relative Improvement vs Greedy",
            "AUTOSOLVER_LLM_API_KEY",
            'title="${escapeText(shockIds.join(",") || frame.time_slice_id)}"',
            'title="${escapeHtml(item.label || item.id)}"',
            'title="${escapeHtml(rider.name)}"',
            "Food Dispatch",
            "Kandbox-style workbench",
            ">LM<",
            ">PL<",
            ">ME<",
            ">JO<",
            ">WK<",
            "Live Map / Advantage Console",
            "ReasonGraph Planner",
            "Demand Input Board",
            "Capacity Resource Board",
            "Hermes Memory Hub",
            "重点订单队列",
            'id="toggle-engine-sound"',
            "引擎音效",
            "优势推理链",
            "候选路径对比与淘汰",
        ]:
            self.assertNotIn(forbidden, html)

        self.assertIn("@media (max-width: 1180px)", html)
        self.assertIn("@media (max-width: 720px)", html)

    def test_home_page_bootstrap_contains_dispatch_workbench_model(self):
        from web_agent_demo.server import render_index

        html = render_index()
        start = html.index('<script id="dispatch-workbench-bootstrap" type="application/json">')
        start = html.index(">", start) + 1
        end = html.index("</script>", start)
        payload = json.loads(html[start:end])
        contract = payload["contract"]
        workbench = payload["workbench"]

        self.assertEqual(payload["mode"], "dispatch-workbench-shell")
        self.assertEqual(payload["endpoints"]["run"], "/api/day-simulation/run")
        self.assertEqual(contract["scenario"]["id"], "weekday_full_day")
        self.assertEqual(contract["baseline_run"]["algorithm_id"], "nearest_greedy")
        self.assertEqual(contract["challenger_run"]["algorithm_id"], "autosolver_agent")
        self.assertGreater(len(contract["frames"]), 10)
        self.assertGreater(len(contract["orders"]), 100)
        self.assertEqual(
            {event["event_type"] for event in contract["evolution_events"]},
            {"memory_recall", "memory_writeback", "future_policy_shift"},
        )
        self.assertGreater(contract["frames"][0]["delta"]["time_saved_s"], 0)
        self.assertTrue(contract["frames"][0]["highlighted_order_ids"])
        self.assertTrue(contract["frames"][0]["highlighted_courier_ids"])
        self.assertEqual(contract["reasoning_traces"][0]["expected_impact"], contract["frames"][0]["delta"])
        self.assertEqual(contract["reasoning_traces"][0]["frame_id"], contract["frames"][0]["id"])
        self.assertEqual(contract["privacy"]["secret_handling"], "env-only-redacted")
        self.assertTrue(contract["frames"][0]["memory_event_ids"])
        self.assertEqual(contract["frames"][0]["baseline"]["simulation_trace"]["engine_id"], "courier-agent-sim-v1")
        self.assertEqual(contract["frames"][0]["challenger"]["simulation_trace"]["engine_mode"], "discrete-event-agent-simulation")
        self.assertFalse(contract["frames"][0]["challenger"]["simulation_trace"]["map_labels_visible"])
        self.assertTrue(contract["frames"][0]["challenger"]["simulation_trace"]["courier_tracks"])
        self.assertTrue(contract["frames"][0]["challenger"]["simulation_trace"]["event_queue"])
        self.assertEqual(workbench["model_version"], "dispatch-workbench-v1")
        self.assertEqual(
            [route["id"] for route in workbench["routes"]],
            ["live", "decisions", "memory", "orders", "riders"],
        )
        self.assertEqual(workbench["inspection"]["order_count"], len(contract["orders"]))
        self.assertEqual(workbench["inspection"]["rider_count"], len(contract["couriers"]))
        self.assertEqual(workbench["inspection"]["decision_count"], len(contract["frames"]))
        self.assertTrue(workbench["inspection"]["full_day_preloaded"])
        self.assertTrue(workbench["inspection"]["deterministic"])

    def test_day_simulation_api_payloads_support_replay_controls(self):
        from web_agent_demo.server import (
            _day_simulation_frame_payload,
            _day_simulation_engines_payload,
            _day_simulation_memory_payload,
            _day_simulation_scenarios_payload,
            _run_day_simulation_payload,
        )

        scenarios = _day_simulation_scenarios_payload()
        engines = _day_simulation_engines_payload({"engine_adapter": ["sumo-traci"]})
        run_payload = _run_day_simulation_payload(
            {
                "scenario_id": "weekday_full_day",
                "seed": "api-contract-day",
                "controls": {"courier_count": 12, "order_scale": 0.22, "weather": "rain", "engine_adapter": "uxsim"},
            }
        )
        frame_payload = _day_simulation_frame_payload(
            {
                "seed": ["api-contract-day"],
                "courier_count": ["12"],
                "order_scale": ["0.22"],
                "weather": ["rain"],
                "engine_adapter": ["uxsim"],
                "frame_index": ["3"],
            }
        )
        memory_payload = _day_simulation_memory_payload(
            {
                "seed": ["api-contract-day"],
                "courier_count": ["12"],
                "order_scale": ["0.22"],
                "weather": ["rain"],
                "engine_adapter": ["uxsim"],
            }
        )

        self.assertEqual(scenarios["status"], "ok")
        self.assertEqual(scenarios["endpoints"]["run"], "/api/day-simulation/run")
        self.assertEqual(scenarios["endpoints"]["engines"], "/api/day-simulation/engines")
        self.assertEqual(scenarios["engine"]["selected_adapter_id"], "native-local")
        self.assertEqual(scenarios["engine"]["active_adapter"]["status"], "active")
        self.assertEqual(engines["status"], "ok")
        self.assertEqual(engines["engine"]["selected_adapter_id"], "native-local")
        self.assertEqual(engines["engine"]["active_adapter"]["id"], "native-local")
        self.assertTrue({"uxsim", "sumo-traci"}.issubset({item["id"] for item in engines["engine"]["adapter_capabilities"]}))
        self.assertEqual(run_payload["status"], "ok")
        self.assertEqual(run_payload["engine"]["selected_adapter_id"], "native-local")
        self.assertEqual(run_payload["engine"]["active_adapter"]["id"], "native-local")
        self.assertEqual(run_payload["engine"]["version"], "courier-agent-sim-v1")
        self.assertGreater(run_payload["order_count"], 50)
        self.assertGreater(run_payload["frame_count"], 10)
        self.assertEqual(run_payload["memory_event_count"], run_payload["frame_count"] * 3)
        self.assertEqual(run_payload["contract"]["baseline_run"]["algorithm_id"], "nearest_greedy")
        self.assertEqual(run_payload["contract"]["challenger_run"]["algorithm_id"], "autosolver_agent")
        self.assertEqual(frame_payload["status"], "ok")
        self.assertEqual(frame_payload["frame_index"], 3)
        self.assertEqual(frame_payload["engine"]["selected_adapter_id"], "native-local")
        self.assertEqual(frame_payload["frame"]["baseline"]["active_order_ids"], frame_payload["frame"]["challenger"]["active_order_ids"])
        self.assertTrue(frame_payload["frame"]["highlighted_order_ids"])
        self.assertTrue(frame_payload["frame"]["highlighted_courier_ids"])
        self.assertEqual(frame_payload["frame"]["challenger"]["simulation_trace"]["engine_id"], "courier-agent-sim-v1")
        self.assertGreater(frame_payload["frame"]["challenger"]["simulation_trace"]["emitted_tick_count"], 0)
        self.assertGreater(frame_payload["frame"]["challenger"]["simulation_trace"]["event_count"], 0)
        self.assertGreater(frame_payload["frame"]["delta"]["time_saved_s"], 0)
        self.assertIn("cumulatively", frame_payload["frame"]["delta"]["headline"])
        self.assertEqual(memory_payload["status"], "ok")
        self.assertEqual(memory_payload["engine"]["selected_adapter_id"], "native-local")
        self.assertEqual(
            {event["event_type"] for event in memory_payload["evolution_events"]},
            {"memory_recall", "memory_writeback", "future_policy_shift"},
        )
        self.assertEqual(memory_payload["privacy"]["secret_handling"], "env-only-redacted")

    def test_dispatch_map_uses_case_candidate_data(self):
        from web_agent_demo.server import build_dispatch_assignment_map

        payload = build_dispatch_assignment_map("scarce_couriers_seed401")

        self.assertEqual(payload["stage"], "preview")
        self.assertGreater(len(payload["assignments"]), 0)
        self.assertGreater(len(payload["entities"]), 0)
        first = payload["assignments"][0]
        self.assertRegex(first["task_key"], r"^T\d+")
        self.assertRegex(first["courier"], r"^C\d+")
        self.assertTrue(str(first["pickup"]).startswith("G"))
        entity_by_id = {item["id"]: item for item in payload["entities"]}
        self.assertGreaterEqual(entity_by_id[first["pickup"]]["x"], 7.5)
        self.assertLessEqual(entity_by_id[first["pickup"]]["x"], 92.5)
        self.assertIn(str(first["courier"]).split(" + ")[0], entity_by_id)
        self.assertNotIn(" + ", first["courier"])
        self.assertEqual(first["map_couriers"], [first["courier"]])
        self.assertIn("backup_couriers", first)
        self.assertEqual(first["map_orders"], [])
        self.assertGreaterEqual(first["order_count"], 1)
        self.assertTrue(first["orders"])
        self.assertFalse(any(entity["kind"] == "order" for entity in payload["entities"]))

    def test_all_listed_cases_have_dispatch_maps(self):
        from web_agent_demo.server import build_dispatch_assignment_map, list_cases

        seen_first_assignments = set()
        for case in list_cases():
            payload = build_dispatch_assignment_map(case["id"])
            self.assertEqual(payload["case_id"], case["id"])
            self.assertGreater(len(payload["assignments"]), 0, case["id"])
            self.assertGreater(len(payload["entities"]), 0, case["id"])
            first = payload["assignments"][0]
            seen_first_assignments.add((first["task_key"], first["courier"]))
            entity_by_id = {item["id"]: item for item in payload["entities"]}
            self.assertIn(first["pickup"], entity_by_id)
            for courier in str(first["courier"]).split(" + "):
                self.assertIn(courier, entity_by_id)
            self.assertNotIn(" + ", first["courier"])
            self.assertEqual(first["map_couriers"], [first["courier"]])
            self.assertEqual(first["map_orders"], [])
            self.assertFalse(any(entity["kind"] == "order" for entity in payload["entities"]))

        self.assertGreater(len(seen_first_assignments), 5)

    def test_dispatch_map_uses_network_clusters_not_lanes(self):
        from web_agent_demo.server import build_dispatch_assignment_map

        payload = build_dispatch_assignment_map("large_seed301", limit=8)
        pickups = [
            entity
            for entity in payload["entities"]
            if entity["kind"] == "pickup_cluster"
        ]
        xs = [entity["x"] for entity in pickups]
        ys = [entity["y"] for entity in pickups]

        self.assertGreaterEqual(len(pickups), 6)
        self.assertGreater(max(xs) - min(xs), 25)
        self.assertGreater(max(ys) - min(ys), 18)
        rounded_y_steps = {
            round(ys[index + 1] - ys[index], 1)
            for index in range(len(ys) - 1)
        }
        self.assertGreater(len(rounded_y_steps), 3)

    def test_simulated_scenarios_generate_ten_samples_each(self):
        from web_agent_demo.server import (
            _COURIER_ANCHORS,
            _MERCHANT_ANCHORS,
            build_simulated_scenario_sample,
            list_simulated_scenarios,
        )

        scenarios = list_simulated_scenarios()
        merchant_anchor_ids = {item["id"] for item in _MERCHANT_ANCHORS}
        courier_anchor_ids = {item["id"] for item in _COURIER_ANCHORS}

        expected_scenarios = {
            "commerce_peak": "商圈十字路口高峰",
            "medium_parallel": "中型并行派单",
            "scarce_repair": "骑手稀缺修复",
            "rain_low_willingness": "雨天低接单意愿",
            "offpeak_greedy": "低峰分散订单",
            "event_mixed_pressure": "活动混合压力",
            "night_foodcourt": "夜间商圈宵夜",
            "campus_lunch_peak": "校园午高峰",
            "hospital_office_peak": "医院写字楼午峰",
            "congestion_reassign": "拥堵异常补单",
        }

        self.assertEqual(len(scenarios), 10)
        self.assertEqual({item["id"]: item["name"] for item in scenarios}, expected_scenarios)
        self.assertEqual(len({item["id"] for item in scenarios}), 10)
        self.assertEqual(len({item["case_id"] for item in scenarios}), 10)
        self.assertGreaterEqual(len(_MERCHANT_ANCHORS), 20)
        self.assertGreaterEqual(len(_COURIER_ANCHORS), 28)
        self.assertTrue(all(item["role"] == "merchant" for item in _MERCHANT_ANCHORS))
        self.assertTrue(all(item["role"] == "courier" for item in _COURIER_ANCHORS))
        self.assertTrue(all(float(item["curb_distance"]) >= 1.35 for item in _MERCHANT_ANCHORS))
        self.assertTrue(all(float(item["curb_distance"]) <= 0.25 for item in _COURIER_ANCHORS))
        self.assertTrue(all(item["sample_count"] == 10 for item in scenarios))
        self.assertTrue(all(item["map_style"] == "meituan_delivery_project_map_v3" for item in scenarios))
        observed_weather = set()
        observed_density = set()
        observed_strategy_sets = set()
        observed_scene_sizes = set()
        for scenario in scenarios:
            scenario_weather = set()
            scenario_density = set()
            scenario_strategy_ids = set()
            for sample_index in range(10):
                sample = build_simulated_scenario_sample(str(scenario["id"]), sample_index)
                self.assertEqual(sample["stage"], "preview")
                self.assertEqual(sample["sample_index"], sample_index)
                self.assertGreaterEqual(len(sample["merchants"]), 3)
                self.assertLessEqual(len(sample["merchants"]), 6)
                self.assertGreaterEqual(len(sample["couriers"]), 7)
                self.assertGreaterEqual(len(sample["candidates"]), len(sample["merchants"]) * 2)
                self.assertEqual(len(sample["assignments"]), len(sample["merchants"]))
                self.assertTrue(sample["map_layers"]["hide_road_names"])
                self.assertEqual(sample["map_layers"]["road_name_labels"], [])
                self.assertEqual(sample["map_layers"]["style"], "meituan_delivery_project_map_v3")
                self.assertEqual(sample["map_layers"]["map_provider"], "delivery_routes_clone_meituan_grid")
                self.assertEqual(sample["map_layers"]["road_graph"], "delivery_routes_project_road_graph_v3")
                self.assertEqual(sample["map_layers"]["layer_schema"], "delivery_routes_optimization_maplibre_clone")
                self.assertIn("delivery_project_trace_map", sample["map_layers"]["layers"])
                self.assertIn("delivery_route_source", sample["map_layers"]["layers"])
                self.assertGreaterEqual(len(sample["map_layers"]["base_map_traces"]), 29)
                self.assertIn("meituan_delivery_grid", sample["map_layers"]["layers"])
                self.assertGreaterEqual(len(sample["map_layers"]["roads"]), 8)
                self.assertGreaterEqual(len(sample["map_layers"]["districts"]), 12)
                self.assertGreaterEqual(len(sample["map_layers"]["roads"]), 40)
                self.assertGreaterEqual(len(sample["map_layers"]["building_blocks"]), 36)
                self.assertGreaterEqual(len(sample["map_layers"]["commerce_hotspots"]), 3)
                self.assertGreaterEqual(len(sample["map_layers"]["intersections"]), 6)
                self.assertEqual(sample["map_layers"]["anchor_model"], "predefined_dispatch_anchor_pool_v1")
                self.assertEqual(sample["summary"]["anchor_model"], "predefined_dispatch_anchor_pool_v1")
                self.assertIn("anchor_pools", sample["map_layers"])
                self.assertEqual(len(sample["map_layers"]["anchor_pools"]["merchant_selected"]), len(sample["merchants"]))
                self.assertEqual(len(sample["map_layers"]["anchor_pools"]["courier_selected"]), len(sample["couriers"]))
                self.assertTrue(set(sample["map_layers"]["anchor_pools"]["merchant_selected"]).issubset(merchant_anchor_ids))
                self.assertTrue(set(sample["map_layers"]["anchor_pools"]["courier_selected"]).issubset(courier_anchor_ids))
                self.assertIn(sample["summary"]["weather"], {"clear", "rain", "event"})
                self.assertIn("density_profile", sample["summary"])
                observed_weather.add(sample["summary"]["weather"])
                observed_density.add(sample["summary"]["density_profile"])
                scenario_weather.add(sample["summary"]["weather"])
                scenario_density.add(sample["summary"]["density_profile"])
                scenario_strategy_ids.add(sample["selected_strategy_id"])
                observed_scene_sizes.add((len(sample["merchants"]), len(sample["couriers"])))
                self.assertTrue(all(not road["name_visible"] for road in sample["map_layers"]["roads"]))
                merchant_points = [(float(item["x"]), float(item["y"])) for item in sample["merchants"]]
                courier_points = [(float(item["x"]), float(item["y"])) for item in sample["couriers"]]
                self.assertGreater(len(set(merchant_points)), 2)
                self.assertGreater(len(set(courier_points)), 5)
                courier_visual_distances = [
                    math.hypot((left[0] - right[0]) * 7.04, (left[1] - right[1]) * 3.98)
                    for left_index, left in enumerate(courier_points)
                    for right in courier_points[left_index + 1 :]
                ]
                self.assertGreaterEqual(min(courier_visual_distances), 36.0)
                for merchant in sample["merchants"]:
                    self.assertIn(merchant["anchor_id"], merchant_anchor_ids)
                    self.assertEqual(merchant["anchor_role"], "merchant")
                    self.assertFalse(merchant["on_road"])
                    self.assertGreaterEqual(float(merchant["curb_distance"]), 1.35)
                    self.assertTrue(str(merchant["anchor_road_id"]).startswith("R"))
                    delivery_points = merchant["delivery_points"]
                    self.assertEqual(len(delivery_points), 1)
                    for point in delivery_points:
                        self.assertEqual(point["kind"], "merchant_order")
                        self.assertEqual(point["parent_merchant_id"], merchant["id"])
                        self.assertEqual((point["x"], point["y"]), (merchant["x"], merchant["y"]))
                        self.assertEqual(point["anchor_id"], merchant["anchor_id"])
                        self.assertEqual(point["anchor_role"], "merchant")
                for courier in sample["couriers"]:
                    self.assertIn(courier["anchor_id"], courier_anchor_ids)
                    self.assertEqual(courier["anchor_role"], "courier")
                    self.assertTrue(courier["on_road"])
                    self.assertLessEqual(float(courier["curb_distance"]), 0.25)
                    self.assertTrue(str(courier["anchor_road_id"]).startswith("R"))
            self.assertEqual(len(scenario_weather), 1)
            self.assertEqual(len(scenario_density), 1)
            self.assertGreaterEqual(len(scenario_strategy_ids), 2)
            observed_strategy_sets.add(tuple(sorted(scenario_strategy_ids)))
        self.assertEqual(observed_weather, {"clear", "rain", "event"})
        self.assertGreaterEqual(len(observed_density), 5)
        self.assertGreaterEqual(len(observed_strategy_sets), 4)
        self.assertGreaterEqual(len(observed_scene_sizes), 10)

    def test_simulated_refresh_uses_predefined_anchor_variants(self):
        from web_agent_demo.server import build_simulated_scenario_sample

        first = build_simulated_scenario_sample("commerce_peak", 0, "anchor-refresh-a")
        second = build_simulated_scenario_sample("commerce_peak", 0, "anchor-refresh-b")
        first_merchants = {item["anchor_id"] for item in first["merchants"]}
        second_merchants = {item["anchor_id"] for item in second["merchants"]}
        first_couriers = {item["anchor_id"] for item in first["couriers"]}
        second_couriers = {item["anchor_id"] for item in second["couriers"]}

        self.assertEqual(first["scenario_id"], second["scenario_id"])
        self.assertNotEqual((first_merchants, first_couriers), (second_merchants, second_couriers))
        self.assertTrue(first_merchants.issubset(set(first["map_layers"]["anchor_pools"]["merchant_selected"])))
        self.assertTrue(second_merchants.issubset(set(second["map_layers"]["anchor_pools"]["merchant_selected"])))

        rain_sample = build_simulated_scenario_sample("rain_low_willingness", 0)
        self.assertEqual(rain_sample["summary"]["weather"], "rain")
        self.assertLess(rain_sample["summary"]["avg_willingness"], 0.55)
        self.assertGreaterEqual(len(rain_sample["map_layers"]["rain_streaks"]), 60)

        commerce_sample = build_simulated_scenario_sample("commerce_peak", 0)
        commerce_xs = [float(item["x"]) for item in commerce_sample["merchants"]]
        commerce_ys = [float(item["y"]) for item in commerce_sample["merchants"]]
        self.assertLess(max(commerce_xs) - min(commerce_xs), 26)
        self.assertLess(max(commerce_ys) - min(commerce_ys), 24)

    def test_simulated_samples_cover_all_strategy_paths(self):
        from web_agent_demo.server import build_simulated_scenario_samples

        samples = build_simulated_scenario_samples()
        selected = {sample["selected_strategy_id"] for sample in samples}
        selected_by_scene = {}
        major_evaluated_by_scene = {}

        self.assertEqual(len(samples), 100)
        self.assertTrue({"S1", "S2", "S3", "S4", "S5"}.issubset(selected))
        for sample in samples:
            path = sample["strategy_path"]
            self.assertEqual(len(path), 5)
            self.assertEqual(sum(1 for item in path if item["status"] == "selected"), 1)
            self.assertEqual(path[0]["id"], sample["selected_strategy_id"])
            self.assertEqual(path[0]["score"], max(item["score"] for item in path))
            self.assertIn("strategy_decision", sample)
            self.assertIn("candidate_competition", sample["strategy_decision"]["metrics"])
            self.assertIn("strategy_attempt_flow", sample)
            self.assertGreaterEqual(len(sample["strategy_attempt_flow"]), 5)
            attempt_names = {item["name"] for item in sample["strategy_attempt_flow"]}
            self.assertTrue({"greedy_baseline", "single_multidispatch", "disjoint_gain", "production_solver", "evolution_replay"}.issubset(attempt_names))
            self.assertTrue(all(item["branch"] in {"S1", "S2", "S3", "S4", "S5"} for item in sample["strategy_attempt_flow"]))
            self.assertTrue(all(item["phase"] in {"initial", "adaptive", "production", "evolution"} for item in sample["strategy_attempt_flow"]))
            self.assertEqual(sum(1 for item in sample["strategy_attempt_flow"] if item["selected_branch"]), 1)
            self.assertTrue(all("evidence" in item for item in path))
            scene_id = sample["scenario_id"]
            selected_by_scene.setdefault(scene_id, set()).add(sample["selected_strategy_id"])
            major_evaluated_by_scene.setdefault(scene_id, set()).update(item["id"] for item in path[:3])
            globally_allocated_couriers = []
            for assignment in sample["assignments"]:
                self.assertIn("merchant_id", assignment)
                self.assertIn("courier_id", assignment)
                self.assertIn("backup_courier_id", assignment)
                allocated_couriers = list(assignment.get("allocated_courier_ids") or [assignment["courier_id"]])
                self.assertIn(assignment["courier_id"], allocated_couriers)
                self.assertEqual(len(allocated_couriers), len(set(allocated_couriers)))
                if sample["selected_strategy_id"] != "S2":
                    self.assertEqual(allocated_couriers, [assignment["courier_id"]])
                globally_allocated_couriers.extend(allocated_couriers)
                if sample["selected_strategy_id"] == "S2":
                    self.assertNotEqual(assignment["backup_courier_id"], assignment["courier_id"])
                self.assertGreater(float(assignment["cost"]), 0)
                self.assertGreaterEqual(int(assignment["eta_min"]), 6)
                self.assertIn(assignment["risk"], {"Low", "Medium", "High"})
            self.assertEqual(len(globally_allocated_couriers), len(set(globally_allocated_couriers)))
        self.assertTrue(all(len(strategies) >= 2 for strategies in selected_by_scene.values()))
        self.assertTrue(all(len(strategies) >= 4 for strategies in major_evaluated_by_scene.values()))

    def test_home_page_keeps_review_alignment_out_of_frontend_layout(self):
        from web_agent_demo.server import render_index

        html = render_index()

        self.assertNotIn('id="official-alignment"', html)
        self.assertNotIn('id="official-rubric"', html)
        self.assertNotIn('id="official-agent-requirements"', html)
        self.assertNotIn('id="official-run-evidence"', html)
        self.assertNotIn('id="review-alignment"', html)
        self.assertNotIn("官方要求对齐", html)
        self.assertNotIn("Video + Audio Evidence", html)
        self.assertNotIn("不是只交一个求解器", html)

    def test_evolution_loop_uses_dynamic_replay_panel(self):
        from web_agent_demo.server import render_index

        html = render_index()

        self.assertNotIn("evolution-step-generate", html)
        self.assertNotIn("data-evolution-step", html)
        self.assertNotIn("function paintEvolutionPanel()", html)
        self.assertIn("memory_recall", html)
        self.assertIn("memory_writeback", html)
        self.assertIn("future_policy_shift", html)
        self.assertIn("data-secret-handling", html)
        self.assertIn("function renderMemoryPage", html)

    def test_case_listing_exposes_large_seed301_without_local_paths(self):
        from web_agent_demo.server import list_cases

        cases = list_cases()

        self.assertTrue(any(case["id"] == "large_seed301" for case in cases))
        self.assertTrue(all("path" not in case for case in cases))
        self.assertTrue(all("scenario_name" in case for case in cases))
        self.assertTrue(all("scenario_type" in case for case in cases))
        self.assertTrue(all("risk_tags" in case for case in cases))
        self.assertTrue(all("operator_note" in case for case in cases))
        self.assertTrue(all("source_type" in case for case in cases))
        large_case = next(case for case in cases if case["id"] == "large_seed301")
        self.assertEqual(large_case["scenario_name"], "官方大规模候选调度")
        self.assertEqual(large_case["source_type"], "official_case")
        self.assertIn("候选行多", large_case["risk_tags"])

    def test_blueprint_exposes_agent_capabilities(self):
        from autosolver_agent.system import get_agent_blueprint

        blueprint = get_agent_blueprint()

        self.assertIn("objective", blueprint)
        self.assertIn("review_alignment", blueprint)
        self.assertGreaterEqual(len(blueprint["capabilities"]), 4)
        self.assertTrue(any(item["id"] == "critic" for item in blueprint["capabilities"]))
        self.assertTrue(any(item["id"] == "self_evolution" for item in blueprint["capabilities"]))
        self.assertTrue(any(item["id"] == "production_solver" for item in blueprint["strategy_catalog"]))
        alignment = blueprint["review_alignment"]
        self.assertEqual(alignment["source"]["type"], "competition_delivery_requirements")
        self.assertIn("solution_quality", alignment["review_dimensions"])
        self.assertIn("autonomous_iteration", alignment["review_dimensions"])
        self.assertIn("technical_report", alignment["review_dimensions"])
        self.assertEqual(len(alignment["agent_requirements"]), 4)

    def test_api_payload_uses_agent_controller(self):
        from web_agent_demo import server

        fake_report = {
            "case_id": "large_seed301",
            "regime": "large",
            "status": "ok",
            "wall_time_s": 1.23,
            "features": {"tasks": 40, "couriers": 80, "rows": 1234},
            "best": {
                "strategy": "production_solver",
                "local_cost": 657.1,
                "valid": True,
                "covered_tasks": 40,
                "total_tasks": 40,
                "groups": 40,
                "used_couriers": 40,
                "uncovered_tasks": [],
            },
            "rounds": [
                {
                    "round": 1,
                    "reason": "initial diverse exploration",
                    "strategies": [
                        {
                            "name": "greedy_baseline",
                            "local_cost": 700.0,
                            "accepted": True,
                            "elapsed_ms": 10.0,
                            "valid": True,
                            "covered_tasks": 40,
                            "total_tasks": 40,
                        }
                    ],
                }
            ],
            "events": [{"type": "attempt_result", "strategy": "greedy_baseline", "accepted": True}],
            "solution": [("T0000", ["C000"])],
        }

        with mock.patch.object(server, "run_case_agent", return_value=fake_report):
            payload = server.build_agent_payload("large_seed301", budget_s=10.0)

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["report"]["best"]["strategy"], "production_solver")
        self.assertEqual(json.loads(json.dumps(payload))["status"], "ok")

    def test_agent_stream_uses_live_observer_contract(self):
        from autosolver_agent import system

        seen = []

        def observer(event):
            seen.append(event["type"])

        fake_module = mock.Mock()
        fake_module._solution_expected_cost.return_value = 1.0
        fake_module._fallback_official_greedy.return_value = []
        fake_module._solve_single_task_multidispatch.return_value = []
        fake_module._solve_disjoint_then_multidispatch.return_value = []
        fake_module._solve_pair_potential_matching.return_value = []
        fake_module._solve_sparse_cover.return_value = []
        fake_module._solve_low_global_column_search.return_value = []
        fake_module._solve_low_column_search.return_value = []
        fake_module._solve_scarce_k2_column_search.return_value = []
        fake_module._solve_scarce_bundle_mcf_enum.return_value = []
        fake_module.solve.return_value = []
        fake_evolution = mock.Mock()
        fake_evolution.memory_path = "mock-evolution-memory.jsonl"
        fake_evolution.registry_path = "mock-strategy-registry.json"
        fake_evolution.trusted_strategies.return_value = []
        fake_evolution.generate_strategy.return_value = SimpleNamespace(strategy_id="gen_test_v001", path="gen_test_v001.py")
        fake_evolution.safety_check.return_value = SimpleNamespace(passed=False, reason="mock safety gate")

        with mock.patch.object(system, "load_solver", return_value=fake_module), mock.patch.object(system, "parse_candidates", return_value=([("T0000", ("T0000",), "C000", 1.0, 0.9, 0)], {"T0000"})), mock.patch.object(system, "infer_regime", return_value="large"), mock.patch.object(system, "EvolutionManager", return_value=fake_evolution), mock.patch.object(system, "summarize_solution", return_value={"valid": True, "covered_tasks": 1, "total_tasks": 1, "groups": 0, "used_couriers": 0, "uncovered_tasks": [], "riders_per_group": {}, "tasks_per_group": {}, "invalid_reasons": []}):
            report = system.run_agent("task_id_list\nT0000\tC000\t1\t0.9\n", budget_s=1.0, observer=observer)

        self.assertEqual(report["status"], "ok")
        self.assertIn("perception", seen)
        self.assertIn("evolution_generate", seen)
        self.assertIn("evolution_validate", seen)
        self.assertIn("final", seen)
        self.assertTrue(any(item in seen for item in ["attempt_result", "best_update"]))


if __name__ == "__main__":
    unittest.main()
