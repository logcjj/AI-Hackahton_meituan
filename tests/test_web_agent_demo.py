from __future__ import annotations

import json
import unittest
from types import SimpleNamespace
from unittest import mock


class WebAgentDemoTest(unittest.TestCase):
    def test_home_page_contains_agent_system_shell(self):
        from web_agent_demo.server import render_index

        html = render_index()
        self.assertIn("AutoSolver Agent", html)
        self.assertIn("美团即时配送 AI 可解释派单决策工作台", html)
        self.assertIn("--dashboard-width: 1280px", html)
        self.assertIn("--dashboard-height: 720px", html)
        self.assertIn("function syncDashboardScale", html)
        self.assertIn('document.documentElement.style.setProperty("--dashboard-scale"', html)
        self.assertIn(".map-frame.dragging-map", html)
        self.assertIn(".map-bg { opacity: .38; z-index: 1; pointer-events: none; }", html)
        self.assertIn("相比贪心基线优化", html)
        self.assertNotIn("Real-time Dispatch Assignment Optimization", html)
        self.assertNotIn("Relative Improvement vs Greedy", html)
        self.assertIn("large_seed301", html)
        self.assertIn("00:00:08", html)
        self.assertIn("$657.10", html)
        self.assertIn("+68.7%", html)
        self.assertIn("id=\"run-agent\"", html)
        self.assertIn("运行派单推理", html)
        self.assertIn("调度场景", html)
        self.assertNotIn("class=\"scene-strip\"", html)
        self.assertNotIn("class=\"scene-button\"", html)
        self.assertNotIn("10 samples", html)
        self.assertNotIn("samples ·", html)
        self.assertIn("id=\"case-select\"", html)
        self.assertIn("option.dataset.scenario = item.id", html)
        self.assertIn("selectedScenarioId", html)
        self.assertIn("data-map-action=\"routes\"", html)
        self.assertIn("data-map-action=\"locate\"", html)
        self.assertIn("data-map-action=\"fit\"", html)
        self.assertIn("data-map-action=\"depots\"", html)
        self.assertIn("data-map-action=\"fullscreen\"", html)
        self.assertIn("id=\"zoom-in\"", html)
        self.assertIn("id=\"expand-graph\"", html)
        self.assertIn("ReasonGraph 推理链路", html)
        self.assertIn("overflow-y: auto;", html)
        self.assertIn("grid-template-columns: 30px 24px minmax(0, 1fr) 58px;", html)
        self.assertIn("grid-template-columns: 26px minmax(0, 1fr) 86px;", html)
        self.assertIn(".node p { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }", html)
        self.assertIn(".node p br { display: none; }", html)
        self.assertNotIn("margin-left: 46px;", html)
        self.assertNotIn("width: calc(100% - 54px);", html)
        self.assertIn("输入订单与骑手", html)
        self.assertIn("场景识别", html)
        self.assertIn("动态策略组合", html)
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
        self.assertIn("组合搜索 / MCF", html)
        self.assertIn("单任务多派", html)
        self.assertIn("覆盖修复搜索", html)
        self.assertIn("贪心基线", html)
        self.assertIn("低意愿 / 自适应补充", html)
        self.assertIn("下方是算法族分组，不是固定调用顺序", html)
        self.assertIn("production solver", html)
        self.assertIn("evolution replay", html)
        self.assertIn('data-branch="S1"', html)
        self.assertIn('id="expand-graph" aria-expanded="false"', html)
        self.assertIn('event.currentTarget.setAttribute("aria-expanded"', html)
        self.assertIn(".left-panel.expanded .node p br", html)
        self.assertIn(".left-panel.expanded .strategy p br", html)
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
        self.assertIn("await loadSimulationScenario(option.dataset.scenario)", html)
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
        self.assertNotIn("低优先级", html)
        self.assertIn("骑手位置", html)
        self.assertIn("renderProjectBasemapState", html)
        self.assertIn("https://unpkg.com/maplibre-gl@5.24.0/dist/maplibre-gl.js", html)
        self.assertIn("https://unpkg.com/maplibre-gl@5.24.0/dist/maplibre-gl.css", html)
        self.assertIn("https://tiles.openfreemap.org/styles/positron", html)
        self.assertIn("运营分析浅色区域", html)
        self.assertIn("hideSemiRealMapTextLayers", html)
        self.assertIn("semiRealMapTextLayerAudit", html)
        self.assertIn('semiRealMap.setLayoutProperty(layer.id, "visibility", "none")', html)
        self.assertIn("semiRealMapRegions", html)
        self.assertNotIn("https://tiles.openfreemap.org/styles/bright", html)
        self.assertNotIn("https://tiles.openfreemap.org/styles/liberty", html)
        self.assertNotIn("美团浅色 LBS 底图", html)
        self.assertNotIn("商圈标准路网底图", html)
        self.assertIn("id=\"semi-real-map\"", html)
        self.assertIn("刷新位置", html)
        self.assertIn("id=\"refresh-map\"", html)
        self.assertIn("刷新地图", html)
        self.assertIn('>点位</button>', html)
        self.assertIn('>线路</button>', html)
        self.assertIn('>适配</button>', html)
        self.assertIn('>定位</button>', html)
        self.assertIn('>全屏</button>', html)
        self.assertIn('button.textContent = expanded ? "退出" : "全屏"', html)
        self.assertIn("refreshSemiRealMap", html)
        self.assertIn("syncSemiRealMapOverlay", html)
        self.assertIn("已刷新配送区域", html)
        self.assertNotIn("已切换地图底图", html)
        self.assertIn("meituan_delivery_project_map_v3", html)
        self.assertIn("delivery_routes_optimization_maplibre_clone", html)
        self.assertIn("delivery-routes-road-graph-v3", html)
        self.assertIn("map-trace", html)
        self.assertNotIn("leaflet.css", html)
        self.assertNotIn("leaflet.js", html)
        self.assertNotIn("id=\"tile-map\"", html)
        self.assertNotIn("id=\"real-map\"", html)
        self.assertNotIn("basemaps.cartocdn.com", html)
        self.assertNotIn("renderRasterTileBasemap", html)
        self.assertNotIn("tileWorldPoint", html)
        self.assertNotIn("unpkg.com/leaflet", html)
        self.assertNotIn("router.project-osrm.org", html)
        self.assertNotIn("pointToLatLng", html)
        self.assertNotIn("latLngToPoint", html)
        self.assertIn("couriers.map((courierId, courierIndex) =>", html)
        self.assertIn("function dispatchRelationshipRoute", html)
        self.assertIn("const pickupRoute = dispatchRelationshipRoute(courierPoint, pickupPoint, `${assignment.id}:${courierId}:${courierIndex}`, obstacles);", html)
        self.assertNotIn("roadFollowingRoute(courierPoints[0], pickupPoint, mapLayers)", html)
        self.assertIn('"route-source": "dispatch-relationship-line-v4"', html)
        self.assertNotIn('"route-source": "delivery-routes-road-graph-v3"', html)
        self.assertIn('"endpoint-connectors": Array.isArray(pickupRoute.endpointConnectors) ? pickupRoute.endpointConnectors.length : 0', html)
        self.assertNotIn("function stableDispatchRoute", html)
        self.assertNotIn('"route-source": "stable-local"', html)
        self.assertNotIn("upgradeDispatchRoutesWithOsrm", html)
        self.assertIn("const feasiblePassed = Math.max(0, Math.min(covered, total));", html)
        self.assertIn("`${feasiblePassed} / ${feasibleTotal}`", html)
        self.assertNotIn("report.best && report.best.groups, Object.keys((profile && profile.assignments)", html)
        self.assertNotIn("renderLeafletDispatchMap", html)
        self.assertNotIn("ensureLeafletMap", html)
        self.assertNotIn("fetchOsrmRoute", html)
        self.assertNotIn("leaflet-ready", html)
        self.assertNotIn("leaflet-dispatch-route", html)
        self.assertIn("data-route-role=\"main\"", html)
        self.assertNotIn("      renderLeafletDispatchMap(profile, entityPoints);", html)
        self.assertIn("map-entities", html)
        self.assertIn("pickup-leg", html)
        self.assertIn("dispatchArrowFor", html)
        self.assertIn("dispatch-arrow", html)
        self.assertNotIn("dispatch-hit-area", html)
        self.assertIn("dispatch-visual", html)
        self.assertIn("function routeClickMidpoint", html)
        self.assertIn("function dispatchRouteClickTargetFor", html)
        self.assertIn("function routeObstacleClearance", html)
        self.assertIn("function alignDispatchArrowsToRenderedPaths", html)
        self.assertIn('arrow.dataset.arrowAnchored = "rendered-path"', html)
        self.assertIn("alignDispatchArrowsToRenderedPaths(svg);", html)
        self.assertIn("const d = dispatchPathFor(points);", html)
        self.assertIn("const merchantObstacleEntries = (profile.dispatchMap.entities || [])", html)
        self.assertIn("merchantId !== assignment.pickup", html)
        self.assertIn("route-click-target", html)
        self.assertIn(".route-svg { z-index: 7; pointer-events: none; }", html)
        self.assertIn("const entityPinAtClientPoint = (event) =>", html)
        self.assertIn("distance <= 7", html)
        self.assertIn("pointer-events: stroke", html)
        self.assertNotIn("pointer-events: bounding-box", html)
        self.assertIn("pointer-events: none;", html)
        self.assertIn("等待运行派单推理", html)
        for fake_value in ["C017 + C035", "Merchant R02", "<span class=\"chip\">T0012</span>", "T0018<small>", "T0023<small>"]:
            self.assertNotIn(fake_value, html)
        self.assertNotIn("selected-route", html)
        self.assertNotIn("candidate-route", html)
        self.assertIn("派单决策解释", html)
        self.assertIn("派单详情：${assignment.pickup || assignment.merchant || resolvedAssignment} → ${assignment.courier}", html)
        self.assertIn('id="prob-label">指标</span>', html)
        self.assertIn("function setProbabilityMetric", html)
        self.assertIn('setProbabilityMetric("商家覆盖率"', html)
        self.assertIn('setProbabilityMetric("策略评分"', html)
        self.assertIn('setProbabilityMetric("骑手接单意愿"', html)
        self.assertNotIn("接单 / 覆盖概率", html)
        self.assertIn("相对贪心基线", html)
        self.assertIn("候选派单策略对比", html)
        self.assertIn("最终 AutoSolver", html)
        self.assertIn("选中方案", html)
        self.assertIn("动态策略路径最高分，成本、风险、履约时效综合最优", html)
        self.assertIn("sampleScoreForBranch", html)
        self.assertIn("sampleSelectedScore(currentSimulationSample)", html)
        self.assertNotIn('data-score="0.89"', html)
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
        self.assertIn("const activeCouriers = new Set()", html)
        self.assertIn('if (hasFinalAssignments && kind === "courier" && !activeCouriers.has(entity.id)) return;', html)
        self.assertIn("caseCatalog", html)
        self.assertIn("profileForCase", html)
        self.assertIn("renderAssignmentDetail", html)
        self.assertIn("renderFinalEntityDetail", html)
        self.assertIn("renderRouteDetail", html)
        self.assertIn("renderStrategyDetail", html)
        self.assertIn("renderTableRowDetail", html)
        self.assertIn("最终派单 <code>${merchantId} → ${courierId}</code>", html)
        self.assertIn("该线属于最终派单 ${resolvedAssignment}：商家 ${merchantId} 派给骑手 ${courierId}", html)
        self.assertIn("setDetailContext", html)
        self.assertIn("updateReasonSummary", html)
        self.assertIn("label.dataset.assignment", html)
        self.assertIn("dispatch-link", html)
        self.assertIn("courier-node", html)
        self.assertIn("function applyMapFocus", html)
        self.assertIn("function labelOffsetFor", html)
        self.assertIn("function simulationPreviewMap", html)
        self.assertIn("function simulationFinalMap", html)
        self.assertIn("assignment_reconciled_variant: renderedDispatchMap.assignment_reconciled_variant || fallback.assignment_reconciled_variant", html)
        self.assertNotIn("assignment_reconciled_variant: renderedDispatchMap.anchor_variant || renderedDispatchMap.assignment_reconciled_variant", html)
        self.assertIn("function renderEntityPreviewDetail", html)
        self.assertIn("function runCurrentSimulationSample", html)
        self.assertIn("function applySimulationSample", html)
        self.assertIn("function refreshSimulationSample", html)
        self.assertIn("function resetMapControlState", html)
        self.assertIn("function resetSemiRealMapViewportForScenario", html)
        self.assertIn('resetSemiRealMapViewportForScenario("refresh-position-reset")', html)
        self.assertIn("map.jumpTo({center: region.center, zoom: region.zoom", html)
        self.assertIn('frame.classList.remove("hide-entities", "hide-dispatch-routes", "hide-candidates", "locating")', html)
        self.assertIn('frame.dataset.locating = "false"', html)
        self.assertIn('frame.dataset.routesHidden = "false"', html)
        self.assertIn('frame.dataset.entitiesMuted = "false"', html)
        self.assertNotIn(".map-frame.zoomed", html)
        self.assertIn("const targetZoom = Math.min(18.5, map.getZoom() + 0.85)", html)
        self.assertIn("const targetZoom = Math.max(10.5, map.getZoom() - 0.85)", html)
        self.assertIn("frame.dataset.zoomLevel = targetZoom.toFixed(2)", html)
        self.assertIn("map.easeTo({zoom: targetZoom, duration: 360})", html)
        self.assertIn('semiRealMap.on("move", handleSemiRealMapMove)', html)
        self.assertIn('semiRealMap.on("moveend", handleSemiRealMapMoveEnd)', html)
        self.assertIn('semiRealMap.on("movestart", handleSemiRealMapMoveStart)', html)
        self.assertIn("function syncCurrentProfileProjectionToMapViewport", html)
        self.assertIn('syncCurrentProfileProjectionToMapViewport("viewport-live")', html)
        self.assertIn('frame.dataset.mapMoving = "true"', html)
        self.assertIn('frame.dataset.mapMoving = "false"', html)
        self.assertIn('interactive: true', html)
        self.assertIn("semiRealMap.dragPan.enable()", html)
        self.assertIn("function screenNormToLngLat", html)
        self.assertIn("function projectEntityLngLatToScreen", html)
        self.assertIn("function syncRenderedAnchorsToViewport", html)
        self.assertIn("clampToMapSafeZone", html)
        self.assertNotIn("const safePoint = clampToMapSafeZone(projected, kind);", html)
        self.assertIn("entity.x = Number(projected[0].toFixed(4));", html)
        self.assertNotIn("now - semiRealMapLastLiveSyncAt < 32", html)
        self.assertIn("entity.rendered_in_view = projected[0] >= 0", html)
        self.assertIn("bindMapDragFallback", html)
        self.assertIn('frame.dataset.dragFallbackBound = "native-maplibre"', html)
        self.assertIn('frame.dataset.dragPan = "native"', html)
        self.assertIn('frame.addEventListener("mousedown", beginDrag, true)', html)
        self.assertIn('frame.addEventListener("touchstart", beginDrag, true)', html)
        self.assertIn('frame.addEventListener("dragstart", beginDrag, true)', html)
        self.assertIn('window.addEventListener("mousemove", moveDrag, true)', html)
        self.assertIn('window.addEventListener("dragend", finishDrag, true)', html)
        self.assertIn('window.addEventListener("mouseup", finishDrag, true)', html)
        self.assertIn('map.panBy([-dx, -dy], {duration: 260})', html)
        self.assertIn("semiRealMapViewport", html)
        self.assertIn(".map-frame.maplibre-ready .map-bg { display: none; opacity: 0; mix-blend-mode: normal; }", html)
        self.assertIn("const signSeed = routeSeed ||", html)
        self.assertIn("const curveX = (1 - t) * (1 - t)", html)
        self.assertIn("globalThis.__AUTO_SOLVER_DEBUG__ = debugStateSnapshot", html)
        self.assertIn('const isPersistentMapAction = (action) => action === "depots" || action === "routes" || action === "fullscreen";', html)
        self.assertIn("const clearTransientMapButtons = () =>", html)
        self.assertIn("const clearLocatingStateSoon = (frame, delay = 760) =>", html)
        self.assertIn('document.querySelectorAll(\'[data-map-action="fit"], [data-map-action="locate"], #zoom-in, #zoom-out, #recenter\')', html)
        self.assertIn("clearLocatingStateSoon(frame);", html)
        self.assertNotIn('button.classList.toggle("active");\\n          if (action === "depots")', html)
        self.assertIn("function reconcileDispatchPairsToVisibleMap", html)
        self.assertIn("const preferUniqueCouriers = couriers.length >= profile.dispatchMap.assignments.length", html)
        self.assertIn("const unusedCourierIds = new Set(couriers.map((courier) => courier.id))", html)
        self.assertIn("unusedCourierIds.delete(chosen.id)", html)
        self.assertIn("const reusePenalty = preferUniqueCouriers ? load * 10000 : load * 36", html)
        self.assertIn("const overlapPenalty = distance < 5.2 ? (5.2 - distance) * 90 : 0", html)
        self.assertIn("distance + reusePenalty + overlapPenalty", html)
        self.assertNotIn("return {courier, score: distance + load * 4.5};", html)
        self.assertIn("function enforceCourierSeparation", html)
        self.assertIn('entity.rendered_anchor_source = "maplibre-road-slot-fallback"', html)
        self.assertIn("const shouldReconcileAssignments = () => Boolean(", html)
        self.assertIn('profile.dispatchMap.stage === "simulation_final" || profile.dispatchMap.stage === "final"', html)
        self.assertIn("profile.dispatchMap.assignments = completeAssignments", html)
        self.assertIn("syncNormalizedAssignment(profile, assignment)", html)
        self.assertIn("function finalCourierTokensForAssignment", html)
        self.assertIn("function finalCourierForAssignment", html)
        self.assertIn("function assignmentStatsForProfile", html)
        self.assertIn("function syncReportMetricsFromAssignments", html)
        self.assertIn("report.best.used_couriers = stats.courierCount", html)
        self.assertIn("report.best.groups = stats.merchantCount", html)
        self.assertIn("report.best.order_tasks = stats.orderCount", html)
        self.assertIn("map_couriers: finalCouriers", html)
        self.assertIn("backup_couriers:", html)
        self.assertIn("const couriers = finalCourierTokensForAssignment(normalizedAssignment);", html)
        self.assertIn("if (finalCourierId && clickedCourierId && clickedCourierId !== finalCourierId) return false;", html)
        self.assertIn('if (mapPayload.stage === "simulation_final" || mapPayload.stage === "final")', html)
        self.assertIn("reconcileDispatchPairsToVisibleMap(profile);", html)
        self.assertIn("syncReportMetricsFromAssignments(currentReport, profile);", html)
        self.assertIn('const routeClickTarget = target.classList.contains("route-click-target");', html)
        self.assertIn('(target.classList.contains("dispatch-link") && !routeClickTarget)', html)
        self.assertIn("function dispatchRouteAtClientPoint(event, threshold = 14)", html)
        self.assertIn('document.querySelectorAll(".dispatch-visual.pickup-leg")', html)
        self.assertIn('const preferEntityTarget = Boolean(domTarget && (domTarget.classList.contains("pin") || domTarget.classList.contains("map-label")));', html)
        self.assertIn("const routeByPoint = preferEntityTarget ? null : dispatchRouteAtClientPoint(event);", html)
        self.assertIn("const target = preferEntityTarget ? domTarget : (routeByPoint || domTarget);", html)
        self.assertNotIn("const couriers = assignment.map_couriers || courierTokens(assignment.courier);", html)
        self.assertIn("densifyRoutePoints([start, startPoint, ...(coreRoute || []), endPoint, end], 4.8)", html)
        self.assertIn('frame.dataset.routesHidden = active ? "true" : "false"', html)
        self.assertIn('frame.dataset.entitiesMuted = hidden ? "true" : "false"', html)
        self.assertIn("/api/simulation-sample?", html)
        self.assertIn("sample-preview", html)
        self.assertIn("hideLabel: true", html)
        self.assertIn('assignments: []', html)
        self.assertIn("focus-selected", html)
        self.assertIn("data-selected-assignment", html)
        self.assertIn('pin.classList.toggle("active-assignment"', html)
        self.assertIn("const showInOverview = Boolean(!focusMode && assignment.id === selectedAssignment && !longPickup);", html)
        self.assertIn("const visiblePickupRoute = pickupRoute;", html)
        self.assertIn('const routePalette = ["#0f766e", "#11836e", "#147a64", "#0d9488", "#15803d", "#0f766e", "#11836e", "#147a64"];', html)
        self.assertNotIn('const routePalette = ["#16a34a", "#0f766e", "#2563eb", "#ca8a04"', html)
        self.assertIn(".map-frame.assignment-overview .dispatch-visual.pickup-leg { stroke: var(--route-color, var(--map-route)); stroke-width: 1.75; opacity: .72;", html)
        self.assertIn('"road-core-points": Array.isArray(pickupRoute.roadCore) ? pickupRoute.roadCore.length : visiblePickupRoute.length', html)
        self.assertIn('data-leg-index="${courierIndex}"', html)
        self.assertIn('dispatchArrowFor(visiblePickupRoute, `${arrowCls}${showInOverview ? " selected-overview" : ""}${longPickup ? " long-pickup" : ""}`, assignment.id, isActive, routeStyle, pickupMeta)', html)
        self.assertIn('event.target.closest(".map-label, .pin, .dispatch-link, .dispatch-arrow")', html)
        self.assertNotIn('event.target.closest(".map-label, .pin, .dispatch-link, .dispatch-arrow, .dispatch-hit-area")', html)
        self.assertNotIn("weather-bar", html)
        self.assertIn("function renderAssignmentOverviewDetail", html)
        self.assertIn("派单总览：全部商家已自动连线", html)
        self.assertIn("商家点同时代表该商家的", html)
        self.assertIn("function buildRoadGraph", html)
        self.assertIn("function shortestRoadGraphPath", html)
        self.assertIn("function endpointConnectorFor", html)
        self.assertIn("function dispatchEndpointConnectorsFor", html)
        self.assertIn("route.endpointConnectors", html)
        self.assertIn("[start, startPoint, ...(coreRoute || []), endPoint, end]", html)
        self.assertIn("endpoint-connector", html)
        self.assertIn("const isActive = Boolean(focusMode && assignment.id === selectedAssignment);", html)
        self.assertIn("longRouteClass", html)
        self.assertIn("long-pickup", html)
        self.assertNotIn("long-delivery", html)
        self.assertIn("selected-overview", html)
        self.assertIn("simplifyRoutePoints", html)
        self.assertIn("points.curveControl", html)
        self.assertIn("transfer && transfer.distance <= 0.85", html)
        self.assertIn("connector.direct.distance <= 1.4", html)
        self.assertNotIn("overviewAssignmentIdForRoutes", html)
        self.assertNotIn("renderReferenceRouteBundle", html)
        self.assertNotIn("routeBundlePlanSegments", html)
        self.assertNotIn("uniqueRouteStops", html)
        self.assertNotIn("route-stop-label", html)
        self.assertNotIn("data-bundle-corridor", html)
        self.assertNotIn("route-bundle-highlight", html)
        self.assertNotIn("route-bundle-candidate", html)
        self.assertNotIn("route-bundle-label", html)
        self.assertNotIn("routeBundleLabel", html)
        self.assertNotIn("escapeHtml", html)
        self.assertNotIn("const overviewAssignmentId = focusMode ? selectedAssignment : overviewAssignmentIdForRoutes(profile.dispatchMap.assignments, entityPoints, mapLayers, selectedAssignment);", html)
        self.assertNotIn("const pickupIsShort = !longRouteClass", html)
        self.assertNotIn("const noShortLegPenalty = pickupIsShort ? 0 : 160;", html)
        self.assertIn('const active = Boolean(hasDispatch && focused && node.dataset.assignment === selectedAssignment);', html)
        self.assertIn("hide-dispatch-routes", html)
        self.assertIn("派单关系线已隐藏，仅保留点位", html)
        self.assertIn("weather-badge", html)
        self.assertIn("weather-state", html)
        self.assertIn("weather-impact-value", html)
        self.assertIn("background: linear-gradient(180deg, rgba(255,255,255,.96), rgba(248,250,252,.98));", html)
        self.assertIn("color: #334155 !important;", html)
        self.assertIn("pointer-events: none;", html)
        self.assertIn("grid-template-columns: 1fr 1fr", html)
        self.assertIn("调度建议：提高近场骑手权重", html)
        self.assertIn("weather.querySelector(\".weather-badge\")", html)
        self.assertNotIn("weather.querySelector(\".row strong:last-child\")", html)
        self.assertNotIn("weather.querySelector(\".bar\")", html)
        self.assertIn("function businessValueForReport", html)
        self.assertIn("商家覆盖率", html)
        self.assertIn("未派商家", html)
        self.assertIn("单城月节约测算", html)
        self.assertIn("运营测算批次节约", html)
        self.assertIn("assignmentOrders", html)
        self.assertIn("rawPerOrderSaving * 0.025", html)
        self.assertIn("locate-assignment-control", html)
        self.assertIn("map.easeTo({center: lngLat", html)
        self.assertIn("运营测算假设：每单履约损耗节约", html)
        self.assertIn("按日均 10 万单估算单城月节约", html)
        self.assertIn('frame.dataset.routesHidden = "false"', html)
        self.assertIn('frame.dataset.entitiesMuted = "false"', html)
        self.assertIn('frame.dataset.fullscreen = expanded ? "true" : "false"', html)
        self.assertIn('if (layerMode) layerMode.value = "all";', html)
        self.assertIn("assignment-overview", html)
        self.assertIn("overview-route", html)
        self.assertIn("hide-entities", html)
        self.assertIn(".map-panel.active", html)
        self.assertIn("roadFollowingRoute", html)
        self.assertIn("closestRoadTransfer", html)
        self.assertIn("function routeMetaAttributes", html)
        self.assertNotIn("function dispatchHitAreaFor", html)
        self.assertIn("function displayPositionsForLabels", html)
        self.assertIn("function densifyRoutePoints", html)
        self.assertIn("distance > 8.0", html)
        self.assertIn("function sampleOrderById", html)
        self.assertIn("function candidateForPair", html)
        self.assertIn("function strategyLabelForAssignment", html)
        self.assertIn("dataset.detailType", html)
        self.assertIn('"route-points": visiblePickupRoute.length', html)
        self.assertIn('"connector-points": pickupRoute.length', html)
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
        self.assertIn("window.__AUTO_SOLVER_DEBUG__", html)
        self.assertIn('data-row-type="strategy-candidate"', html)
        self.assertIn('data-row-type="preview-strategy"', html)
        self.assertIn('data-row-type="scene-summary"', html)
        self.assertIn('pin.dataset.rawX', html)
        self.assertIn('pin.dataset.kind = item.kind || "";', html)
        self.assertIn('const pinKind = isMerchantPoint ? "merchant"', html)
        self.assertIn('class="mark merchant"', html)
        self.assertIn('class="mark-symbol">商</span>', html)
        self.assertIn('class="mark-symbol">骑</span>', html)
        self.assertIn('"#16a34a"', html)
        self.assertIn('"#0f766e"', html)
        self.assertNotIn('"#25ead8", "#37d6c8"', html)
        self.assertIn('pin.classList.toggle("label-avoided"', html)
        self.assertIn('pin.style.left = Number(rawPoint.x).toFixed(1) + "%";', html)
        self.assertIn('pin.style.top = Number(rawPoint.y).toFixed(1) + "%";', html)
        self.assertIn('label.style.left = Number(display.x).toFixed(1) + "%";', html)
        self.assertIn('label.style.top = Number(display.y).toFixed(1) + "%";', html)
        self.assertIn("const showSelectedLabel = false;", html)
        self.assertNotIn("<small>ETA", html)
        self.assertNotIn("selectedLabelHtml", html)
        self.assertNotIn("订单期望 ETA", html)
        self.assertIn("派单关系：", html)
        self.assertIn("骑手输入：", html)
        self.assertIn("骑手承接：", html)
        self.assertIn("商家输入：", html)
        self.assertIn("商家派单：", html)
        self.assertNotIn("订单详情：", html)
        self.assertIn("if (!relatedCandidates.length)", html)
        self.assertIn("profile.dispatchMap.assignments.flatMap((assignment", html)
        self.assertNotIn("profile.dispatchMap.assignments.slice(0, 8).map", html)
        self.assertIn("const hasFinalAssignments = Boolean(profile && profile.assignments && Object.keys(profile.assignments).length);", html)
        self.assertIn("if (!hasFinalAssignments || !profile.dispatchMap || !Array.isArray(profile.dispatchMap.assignments))", html)
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
