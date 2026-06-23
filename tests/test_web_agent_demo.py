from __future__ import annotations

import json
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest import mock


class WebAgentDemoTest(unittest.TestCase):
    def test_home_page_contains_agent_system_shell(self):
        from web_agent_demo.server import render_index

        html = render_index()
        asset_root = Path(__file__).resolve().parents[1] / "web_agent_demo" / "static" / "leaflet"
        self.assertTrue((asset_root / "leaflet.js").exists())
        self.assertTrue((asset_root / "leaflet.css").exists())

        self.assertIn("AutoSolver Agent", html)
        self.assertIn("Real-time Dispatch Assignment Optimization", html)
        self.assertIn("Relative Improvement vs Greedy", html)
        self.assertIn("large_seed301", html)
        self.assertIn("00:00:08", html)
        self.assertIn("$657.10", html)
        self.assertIn("+68.7%", html)
        self.assertIn("id=\"run-agent\"", html)
        self.assertIn("运行派单推理", html)
        self.assertIn("选择调度场景", html)
        self.assertIn("data-case=\"large_seed301\"", html)
        self.assertIn("data-case=\"medium_seed201\"", html)
        self.assertIn("data-case=\"scarce_couriers_seed401\"", html)
        self.assertIn("data-case=\"low_willingness_seed501\"", html)
        self.assertIn("data-map-action=\"routes\"", html)
        self.assertIn("data-map-action=\"locate\"", html)
        self.assertIn("data-map-action=\"fit\"", html)
        self.assertIn("data-map-action=\"depots\"", html)
        self.assertIn("data-map-action=\"fullscreen\"", html)
        self.assertIn("id=\"zoom-in\"", html)
        self.assertIn("id=\"expand-graph\"", html)
        self.assertIn("ReasonGraph 推理链路", html)
        self.assertIn("输入订单与骑手", html)
        self.assertIn("场景识别", html)
        self.assertIn("候选策略生成", html)
        self.assertIn("派单可行性校验", html)
        self.assertIn("成本 / 风险评估", html)
        self.assertIn("最终派单方案", html)
        self.assertIn("<strong>待推理</strong>", html)
        self.assertIn("function updateReasonMetrics", html)
        self.assertIn("function setNodeMetric", html)
        self.assertNotIn("<strong>1.00</strong>", html)
        self.assertNotIn("<strong>0.96</strong>", html)
        self.assertNotIn("<strong>0.89</strong>", html)
        self.assertNotIn("<span>可信度</span><strong>--</strong>", html)
        self.assertNotIn("<span>置信度</span><strong>--</strong>", html)
        self.assertIn("合单优先", html)
        self.assertIn("多派候选", html)
        self.assertIn("局部修复", html)
        self.assertIn("贪心基线", html)
        self.assertIn("风险平衡", html)
        self.assertIn('data-branch="S1"', html)
        self.assertIn("selectedBranchForReport", html)
        self.assertIn("renderStrategyCards", html)
        self.assertIn("const revealStrategyData = Boolean(hasReport || reasoningStatus === \"selected\" || reasoningStatus === \"rejected\");", html)
        self.assertIn("const showScoreOnCard = Boolean(isBest || isEvaluating || !hasReport && reasoningStatus === \"rejected\");", html)
        self.assertIn("const showEvidenceOnCard = Boolean(isBest || !hasReport && reasoningStatus === \"rejected\");", html)
        self.assertIn("const reasoningScore = showScoreOnCard && reasoningState && reasoningState.scores", html)
        self.assertIn("strategy.dataset.strategyEvidence = revealStrategyData && sampleItem.evidence ? sampleItem.evidence : \"\";", html)
        self.assertIn("const evidence = showEvidenceOnCard && sampleItem.evidence", html)
        self.assertIn('isEvaluating ? "计算中"', html)
        self.assertIn("let currentReasoningState = null", html)
        self.assertIn("let simulationSampleLoadPromise = null", html)
        self.assertIn("function reasoningOrderForSample", html)
        self.assertIn("function setReasoningState", html)
        self.assertIn("function yieldUi", html)
        self.assertIn("function ensureSimulationSampleReady", html)
        self.assertIn("await ensureSimulationSampleReady()", html)
        self.assertIn("const DEMO_REASONING_TARGET_MS = 10000", html)
        self.assertIn("function waitUntilElapsed", html)
        self.assertIn("await waitUntilElapsed(reasoningStartedAt, DEMO_REASONING_TARGET_MS)", html)
        self.assertIn("wall_time_s: 10", html)
        self.assertIn("function loadSimulationScenario", html)
        self.assertIn("await loadSimulationScenario(button.dataset.scenario)", html)
        self.assertIn("data-reasoning-status", html)
        self.assertIn('document.body.classList.add("pending-run", "sample-preview", "reasoning")', html)
        self.assertIn("setReasoningState(sample, evaluationOrder.length, true)", html)
        self.assertNotIn("先锁定策略，再生成派单线", html)
        self.assertNotIn('class="strategy best"', html)
        self.assertNotIn("S1 ✓</h4>", html)
        self.assertIn("实时派单地图", html)
        self.assertNotIn("仓库", html)
        self.assertIn("商家", html)
        self.assertNotIn("配送点", html)
        self.assertNotIn("订单组", html)
        self.assertIn("订单", html)
        self.assertIn("骑手", html)
        self.assertIn("派单关系", html)
        self.assertIn("长距离低噪", html)
        self.assertIn("骑手位置", html)
        self.assertIn("leaflet.css", html)
        self.assertIn("leaflet.js", html)
        self.assertIn("id=\"tile-map\"", html)
        self.assertIn("id=\"real-map\"", html)
        self.assertIn("basemaps.cartocdn.com", html)
        self.assertIn("renderRasterTileBasemap", html)
        self.assertIn("tileWorldPoint", html)
        self.assertIn("/assets/leaflet/leaflet.js", html)
        self.assertIn("/assets/leaflet/leaflet.css", html)
        self.assertNotIn("unpkg.com/leaflet", html)
        self.assertIn("router.project-osrm.org", html)
        self.assertIn("pointToLatLng", html)
        self.assertIn("latLngToPoint", html)
        self.assertIn("upgradeDispatchRoutesWithOsrm", html)
        self.assertIn("const feasiblePassed = Math.max(0, Math.min(covered, total));", html)
        self.assertIn("`${feasiblePassed} / ${feasibleTotal}`", html)
        self.assertNotIn("report.best && report.best.groups, Object.keys((profile && profile.assignments)", html)
        self.assertIn("renderLeafletDispatchMap", html)
        self.assertIn("ensureLeafletMap", html)
        self.assertIn("fetchOsrmRoute", html)
        self.assertIn("leaflet-ready", html)
        self.assertIn("leaflet-dispatch-route", html)
        self.assertIn("data-route-role=\"main\"", html)
        self.assertNotIn("      renderLeafletDispatchMap(profile, entityPoints);", html)
        self.assertIn("map-entities", html)
        self.assertIn("pickup-leg", html)
        self.assertIn("dispatchArrowFor", html)
        self.assertIn("dispatch-arrow", html)
        self.assertIn("dispatch-hit-area", html)
        self.assertIn("等待运行派单推理", html)
        for fake_value in ["C017 + C035", "Merchant R02", "<span class=\"chip\">T0012</span>", "T0018<small>", "T0023<small>"]:
            self.assertNotIn(fake_value, html)
        self.assertNotIn("selected-route", html)
        self.assertNotIn("candidate-route", html)
        self.assertIn("派单决策解释", html)
        self.assertIn("派单详情：${assignment.pickup || assignment.merchant || resolvedAssignment} → ${assignment.courier}", html)
        self.assertIn("骑手接单概率", html)
        self.assertIn("相对贪心基线", html)
        self.assertIn("候选派单策略对比", html)
        self.assertIn("最终 AutoSolver", html)
        self.assertIn("选中方案", html)
        self.assertIn("成本、风险、ETA 综合最优", html)
        self.assertIn("map-bg", html)
        self.assertIn("district", html)
        self.assertIn("anonymous-navigation-layer", html)
        self.assertIn("simulated-map-layer", html)
        self.assertNotIn("/assets/reference-dark-map.png", html)
        self.assertNotIn("reference-dark-map", html)
        self.assertIn("renderSimulatedBaseMap", html)
        self.assertIn("building-block", html)
        self.assertIn("traffic-band", html)
        self.assertIn("commerce-hotspot", html)
        self.assertIn("assignments:", html)
        self.assertIn("assignmentForEntity", html)
        self.assertIn("sceneLabels", html)
        self.assertIn("caseCatalog", html)
        self.assertIn("profileForCase", html)
        self.assertIn("renderAssignmentDetail", html)
        self.assertIn("renderFinalEntityDetail", html)
        self.assertIn("renderRouteDetail", html)
        self.assertIn("renderStrategyDetail", html)
        self.assertIn("renderTableRowDetail", html)
        self.assertIn("setDetailContext", html)
        self.assertIn("updateReasonSummary", html)
        self.assertIn("label.dataset.assignment", html)
        self.assertIn("dispatch-link", html)
        self.assertIn("courier-node", html)
        self.assertIn("function applyMapFocus", html)
        self.assertIn("function labelOffsetFor", html)
        self.assertIn("function simulationPreviewMap", html)
        self.assertIn("function simulationFinalMap", html)
        self.assertIn("function renderEntityPreviewDetail", html)
        self.assertIn("function runCurrentSimulationSample", html)
        self.assertIn("function applySimulationSample", html)
        self.assertIn("function refreshSimulationSample", html)
        self.assertIn("function resetMapControlState", html)
        self.assertIn('frame.classList.remove("hide-entities", "hide-dispatch-routes", "hide-candidates", "zoomed", "locating")', html)
        self.assertIn("/api/simulation-sample?", html)
        self.assertIn("sample-preview", html)
        self.assertIn("hideLabel: true", html)
        self.assertIn('assignments: []', html)
        self.assertIn("focus-selected", html)
        self.assertIn("data-selected-assignment", html)
        self.assertIn('pin.classList.toggle("active-assignment"', html)
        self.assertIn("const showInOverview = Boolean(!focusMode && !longPickup);", html)
        self.assertIn('dispatchArrowFor(pickupRoute, `${arrowCls}${showInOverview ? " selected-overview" : ""}${longPickup ? " long-pickup" : ""}`, assignment.id, isActive, routeStyle, pickupMeta)', html)
        self.assertIn('event.target.closest(".map-label, .pin, .dispatch-link, .dispatch-arrow, .dispatch-hit-area")', html)
        self.assertIn("function renderAssignmentOverviewDetail", html)
        self.assertIn("派单总览：全部商家已自动连线", html)
        self.assertIn("商家点同时代表该商家的", html)
        self.assertIn("function buildRoadGraph", html)
        self.assertIn("function shortestRoadGraphPath", html)
        self.assertIn("function endpointConnectorFor", html)
        self.assertIn("function dispatchEndpointConnectorsFor", html)
        self.assertIn("route.endpointConnectors", html)
        self.assertIn("[startPoint, ...(coreRoute || []), endPoint]", html)
        self.assertIn("endpoint-connector", html)
        self.assertIn("const isActive = Boolean(focusMode && assignment.id === selectedAssignment);", html)
        self.assertIn("longRouteClass", html)
        self.assertIn("long-pickup", html)
        self.assertNotIn("long-delivery", html)
        self.assertIn("selected-overview", html)
        self.assertIn("overviewAssignmentIdForRoutes", html)
        self.assertIn("renderReferenceRouteBundle", html)
        self.assertIn("routeBundlePlanSegments", html)
        self.assertIn("uniqueRouteStops", html)
        self.assertNotIn("route-stop-label", html)
        self.assertNotIn("data-bundle-corridor", html)
        self.assertIn("route-bundle-highlight", html)
        self.assertIn("route-bundle-candidate", html)
        self.assertNotIn("route-bundle-label", html)
        self.assertNotIn("routeBundleLabel", html)
        self.assertNotIn("escapeHtml", html)
        self.assertIn("const overviewAssignmentId = focusMode ? selectedAssignment : overviewAssignmentIdForRoutes(profile.dispatchMap.assignments, entityPoints, mapLayers, selectedAssignment);", html)
        self.assertIn("const pickupIsShort = !longRouteClass", html)
        self.assertIn("const noShortLegPenalty = pickupIsShort ? 0 : 160;", html)
        self.assertIn('const active = Boolean(hasDispatch && focused && node.dataset.assignment === selectedAssignment);', html)
        self.assertIn("hide-dispatch-routes", html)
        self.assertIn("派单关系线已隐藏，仅保留点位", html)
        self.assertIn("assignment-overview", html)
        self.assertIn("overview-route", html)
        self.assertIn("hide-entities", html)
        self.assertIn(".map-panel.active", html)
        self.assertIn("roadFollowingRoute", html)
        self.assertIn("closestRoadTransfer", html)
        self.assertIn("function routeMetaAttributes", html)
        self.assertIn("function dispatchHitAreaFor", html)
        self.assertIn("function displayPositionsForLabels", html)
        self.assertIn("function sampleOrderById", html)
        self.assertIn("function candidateForPair", html)
        self.assertIn("function strategyLabelForAssignment", html)
        self.assertIn("dataset.detailType", html)
        self.assertIn('"route-points": pickupRoute.length', html)
        self.assertIn('leg: "courier-to-merchant"', html)
        self.assertNotIn("const deliveryRoutes = orderPoints.map", html)
        self.assertNotIn('class="${deliveryClass}"', html)
        self.assertNotIn('order: orders[orderIndex] || ""', html)
        self.assertIn('merchant: assignment.pickup', html)
        self.assertIn("entities: [...preview.entities]", html)
        self.assertIn("map_orders: []", html)
        self.assertIn("strategy_id: assignment.strategy_id || sample.selected_strategy_id", html)
        self.assertIn('if (target.dataset.leg && renderRouteDetail(profile, target.dataset.assignment || profile.selected, target.dataset)) return;', html)
        self.assertIn('if (target.dataset.entity && renderFinalEntityDetail(profile, target.dataset.entity)) return;', html)
        self.assertIn('document.querySelector(".branch-grid").addEventListener("click"', html)
        self.assertIn('document.querySelector(".table-panel tbody").addEventListener("click"', html)
        self.assertIn('renderStrategyDetail(strategy.dataset.branch || "")', html)
        self.assertIn("renderTableRowDetail(row)", html)
        self.assertIn('data-row-type="strategy-candidate"', html)
        self.assertIn('data-row-type="preview-candidate"', html)
        self.assertIn('pin.dataset.rawX', html)
        self.assertIn('pin.classList.toggle("avoided"', html)
        self.assertIn("const showSelectedLabel = false;", html)
        self.assertNotIn("<small>ETA", html)
        self.assertNotIn("selectedLabelHtml", html)
        self.assertNotIn("订单期望 ETA", html)
        self.assertIn("线路详情：", html)
        self.assertIn("骑手详情：", html)
        self.assertIn("商家详情：", html)
        self.assertNotIn("订单详情：", html)
        self.assertIn("if (!relatedCandidates.length)", html)
        self.assertIn("profile.dispatchMap.assignments.map((assignment", html)
        self.assertNotIn("profile.dispatchMap.assignments.slice(0, 8).map", html)
        self.assertIn("rain-streak", html)
        self.assertIn("rain-sheen", html)
        self.assertIn("density_profile", html)
        self.assertIn("order_count: orderCount", html)
        self.assertIn("共 ${orderCount} 单", html)
        self.assertNotIn('const cls = index === 0 ? "dispatch-link primary"', html)
        for forbidden in ["Proxy score", "local_cost", "40/40", "本地分数", "本地评分", "官方成绩"]:
            self.assertNotIn(forbidden, html)

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
        from web_agent_demo.server import build_simulated_scenario_sample, list_simulated_scenarios

        scenarios = list_simulated_scenarios()

        self.assertGreaterEqual(len(scenarios), 5)
        self.assertTrue(all(item["sample_count"] == 10 for item in scenarios))
        self.assertTrue(all(item["map_style"] == "baidu_like_simulated" for item in scenarios))
        for scenario in scenarios:
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
                self.assertGreaterEqual(len(sample["map_layers"]["roads"]), 8)
                self.assertGreaterEqual(len(sample["map_layers"]["districts"]), 12)
                self.assertGreaterEqual(len(sample["map_layers"]["roads"]), 40)
                self.assertGreaterEqual(len(sample["map_layers"]["building_blocks"]), 36)
                self.assertGreaterEqual(len(sample["map_layers"]["commerce_hotspots"]), 3)
                self.assertGreaterEqual(len(sample["map_layers"]["intersections"]), 6)
                self.assertIn(sample["summary"]["weather"], {"clear", "rain", "event"})
                self.assertIn("density_profile", sample["summary"])
                self.assertTrue(all(not road["name_visible"] for road in sample["map_layers"]["roads"]))
                merchant_points = [(float(item["x"]), float(item["y"])) for item in sample["merchants"]]
                courier_points = [(float(item["x"]), float(item["y"])) for item in sample["couriers"]]
                self.assertGreater(len(set(merchant_points)), 2)
                self.assertGreater(len(set(courier_points)), 5)
                for merchant in sample["merchants"]:
                    delivery_points = merchant["delivery_points"]
                    self.assertEqual(len(delivery_points), 1)
                    for point in delivery_points:
                        self.assertEqual(point["kind"], "merchant_order")
                        self.assertEqual(point["parent_merchant_id"], merchant["id"])
                        self.assertEqual((point["x"], point["y"]), (merchant["x"], merchant["y"]))

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

        self.assertEqual(len(samples), 60)
        self.assertTrue({"S1", "S2", "S3", "S4", "S5"}.issubset(selected))
        for sample in samples:
            path = sample["strategy_path"]
            self.assertEqual(len(path), 5)
            self.assertEqual(sum(1 for item in path if item["status"] == "selected"), 1)
            self.assertEqual(path[0]["id"], sample["selected_strategy_id"])
            self.assertEqual(path[0]["score"], max(item["score"] for item in path))
            self.assertIn("strategy_decision", sample)
            self.assertIn("candidate_competition", sample["strategy_decision"]["metrics"])
            self.assertTrue(all("evidence" in item for item in path))
            scene_id = sample["scenario_id"]
            selected_by_scene.setdefault(scene_id, set()).add(sample["selected_strategy_id"])
            major_evaluated_by_scene.setdefault(scene_id, set()).update(item["id"] for item in path[:3])
            for assignment in sample["assignments"]:
                self.assertIn("merchant_id", assignment)
                self.assertIn("courier_id", assignment)
                self.assertIn("backup_courier_id", assignment)
                self.assertGreater(float(assignment["cost"]), 0)
                self.assertGreaterEqual(int(assignment["eta_min"]), 6)
                self.assertIn(assignment["risk"], {"Low", "Medium", "High"})
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
        self.assertIn("evolution_generate", html)
        self.assertIn("evolution_validate", html)
        self.assertIn("evolution_trial", html)
        self.assertIn("handleProgressEvent", html)

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
