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
    .runtime-strip {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 8px;
      width: 100%;
    }
    .runtime-cell {
      min-height: 58px;
      padding: 9px 10px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--surface-2);
    }
    .runtime-cell b {
      display: block;
      font: 800 15px var(--mono);
      color: var(--ink);
    }
    .runtime-cell span {
      color: var(--muted);
      font: 700 10px var(--mono);
      letter-spacing: .05em;
      text-transform: uppercase;
    }
    .inference-progress {
      width: 100%;
      height: 8px;
      overflow: hidden;
      border-radius: 999px;
      background: #dbe4ed;
    }
    .inference-progress span {
      display: block;
      width: var(--progress, 0%);
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, var(--accent), #22c55e);
      transition: width .28s ease;
    }
    .primary-button {
      border: 0;
      border-radius: 11px;
      padding: 9px 13px;
      color: #fff;
      background: var(--accent);
    }
    .primary-button[disabled] {
      cursor: default;
      opacity: .62;
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
    .map-mode-chip {
      position: absolute;
      z-index: 4;
      right: 14px;
      top: 14px;
      padding: 6px 9px;
      border: 1px solid var(--line);
      border-radius: 999px;
      color: var(--accent-2);
      background: rgba(255,255,255,.86);
      font: 800 11px var(--mono);
      box-shadow: 0 8px 18px rgba(15,23,42,.10);
    }
    .map-legend {
      position: absolute;
      z-index: 4;
      left: 14px;
      bottom: 14px;
      display: flex;
      flex-wrap: wrap;
      gap: 7px;
      max-width: 72%;
      padding: 7px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: rgba(255,255,255,.84);
      box-shadow: 0 8px 18px rgba(15,23,42,.08);
    }
    .legend-item {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      color: var(--muted);
      font-size: 11px;
    }
    .legend-swatch {
      width: 18px;
      height: 3px;
      border-radius: 999px;
      background: var(--accent);
    }
    .legend-swatch[data-lane="baseline"] { background: var(--red); opacity: .48; }
    .legend-swatch[data-lane="difference"] { background: var(--amber); }
    .legend-swatch[data-lane="previous"] { background: #64748b; opacity: .36; }
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
      transition: opacity .32s ease, stroke-width .32s ease;
    }
    .route-line[data-lane="ours"] {
      stroke: var(--accent);
      stroke-width: 2.6;
      opacity: .82;
    }
    .route-line[data-lane="baseline"] {
      stroke: var(--red);
      stroke-width: 1.8;
      stroke-dasharray: 4 5;
      opacity: .34;
    }
    .route-line[data-lane="difference"] {
      stroke: var(--amber);
      stroke-width: 3.1;
      opacity: .88;
    }
    .route-line[data-lane="previous"] {
      stroke: #64748b;
      stroke-width: 1.4;
      stroke-dasharray: 2 7;
      opacity: .23;
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
      transition: left .55s linear, top .55s linear, opacity .25s ease;
    }
    .map-dot[data-kind="merchant"] { background: var(--blue); }
    .map-dot[data-kind="rider"] { --size: 14px; background: var(--accent); }
    .map-dot[data-kind="order"] { --size: 10px; background: var(--amber); }
    .map-dot[data-motion="moving"] {
      outline: 5px solid rgba(15,118,110,.10);
    }
    .map-dot[data-release="new"] {
      animation: order-enter-pulse 1.8s ease-in-out infinite;
    }
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
    .hotspot[data-active="false"] {
      opacity: .34;
      background: rgba(148,163,184,.10);
      border-color: rgba(148,163,184,.22);
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
    .live-grid[data-inference-state="running"] .map-panel {
      outline: 2px solid rgba(15,118,110,.14);
    }
    @keyframes order-enter-pulse {
      0%, 100% { box-shadow: 0 5px 16px rgba(15,23,42,.18); }
      50% { box-shadow: 0 0 0 7px rgba(183,121,31,.14), 0 5px 16px rgba(15,23,42,.18); }
    }
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
      .runtime-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
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
    const contract = dispatchBoot.contract;
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
    const inferenceState = {
      started: false,
      running: false,
      currentTimeS: workbench.timeline.start_s,
      speed: 1,
      mode: "current",
      timerId: null,
      tickMs: 700,
      lastTickAt: 0
    };
    const inferenceModeLabels = {
      current: "当前算法",
      compare: "对比",
      overlay: "叠加"
    };

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

    function clock(seconds) {
      const value = Math.max(0, Math.floor(Number(seconds) || 0));
      const hours = String(Math.floor(value / 3600)).padStart(2, "0");
      const minutes = String(Math.floor((value % 3600) / 60)).padStart(2, "0");
      return `${hours}:${minutes}`;
    }

    function clamp(value, min, max) {
      return Math.max(min, Math.min(max, value));
    }

    function inferenceProgressPct() {
      const span = Math.max(1, workbench.timeline.end_s - workbench.timeline.start_s);
      return Math.round(clamp((inferenceState.currentTimeS - workbench.timeline.start_s) / span, 0, 1) * 1000) / 10;
    }

    function scoreForTime(simTimeS) {
      const series = workbench.metrics.series;
      let selected = series[0] || workbench.metrics.final;
      for (const item of series) {
        if (item.time_s <= simTimeS) selected = item;
        else break;
      }
      return selected;
    }

    function decisionForTime(simTimeS) {
      let selected = workbench.decisions[0];
      for (const item of workbench.decisions) {
        if (item.trigger_time_s <= simTimeS) selected = item;
        else break;
      }
      return selected || workbench.decisions[0];
    }

    function releasedEvents(simTimeS) {
      return workbench.timeline.events.filter((event) => event.time_s <= simTimeS);
    }

    function frameForTime(simTimeS) {
      const frames = contract.frames || [];
      let selected = frames[0];
      for (const frame of frames) {
        if (frame.sim_time_s <= simTimeS) selected = frame;
        else break;
      }
      return selected || { id: "", sim_time_s: workbench.timeline.start_s, highlighted_order_ids: [], challenger: { route_overlays: [], simulation_trace: { courier_tracks: [] }, courier_positions: [] }, baseline: { route_overlays: [], assignments: [] } };
    }

    function previousFrameFor(frame) {
      const frames = contract.frames || [];
      const index = frames.findIndex((item) => item.id === frame.id);
      return index > 0 ? frames[index - 1] : null;
    }

    function routeRowsForFrame(frame, lane) {
      const laneKey = lane === "baseline" ? "baseline" : "ours";
      return workbench.map.routes.filter((route) => route.frame_id === frame.id && route.lane === laneKey);
    }

    function assignmentCourierMap(frame, lane) {
      const algorithmFrame = lane === "baseline" ? frame.baseline : frame.challenger;
      return Object.fromEntries((algorithmFrame.assignments || []).map((assignment) => [assignment.order_id, assignment.courier_id]));
    }

    function differentialOrderIds(frame) {
      const baseline = assignmentCourierMap(frame, "baseline");
      const ours = assignmentCourierMap(frame, "ours");
      const highlighted = new Set(frame.highlighted_order_ids || []);
      const diff = Object.keys(ours).filter((orderId) => baseline[orderId] && baseline[orderId] !== ours[orderId]);
      return new Set([...diff, ...highlighted].slice(0, 8));
    }

    function mapRouteRows(frame) {
      const previous = previousFrameFor(frame);
      const previousRoutes = previous ? routeRowsForFrame(previous, "ours").slice(0, 4).map((route) => ({...route, renderLane: "previous"})) : [];
      const ours = routeRowsForFrame(frame, "ours");
      const baseline = routeRowsForFrame(frame, "baseline");
      const diffIds = differentialOrderIds(frame);
      if (inferenceState.mode === "overlay") {
        const diffOurs = ours.filter((route) => diffIds.has(route.order_id)).slice(0, 7).map((route) => ({...route, renderLane: "difference"}));
        const diffBaseline = baseline.filter((route) => diffIds.has(route.order_id)).slice(0, 5).map((route) => ({...route, renderLane: "baseline"}));
        return [...previousRoutes, ...(diffOurs.length ? diffOurs : ours.slice(0, 5).map((route) => ({...route, renderLane: "ours"}))), ...diffBaseline];
      }
      if (inferenceState.mode === "compare") {
        const diffBaseline = baseline.filter((route) => diffIds.has(route.order_id)).slice(0, 4).map((route) => ({...route, renderLane: "baseline"}));
        return [...previousRoutes, ...ours.slice(0, 7).map((route) => ({...route, renderLane: "ours"})), ...diffBaseline];
      }
      return [...previousRoutes, ...ours.slice(0, 9).map((route) => ({...route, renderLane: "ours"}))];
    }

    function ordersForMap(frame) {
      const anchorsById = Object.fromEntries(workbench.map.anchors.orders.map((order) => [order.id, order]));
      const activeIds = new Set([...(frame.challenger.active_order_ids || []), ...(frame.highlighted_order_ids || [])]);
      const recent = workbench.map.anchors.orders.filter((order) => order.created_at_s <= inferenceState.currentTimeS && order.created_at_s >= inferenceState.currentTimeS - 1800);
      for (const order of recent) activeIds.add(order.id);
      return [...activeIds].map((id) => anchorsById[id]).filter(Boolean).sort((a, b) => a.created_at_s - b.created_at_s).slice(-32);
    }

    function riderPositionsForFrame(frame) {
      const moving = movingRiderPositions(frame);
      if (moving.length) return moving;
      return (frame.challenger.courier_positions || []).slice(0, 18).map((snapshot) => ({
        id: snapshot.courier_id,
        label: snapshot.label || snapshot.courier_id,
        position: snapshot.position,
        motion: "snapshot",
        phase: snapshot.status || "available"
      }));
    }

    function movingRiderPositions(frame) {
      const tracks = frame.challenger?.simulation_trace?.courier_tracks || [];
      return tracks.slice(0, 18).map((track) => {
        const sample = trackPositionAt(track, inferenceState.currentTimeS);
        return sample ? {
          id: track.courier_id,
          label: track.courier_id,
          order_id: track.order_id,
          position: sample.position,
          motion: "moving",
          phase: sample.phase,
          progress: sample.progress
        } : null;
      }).filter(Boolean);
    }

    function trackPositionAt(track, simTimeS) {
      const ticks = track.ticks || [];
      if (!ticks.length) return null;
      if (simTimeS <= ticks[0].absolute_s) return ticks[0];
      for (let index = 1; index < ticks.length; index += 1) {
        const left = ticks[index - 1];
        const right = ticks[index];
        if (simTimeS <= right.absolute_s) {
          const span = Math.max(1, right.absolute_s - left.absolute_s);
          const ratio = clamp((simTimeS - left.absolute_s) / span, 0, 1);
          return {
            phase: right.phase,
            progress: left.progress + (right.progress - left.progress) * ratio,
            position: {
              lat: left.position.lat + (right.position.lat - left.position.lat) * ratio,
              lng: left.position.lng + (right.position.lng - left.position.lng) * ratio,
              screen_x: left.position.screen_x + (right.position.screen_x - left.position.screen_x) * ratio,
              screen_y: left.position.screen_y + (right.position.screen_y - left.position.screen_y) * ratio
            }
          };
        }
      }
      return ticks[ticks.length - 1];
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

    function hydrateLivePage() {
      bindLiveControls();
      renderLiveRuntimeState();
    }

    function bindLiveControls() {
      const startButton = document.getElementById("start-inference");
      const pauseButton = document.getElementById("pause-inference");
      const speedSelect = document.getElementById("playback-speed");
      const modeSelect = document.getElementById("inference-mode");
      if (!startButton || !pauseButton || !speedSelect || !modeSelect) return;
      startButton.addEventListener("click", startInference);
      pauseButton.addEventListener("click", toggleInferencePause);
      speedSelect.value = String(inferenceState.speed);
      modeSelect.value = inferenceState.mode;
      speedSelect.addEventListener("change", () => setInferenceSpeed(Number(speedSelect.value)));
      modeSelect.addEventListener("change", () => setInferenceMode(modeSelect.value));
    }

    function startInference() {
      inferenceState.started = true;
      inferenceState.running = true;
      inferenceState.currentTimeS = workbench.timeline.start_s;
      inferenceState.lastTickAt = Date.now();
      scheduleInferenceTick();
      renderLiveRuntimeState();
    }

    function toggleInferencePause() {
      if (!inferenceState.started) {
        startInference();
        return;
      }
      inferenceState.running = !inferenceState.running;
      if (inferenceState.running) {
        inferenceState.lastTickAt = Date.now();
        scheduleInferenceTick();
      } else {
        clearInferenceTimer();
      }
      renderLiveRuntimeState();
    }

    function setInferenceSpeed(speed) {
      inferenceState.speed = [1, 2, 4].includes(speed) ? speed : 1;
      if (inferenceState.running) {
        inferenceState.lastTickAt = Date.now();
        scheduleInferenceTick();
      }
      renderLiveRuntimeState();
    }

    function setInferenceMode(mode) {
      inferenceState.mode = Object.prototype.hasOwnProperty.call(inferenceModeLabels, mode) ? mode : "current";
      renderLiveRuntimeState();
    }

    function clearInferenceTimer() {
      if (inferenceState.timerId !== null) {
        clearInterval(inferenceState.timerId);
        inferenceState.timerId = null;
      }
    }

    function scheduleInferenceTick() {
      clearInferenceTimer();
      inferenceState.timerId = setInterval(advanceInferenceTick, inferenceState.tickMs);
    }

    function advanceInferenceTick() {
      if (!inferenceState.running) return;
      const now = Date.now();
      const elapsedMs = inferenceState.lastTickAt ? now - inferenceState.lastTickAt : inferenceState.tickMs;
      inferenceState.lastTickAt = now;
      const simulatedStepS = Math.max(60, elapsedMs / 1000 * 900 * inferenceState.speed);
      setInferenceTime(inferenceState.currentTimeS + simulatedStepS);
    }

    function setInferenceTime(nextTimeS) {
      inferenceState.currentTimeS = clamp(nextTimeS, workbench.timeline.start_s, workbench.timeline.end_s);
      if (inferenceState.currentTimeS >= workbench.timeline.end_s) {
        inferenceState.running = false;
        clearInferenceTimer();
      }
      renderLiveRuntimeState();
    }

    function renderLiveRuntimeState() {
      const liveGrid = document.querySelector("[data-page='live']");
      if (!liveGrid) return;
      const stateLabel = inferenceState.running ? "自动推理中" : inferenceState.started ? "已暂停" : "未开始";
      const events = releasedEvents(inferenceState.currentTimeS);
      const currentScore = scoreForTime(inferenceState.currentTimeS);
      const currentDecision = decisionForTime(inferenceState.currentTimeS);
      liveGrid.dataset.inferenceState = inferenceState.running ? "running" : inferenceState.started ? "paused" : "ready";
      setText("inference-state-label", stateLabel);
      setText("inference-clock", clock(inferenceState.currentTimeS));
      setText("inference-speed-label", `${inferenceState.speed}x`);
      setText("inference-mode-label", inferenceModeLabels[inferenceState.mode]);
      setText("inference-event-count", events.length);
      setText("map-runtime-hint", `${stateLabel} / ${clock(inferenceState.currentTimeS)} / ${inferenceModeLabels[inferenceState.mode]}`);
      setText("event-flow-caption", `${events.length} events released automatically`);
      setText("round-summary-time", currentDecision.trigger_time_label);
      const progressBar = document.getElementById("inference-progress-bar");
      if (progressBar) progressBar.style.setProperty("--progress", `${inferenceProgressPct()}%`);
      const mapStage = document.getElementById("live-map-stage");
      if (mapStage) {
        const frame = frameForTime(inferenceState.currentTimeS);
        mapStage.dataset.mapMode = inferenceState.mode;
        mapStage.dataset.frameId = frame.id;
        mapStage.innerHTML = renderLiveMapLayer(frame);
      }
      const startButton = document.getElementById("start-inference");
      if (startButton) {
        startButton.disabled = inferenceState.started && inferenceState.running;
        startButton.textContent = inferenceState.started ? "重新开始" : "开始推理";
      }
      const pauseButton = document.getElementById("pause-inference");
      if (pauseButton) pauseButton.textContent = inferenceState.running ? "暂停" : "继续";
      const scoreStack = document.getElementById("live-score-stack");
      if (scoreStack) scoreStack.innerHTML = renderLiveScoreCards(currentScore);
      const eventFlow = document.getElementById("live-event-flow");
      if (eventFlow) eventFlow.innerHTML = events.slice(-9).reverse().map(renderEventItem).join("") || `<div class="list-item"><strong>等待开始</strong><p>点击开始推理后，订单进入、候选分配和累计结果将自动释放。</p></div>`;
      const summary = document.getElementById("live-round-summary");
      if (summary) summary.innerHTML = renderRoundSummary(currentDecision);
    }

    function setText(id, value) {
      const node = document.getElementById(id);
      if (node) node.textContent = String(value);
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
      if (routeId === "live") {
        hydrateLivePage();
      }
    }

    function renderLivePage() {
      const currentScore = scoreForTime(inferenceState.currentTimeS);
      const events = releasedEvents(inferenceState.currentTimeS).slice(-9).reverse();
      const currentDecision = decisionForTime(inferenceState.currentTimeS);
      const currentFrame = frameForTime(inferenceState.currentTimeS);
      return `
        ${pageHeader("live", "Live Map / GanttMap", "主工作台只展示对调度有用的内容：实时地图、累计优势、事件流和当前轮摘要。")}
        <div class="page-grid live-grid" data-page="live" data-inference-state="${inferenceState.running ? "running" : inferenceState.started ? "paused" : "ready"}">
          <div class="page-grid">
            <div class="control-dock" data-control-strip="live">
              <button id="start-inference" class="primary-button" data-control="start-inference">开始推理</button>
              <button id="pause-inference" class="ghost-button" data-control="pause-resume">暂停/继续</button>
              <select id="playback-speed" class="select-control" data-control="speed"><option value="1">1x</option><option value="2">2x</option><option value="4">4x</option></select>
              <select id="inference-mode" class="select-control" data-control="mode"><option value="current">当前算法</option><option value="compare">对比</option><option value="overlay">叠加</option></select>
              <div class="runtime-strip" data-inference-runtime="status">
                <div class="runtime-cell"><span>状态</span><b id="inference-state-label">未开始</b></div>
                <div class="runtime-cell"><span>推演时间</span><b id="inference-clock">${escapeHtml(clock(inferenceState.currentTimeS))}</b></div>
                <div class="runtime-cell"><span>倍速</span><b id="inference-speed-label">${inferenceState.speed}x</b></div>
                <div class="runtime-cell"><span>模式</span><b id="inference-mode-label">${escapeHtml(inferenceModeLabels[inferenceState.mode])}</b></div>
                <div class="runtime-cell"><span>释放事件</span><b id="inference-event-count">${releasedEvents(inferenceState.currentTimeS).length}</b></div>
              </div>
              <div class="inference-progress" aria-label="full day inference progress"><span id="inference-progress-bar" style="--progress:${inferenceProgressPct()}%"></span></div>
            </div>
            <div class="card map-panel">
              <div class="card-head"><h3>实时地图层</h3><span id="map-runtime-hint">merchants / orders / riders / routes / hotspots</span></div>
              <div id="live-map-stage" class="schematic-map" data-map-layer="primary" data-map-mode="${escapeHtml(inferenceState.mode)}" data-frame-id="${escapeHtml(currentFrame.id)}">
                ${renderLiveMapLayer(currentFrame)}
              </div>
            </div>
            <div class="card">
              <div class="card-head"><h3>轻量事件流</h3><span id="event-flow-caption">按全天推演时间释放</span></div>
              <div id="live-event-flow" class="card-body event-list">${events.map(renderEventItem).join("")}</div>
            </div>
          </div>
          <aside class="page-grid">
            <div class="card">
              <div class="card-head"><h3>实时累计对比栏</h3><span>baseline vs ours</span></div>
              <div id="live-score-stack" class="card-body score-stack">
                ${renderLiveScoreCards(currentScore)}
              </div>
            </div>
            <div class="card">
              <div class="card-head"><h3>本轮摘要</h3><span id="round-summary-time">${escapeHtml(currentDecision.trigger_time_label)}</span></div>
              <div id="live-round-summary" class="card-body compact-list">
                ${renderRoundSummary(currentDecision)}
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

    function renderLiveMapLayer(frame) {
      const routes = mapRouteRows(frame);
      const riders = riderPositionsForFrame(frame);
      const orders = ordersForMap(frame);
      return `
        <div class="map-mode-chip">${escapeHtml(inferenceModeLabels[inferenceState.mode])} / ${escapeHtml(frame.id)}</div>
        ${renderMapRoutes(routes)}
        ${renderHotspots()}
        ${renderMapDots("merchant", workbench.map.anchors.merchants.slice(0, 18), "position")}
        ${renderMapDots("rider", riders, "position")}
        ${renderMapDots("order", orders, "dropoff")}
        ${renderMapLegend()}
      `;
    }

    function renderMapRoutes(routes) {
      if (!routes.length) return "";
      return `
        <svg class="map-route" data-route-count="${routes.length}" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          ${routes.map((route) => {
            const points = route.polyline.map((point) => `${point.screen_x},${point.screen_y}`).join(" ");
            return `<polyline class="route-line" data-lane="${escapeHtml(route.renderLane || route.lane)}" data-order-id="${escapeHtml(route.order_id)}" data-courier-id="${escapeHtml(route.courier_id)}" points="${escapeHtml(points)}"></polyline>`;
          }).join("")}
        </svg>
      `;
    }

    function renderHotspots() {
      return workbench.map.hotspots.map((hotspot) => `
        <div class="hotspot" data-active="${hotspot.start_s <= inferenceState.currentTimeS && inferenceState.currentTimeS <= hotspot.end_s}" title="${escapeHtml(hotspot.summary)}" style="--x:${hotspot.center.screen_x};--y:${hotspot.center.screen_y};--severity:${hotspot.severity}"></div>
      `).join("");
    }

    function renderMapDots(kind, items, positionKey) {
      return items.map((item) => {
        const pos = item[positionKey];
        const release = kind === "order" && item.created_at_s >= inferenceState.currentTimeS - 900 ? "new" : "stable";
        const motion = kind === "rider" ? (item.motion || "snapshot") : "";
        return `<span class="map-dot" data-kind="${escapeHtml(kind)}" data-id="${escapeHtml(item.id)}" data-release="${escapeHtml(release)}" data-motion="${escapeHtml(motion)}" data-phase="${escapeHtml(item.phase || "")}" title="${escapeHtml(item.label || item.id)}" style="--x:${pos.screen_x};--y:${pos.screen_y}"></span>`;
      }).join("");
    }

    function renderMapLegend() {
      const items = [
        ["ours", "我方路线"],
        ["previous", "旧路线淡出"],
        ["baseline", "基线差异"],
        ["difference", "叠加差异"]
      ];
      return `<div class="map-legend">${items.map(([lane, label]) => `<span class="legend-item"><i class="legend-swatch" data-lane="${escapeHtml(lane)}"></i>${escapeHtml(label)}</span>`).join("")}</div>`;
    }

    function renderScoreCard(label, value, detail, tone) {
      return `<div class="score-card" data-tone="${escapeHtml(tone)}"><span>${escapeHtml(label)}</span><b>${escapeHtml(value)}</b><span>${escapeHtml(detail)}</span></div>`;
    }

    function renderLiveScoreCards(score) {
      return [
        renderScoreCard("基线/弹金算法累计", `${fmtNumber(score.baseline.total_cost_yuan, 1)} 元`, `${fmtNumber(score.baseline.total_time_cost_min, 1)} 分钟成本`, "warn"),
        renderScoreCard("我们的算法累计", `${fmtNumber(score.ours.total_cost_yuan, 1)} 元`, `${fmtNumber(score.ours.total_time_cost_min, 1)} 分钟成本`, "good"),
        renderScoreCard("时间差异", `${fmtNumber(score.deltas.time_saved_min, 1)} 分钟`, score.deltas.headline, "good"),
        renderScoreCard("金钱差异", `${fmtNumber(score.deltas.money_saved_yuan, 1)} 元`, `收益/成本差异 ${fmtNumber(score.deltas.profit_delta_yuan, 1)} 元`, "good"),
        renderScoreCard("超时单差异", `${fmtNumber(score.deltas.timeout_order_delta, 0)} 单`, `风险差异 ${fmtNumber(score.deltas.timeout_risk_delta, 3)}`, "good"),
        renderScoreCard("空驶里程差异", `${fmtNumber(score.deltas.empty_mileage_saved_km, 2)} km`, "只强调差异部分，不铺满两套路由", "good")
      ].join("");
    }

    function renderRoundSummary(decision) {
      return `
        <div class="list-item"><strong>${escapeHtml(decision.trigger_reason)}</strong><p>${escapeHtml(decision.round_result.summary)}</p></div>
        <div class="list-item"><strong>候选集合</strong><p>${decision.input_order_ids.length} orders / ${decision.candidate_rider_ids.length} riders</p></div>
        <div class="list-item"><strong>本轮累计优势</strong><p>节省 ${fmtNumber(decision.round_result.time_saved_min, 1)} 分钟，节省 ${fmtNumber(decision.round_result.cost_saved_yuan, 1)} 元。</p></div>
      `;
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
      renderRidersPage,
      inferenceState,
      startInference,
      toggleInferencePause,
      setInferenceSpeed,
      setInferenceMode,
      setInferenceTime,
      advanceInferenceTick,
      scoreForTime,
      decisionForTime,
      releasedEvents
    };
  </script>
</body>
</html>
"""
    return template.replace("__BOOT_JSON__", boot_json)
