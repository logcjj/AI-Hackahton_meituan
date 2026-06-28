from __future__ import annotations

import json
from functools import lru_cache

from web_agent_demo.day_simulation import (
    DAY_SIMULATION_ENDPOINTS,
    DaySimulationControls,
    day_comparison_to_dict,
    run_full_day_comparison,
)
from web_agent_demo.dispatch_workbench_data import build_dispatch_workbench_payload


@lru_cache(maxsize=1)
def _bootstrap_payload() -> dict[str, object]:
    controls = DaySimulationControls(courier_count=18, order_scale=0.38, weather="mixed", congestion_profile="weekday")
    contract = run_full_day_comparison(seed="frontend-shell", controls=controls)
    return {
        "contract": day_comparison_to_dict(contract),
        "workbench": build_dispatch_workbench_payload(contract),
        "endpoints": dict(DAY_SIMULATION_ENDPOINTS),
        "mode": "dispatch-workbench-shell",
    }


def render_day_replay_index() -> str:
    boot_json = json.dumps(_bootstrap_payload(), ensure_ascii=False, sort_keys=True).replace("</", "<\\/")
    template = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>外卖配送智能调度工作台</title>
  <style>
    :root {
      --bg: #eef1f4;
      --surface: #ffffff;
      --surface-2: #f7f9fb;
      --ink: #172026;
      --muted: #6b7785;
      --line: #dce3ea;
      --line-strong: #c9d3dd;
      --nav: #17212b;
      --nav-2: #202c38;
      --accent: #0f766e;
      --accent-2: #115e59;
      --amber: #b7791f;
      --red: #b42318;
      --blue: #2563eb;
      --green-soft: #e6f4f1;
      --amber-soft: #fbf1db;
      --red-soft: #fee4e2;
      --shadow: 0 16px 42px rgba(21, 32, 43, .10);
      --font: "Aptos", "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      --mono: "SFMono-Regular", "Cascadia Mono", "Menlo", monospace;
    }
    * { box-sizing: border-box; }
    html, body { margin: 0; min-height: 100%; }
    body {
      color: var(--ink);
      background:
        linear-gradient(180deg, rgba(255,255,255,.72), rgba(238,241,244,.92)),
        radial-gradient(circle at 84% 12%, rgba(15,118,110,.10), transparent 34%),
        var(--bg);
      font-family: var(--font);
    }
    button, select, input { font: inherit; }
    button { cursor: pointer; }
    .workbench-shell {
      min-height: 100vh;
      display: grid;
      grid-template-columns: 248px minmax(0, 1fr);
    }
    .workbench-nav {
      position: sticky;
      top: 0;
      height: 100vh;
      padding: 18px 14px;
      color: #d8e1ea;
      background: linear-gradient(180deg, var(--nav), var(--nav-2));
      border-right: 1px solid rgba(255,255,255,.08);
    }
    .brand {
      display: grid;
      grid-template-columns: 38px 1fr;
      gap: 10px;
      align-items: center;
      padding: 8px 8px 20px;
      border-bottom: 1px solid rgba(255,255,255,.10);
    }
    .brand-mark {
      width: 38px;
      height: 38px;
      display: grid;
      place-items: center;
      border-radius: 12px;
      color: #e9fffb;
      background: linear-gradient(135deg, var(--accent), #334155);
      font: 800 13px var(--mono);
    }
    .brand strong { display: block; color: #fff; font-size: 15px; }
    .brand span { color: #9fb0c0; font-size: 12px; }
    .nav-section-title {
      margin: 18px 10px 8px;
      color: #8192a3;
      font: 700 11px var(--mono);
      letter-spacing: .08em;
      text-transform: uppercase;
    }
    .nav-list { display: grid; gap: 6px; }
    .nav-link {
      display: grid;
      grid-template-columns: 26px 1fr;
      gap: 10px;
      align-items: center;
      padding: 10px 10px;
      border-radius: 12px;
      color: #c8d4df;
      text-decoration: none;
      border: 1px solid transparent;
    }
    .nav-link:hover { background: rgba(255,255,255,.07); }
    .nav-link[aria-current="page"] {
      color: #fff;
      background: rgba(15,118,110,.26);
      border-color: rgba(45,212,191,.24);
    }
    .nav-icon {
      width: 24px;
      height: 24px;
      border-radius: 8px;
      display: grid;
      place-items: center;
      background: rgba(255,255,255,.08);
      font: 800 11px var(--mono);
    }
    .nav-meta {
      position: absolute;
      left: 14px;
      right: 14px;
      bottom: 16px;
      padding: 12px;
      border: 1px solid rgba(255,255,255,.10);
      border-radius: 14px;
      background: rgba(255,255,255,.06);
      color: #9fb0c0;
      font-size: 12px;
      line-height: 1.5;
    }
    .workbench-main {
      min-width: 0;
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
    }
    .topbar {
      position: sticky;
      top: 0;
      z-index: 20;
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 16px;
      align-items: center;
      min-height: 72px;
      padding: 14px 22px;
      background: rgba(255,255,255,.88);
      border-bottom: 1px solid var(--line);
      backdrop-filter: blur(18px);
    }
    .topbar h1 { margin: 0 0 3px; font-size: 18px; letter-spacing: -.02em; }
    .topbar p { margin: 0; color: var(--muted); font-size: 13px; }
    .topbar-stats {
      display: grid;
      grid-template-columns: repeat(4, auto);
      gap: 8px;
      align-items: center;
    }
    .stat-pill {
      min-width: 92px;
      padding: 8px 10px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--surface-2);
    }
    .stat-pill b { display: block; font-size: 15px; }
    .stat-pill span {
      color: var(--muted);
      font: 700 10px var(--mono);
      letter-spacing: .05em;
      text-transform: uppercase;
    }
    .route-view {
      min-width: 0;
      padding: 22px;
    }
    .page-head {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 14px;
      align-items: end;
      margin-bottom: 16px;
    }
    .eyebrow {
      color: var(--accent);
      font: 800 11px var(--mono);
      letter-spacing: .08em;
      text-transform: uppercase;
    }
    .page-head h2 { margin: 5px 0 6px; font-size: 28px; letter-spacing: -.04em; }
    .page-head p { margin: 0; max-width: 820px; color: var(--muted); line-height: 1.55; }
    .page-grid { display: grid; gap: 14px; }
    .live-grid {
      grid-template-columns: minmax(0, 1.4fr) 360px;
      align-items: start;
    }
    .decision-grid {
      grid-template-columns: 280px minmax(0, 1fr) 340px;
      align-items: start;
    }
    .memory-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
    .rider-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    .card {
      border: 1px solid var(--line);
      border-radius: 18px;
      background: rgba(255,255,255,.92);
      box-shadow: var(--shadow);
      overflow: hidden;
    }
    .card-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
      background: linear-gradient(180deg, #fff, var(--surface-2));
    }
    .card-head h3 { margin: 0; font-size: 15px; }
    .card-head span { color: var(--muted); font-size: 12px; }
    .card-body { padding: 14px 16px; }
    .control-dock {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 16px;
      background: var(--surface);
      box-shadow: var(--shadow);
    }
    .primary-button {
      border: 0;
      border-radius: 11px;
      padding: 9px 13px;
      color: #fff;
      background: var(--accent);
    }
    .ghost-button, .select-control {
      border: 1px solid var(--line-strong);
      border-radius: 11px;
      padding: 8px 11px;
      color: var(--ink);
      background: var(--surface-2);
    }
    .map-panel { min-height: 520px; position: relative; }
    .schematic-map {
      position: relative;
      height: 458px;
      margin: 14px;
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: 18px;
      background:
        linear-gradient(90deg, rgba(148,163,184,.16) 1px, transparent 1px),
        linear-gradient(0deg, rgba(148,163,184,.16) 1px, transparent 1px),
        radial-gradient(circle at 60% 40%, rgba(15,118,110,.14), transparent 32%),
        #f8fafc;
      background-size: 44px 44px, 44px 44px, auto, auto;
    }
    .map-route {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
    }
    .route-line {
      fill: none;
      stroke: var(--accent);
      stroke-width: 2.2;
      stroke-linecap: round;
      opacity: .76;
    }
    .map-dot {
      --size: 12px;
      position: absolute;
      left: calc(var(--x) * 1%);
      top: calc(var(--y) * 1%);
      width: var(--size);
      height: var(--size);
      transform: translate(-50%, -50%);
      border-radius: 999px;
      border: 2px solid #fff;
      box-shadow: 0 5px 16px rgba(15,23,42,.18);
    }
    .map-dot[data-kind="merchant"] { background: var(--blue); }
    .map-dot[data-kind="rider"] { --size: 14px; background: var(--accent); }
    .map-dot[data-kind="order"] { --size: 10px; background: var(--amber); }
    .hotspot {
      position: absolute;
      left: calc(var(--x) * 1%);
      top: calc(var(--y) * 1%);
      width: calc(72px + var(--severity) * 56px);
      height: calc(72px + var(--severity) * 56px);
      transform: translate(-50%, -50%);
      border-radius: 999px;
      background: rgba(183,121,31,.13);
      border: 1px solid rgba(183,121,31,.24);
    }
    .score-stack { display: grid; gap: 10px; }
    .score-card {
      padding: 13px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: var(--surface-2);
    }
    .score-card b { display: block; font-size: 22px; letter-spacing: -.03em; }
    .score-card span { color: var(--muted); font-size: 12px; }
    .score-card[data-tone="good"] { background: var(--green-soft); border-color: rgba(15,118,110,.24); }
    .score-card[data-tone="warn"] { background: var(--amber-soft); border-color: rgba(183,121,31,.24); }
    .event-list, .timeline-list, .memory-list, .compact-list {
      display: grid;
      gap: 9px;
    }
    .list-item {
      padding: 10px 11px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--surface-2);
    }
    .list-item strong { display: block; margin-bottom: 4px; font-size: 13px; }
    .list-item span, .list-item p { margin: 0; color: var(--muted); font-size: 12px; line-height: 1.45; }
    .timeline-item { text-align: left; width: 100%; border: 1px solid var(--line); background: var(--surface-2); border-radius: 12px; padding: 10px; }
    .timeline-item[data-active="true"] { border-color: rgba(15,118,110,.42); background: var(--green-soft); }
    .stage-row {
      display: grid;
      grid-template-columns: 130px 1fr auto;
      gap: 12px;
      align-items: start;
      padding: 12px 0;
      border-bottom: 1px solid var(--line);
    }
    .stage-row:last-child { border-bottom: 0; }
    .stage-row b { color: var(--accent-2); font-size: 13px; }
    .stage-row span { color: var(--muted); font-size: 12px; }
    .table-shell {
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 16px;
      background: var(--surface);
      box-shadow: var(--shadow);
    }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { padding: 10px 12px; border-bottom: 1px solid var(--line); text-align: left; white-space: nowrap; }
    th { position: sticky; top: 0; z-index: 1; color: var(--muted); background: var(--surface-2); font: 800 11px var(--mono); text-transform: uppercase; }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 4px 8px;
      border-radius: 999px;
      color: var(--accent-2);
      background: var(--green-soft);
      font-size: 12px;
    }
    .badge[data-risk="high"], .badge[data-state="late_risk"] { color: var(--red); background: var(--red-soft); }
    .badge[data-risk="medium"] { color: var(--amber); background: var(--amber-soft); }
    .filter-bar {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 12px;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 16px;
      background: rgba(255,255,255,.80);
    }
    .memory-card { min-height: 220px; }
    .rider-card .card-body { display: grid; gap: 10px; }
    .mini-map {
      position: relative;
      height: 92px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background:
        linear-gradient(90deg, rgba(148,163,184,.18) 1px, transparent 1px),
        linear-gradient(0deg, rgba(148,163,184,.18) 1px, transparent 1px),
        #f8fafc;
      background-size: 24px 24px;
    }
    .route-empty {
      padding: 30px;
      color: var(--muted);
      text-align: center;
    }
    @media (max-width: 1180px) {
      .workbench-shell { grid-template-columns: 78px minmax(0, 1fr); }
      .brand { grid-template-columns: 1fr; }
      .brand strong, .brand span, .nav-link span:not(.nav-icon), .nav-section-title, .nav-meta { display: none; }
      .nav-link { grid-template-columns: 1fr; justify-items: center; }
      .live-grid, .decision-grid, .memory-grid, .rider-grid { grid-template-columns: 1fr; }
      .topbar { grid-template-columns: 1fr; }
      .topbar-stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (max-width: 720px) {
      .workbench-shell { display: block; }
      .workbench-nav { position: relative; height: auto; }
      .nav-list { grid-template-columns: repeat(5, minmax(0, 1fr)); }
      .nav-link { padding: 8px 4px; }
      .route-view { padding: 14px; }
      .page-head { grid-template-columns: 1fr; }
      .schematic-map { height: 360px; }
    }
  </style>
</head>
<body data-shell="dispatch-workbench-shell" data-secret-handling="env-only-redacted">
  <div id="dispatch-workbench-shell" class="workbench-shell" data-product-reference="kandbox-dispatch">
    <aside class="workbench-nav" aria-label="Dispatch workbench navigation">
      <div class="brand">
        <div class="brand-mark">FD</div>
        <div>
          <strong>Food Dispatch</strong>
          <span>Kandbox-style workbench</span>
        </div>
      </div>
      <div class="nav-section-title">Workbench</div>
      <nav id="route-nav" class="nav-list"></nav>
      <div class="nav-meta">
        <strong>Dispatch scope</strong><br>
        Full-day orders, riders, planner decisions, live map, score and memory share one model.
      </div>
    </aside>
    <main class="workbench-main">
      <header class="topbar">
        <div>
          <h1 id="route-title">外卖配送智能调度工作台</h1>
          <p id="route-subtitle">按照 Kandbox Dispatch 的 Workers / Jobs / Planner / Live Map 拆法重组业务对象。</p>
        </div>
        <div id="topbar-stats" class="topbar-stats"></div>
      </header>
      <section id="route-view" class="route-view" data-route-view="live" aria-live="polite"></section>
    </main>
  </div>
  <script id="dispatch-workbench-bootstrap" type="application/json">__BOOT_JSON__</script>
  <script>
    const dispatchBoot = JSON.parse(document.getElementById("dispatch-workbench-bootstrap").textContent);
    const workbench = dispatchBoot.workbench;
    const routeCopy = {
      live: {
        icon: "LM",
        title: "实时推理页",
        subtitle: "Live Map 工作台：订单释放、骑手资源、路线变化和累计对比在同一个运营视图中联动。"
      },
      decisions: {
        icon: "PL",
        title: "决策页",
        subtitle: "Planner / Chart 角色：每一轮触发、过滤、评分、动作和回写独立成页。"
      },
      memory: {
        icon: "ME",
        title: "Memory 页",
        subtitle: "长期记忆视图：展示新沉淀、已整理、当前命中和效果反馈，而不是资产表。"
      },
      orders: {
        icon: "JO",
        title: "订单页",
        subtitle: "Jobs / Orders 输入视图：全天订单全集预置，仅用于调度可见性和筛选。"
      },
      riders: {
        icon: "WK",
        title: "骑手页",
        subtitle: "Workers 资源视图：骑手班次、状态、位置、负载和任务链统一盘点。"
      }
    };
    const routeOrder = ["live", "decisions", "memory", "orders", "riders"];

    function escapeHtml(value) {
      return String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      }[char]));
    }

    function fmtNumber(value, digits = 0) {
      if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
      return Number(value).toLocaleString("zh-CN", { maximumFractionDigits: digits, minimumFractionDigits: digits });
    }

    function routeFromHash() {
      const value = (window.location.hash || "#/live").replace(/^#\\/?/, "");
      return routeOrder.includes(value) ? value : "live";
    }

    function pageHeader(routeId, eyebrow, description) {
      const copy = routeCopy[routeId];
      return `
        <div class="page-head">
          <div>
            <div class="eyebrow">${escapeHtml(eyebrow)}</div>
            <h2>${escapeHtml(copy.title)}</h2>
            <p>${escapeHtml(description || copy.subtitle)}</p>
          </div>
          <div class="badge">${escapeHtml(workbench.source.scenario_name)}</div>
        </div>
      `;
    }

    function renderTopbarStats() {
      const stats = workbench.inspection;
      const finalDelta = workbench.metrics.final.deltas;
      document.getElementById("topbar-stats").innerHTML = [
        ["Orders", stats.order_count],
        ["Riders", stats.rider_count],
        ["Decisions", stats.decision_count],
        ["Saved min", fmtNumber(finalDelta.time_saved_min, 1)]
      ].map(([label, value]) => `
        <div class="stat-pill"><b>${escapeHtml(value)}</b><span>${escapeHtml(label)}</span></div>
      `).join("");
    }

    function renderNav() {
      document.getElementById("route-nav").innerHTML = workbench.routes.map((route) => {
        const copy = routeCopy[route.id];
        return `
          <a class="nav-link" href="${escapeHtml(route.path)}" data-route-link="${escapeHtml(route.id)}">
            <span class="nav-icon">${escapeHtml(copy.icon)}</span>
            <span>
              <strong>${escapeHtml(route.label)}</strong><br>
              <small>${escapeHtml(route.kandbox_module)}</small>
            </span>
          </a>
        `;
      }).join("");
    }

    function setRoute(routeId) {
      const safeRoute = routeOrder.includes(routeId) ? routeId : "live";
      if (window.location.hash !== `#/${safeRoute}`) {
        history.replaceState(null, "", `#/${safeRoute}`);
      }
      document.body.dataset.route = safeRoute;
      document.getElementById("route-title").textContent = routeCopy[safeRoute].title;
      document.getElementById("route-subtitle").textContent = routeCopy[safeRoute].subtitle;
      for (const link of document.querySelectorAll("[data-route-link]")) {
        link.setAttribute("aria-current", link.dataset.routeLink === safeRoute ? "page" : "false");
      }
      renderRoute(safeRoute);
    }

    function renderRoute(routeId) {
      const view = document.getElementById("route-view");
      view.dataset.routeView = routeId;
      const renderers = {
        live: renderLivePage,
        decisions: renderDecisionsPage,
        memory: renderMemoryPage,
        orders: renderOrdersPage,
        riders: renderRidersPage
      };
      view.innerHTML = renderers[routeId]();
    }

    function renderLivePage() {
      const finalScore = workbench.metrics.final;
      const events = workbench.timeline.events.slice(0, 9);
      const currentDecision = workbench.decisions[0];
      return `
        ${pageHeader("live", "Live Map / GanttMap", "主工作台只展示对调度有用的内容：实时地图、累计优势、事件流和当前轮摘要。")}
        <div class="page-grid live-grid" data-page="live">
          <div class="page-grid">
            <div class="control-dock" data-control-strip="live">
              <button id="start-inference" class="primary-button" data-control="start-inference">开始推理</button>
              <button class="ghost-button" data-control="pause-resume">暂停/继续</button>
              <select class="select-control" data-control="speed"><option>1x</option><option>2x</option><option>4x</option></select>
              <select class="select-control" data-control="mode"><option>当前算法</option><option>对比</option><option>叠加</option></select>
            </div>
            <div class="card map-panel">
              <div class="card-head"><h3>实时地图层</h3><span>merchants / orders / riders / routes / hotspots</span></div>
              <div class="schematic-map" data-map-layer="primary">
                ${renderMapRoutes()}
                ${renderHotspots()}
                ${renderMapDots("merchant", workbench.map.anchors.merchants.slice(0, 18), "position")}
                ${renderMapDots("rider", workbench.map.anchors.riders.slice(0, 18), "position")}
                ${renderMapDots("order", workbench.map.anchors.orders.slice(0, 28), "dropoff")}
              </div>
            </div>
            <div class="card">
              <div class="card-head"><h3>轻量事件流</h3><span>按全天推演时间释放</span></div>
              <div class="card-body event-list">${events.map(renderEventItem).join("")}</div>
            </div>
          </div>
          <aside class="page-grid">
            <div class="card">
              <div class="card-head"><h3>实时累计对比栏</h3><span>baseline vs ours</span></div>
              <div class="card-body score-stack">
                ${renderScoreCard("基线/弹金算法累计", `${fmtNumber(finalScore.baseline.total_cost_yuan, 1)} 元`, `${fmtNumber(finalScore.baseline.total_time_cost_min, 1)} 分钟成本`, "warn")}
                ${renderScoreCard("我们的算法累计", `${fmtNumber(finalScore.ours.total_cost_yuan, 1)} 元`, `${fmtNumber(finalScore.ours.total_time_cost_min, 1)} 分钟成本`, "good")}
                ${renderScoreCard("时间差异", `${fmtNumber(finalScore.deltas.time_saved_min, 1)} 分钟`, finalScore.deltas.headline, "good")}
                ${renderScoreCard("金钱差异", `${fmtNumber(finalScore.deltas.money_saved_yuan, 1)} 元`, `收益/成本差异 ${fmtNumber(finalScore.deltas.profit_delta_yuan, 1)} 元`, "good")}
                ${renderScoreCard("超时单差异", `${fmtNumber(finalScore.deltas.timeout_order_delta, 0)} 单`, `风险差异 ${fmtNumber(finalScore.deltas.timeout_risk_delta, 3)}`, "good")}
                ${renderScoreCard("空驶里程差异", `${fmtNumber(finalScore.deltas.empty_mileage_saved_km, 2)} km`, "只强调差异部分，不铺满两套路由", "good")}
              </div>
            </div>
            <div class="card">
              <div class="card-head"><h3>本轮摘要</h3><span>${escapeHtml(currentDecision.trigger_time_label)}</span></div>
              <div class="card-body compact-list">
                <div class="list-item"><strong>${escapeHtml(currentDecision.trigger_reason)}</strong><p>${escapeHtml(currentDecision.round_result.summary)}</p></div>
                <div class="list-item"><strong>候选集合</strong><p>${currentDecision.input_order_ids.length} orders / ${currentDecision.candidate_rider_ids.length} riders</p></div>
              </div>
            </div>
          </aside>
        </div>
      `;
    }

    function renderDecisionsPage() {
      const decision = workbench.decisions[0];
      return `
        ${pageHeader("decisions", "Planner / Chart / Gantt", "把规划视图重构为推导过程页：左侧轮次，中间推导，右侧上下文和回写。")}
        <div class="page-grid decision-grid" data-page="decisions">
          <div class="card">
            <div class="card-head"><h3>决策轮次时间线</h3><span>${workbench.decisions.length} rounds</span></div>
            <div class="card-body timeline-list">
              ${workbench.decisions.slice(0, 16).map((item, index) => `
                <button class="timeline-item" data-decision-id="${escapeHtml(item.id)}" data-active="${index === 0}">
                  <strong>${escapeHtml(item.trigger_time_label)} ${escapeHtml(item.id)}</strong>
                  <span>${escapeHtml(item.trigger_reason)}</span>
                </button>
              `).join("")}
            </div>
          </div>
          <div class="card">
            <div class="card-head"><h3>当前轮推导过程</h3><span>${escapeHtml(decision.context.demand_phase)}</span></div>
            <div class="card-body">
              ${renderStageRow("输入订单集合", `${decision.input_orders.length} orders`, decision.input_orders.slice(0, 5).map((item) => item.id).join(", "))}
              ${renderStageRow("候选骑手集合", `${decision.candidate_riders.length} riders`, decision.candidate_riders.slice(0, 5).map((item) => item.id).join(", "))}
              ${decision.filtering_process.map((stage) => renderStageRow(stage.stage, `${stage.remaining} remain`, stage.summary)).join("")}
              ${renderStageRow("评分过程", `${decision.scoring_process.length} algorithms`, decision.scoring_process.map((item) => `${item.algorithm_id}: ${fmtNumber(item.score, 3)}`).join(" / "))}
              ${renderStageRow("最终动作", `${decision.final_actions.length} assignments`, decision.final_actions.slice(0, 5).map((item) => `${item.order_id}->${item.courier_id}`).join(", "))}
              ${renderStageRow("被放弃动作", `${decision.abandoned_actions.length} baseline actions`, decision.abandoned_actions.slice(0, 4).map((item) => `${item.order_id}->${item.courier_id}`).join(", "))}
              ${renderStageRow("结果回写", `${decision.result_writeback.writeback_count} writebacks`, decision.result_writeback.summary)}
            </div>
          </div>
          <aside class="card">
            <div class="card-head"><h3>输入上下文 + 输出结果</h3><span>${escapeHtml(decision.context.time_slice_id)}</span></div>
            <div class="card-body compact-list">
              <div class="list-item"><strong>上下文</strong><p>${escapeHtml(decision.context.weather)} / congestion ${fmtNumber(decision.context.congestion_level, 2)} / supply ${decision.context.courier_supply}</p></div>
              <div class="list-item"><strong>本轮结果</strong><p>节省 ${fmtNumber(decision.round_result.time_saved_min, 1)} 分钟，节省 ${fmtNumber(decision.round_result.cost_saved_yuan, 1)} 元。</p></div>
              <div class="list-item"><strong>结果回写</strong><p>${decision.result_writeback.memory_event_ids.map(escapeHtml).join(", ")}</p></div>
            </div>
          </aside>
        </div>
      `;
    }

    function renderMemoryPage() {
      const sections = [
        ["new", "新沉淀记忆"],
        ["curated", "已整理记忆"],
        ["active", "当前命中的记忆"],
        ["feedback", "记忆效果反馈"]
      ];
      const byId = Object.fromEntries(workbench.memory.items.map((item) => [item.id, item]));
      return `
        ${pageHeader("memory", "Hermes-style Memory", "这里展示系统长期记忆的形成、整理、命中和反馈，不做资产表或文档中心。")}
        <div class="page-grid memory-grid" data-page="memory">
          ${sections.map(([sectionId, title]) => `
            <div class="card memory-card" data-memory-section="${escapeHtml(sectionId)}">
              <div class="card-head"><h3>${escapeHtml(title)}</h3><span>${workbench.memory.sections[sectionId].length}</span></div>
              <div class="card-body memory-list">
                ${workbench.memory.sections[sectionId].slice(0, 4).map((id) => renderMemoryItem(byId[id])).join("")}
              </div>
            </div>
          `).join("")}
        </div>
      `;
    }

    function renderOrdersPage() {
      const orders = workbench.entities.orders;
      return `
        ${pageHeader("orders", "Jobs / Orders", "全天订单全集已经预置，页面定位是调度输入视图，不是后台录入表。")}
        <div data-page="orders">
          <div class="filter-bar" data-filter-bar="orders">
            <select class="select-control"><option>全部时间段</option>${workbench.filters.order_time_bands.map((item) => `<option>${escapeHtml(item.label)}</option>`).join("")}</select>
            <select class="select-control"><option>全部商圈</option>${workbench.filters.areas.map((item) => `<option>${escapeHtml(item)}</option>`).join("")}</select>
            <select class="select-control"><option>全部状态</option>${workbench.filters.statuses.map((item) => `<option>${escapeHtml(item)}</option>`).join("")}</select>
            <select class="select-control"><option>全部风险</option>${workbench.filters.risk_levels.map((item) => `<option>${escapeHtml(item)}</option>`).join("")}</select>
          </div>
          <div class="table-shell">
            <table>
              <thead><tr><th>订单编号</th><th>商家/提货点</th><th>下单时间</th><th>承诺送达</th><th>状态</th><th>风险</th><th>商圈</th><th>进入推理</th><th>基线结果</th><th>我方结果</th></tr></thead>
              <tbody>${orders.map(renderOrderRow).join("")}</tbody>
            </table>
          </div>
        </div>
      `;
    }

    function renderRidersPage() {
      return `
        ${pageHeader("riders", "Workers", "全天骑手资源预置为调度资源盘点：班次、状态、位置、负载和任务链。")}
        <div class="page-grid rider-grid" data-page="riders">
          ${workbench.entities.riders.map(renderRiderCard).join("")}
        </div>
      `;
    }

    function renderMapRoutes() {
      const routes = workbench.map.routes.filter((route) => route.lane === "ours").slice(0, 10);
      if (!routes.length) return "";
      return `
        <svg class="map-route" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          ${routes.map((route) => {
            const points = route.polyline.map((point) => `${point.screen_x},${point.screen_y}`).join(" ");
            return `<polyline class="route-line" points="${escapeHtml(points)}"></polyline>`;
          }).join("")}
        </svg>
      `;
    }

    function renderHotspots() {
      return workbench.map.hotspots.map((hotspot) => `
        <div class="hotspot" title="${escapeHtml(hotspot.summary)}" style="--x:${hotspot.center.screen_x};--y:${hotspot.center.screen_y};--severity:${hotspot.severity}"></div>
      `).join("");
    }

    function renderMapDots(kind, items, positionKey) {
      return items.map((item) => {
        const pos = item[positionKey];
        return `<span class="map-dot" data-kind="${escapeHtml(kind)}" data-id="${escapeHtml(item.id)}" title="${escapeHtml(item.label || item.id)}" style="--x:${pos.screen_x};--y:${pos.screen_y}"></span>`;
      }).join("");
    }

    function renderScoreCard(label, value, detail, tone) {
      return `<div class="score-card" data-tone="${escapeHtml(tone)}"><span>${escapeHtml(label)}</span><b>${escapeHtml(value)}</b><span>${escapeHtml(detail)}</span></div>`;
    }

    function renderEventItem(event) {
      return `<div class="list-item" data-event-type="${escapeHtml(event.type)}"><strong>${escapeHtml(event.time_label)} ${escapeHtml(event.type)}</strong><p>${escapeHtml(event.summary)}</p></div>`;
    }

    function renderStageRow(label, count, summary) {
      return `<div class="stage-row"><b>${escapeHtml(label)}</b><span>${escapeHtml(summary || "Pending")}</span><em>${escapeHtml(count)}</em></div>`;
    }

    function renderMemoryItem(item) {
      if (!item) return "";
      return `
        <div class="list-item" data-memory-id="${escapeHtml(item.id)}">
          <strong>${escapeHtml(item.latest_hit_time_label)} / ${escapeHtml(item.trigger_scenario)}</strong>
          <p>${escapeHtml(item.context_summary)}</p>
          <p>${escapeHtml(item.effect_feedback)} Confidence ${fmtNumber(item.confidence, 2)} / recalls ${item.recall_count}</p>
        </div>
      `;
    }

    function renderOrderRow(order) {
      return `
        <tr data-order-id="${escapeHtml(order.id)}">
          <td>${escapeHtml(order.id)}</td>
          <td>${escapeHtml(order.pickup_label)}</td>
          <td>${escapeHtml(order.created_at_label)}</td>
          <td>${escapeHtml(order.promised_at_label)}</td>
          <td><span class="badge" data-state="${escapeHtml(order.status)}">${escapeHtml(order.status)}</span></td>
          <td><span class="badge" data-risk="${escapeHtml(order.risk_level)}">${escapeHtml(order.risk_level)}</span></td>
          <td>${escapeHtml(order.business_area)}</td>
          <td>${order.entered_inference ? "是" : "否"}</td>
          <td>${escapeHtml(order.baseline_result.courier_id || "-")} / ${escapeHtml(order.baseline_result.eta_min ?? "-")}</td>
          <td>${escapeHtml(order.our_result.courier_id || "-")} / ${escapeHtml(order.our_result.eta_min ?? "-")}</td>
        </tr>
      `;
    }

    function renderRiderCard(rider) {
      const pos = rider.position;
      return `
        <article class="card rider-card" data-rider-id="${escapeHtml(rider.id)}">
          <div class="card-head"><h3>${escapeHtml(rider.name)}</h3><span>${escapeHtml(rider.online_state)}</span></div>
          <div class="card-body">
            <div class="mini-map">
              <span class="map-dot" data-kind="rider" style="--x:${pos.screen_x};--y:${pos.screen_y}"></span>
            </div>
            <div class="compact-list">
              <div class="list-item"><strong>${escapeHtml(rider.shift_label)} / ${escapeHtml(rider.business_area)}</strong><p>负载 ${rider.current_load}/${rider.capacity}，预计空闲 ${escapeHtml(rider.estimated_free_at_label)}</p></div>
              <div class="list-item"><strong>当前任务链 ${rider.task_chain_size}</strong><p>${rider.task_chain.slice(0, 4).map((item) => item.order_id).join(", ") || "暂无任务"}</p></div>
              <div class="list-item"><strong>历史表现摘要</strong><p>${escapeHtml(rider.performance.summary)}</p></div>
            </div>
          </div>
        </article>
      `;
    }

    function bootstrapDispatchWorkbench() {
      renderNav();
      renderTopbarStats();
      setRoute(routeFromHash());
      window.addEventListener("hashchange", () => setRoute(routeFromHash()));
    }

    document.addEventListener("DOMContentLoaded", bootstrapDispatchWorkbench);
    window.__DISPATCH_WORKBENCH__ = {
      boot: dispatchBoot,
      workbench,
      routeFromHash,
      setRoute,
      renderRoute,
      renderLivePage,
      renderDecisionsPage,
      renderMemoryPage,
      renderOrdersPage,
      renderRidersPage
    };
  </script>
</body>
</html>
"""
    return template.replace("__BOOT_JSON__", boot_json)
