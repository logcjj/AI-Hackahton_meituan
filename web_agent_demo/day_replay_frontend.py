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
    .memory-workspace { grid-template-columns: 1fr; }
    .memory-overview {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
    }
    .memory-section-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }
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
    .algorithm-pair {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }
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
    .score-card[data-tone="risk"] { background: var(--red-soft); border-color: rgba(180,35,24,.22); }
    .delta-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }
    .metric-strip {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 9px;
    }
    .metric-chip {
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--surface-2);
    }
    .metric-chip b { display: block; margin-bottom: 2px; font: 800 16px var(--mono); }
    .metric-chip span { display: block; color: var(--muted); font-size: 12px; }
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
    .event-item {
      display: grid;
      grid-template-columns: auto minmax(0, 1fr);
      gap: 8px;
      align-items: start;
    }
    .event-tag {
      padding: 4px 7px;
      border-radius: 999px;
      color: var(--accent-2);
      background: var(--green-soft);
      font: 800 10px var(--mono);
      white-space: nowrap;
    }
    .event-tag[data-family="order"] { color: #92400e; background: var(--amber-soft); }
    .event-tag[data-family="score"] { color: var(--accent-2); background: var(--green-soft); }
    .event-tag[data-family="memory"] { color: #1d4ed8; background: #dbeafe; }
    .event-tag[data-family="decision"] { color: #334155; background: #e2e8f0; }
    .round-summary-grid {
      display: grid;
      gap: 9px;
    }
    .timeline-item { text-align: left; width: 100%; border: 1px solid var(--line); background: var(--surface-2); border-radius: 12px; padding: 10px; }
    .timeline-item[data-active="true"] { border-color: rgba(15,118,110,.42); background: var(--green-soft); }
    .timeline-item strong { display: block; margin-bottom: 4px; font-size: 13px; }
    .timeline-item span { display: block; color: var(--muted); font-size: 12px; line-height: 1.45; }
    .timeline-meta {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
      margin-top: 7px;
      color: var(--muted);
      font: 700 10px var(--mono);
    }
    .decision-scroll { max-height: 690px; overflow: auto; }
    .decision-canvas { display: grid; gap: 12px; }
    .decision-stage {
      border: 1px solid var(--line);
      border-radius: 14px;
      background: var(--surface-2);
      overflow: hidden;
    }
    .decision-stage-head {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      padding: 11px 12px;
      border-bottom: 1px solid var(--line);
      background: rgba(255,255,255,.62);
    }
    .decision-stage-head b { color: var(--accent-2); font-size: 13px; }
    .decision-stage-head span { color: var(--muted); font: 800 10px var(--mono); }
    .decision-stage-body { display: grid; gap: 8px; padding: 11px 12px; }
    .chip-list { display: flex; flex-wrap: wrap; gap: 6px; }
    .data-chip {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 5px 8px;
      border: 1px solid var(--line);
      border-radius: 999px;
      color: var(--ink);
      background: #fff;
      font: 700 11px var(--mono);
    }
    .score-row {
      display: grid;
      grid-template-columns: 138px 1fr auto;
      gap: 9px;
      align-items: center;
      padding: 8px;
      border: 1px solid var(--line);
      border-radius: 11px;
      background: #fff;
    }
    .score-bar {
      height: 8px;
      overflow: hidden;
      border-radius: 999px;
      background: #e2e8f0;
    }
    .score-bar span {
      display: block;
      width: calc(var(--score) * 100%);
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, var(--accent), #22c55e);
    }
    .action-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
    }
    .action-card {
      padding: 9px;
      border: 1px solid var(--line);
      border-radius: 11px;
      background: #fff;
    }
    .action-card strong { display: block; margin-bottom: 4px; font-size: 12px; }
    .action-card p { margin: 0; color: var(--muted); font-size: 12px; line-height: 1.45; }
    .context-metric-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
    }
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
    .input-workspace, .resource-workspace { grid-template-columns: 1fr; }
    .operations-overview {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
    }
    .operations-grid {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 330px;
      gap: 14px;
      align-items: start;
    }
    .orders-table-shell { max-height: 660px; }
    .filter-bar .filter-count {
      margin-left: auto;
      align-self: center;
      color: var(--muted);
      font: 800 11px var(--mono);
      letter-spacing: .04em;
      text-transform: uppercase;
    }
    .order-context-list, .rider-context-list {
      display: grid;
      gap: 9px;
    }
    .time-lane {
      display: grid;
      gap: 8px;
    }
    .time-lane-item {
      display: grid;
      grid-template-columns: 92px minmax(0, 1fr) auto;
      gap: 8px;
      align-items: center;
      color: var(--muted);
      font-size: 12px;
    }
    .lane-bar {
      height: 7px;
      overflow: hidden;
      border-radius: 999px;
      background: #e2e8f0;
    }
    .lane-bar span {
      display: block;
      width: calc(var(--weight) * 100%);
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, var(--accent), #22c55e);
    }
    .result-pair {
      display: grid;
      gap: 2px;
      font-size: 12px;
    }
    .result-pair b { color: var(--ink); font-weight: 800; }
    .result-pair span { color: var(--muted); }
    .rider-board {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }
    .rider-card[data-state="busy"] { border-color: rgba(15,118,110,.30); }
    .rider-card[data-state="ending_shift"] { border-color: rgba(183,121,31,.30); }
    .rider-load {
      height: 7px;
      overflow: hidden;
      border-radius: 999px;
      background: #e2e8f0;
    }
    .rider-load span {
      display: block;
      width: calc(var(--load) * 100%);
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, var(--accent), #22c55e);
    }
    .mini-map .map-dot[data-kind="home"] { --size: 9px; background: #64748b; }
    .mini-map .map-dot[data-kind="linked-order"] { --size: 8px; background: var(--amber); }
    .memory-card { min-height: 220px; }
    .memory-card[data-memory-section] .card-head span {
      font: 800 11px var(--mono);
    }
    .memory-item {
      display: grid;
      gap: 8px;
    }
    .memory-item-head {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: flex-start;
    }
    .memory-item-head strong { margin: 0; }
    .memory-stage {
      padding: 4px 7px;
      border-radius: 999px;
      color: var(--accent-2);
      background: var(--green-soft);
      font: 800 10px var(--mono);
      white-space: nowrap;
    }
    .memory-stage[data-stage="curated"] { color: #1d4ed8; background: #dbeafe; }
    .memory-stage[data-stage="active"] { color: #92400e; background: var(--amber-soft); }
    .memory-stage[data-stage="feedback"] { color: #334155; background: #e2e8f0; }
    .memory-field-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 7px;
    }
    .memory-field {
      padding: 8px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: #fff;
    }
    .memory-field b {
      display: block;
      margin-bottom: 3px;
      color: var(--accent-2);
      font: 800 10px var(--mono);
      letter-spacing: .04em;
      text-transform: uppercase;
    }
    .memory-field span { color: var(--muted); font-size: 12px; line-height: 1.45; }
    .memory-meter {
      height: 7px;
      overflow: hidden;
      border-radius: 999px;
      background: #e2e8f0;
    }
    .memory-meter span {
      display: block;
      width: calc(var(--confidence) * 100%);
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, var(--accent), #22c55e);
    }
    .recall-lane {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }
    .recall-card {
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: var(--surface-2);
    }
    .recall-card strong { display: block; margin-bottom: 6px; font-size: 13px; }
    .recall-card p { margin: 0 0 8px; color: var(--muted); font-size: 12px; line-height: 1.45; }
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
      .metric-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .operations-overview, .operations-grid, .rider-board { grid-template-columns: 1fr; }
      .memory-overview, .memory-section-grid, .recall-lane { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (max-width: 720px) {
      .workbench-shell { display: block; }
      .workbench-nav { position: relative; height: auto; }
      .nav-list { grid-template-columns: repeat(5, minmax(0, 1fr)); }
      .nav-link { padding: 8px 4px; }
      .route-view { padding: 14px; }
      .page-head { grid-template-columns: 1fr; }
      .algorithm-pair, .delta-grid, .metric-strip { grid-template-columns: 1fr; }
      .operations-overview { grid-template-columns: 1fr; }
      .memory-overview, .memory-section-grid, .recall-lane, .memory-field-grid, .context-metric-grid { grid-template-columns: 1fr; }
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
    let selectedDecisionId = workbench.decisions[0]?.id || "";
    const orderIndex = Object.fromEntries(workbench.entities.orders.map((order) => [order.id, order]));
    const orderFilterState = {
      timeBand: "all",
      area: "all",
      status: "all",
      risk: "all"
    };
    const riderFilterState = {
      area: "all",
      state: "all"
    };
    const inferenceModeLabels = {
      current: "当前算法",
      compare: "对比",
      overlay: "叠加"
    };
    const eventTypeClasses = {
      order_entered: "event-type-order_entered",
      decision_round: "event-type-decision_round",
      score_update: "event-type-score_update",
      memory_writeback: "event-type-memory_writeback",
      memory_recall: "event-type-memory_recall",
      future_policy_shift: "event-type-future_policy_shift"
    };
    const eventMeta = {
      order_entered: { label: "订单进入", family: "order" },
      decision_round: { label: "决策轮次", family: "decision" },
      score_update: { label: "累计更新", family: "score" },
      memory_writeback: { label: "记忆写入", family: "memory" },
      memory_recall: { label: "记忆命中", family: "memory" },
      future_policy_shift: { label: "策略整理", family: "memory" }
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

    function fmtSigned(value, digits = 1) {
      const numberValue = Number(value);
      if (Number.isNaN(numberValue)) return "-";
      const sign = numberValue > 0 ? "+" : "";
      return `${sign}${fmtNumber(numberValue, digits)}`;
    }

    function fmtFewer(value, unit, digits = 0) {
      const numberValue = Number(value) || 0;
      if (numberValue < 0) return `少 ${fmtNumber(Math.abs(numberValue), digits)} ${unit}`;
      if (numberValue > 0) return `多 ${fmtNumber(numberValue, digits)} ${unit}`;
      return `持平 ${fmtNumber(0, digits)} ${unit}`;
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

    function zeroMetrics() {
      return {
        total_orders: 0,
        delivered_orders: 0,
        assigned_orders: 0,
        late_orders: 0,
        coverage_rate: 0,
        avg_eta_min: 0,
        p95_eta_min: 0,
        total_time_cost_min: 0,
        total_distance_km: 0,
        total_cost_yuan: 0,
        timeout_risk: 0,
        courier_utilization: 0,
        gross_revenue_yuan: 0
      };
    }

    function preDispatchScore(simTimeS) {
      return {
        frame_id: "pre-dispatch",
        time_s: simTimeS,
        time_label: clock(simTimeS),
        baseline: zeroMetrics(),
        ours: zeroMetrics(),
        deltas: {
          time_saved_s: 0,
          time_saved_min: 0,
          money_saved_yuan: 0,
          timeout_order_delta: 0,
          timeout_risk_delta: 0,
          empty_mileage_saved_m: 0,
          empty_mileage_saved_km: 0,
          revenue_delta_yuan: 0,
          profit_delta_yuan: 0,
          extra_delivered_orders: 0,
          utilization_delta: 0,
          headline: "等待首轮规划评分，订单正在进入推理队列。"
        }
      };
    }

    function scoreForTime(simTimeS) {
      const series = workbench.metrics.series;
      if (!series.length) return workbench.metrics.final || preDispatchScore(simTimeS);
      if (simTimeS < series[0].time_s) return preDispatchScore(simTimeS);
      let selected = series[0] || workbench.metrics.final;
      for (const item of series) {
        if (item.time_s <= simTimeS) selected = item;
        else break;
      }
      return selected;
    }

    function preDispatchDecision(simTimeS) {
      const queuedOrders = workbench.map.anchors.orders.filter((order) => order.created_at_s <= simTimeS).slice(-8).map((order) => order.id);
      const onlineRiders = workbench.entities.riders.slice(0, 6).map((rider) => rider.id);
      return {
        id: "D-pre-dispatch",
        frame_id: "pre-dispatch",
        trigger_time_s: simTimeS,
        trigger_time_label: clock(simTimeS),
        trigger_reason: "等待首轮 Planner 决策触发。",
        input_order_ids: queuedOrders,
        input_orders: [],
        candidate_rider_ids: onlineRiders,
        candidate_riders: [],
        filtering_process: [
          { stage: "order_release", remaining: queuedOrders.length, summary: "订单逐步进入推理队列，尚未触发首轮评分。" },
          { stage: "rider_pool", remaining: onlineRiders.length, summary: "在线骑手资源已预载，等待规划窗口开启。" }
        ],
        scoring_process: [],
        final_actions: [],
        abandoned_actions: [],
        round_result: {
          summary: "首轮决策尚未生成；当前仅展示已进入队列的订单和资源上下文。",
          time_saved_min: 0,
          cost_saved_yuan: 0,
          timeout_risk_delta: 0,
          extra_delivered_orders: 0
        },
        result_writeback: {
          memory_event_ids: [],
          writeback_count: 0,
          summary: "No memory writeback before first planner decision."
        },
        context: {
          time_slice_id: "pre-dispatch",
          demand_phase: "pre-dispatch",
          weather: "pending",
          congestion_level: 0,
          courier_supply: onlineRiders.length,
          shock_ids: []
        }
      };
    }

    function decisionForTime(simTimeS) {
      if (!workbench.decisions.length || simTimeS < workbench.decisions[0].trigger_time_s) {
        return preDispatchDecision(simTimeS);
      }
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
      if (frames.length && simTimeS < frames[0].sim_time_s) {
        return preDispatchFrame(simTimeS);
      }
      for (const frame of frames) {
        if (frame.sim_time_s <= simTimeS) selected = frame;
        else break;
      }
      return selected || { id: "", sim_time_s: workbench.timeline.start_s, highlighted_order_ids: [], challenger: { route_overlays: [], simulation_trace: { courier_tracks: [] }, courier_positions: [] }, baseline: { route_overlays: [], assignments: [] } };
    }

    function preDispatchFrame(simTimeS) {
      return {
        id: "pre-dispatch",
        sim_time_s: simTimeS,
        highlighted_order_ids: [],
        challenger: {
          active_order_ids: [],
          route_overlays: [],
          simulation_trace: { courier_tracks: [] },
          courier_positions: workbench.map.anchors.riders.slice(0, 18).map((rider) => ({
            courier_id: rider.id,
            label: rider.label,
            position: rider.position,
            status: "online"
          }))
        },
        baseline: { route_overlays: [], assignments: [] }
      };
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
      setText("cumulative-metrics-caption", `${currentScore.time_label} 累计优势`);
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
      const cumulativeMetrics = document.getElementById("live-cumulative-metrics");
      if (cumulativeMetrics) cumulativeMetrics.innerHTML = renderLiveCumulativeMetrics(currentScore);
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
      } else if (routeId === "decisions") {
        hydrateDecisionPage();
      } else if (routeId === "orders") {
        hydrateOrdersPage();
      } else if (routeId === "riders") {
        hydrateRidersPage();
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
            <div class="card">
              <div class="card-head"><h3>累积指标区</h3><span id="cumulative-metrics-caption">${escapeHtml(currentScore.time_label)} 累计优势</span></div>
              <div id="live-cumulative-metrics" class="card-body metric-strip">
                ${renderLiveCumulativeMetrics(currentScore)}
              </div>
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
      const decision = selectedDecision();
      return `
        ${pageHeader("decisions", "Planner / Chart / Gantt", "把规划视图重构为推导过程页：左侧轮次，中间推导，右侧上下文和回写。")}
        <div class="page-grid decision-grid" data-page="decisions" data-decision-route="planner">
          <div class="card">
            <div class="card-head"><h3>决策轮次时间线</h3><span id="decision-route-status">${workbench.decisions.length} rounds</span></div>
            <div id="decision-timeline" class="card-body timeline-list decision-scroll">
              ${renderDecisionTimeline(decision.id)}
            </div>
          </div>
          <div class="card">
            <div class="card-head"><h3>当前轮推导过程</h3><span id="decision-reasoning-phase">${escapeHtml(decision.context.demand_phase)}</span></div>
            <div id="decision-reasoning-canvas" class="card-body decision-canvas">
              ${renderDecisionReasoning(decision)}
            </div>
          </div>
          <aside class="card">
            <div class="card-head"><h3>输入上下文 + 输出结果</h3><span id="decision-context-slice">${escapeHtml(decision.context.time_slice_id)}</span></div>
            <div id="decision-context-pane" class="card-body compact-list">
              ${renderDecisionContext(decision)}
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
      const stats = memoryStats();
      const activeHits = memoryItemsForSection("active", byId).slice(0, 3);
      return `
        ${pageHeader("memory", "Hermes-style Memory", "这里展示系统长期记忆的形成、整理、命中和反馈，不做资产表或文档中心。")}
        <div class="page-grid memory-workspace" data-page="memory" data-memory-route="hermes-long-term">
          <div id="memory-overview" class="memory-overview">
            ${renderMemoryOverview(stats)}
          </div>
          <div class="card" id="memory-current-recall">
            <div class="card-head"><h3>当前召回链路</h3><span>${activeHits.length} active hits</span></div>
            <div class="card-body recall-lane">
              ${activeHits.map(renderMemoryRecallCard).join("")}
            </div>
          </div>
          <div class="memory-section-grid">
            ${sections.map(([sectionId, title]) => `
              <div class="card memory-card" id="memory-section-${escapeHtml(sectionId)}" data-memory-section="${escapeHtml(sectionId)}">
                <div class="card-head"><h3>${escapeHtml(title)}</h3><span>${workbench.memory.sections[sectionId].length} memories</span></div>
                <div class="card-body memory-list">
                  ${memoryItemsForSection(sectionId, byId).slice(0, 5).map(renderMemoryItem).join("")}
                </div>
              </div>
            `).join("")}
          </div>
        </div>
      `;
    }

    function renderOrdersPage() {
      const orders = filteredOrders();
      return `
        ${pageHeader("orders", "Jobs / Orders", "全天订单全集已经预置，页面定位是调度输入视图，不是后台录入表。")}
        <div class="page-grid input-workspace" data-page="orders" data-orders-route="jobs-input">
          <div id="orders-overview" class="operations-overview">
            ${renderOrdersOverview(orders)}
          </div>
          <div id="orders-filter-bar" class="filter-bar" data-filter-bar="orders">
            <select id="orders-filter-time" class="select-control" data-order-filter="timeBand">
              <option value="all">全部时间段</option>
              ${workbench.filters.order_time_bands.map((item) => `<option value="${escapeHtml(item.id)}"${item.id === orderFilterState.timeBand ? " selected" : ""}>${escapeHtml(item.label)} / ${escapeHtml(item.time_label)}</option>`).join("")}
            </select>
            <select id="orders-filter-area" class="select-control" data-order-filter="area">
              <option value="all">全部商圈</option>
              ${workbench.filters.areas.map((item) => `<option value="${escapeHtml(item)}"${item === orderFilterState.area ? " selected" : ""}>${escapeHtml(item)}</option>`).join("")}
            </select>
            <select id="orders-filter-status" class="select-control" data-order-filter="status">
              <option value="all">全部状态</option>
              ${workbench.filters.statuses.map((item) => `<option value="${escapeHtml(item)}"${item === orderFilterState.status ? " selected" : ""}>${escapeHtml(item)}</option>`).join("")}
            </select>
            <select id="orders-filter-risk" class="select-control" data-order-filter="risk">
              <option value="all">全部风险</option>
              ${workbench.filters.risk_levels.map((item) => `<option value="${escapeHtml(item)}"${item === orderFilterState.risk ? " selected" : ""}>${escapeHtml(item)}</option>`).join("")}
            </select>
            <span id="orders-result-count" class="filter-count">${orders.length} / ${workbench.entities.orders.length} orders</span>
          </div>
          <div class="operations-grid">
            <div class="table-shell orders-table-shell" data-order-universe="full-day">
              <table>
                <thead><tr><th>订单编号</th><th>商家/提货点</th><th>下单时间</th><th>承诺送达</th><th>当前状态</th><th>风险等级</th><th>所属商圈</th><th>进入推理</th><th>基线算法结果</th><th>我方算法结果</th></tr></thead>
                <tbody id="orders-table-body">${orders.map(renderOrderRow).join("")}</tbody>
              </table>
            </div>
            <aside class="card" id="orders-context-panel">
              ${renderOrdersContext(orders)}
            </aside>
          </div>
        </div>
      `;
    }

    function renderRidersPage() {
      const riders = filteredRiders();
      return `
        ${pageHeader("riders", "Workers", "全天骑手资源预置为调度资源盘点：班次、状态、位置、负载和任务链。")}
        <div class="page-grid resource-workspace" data-page="riders" data-riders-route="workers-resource">
          <div id="riders-overview" class="operations-overview">
            ${renderRidersOverview(riders)}
          </div>
          <div id="riders-filter-bar" class="filter-bar" data-filter-bar="riders">
            <select id="riders-filter-area" class="select-control" data-rider-filter="area">
              <option value="all">全部区域</option>
              ${workbench.filters.areas.map((item) => `<option value="${escapeHtml(item)}"${item === riderFilterState.area ? " selected" : ""}>${escapeHtml(item)}</option>`).join("")}
            </select>
            <select id="riders-filter-state" class="select-control" data-rider-filter="state">
              <option value="all">全部在线状态</option>
              ${workbench.filters.rider_states.map((item) => `<option value="${escapeHtml(item)}"${item === riderFilterState.state ? " selected" : ""}>${escapeHtml(item)}</option>`).join("")}
            </select>
            <span id="riders-result-count" class="filter-count">${riders.length} / ${workbench.entities.riders.length} riders</span>
          </div>
          <div class="operations-grid">
            <div id="rider-resource-board" class="rider-board">
              ${riders.map(renderRiderCard).join("")}
            </div>
            <aside class="card" id="rider-context-panel">
              ${renderRidersContext(riders)}
            </aside>
          </div>
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

    function renderScoreCard(label, value, detail, tone, metricId = "") {
      const metricAttrs = metricId ? ` id="${escapeHtml(metricId)}" data-metric="${escapeHtml(metricId)}"` : "";
      return `<div class="score-card" data-tone="${escapeHtml(tone)}"${metricAttrs}><span>${escapeHtml(label)}</span><b>${escapeHtml(value)}</b><span>${escapeHtml(detail)}</span></div>`;
    }

    function renderLiveScoreCards(score) {
      const timeoutTone = score.deltas.timeout_order_delta <= 0 ? "good" : "risk";
      const emptyTone = score.deltas.empty_mileage_saved_km >= 0 ? "good" : "risk";
      const profitTone = score.deltas.profit_delta_yuan >= 0 ? "good" : "risk";
      return `
        <div class="algorithm-pair" data-score-section="algorithm-cumulative">
          ${renderScoreCard("基线/弹金算法累计", `${fmtNumber(score.baseline.total_cost_yuan, 1)} 元`, `${fmtNumber(score.baseline.total_time_cost_min, 1)} 分钟 / ${score.baseline.late_orders} 超时单`, "warn", "metric-baseline-cumulative")}
          ${renderScoreCard("我们的算法累计", `${fmtNumber(score.ours.total_cost_yuan, 1)} 元`, `${fmtNumber(score.ours.total_time_cost_min, 1)} 分钟 / ${score.ours.late_orders} 超时单`, "good", "metric-ours-cumulative")}
        </div>
        <div class="delta-grid" data-score-section="advantage-deltas">
          ${renderScoreCard("时间差异", `节省 ${fmtNumber(score.deltas.time_saved_min, 1)} 分钟`, score.deltas.headline, "good", "metric-time-delta")}
          ${renderScoreCard("金钱差异", `节省 ${fmtNumber(score.deltas.money_saved_yuan, 1)} 元`, `收益 ${fmtSigned(score.deltas.revenue_delta_yuan, 1)} 元 / 利润 ${fmtSigned(score.deltas.profit_delta_yuan, 1)} 元`, profitTone, "metric-money-delta")}
          ${renderScoreCard("超时单差异", fmtFewer(score.deltas.timeout_order_delta, "单"), `风险差异 ${fmtSigned(score.deltas.timeout_risk_delta, 3)}`, timeoutTone, "metric-timeout-delta")}
          ${renderScoreCard("空驶里程差异", `节省 ${fmtNumber(score.deltas.empty_mileage_saved_km, 2)} km`, "对比/叠加模式只强调差异路线", emptyTone, "metric-empty-mileage-delta")}
          ${renderScoreCard("收益/成本差异", `${fmtSigned(score.deltas.profit_delta_yuan, 1)} 元`, `收入 ${fmtSigned(score.deltas.revenue_delta_yuan, 1)} 元 / 成本节省 ${fmtNumber(score.deltas.money_saved_yuan, 1)} 元`, profitTone, "metric-profit-delta")}
        </div>
      `;
    }

    function renderMetricChip(metricId, label, value, detail) {
      return `<div class="metric-chip" id="metric-chip-${escapeHtml(metricId)}" data-metric="${escapeHtml(metricId)}"><span>${escapeHtml(label)}</span><b>${escapeHtml(value)}</b><span>${escapeHtml(detail)}</span></div>`;
    }

    function renderLiveCumulativeMetrics(score) {
      return [
        renderMetricChip("time-delta", "时间差异", `${fmtNumber(score.deltas.time_saved_min, 1)} min`, `baseline ${fmtNumber(score.baseline.total_time_cost_min, 1)} / ours ${fmtNumber(score.ours.total_time_cost_min, 1)}`),
        renderMetricChip("money-delta", "金钱差异", `${fmtNumber(score.deltas.money_saved_yuan, 1)} 元`, `baseline ${fmtNumber(score.baseline.total_cost_yuan, 1)} / ours ${fmtNumber(score.ours.total_cost_yuan, 1)}`),
        renderMetricChip("timeout-delta", "超时单差异", fmtFewer(score.deltas.timeout_order_delta, "单"), `baseline ${score.baseline.late_orders} / ours ${score.ours.late_orders}`),
        renderMetricChip("empty-mileage-delta", "空驶里程差异", `${fmtNumber(score.deltas.empty_mileage_saved_km, 2)} km`, `总距离差异 ${fmtSigned(score.deltas.empty_mileage_saved_m, 0)} m`),
        renderMetricChip("profit-delta", "收益/成本差异", `${fmtSigned(score.deltas.profit_delta_yuan, 1)} 元`, `收益 ${fmtSigned(score.deltas.revenue_delta_yuan, 1)} / 成本 ${fmtNumber(score.deltas.money_saved_yuan, 1)}`)
      ].join("");
    }

    function actionSummary(actions, limit = 3) {
      if (!actions || !actions.length) return "暂无动作";
      const preview = actions.slice(0, limit).map((item) => {
        const eta = item.total_eta_min === undefined ? "" : ` / ${fmtNumber(item.total_eta_min, 1)}min`;
        return `${item.order_id}->${item.courier_id}${eta}`;
      }).join(", ");
      return actions.length > limit ? `${preview} +${actions.length - limit} more` : preview;
    }

    function decisionById(decisionId) {
      return workbench.decisions.find((item) => item.id === decisionId) || workbench.decisions[0];
    }

    function selectedDecision() {
      const decision = decisionById(selectedDecisionId);
      selectedDecisionId = decision?.id || "";
      return decision;
    }

    function hydrateDecisionPage() {
      const timeline = document.getElementById("decision-timeline");
      if (!timeline) return;
      timeline.addEventListener("click", (event) => {
        const button = event.target.closest("[data-decision-id]");
        if (button) selectDecisionRound(button.dataset.decisionId);
      });
      selectDecisionRound(selectedDecisionId || workbench.decisions[0]?.id);
    }

    function selectDecisionRound(decisionId) {
      const decision = decisionById(decisionId);
      if (!decision) return;
      selectedDecisionId = decision.id;
      const timeline = document.getElementById("decision-timeline");
      if (timeline) {
        for (const item of timeline.querySelectorAll("[data-decision-id]")) {
          item.dataset.active = item.dataset.decisionId === decision.id ? "true" : "false";
        }
      }
      setText("decision-route-status", `${decision.trigger_time_label} / ${decision.id}`);
      setText("decision-reasoning-phase", decision.context.demand_phase);
      setText("decision-context-slice", decision.context.time_slice_id);
      const reasoning = document.getElementById("decision-reasoning-canvas");
      if (reasoning) reasoning.innerHTML = renderDecisionReasoning(decision);
      const contextPane = document.getElementById("decision-context-pane");
      if (contextPane) contextPane.innerHTML = renderDecisionContext(decision);
    }

    function renderDecisionTimeline(activeId) {
      return workbench.decisions.map((item) => `
        <button class="timeline-item" data-decision-id="${escapeHtml(item.id)}" data-active="${item.id === activeId}">
          <strong>${escapeHtml(item.trigger_time_label)} ${escapeHtml(item.id)}</strong>
          <span>${escapeHtml(item.trigger_reason)}</span>
          <span class="timeline-meta">
            <em>${item.input_order_ids.length} orders</em>
            <em>${item.candidate_rider_ids.length} riders</em>
            <em>${escapeHtml(item.context.demand_phase)}</em>
          </span>
        </button>
      `).join("");
    }

    function renderDecisionStage(stageId, title, count, body) {
      return `
        <section class="decision-stage" id="${escapeHtml(stageId)}" data-decision-stage="${escapeHtml(stageId)}">
          <div class="decision-stage-head"><b>${escapeHtml(title)}</b><span>${escapeHtml(count)}</span></div>
          <div class="decision-stage-body">${body}</div>
        </section>
      `;
    }

    function renderChipList(items, emptyLabel = "None") {
      const values = (items || []).filter(Boolean);
      if (!values.length) return `<p>${escapeHtml(emptyLabel)}</p>`;
      return `<div class="chip-list">${values.map((item) => `<span class="data-chip">${escapeHtml(item)}</span>`).join("")}</div>`;
    }

    function renderDecisionScoreRows(scores) {
      if (!scores.length) return `<p>等待评分</p>`;
      const maxScore = Math.max(...scores.map((item) => Number(item.score) || 0), 1);
      return scores.map((item) => {
        const normalized = clamp((Number(item.score) || 0) / maxScore, 0.04, 1);
        return `
          <div class="score-row" data-algorithm-id="${escapeHtml(item.algorithm_id)}">
            <b>${escapeHtml(item.algorithm_id)}</b>
            <div>
              <div class="score-bar" style="--score:${normalized}"><span></span></div>
              <p>${escapeHtml(item.reason)}</p>
            </div>
            <em>${fmtNumber(item.score, 3)}</em>
          </div>
        `;
      }).join("");
    }

    function renderDecisionActions(actions, kind) {
      if (!actions.length) return `<p>暂无动作</p>`;
      return `<div class="action-grid">${actions.map((item) => {
        const detail = kind === "final"
          ? `ETA ${fmtNumber(item.total_eta_min, 1)} min / cost ${fmtNumber(item.expected_cost_yuan, 1)} yuan / risk ${fmtNumber(item.timeout_risk, 3)}`
          : item.reason || "Rejected by current scoring policy.";
        return `
          <div class="action-card" data-action-kind="${escapeHtml(kind)}">
            <strong>${escapeHtml(item.order_id)} -> ${escapeHtml(item.courier_id)}</strong>
            <p>${escapeHtml(detail)}</p>
          </div>
        `;
      }).join("")}</div>`;
    }

    function renderDecisionReasoning(decision) {
      const inputOrderIds = decision.input_orders.length ? decision.input_orders.map((item) => item.id) : decision.input_order_ids;
      const candidateRiderIds = decision.candidate_riders.length ? decision.candidate_riders.map((item) => item.id) : decision.candidate_rider_ids;
      return `
        ${renderDecisionStage("decision-trigger-time", "触发时间", decision.trigger_time_label, `<p>${escapeHtml(decision.trigger_time_label)} / ${escapeHtml(decision.id)}</p>`)}
        ${renderDecisionStage("decision-trigger-reason", "触发原因", decision.context.time_slice_id, `<p>${escapeHtml(decision.trigger_reason)}</p>`)}
        ${renderDecisionStage("decision-input-orders", "输入订单集合", `${inputOrderIds.length} orders`, renderChipList(inputOrderIds, "当前轮无释放订单"))}
        ${renderDecisionStage("decision-candidate-riders", "候选骑手集合", `${candidateRiderIds.length} riders`, renderChipList(candidateRiderIds, "暂无候选骑手"))}
        ${renderDecisionStage("decision-filtering-process", "过滤过程", `${decision.filtering_process.length} stages`, decision.filtering_process.map((stage) => renderStageRow(stage.stage, `${stage.remaining} remain`, stage.summary)).join(""))}
        ${renderDecisionStage("decision-scoring-process", "评分过程", `${decision.scoring_process.length} algorithms`, renderDecisionScoreRows(decision.scoring_process))}
        ${renderDecisionStage("decision-final-actions", "最终动作", `${decision.final_actions.length} assignments`, renderDecisionActions(decision.final_actions, "final"))}
        ${renderDecisionStage("decision-abandoned-actions", "被放弃动作", `${decision.abandoned_actions.length} alternatives`, renderDecisionActions(decision.abandoned_actions, "abandoned"))}
        ${renderDecisionStage("decision-round-result", "本轮结果", `${fmtNumber(decision.round_result.time_saved_min, 1)} min saved`, `<p>${escapeHtml(decision.round_result.summary)}</p>`)}
        ${renderDecisionStage("decision-result-writeback", "结果回写", `${decision.result_writeback.writeback_count} writebacks`, `<p>${escapeHtml(decision.result_writeback.summary)}</p>${renderChipList(decision.result_writeback.memory_event_ids, "无回写记忆")}`)}
      `;
    }

    function renderDecisionContext(decision) {
      return `
        <div class="list-item" id="decision-context-input">
          <strong>输入上下文</strong>
          <p>${escapeHtml(decision.context.demand_phase)} / ${escapeHtml(decision.context.weather)} / congestion ${fmtNumber(decision.context.congestion_level, 2)} / supply ${decision.context.courier_supply}</p>
          <p>shocks: ${decision.context.shock_ids.length ? decision.context.shock_ids.map(escapeHtml).join(", ") : "none"}</p>
        </div>
        <div class="list-item" id="decision-output-result">
          <strong>输出结果</strong>
          <p>${escapeHtml(decision.round_result.summary)}</p>
        </div>
        <div class="context-metric-grid">
          ${renderMetricChip("decision-time-saved", "时间收益", `${fmtNumber(decision.round_result.time_saved_min, 1)} min`, "this round")}
          ${renderMetricChip("decision-cost-saved", "成本收益", `${fmtNumber(decision.round_result.cost_saved_yuan, 1)} 元`, "this round")}
          ${renderMetricChip("decision-risk-delta", "风险变化", fmtSigned(decision.round_result.timeout_risk_delta, 3), "timeout risk")}
          ${renderMetricChip("decision-extra-delivered", "额外交付", `${decision.round_result.extra_delivered_orders} 单`, "vs baseline")}
        </div>
        <div class="list-item" id="decision-round-summary">
          <strong>本轮摘要</strong>
          <p>输入 ${decision.input_order_ids.length} 单，候选 ${decision.candidate_rider_ids.length} 名骑手，最终 ${decision.final_actions.length} 个动作，放弃 ${decision.abandoned_actions.length} 个基线动作。</p>
        </div>
        <div class="list-item" id="decision-writeback-summary">
          <strong>结果回写</strong>
          <p>${decision.result_writeback.writeback_count} writebacks / ${decision.result_writeback.memory_event_ids.map(escapeHtml).join(", ") || "无"}</p>
        </div>
      `;
    }

    function renderRoundSummary(decision) {
      const finalActions = actionSummary(decision.final_actions, 3);
      const abandonedActions = actionSummary(decision.abandoned_actions, 3);
      const filterSummary = decision.filtering_process.slice(0, 3).map((stage) => `${stage.stage}: ${stage.remaining}`).join(" / ");
      const scoreSummary = decision.scoring_process.slice(0, 3).map((item) => `${item.algorithm_id} ${fmtNumber(item.score, 3)}`).join(" / ") || "等待评分";
      const writebackIds = decision.result_writeback.memory_event_ids.slice(0, 4).join(", ") || "无";
      return `
        <div class="round-summary-grid" data-decision-id="${escapeHtml(decision.id)}">
          <div class="list-item" id="round-trigger"><strong>触发原因</strong><p>${escapeHtml(decision.trigger_reason)}</p></div>
          <div class="list-item" id="round-input-context"><strong>输入上下文</strong><p>${decision.input_order_ids.length} orders / ${decision.candidate_rider_ids.length} riders / ${escapeHtml(decision.context.weather)} / congestion ${fmtNumber(decision.context.congestion_level, 2)}</p></div>
          <div class="list-item" id="round-filtering"><strong>过滤过程</strong><p>${escapeHtml(filterSummary)}</p></div>
          <div class="list-item" id="round-scoring"><strong>评分过程</strong><p>${escapeHtml(scoreSummary)}</p></div>
          <div class="list-item" id="round-final-actions"><strong>最终动作</strong><p>${escapeHtml(finalActions)}</p></div>
          <div class="list-item" id="round-abandoned-actions"><strong>被放弃动作</strong><p>${escapeHtml(abandonedActions)}</p></div>
          <div class="list-item" id="round-writeback"><strong>结果回写</strong><p>${decision.result_writeback.writeback_count} writebacks / ${escapeHtml(writebackIds)}</p></div>
          <div class="list-item" id="round-metric-impact"><strong>本轮结果</strong><p>${escapeHtml(decision.round_result.summary)}；节省 ${fmtNumber(decision.round_result.time_saved_min, 1)} 分钟，节省 ${fmtNumber(decision.round_result.cost_saved_yuan, 1)} 元，风险差异 ${fmtSigned(decision.round_result.timeout_risk_delta, 3)}。</p></div>
        </div>
      `;
    }

    function renderEventItem(event) {
      const meta = eventMeta[event.type] || { label: event.type, family: "decision" };
      const typeClass = eventTypeClasses[event.type] || "event-type-other";
      const detailParts = [];
      if (event.order_id) detailParts.push(`order ${event.order_id}`);
      if (event.order_ids) detailParts.push(`${event.order_ids.length} orders`);
      if (event.courier_ids) detailParts.push(`${event.courier_ids.length} riders`);
      if (event.business_area) detailParts.push(event.business_area);
      if (event.memory_id) detailParts.push(`memory ${event.memory_id}`);
      const detail = detailParts.join(" / ");
      return `
        <div class="list-item event-item ${escapeHtml(typeClass)}" data-event-type="${escapeHtml(event.type)}" data-event-sequence="${escapeHtml(event.sequence)}">
          <span class="event-tag" data-family="${escapeHtml(meta.family)}">${escapeHtml(meta.label)}</span>
          <div>
            <strong>${escapeHtml(event.time_label)} ${escapeHtml(meta.label)}</strong>
            <p>${escapeHtml(event.summary)}</p>
            ${detail ? `<p>${escapeHtml(detail)}</p>` : ""}
          </div>
        </div>
      `;
    }

    function renderStageRow(label, count, summary) {
      return `<div class="stage-row"><b>${escapeHtml(label)}</b><span>${escapeHtml(summary || "Pending")}</span><em>${escapeHtml(count)}</em></div>`;
    }

    function memoryItemsForSection(sectionId, byId = null) {
      const itemById = byId || Object.fromEntries(workbench.memory.items.map((item) => [item.id, item]));
      return (workbench.memory.sections[sectionId] || [])
        .map((id) => itemById[id])
        .filter(Boolean)
        .sort((a, b) => (b.latest_hit_time_s || 0) - (a.latest_hit_time_s || 0));
    }

    function memoryStats() {
      const items = workbench.memory.items;
      const totalConfidence = items.reduce((sum, item) => sum + (Number(item.confidence) || 0), 0);
      const totalRecalls = items.reduce((sum, item) => sum + (Number(item.recall_count) || 0), 0);
      const latest = items.reduce((selected, item) => !selected || item.latest_hit_time_s > selected.latest_hit_time_s ? item : selected, null);
      return {
        total: items.length,
        avgConfidence: items.length ? totalConfidence / items.length : 0,
        totalRecalls,
        latestHitLabel: latest?.latest_hit_time_label || "-",
        linkedDecisionCount: new Set(items.map((item) => item.linked_decision_id)).size
      };
    }

    function renderMemoryOverview(stats) {
      return [
        renderMetricChip("memory-total", "长期记忆总量", `${stats.total}`, "new / curated / active / feedback"),
        renderMetricChip("memory-confidence", "平均置信度", fmtNumber(stats.avgConfidence, 2), "confidence after feedback"),
        renderMetricChip("memory-recalls", "累计召回", `${stats.totalRecalls}`, "historical case hits"),
        renderMetricChip("memory-latest-hit", "最近命中", stats.latestHitLabel, `${stats.linkedDecisionCount} linked decisions`)
      ].join("");
    }

    function renderMemoryRecallCard(item) {
      if (!item) return "";
      return `
        <div class="recall-card" data-memory-id="${escapeHtml(item.id)}" data-memory-recall="active">
          <strong>${escapeHtml(item.latest_hit_time_label)} / ${escapeHtml(item.trigger_scenario)}</strong>
          <p>${escapeHtml(item.strategy_summary)}</p>
          <div class="memory-meter" style="--confidence:${clamp(item.confidence, 0, 1)}"><span></span></div>
          <p>decision ${escapeHtml(item.linked_decision_id)} / recalls ${item.recall_count}</p>
        </div>
      `;
    }

    function renderMemoryField(label, value) {
      return `<div class="memory-field"><b>${escapeHtml(label)}</b><span>${escapeHtml(value || "-")}</span></div>`;
    }

    function renderMemoryItem(item) {
      if (!item) return "";
      return `
        <div class="list-item memory-item" data-memory-id="${escapeHtml(item.id)}" data-memory-stage="${escapeHtml(item.stage)}">
          <div class="memory-item-head">
            <strong>${escapeHtml(item.latest_hit_time_label)} / ${escapeHtml(item.id)}</strong>
            <span class="memory-stage" data-stage="${escapeHtml(item.stage)}">${escapeHtml(item.stage)}</span>
          </div>
          <div class="memory-field-grid">
            ${renderMemoryField("触发场景", item.trigger_scenario)}
            ${renderMemoryField("上下文摘要", item.context_summary)}
            ${renderMemoryField("策略摘要", item.strategy_summary)}
            ${renderMemoryField("决策结果", item.decision_result)}
            ${renderMemoryField("效果反馈", item.effect_feedback)}
            ${renderMemoryField("最近命中时间", item.latest_hit_time_label)}
          </div>
          <div class="context-metric-grid">
            ${renderMetricChip(`${item.id}-confidence`, "置信度", fmtNumber(item.confidence, 2), `before ${fmtNumber(item.confidence_before, 2)} / after ${fmtNumber(item.confidence_after, 2)}`)}
            ${renderMetricChip(`${item.id}-recall`, "召回次数", `${item.recall_count}`, item.recalled_case_ids.join(", ") || "no recalled cases")}
          </div>
          <div class="chip-list">
            <span class="data-chip">decision ${escapeHtml(item.linked_decision_id)}</span>
            ${item.tags.map((tag) => `<span class="data-chip">${escapeHtml(tag)}</span>`).join("")}
          </div>
        </div>
      `;
    }

    function orderTimeBandById(timeBandId) {
      return workbench.filters.order_time_bands.find((item) => item.id === timeBandId) || null;
    }

    function orderMatchesFilters(order) {
      const band = orderTimeBandById(orderFilterState.timeBand);
      const inBand = !band || (order.created_at_s >= band.start_s && order.created_at_s <= band.end_s);
      const inArea = orderFilterState.area === "all" || order.business_area === orderFilterState.area;
      const inRisk = orderFilterState.risk === "all" || order.risk_level === orderFilterState.risk;
      const inStatus = orderFilterState.status === "all"
        || order.status === orderFilterState.status
        || (orderFilterState.status === "entered_inference" && order.entered_inference);
      return inBand && inArea && inRisk && inStatus;
    }

    function filteredOrders() {
      return workbench.entities.orders.filter(orderMatchesFilters);
    }

    function riderMatchesFilters(rider) {
      const inArea = riderFilterState.area === "all" || rider.business_area === riderFilterState.area;
      const inState = riderFilterState.state === "all" || rider.online_state === riderFilterState.state;
      return inArea && inState;
    }

    function filteredRiders() {
      return workbench.entities.riders.filter(riderMatchesFilters);
    }

    function renderOrdersOverview(orders) {
      const entered = orders.filter((order) => order.entered_inference).length;
      const highRisk = orders.filter((order) => order.risk_level === "high").length;
      const assigned = orders.filter((order) => order.our_result.state === "assigned").length;
      const improved = orders.filter((order) => {
        const ours = Number(order.our_result.eta_min);
        const baseline = Number(order.baseline_result.eta_min);
        return Number.isFinite(ours) && Number.isFinite(baseline) && ours < baseline;
      }).length;
      return [
        renderMetricChip("orders-visible", "当前订单视图", `${orders.length}`, `full-day ${workbench.entities.orders.length}`),
        renderMetricChip("orders-entered", "已进入推理", `${entered}`, "released to planner"),
        renderMetricChip("orders-high-risk", "高风险订单", `${highRisk}`, "deadline / weather guardrail"),
        renderMetricChip("orders-improved", "我方优于基线", `${improved}/${assigned}`, "assigned orders")
      ].join("");
    }

    function countBy(items, keyFn) {
      return items.reduce((counts, item) => {
        const key = keyFn(item) || "-";
        counts[key] = (counts[key] || 0) + 1;
        return counts;
      }, {});
    }

    function renderCountChips(counts, limit = 6) {
      const rows = Object.entries(counts).sort((left, right) => right[1] - left[1]).slice(0, limit);
      if (!rows.length) return `<p>当前筛选无数据</p>`;
      return `<div class="chip-list">${rows.map(([key, value]) => `<span class="data-chip">${escapeHtml(key)} ${value}</span>`).join("")}</div>`;
    }

    function renderOrderTimeLane(orders) {
      const maxCount = Math.max(...workbench.filters.order_time_bands.map((band) => orders.filter((order) => order.created_at_s >= band.start_s && order.created_at_s <= band.end_s).length), 1);
      return `
        <div class="time-lane">
          ${workbench.filters.order_time_bands.map((band) => {
            const count = orders.filter((order) => order.created_at_s >= band.start_s && order.created_at_s <= band.end_s).length;
            return `
              <div class="time-lane-item" data-order-time-band="${escapeHtml(band.id)}">
                <b>${escapeHtml(band.label)}</b>
                <div class="lane-bar" style="--weight:${count / maxCount}"><span></span></div>
                <span>${count}</span>
              </div>
            `;
          }).join("")}
        </div>
      `;
    }

    function renderOrdersContext(orders) {
      const riskCounts = countBy(orders, (order) => order.risk_level);
      const areaCounts = countBy(orders, (order) => order.business_area);
      const statusCounts = countBy(orders, (order) => order.entered_inference ? "entered_inference" : order.status);
      return `
        <div class="card-head"><h3>调度输入上下文</h3><span id="orders-context-count">${orders.length} visible</span></div>
        <div class="card-body order-context-list">
          <div class="list-item" id="orders-time-distribution"><strong>全天释放节奏</strong>${renderOrderTimeLane(orders)}</div>
          <div class="list-item" id="orders-area-distribution"><strong>商圈分布</strong>${renderCountChips(areaCounts)}</div>
          <div class="list-item" id="orders-risk-distribution"><strong>风险结构</strong>${renderCountChips(riskCounts)}</div>
          <div class="list-item" id="orders-status-distribution"><strong>推理状态</strong>${renderCountChips(statusCounts)}</div>
        </div>
      `;
    }

    function renderAlgorithmResult(result) {
      if (!result || result.state !== "assigned") {
        return `<div class="result-pair"><b>未释放</b><span>${escapeHtml(result?.algorithm_id || "-")}</span></div>`;
      }
      return `
        <div class="result-pair">
          <b>${escapeHtml(result.courier_id)} / ${fmtNumber(result.eta_min, 1)} min</b>
          <span>${fmtNumber(result.expected_cost_yuan, 1)} yuan / risk ${fmtNumber(result.timeout_risk, 3)}</span>
        </div>
      `;
    }

    function hydrateOrdersPage() {
      for (const control of document.querySelectorAll("[data-order-filter]")) {
        control.addEventListener("change", () => {
          orderFilterState[control.dataset.orderFilter] = control.value;
          updateOrdersView();
        });
      }
      updateOrdersView();
    }

    function updateOrdersView() {
      const orders = filteredOrders();
      const overview = document.getElementById("orders-overview");
      if (overview) overview.innerHTML = renderOrdersOverview(orders);
      const body = document.getElementById("orders-table-body");
      if (body) body.innerHTML = orders.map(renderOrderRow).join("") || `<tr><td colspan="10">当前筛选无订单，调整时间段、商圈、状态或风险。</td></tr>`;
      const context = document.getElementById("orders-context-panel");
      if (context) context.innerHTML = renderOrdersContext(orders);
      setText("orders-result-count", `${orders.length} / ${workbench.entities.orders.length} orders`);
    }

    function renderRidersOverview(riders) {
      const busy = riders.filter((rider) => rider.online_state === "busy").length;
      const ending = riders.filter((rider) => rider.online_state === "ending_shift").length;
      const tasks = riders.reduce((sum, rider) => sum + rider.task_chain_size, 0);
      const avgLoad = riders.length ? riders.reduce((sum, rider) => sum + rider.current_load / Math.max(1, rider.capacity), 0) / riders.length : 0;
      return [
        renderMetricChip("riders-visible", "当前骑手资源", `${riders.length}`, `full-day ${workbench.entities.riders.length}`),
        renderMetricChip("riders-busy", "忙碌骑手", `${busy}`, `${ending} ending shift`),
        renderMetricChip("riders-task-chain", "任务链总量", `${tasks}`, "assigned by our planner"),
        renderMetricChip("riders-avg-load", "平均负载", fmtNumber(avgLoad, 2), "current load / capacity")
      ].join("");
    }

    function renderRidersContext(riders) {
      const stateCounts = countBy(riders, (rider) => rider.online_state);
      const areaCounts = countBy(riders, (rider) => rider.business_area);
      const topChains = [...riders].sort((left, right) => right.task_chain_size - left.task_chain_size).slice(0, 5);
      return `
        <div class="card-head"><h3>资源盘点上下文</h3><span id="riders-context-count">${riders.length} visible</span></div>
        <div class="card-body rider-context-list">
          <div class="list-item" id="rider-state-distribution"><strong>在线状态</strong>${renderCountChips(stateCounts)}</div>
          <div class="list-item" id="rider-area-distribution"><strong>区域供给</strong>${renderCountChips(areaCounts)}</div>
          <div class="list-item" id="rider-chain-focus">
            <strong>任务链焦点</strong>
            ${topChains.length ? topChains.map((rider) => `<p>${escapeHtml(rider.id)} ${escapeHtml(rider.name)} / ${rider.task_chain_size} tasks / free ${escapeHtml(rider.estimated_free_at_label)}</p>`).join("") : "<p>当前筛选无骑手</p>"}
          </div>
        </div>
      `;
    }

    function hydrateRidersPage() {
      for (const control of document.querySelectorAll("[data-rider-filter]")) {
        control.addEventListener("change", () => {
          riderFilterState[control.dataset.riderFilter] = control.value;
          updateRidersView();
        });
      }
      updateRidersView();
    }

    function updateRidersView() {
      const riders = filteredRiders();
      const overview = document.getElementById("riders-overview");
      if (overview) overview.innerHTML = renderRidersOverview(riders);
      const board = document.getElementById("rider-resource-board");
      if (board) board.innerHTML = riders.map(renderRiderCard).join("") || `<div class="list-item"><strong>当前筛选无骑手</strong><p>调整区域或在线状态筛选。</p></div>`;
      const context = document.getElementById("rider-context-panel");
      if (context) context.innerHTML = renderRidersContext(riders);
      setText("riders-result-count", `${riders.length} / ${workbench.entities.riders.length} riders`);
    }

    function renderOrderRow(order) {
      return `
        <tr data-order-id="${escapeHtml(order.id)}" data-order-status="${escapeHtml(order.status)}" data-order-risk="${escapeHtml(order.risk_level)}" data-order-area="${escapeHtml(order.business_area)}">
          <td>${escapeHtml(order.id)}</td>
          <td>${escapeHtml(order.merchant_label)}<br><span>${escapeHtml(order.pickup_label)}</span></td>
          <td>${escapeHtml(order.created_at_label)}</td>
          <td>${escapeHtml(order.promised_at_label)}</td>
          <td><span class="badge" data-state="${escapeHtml(order.status)}">${escapeHtml(order.status)}</span></td>
          <td><span class="badge" data-risk="${escapeHtml(order.risk_level)}">${escapeHtml(order.risk_level)}</span></td>
          <td>${escapeHtml(order.business_area)}</td>
          <td>${order.entered_inference ? "是" : "否"}</td>
          <td>${renderAlgorithmResult(order.baseline_result)}</td>
          <td>${renderAlgorithmResult(order.our_result)}</td>
        </tr>
      `;
    }

    function renderRiderMiniMap(rider) {
      const linkedOrders = rider.mini_map.linked_order_ids.map((orderId) => orderIndex[orderId]).filter(Boolean).slice(0, 4);
      return `
        <div class="mini-map" data-rider-mini-map="${escapeHtml(rider.id)}">
          <span class="map-dot" data-kind="home" title="home" style="--x:${rider.mini_map.home.screen_x};--y:${rider.mini_map.home.screen_y}"></span>
          <span class="map-dot" data-kind="rider" title="${escapeHtml(rider.name)}" style="--x:${rider.position.screen_x};--y:${rider.position.screen_y}"></span>
          ${linkedOrders.map((order) => `<span class="map-dot" data-kind="linked-order" title="${escapeHtml(order.id)}" style="--x:${order.dropoff_position.screen_x};--y:${order.dropoff_position.screen_y}"></span>`).join("")}
        </div>
      `;
    }

    function renderRiderCard(rider) {
      const loadRatio = clamp(rider.current_load / Math.max(1, rider.capacity), 0, 1);
      return `
        <article class="card rider-card" data-rider-id="${escapeHtml(rider.id)}" data-state="${escapeHtml(rider.online_state)}" data-area="${escapeHtml(rider.business_area)}">
          <div class="card-head"><h3>${escapeHtml(rider.name)}</h3><span>${escapeHtml(rider.online_state)}</span></div>
          <div class="card-body">
            ${renderRiderMiniMap(rider)}
            <div class="rider-load" style="--load:${loadRatio}"><span></span></div>
            <div class="compact-list">
              <div class="list-item"><strong>班次时间 / 所属区域</strong><p>${escapeHtml(rider.shift_label)} / ${escapeHtml(rider.business_area)}</p></div>
              <div class="list-item"><strong>当前负载 / 预计空闲时间</strong><p>${rider.current_load}/${rider.capacity} / ${escapeHtml(rider.estimated_free_at_label)}</p></div>
              <div class="list-item"><strong>当前任务链 ${rider.task_chain_size}</strong><p>${rider.task_chain.slice(0, 5).map((item) => `${item.order_id}(${fmtNumber(item.eta_min, 1)}m)`).join(", ") || "暂无任务"}</p></div>
              <div class="list-item"><strong>历史表现摘要</strong><p>${escapeHtml(rider.performance.summary)} / willingness ${fmtNumber(rider.performance.willingness, 2)}</p></div>
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
      renderDecisionTimeline,
      renderDecisionReasoning,
      renderDecisionContext,
      hydrateDecisionPage,
      selectDecisionRound,
      renderMemoryPage,
      memoryStats,
      memoryItemsForSection,
      renderMemoryRecallCard,
      renderMemoryItem,
      renderOrdersPage,
      hydrateOrdersPage,
      updateOrdersView,
      filteredOrders,
      orderFilterState,
      renderOrdersOverview,
      renderOrdersContext,
      renderRidersPage,
      hydrateRidersPage,
      updateRidersView,
      filteredRiders,
      riderFilterState,
      renderRidersOverview,
      renderRidersContext,
      renderLiveCumulativeMetrics,
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
