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
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="anonymous">
  <script defer src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin="anonymous"></script>
  <style>
    :root {
      --bg: #f3f5f8;
      --surface: #ffffff;
      --surface-2: #f8fafc;
      --surface-3: #edf1f5;
      --surface-glass: rgba(255,255,255,.92);
      --ink: #17212b;
      --ink-2: #2b3947;
      --muted: #647286;
      --line: #dfe5ec;
      --line-strong: #c9d3df;
      --nav: #121923;
      --nav-2: #1a2430;
      --nav-active: rgba(255,184,28,.14);
      --accent: #0f766e;
      --accent-2: #115e59;
      --amber: #b7791f;
      --red: #b42318;
      --blue: #2563eb;
      --green-soft: #e6f4f1;
      --amber-soft: #fbf1db;
      --red-soft: #fee4e2;
      --shadow: 0 14px 30px rgba(21, 32, 43, .08);
      --shadow-tight: 0 8px 18px rgba(21, 32, 43, .055);
      --shadow-card: 0 1px 2px rgba(15,23,42,.04), 0 10px 24px rgba(15,23,42,.055);
      --shadow-float: 0 22px 46px rgba(21, 32, 43, .10);
      --focus-ring: 0 0 0 3px rgba(15,118,110,.18);
      --radius-lg: 18px;
      --radius-md: 12px;
      --font: "HarmonyOS Sans SC", "MiSans", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
      --mono: "SFMono-Regular", "Cascadia Mono", "Menlo", monospace;
    }
    * { box-sizing: border-box; }
    html, body { margin: 0; min-height: 100%; }
    html {
      color-scheme: light;
      scrollbar-color: #a9b6c2 transparent;
    }
    body {
      color: var(--ink);
      background:
        linear-gradient(180deg, rgba(255,255,255,.90), rgba(243,245,248,.96)),
        radial-gradient(circle at 88% 8%, rgba(255,184,28,.10), transparent 27%),
        radial-gradient(circle at 10% 0%, rgba(15,118,110,.07), transparent 31%),
        linear-gradient(90deg, rgba(100,116,139,.035) 1px, transparent 1px),
        linear-gradient(0deg, rgba(100,116,139,.032) 1px, transparent 1px),
        var(--bg);
      background-size: auto, auto, auto, 34px 34px, 34px 34px, auto;
      font-family: var(--font);
      -webkit-font-smoothing: antialiased;
      text-rendering: geometricPrecision;
    }
    button, select, input { font: inherit; }
    button { cursor: pointer; }
    button, select, input, a {
      transition: border-color .16s ease, background-color .16s ease, color .16s ease, box-shadow .16s ease, transform .16s ease;
    }
    button:focus-visible, select:focus-visible, input:focus-visible, a:focus-visible {
      outline: 0;
      box-shadow: var(--focus-ring);
    }
    .workbench-shell {
      min-height: 100vh;
      display: grid;
      grid-template-columns: 278px minmax(0, 1fr);
      background: linear-gradient(90deg, rgba(18,25,35,.035), transparent 18%);
    }
    body[data-route="live"] { --route-accent: #0f766e; --route-soft: #e6f4f1; --route-ink: #115e59; }
    body[data-route="decisions"] { --route-accent: #1d4ed8; --route-soft: #dbeafe; --route-ink: #1e3a8a; }
    body[data-route="memory"] { --route-accent: #b7791f; --route-soft: #fbf1db; --route-ink: #92400e; }
    body[data-route="orders"] { --route-accent: #b45309; --route-soft: #ffedd5; --route-ink: #9a3412; }
    body[data-route="riders"] { --route-accent: #475569; --route-soft: #e2e8f0; --route-ink: #334155; }
    .workbench-nav {
      position: sticky;
      top: 0;
      height: 100vh;
      padding: 18px 14px;
      color: #d8e1ea;
      background:
        linear-gradient(180deg, rgba(255,255,255,.035), transparent 28%),
        linear-gradient(180deg, var(--nav), var(--nav-2));
      border-right: 1px solid rgba(255,255,255,.08);
      box-shadow: inset -1px 0 rgba(15,23,42,.42), 8px 0 28px rgba(15,23,42,.05);
    }
    .brand {
      display: grid;
      grid-template-columns: 38px 1fr;
      gap: 10px;
      align-items: center;
      padding: 8px 8px 18px;
      border-bottom: 1px solid rgba(255,255,255,.10);
    }
    .brand-mark {
      width: 38px;
      height: 38px;
      display: grid;
      place-items: center;
      border-radius: 13px;
      color: #172026;
      background: linear-gradient(135deg, #ffd05a, #ffb81c);
      box-shadow: 0 10px 24px rgba(255,184,28,.18);
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
    .nav-list { display: grid; gap: 8px; }
    .nav-link {
      display: grid;
      grid-template-columns: 30px 1fr;
      gap: 10px;
      align-items: start;
      padding: 11px 10px;
      border-radius: 14px;
      color: #c8d4df;
      text-decoration: none;
      border: 1px solid transparent;
      position: relative;
      overflow: hidden;
    }
    .nav-link:hover { background: rgba(255,255,255,.07); transform: translateX(1px); }
    .nav-link[aria-current="page"] {
      color: #fff;
      background: var(--nav-active);
      border-color: rgba(255,184,28,.22);
      box-shadow: inset 0 0 0 1px rgba(255,255,255,.035);
    }
    .nav-link[aria-current="page"]::before {
      position: absolute;
      inset: 10px auto 10px 0;
      width: 3px;
      border-radius: 999px;
      background: #ffb81c;
      content: "";
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
    .nav-link[aria-current="page"] .nav-icon {
      color: #172026;
      background: #ffb81c;
    }
    .nav-copy { min-width: 0; }
    .nav-title-line {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }
    .nav-title-line strong {
      color: #eef7fb;
      font-size: 14px;
      letter-spacing: -.01em;
    }
    .nav-role {
      padding: 3px 6px;
      border-radius: 999px;
      color: #9fb0c0;
      background: rgba(255,255,255,.07);
      font: 800 9px var(--mono);
      white-space: nowrap;
    }
    .nav-hint {
      display: block;
      margin-top: 4px;
      color: #9fb0c0;
      font-size: 12px;
      line-height: 1.32;
    }
    .nav-module {
      display: block;
      margin-top: 5px;
      color: #7f93a5;
      font: 800 10px var(--mono);
      letter-spacing: .04em;
      text-transform: uppercase;
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
      background: rgba(255,255,255,.94);
      border-bottom: 1px solid var(--line);
      backdrop-filter: blur(18px);
      box-shadow: 0 8px 18px rgba(15,23,42,.045);
    }
    .topbar h1 { margin: 0 0 3px; font-size: 18px; letter-spacing: -.02em; font-weight: 850; }
    .topbar p { margin: 0; color: var(--muted); font-size: 13px; }
    .topbar-stats {
      display: grid;
      grid-template-columns: repeat(4, auto);
      gap: 8px;
      align-items: center;
    }
    .stat-pill {
      min-width: 92px;
      padding: 8px 11px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: #fff;
      box-shadow: 0 1px 2px rgba(15,23,42,.035);
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
      padding: 24px 26px;
    }
    .page-head {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 280px;
      gap: 14px;
      align-items: stretch;
      margin-bottom: 18px;
      padding: 18px;
      border: 1px solid var(--line);
      border-radius: 20px;
      background:
        linear-gradient(90deg, var(--route-soft, var(--green-soft)), rgba(255,255,255,.92) 33%, rgba(255,255,255,.96)),
        #fff;
      box-shadow: var(--shadow-card);
      backdrop-filter: blur(12px);
      position: relative;
      overflow: hidden;
    }
    .page-head::before {
      position: absolute;
      inset: 0 auto 0 0;
      width: 5px;
      background: var(--route-accent, var(--accent));
      content: "";
    }
    .eyebrow {
      color: var(--route-ink, var(--accent-2));
      font-size: 12px;
      font-weight: 850;
      letter-spacing: .02em;
    }
    .page-head h2 { margin: 5px 0 6px; font-size: 29px; letter-spacing: -.04em; font-weight: 900; }
    .page-head p { margin: 0; max-width: 820px; color: var(--muted); line-height: 1.55; }
    .page-role-strip {
      display: flex;
      flex-wrap: wrap;
      gap: 7px;
      margin-top: 12px;
    }
    .page-role-strip span {
      padding: 6px 8px;
      border: 1px solid rgba(15,23,42,.08);
      border-radius: 999px;
      color: var(--route-ink, var(--accent-2));
      background: rgba(255,255,255,.70);
      font: 800 11px var(--mono);
    }
    .page-role-card {
      display: grid;
      align-content: center;
      gap: 6px;
      padding: 12px;
      border: 1px solid rgba(15,23,42,.08);
      border-radius: 16px;
      background: rgba(255,255,255,.82);
      box-shadow: inset 0 1px rgba(255,255,255,.72);
    }
    .page-role-card b {
      color: var(--route-ink, var(--accent-2));
      font-size: 15px;
    }
    .page-role-card span {
      color: var(--ink-2);
      font-size: 12px;
      line-height: 1.45;
    }
    .page-role-card em {
      color: var(--muted);
      font: 800 10px var(--mono);
      font-style: normal;
      letter-spacing: .04em;
      text-transform: uppercase;
    }
    .page-grid { display: grid; gap: 14px; }
    .live-grid {
      grid-template-columns: 1fr;
      align-items: start;
    }
    .live-advantage-hero {
      display: grid;
      grid-template-columns: minmax(260px, .72fr) minmax(0, 1.28fr);
      gap: 16px;
      padding: 16px;
      border: 1px solid rgba(15,118,110,.24);
      border-radius: 22px;
      background:
        linear-gradient(120deg, rgba(15,118,110,.10), rgba(255,255,255,.94) 43%),
        radial-gradient(circle at 14% 8%, rgba(34,197,94,.12), transparent 34%),
        #fff;
      box-shadow: var(--shadow-card);
      backdrop-filter: blur(14px);
    }
    .advantage-lead {
      display: grid;
      align-content: center;
      gap: 11px;
      padding: 8px 6px;
    }
    .advantage-kicker {
      display: inline-flex;
      width: fit-content;
      align-items: center;
      gap: 7px;
      padding: 6px 9px;
      border: 1px solid rgba(15,118,110,.20);
      border-radius: 999px;
      color: var(--accent-2);
      background: rgba(255,255,255,.70);
      font: 800 11px var(--mono);
      text-transform: uppercase;
      letter-spacing: .06em;
    }
    .advantage-kicker::before {
      width: 8px;
      height: 8px;
      border-radius: 999px;
      background: var(--accent);
      box-shadow: 0 0 0 5px rgba(15,118,110,.10);
      content: "";
    }
    .advantage-lead h3 {
      margin: 0;
      color: var(--ink);
      font-size: clamp(30px, 4.2vw, 56px);
      line-height: .96;
      letter-spacing: -.06em;
    }
    .advantage-lead p {
      margin: 0;
      max-width: 560px;
      color: var(--ink-2);
      font-size: 14px;
      line-height: 1.58;
    }
    .advantage-target-row {
      display: flex;
      flex-wrap: wrap;
      gap: 7px;
    }
    .advantage-target-row span {
      padding: 6px 8px;
      border: 1px solid rgba(15,23,42,.08);
      border-radius: 999px;
      color: var(--muted);
      background: rgba(255,255,255,.72);
      font: 800 11px var(--mono);
    }
    .live-advantage-metrics {
      display: grid;
      gap: 10px;
      min-width: 0;
    }
    .live-ops-shell {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 336px;
      gap: 14px;
      align-items: start;
    }
    .live-primary-column,
    .live-side-rail {
      display: grid;
      gap: 14px;
      min-width: 0;
    }
    .live-side-rail {
      position: sticky;
      top: 88px;
      align-self: start;
    }
    .live-run-panel .card-body {
      display: grid;
      gap: 12px;
    }
    .live-run-panel .event-list {
      max-height: 250px;
      overflow: auto;
    }
    .decision-grid {
      grid-template-columns: 280px minmax(0, 1fr) 340px;
      align-items: start;
    }
    .memory-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
    .memory-workspace { grid-template-columns: 1fr; }
    .hermes-memory-workspace {
      gap: 16px;
    }
    .memory-overview {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
    }
    .memory-command-center {
      display: grid;
      grid-template-columns: minmax(280px, .8fr) minmax(0, 1.2fr);
      gap: 16px;
      padding: 16px;
      border: 1px solid rgba(183,121,31,.26);
      border-radius: 22px;
      background:
        linear-gradient(120deg, rgba(251,241,219,.86), rgba(255,255,255,.94) 46%),
        radial-gradient(circle at 12% 12%, rgba(183,121,31,.12), transparent 34%),
        #fff;
      box-shadow: var(--shadow-card);
      backdrop-filter: blur(14px);
    }
    .memory-command-copy {
      display: grid;
      align-content: center;
      gap: 11px;
      padding: 6px;
    }
    .memory-command-copy h3 {
      margin: 0;
      font-size: clamp(28px, 3.4vw, 48px);
      line-height: 1;
      letter-spacing: -.055em;
    }
    .memory-command-copy p {
      margin: 0;
      max-width: 620px;
      color: var(--ink-2);
      font-size: 14px;
      line-height: 1.6;
    }
    .memory-kicker {
      width: fit-content;
      padding: 6px 9px;
      border: 1px solid rgba(183,121,31,.25);
      border-radius: 999px;
      color: var(--route-ink);
      background: rgba(255,255,255,.74);
      font: 800 11px var(--mono);
      letter-spacing: .06em;
      text-transform: uppercase;
    }
    .memory-model-row {
      display: flex;
      flex-wrap: wrap;
      gap: 7px;
    }
    .memory-model-row span {
      padding: 6px 8px;
      border: 1px solid rgba(15,23,42,.08);
      border-radius: 999px;
      color: var(--muted);
      background: rgba(255,255,255,.74);
      font: 800 11px var(--mono);
    }
    .memory-command-metrics {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      align-content: stretch;
    }
    .memory-operating-grid {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 360px;
      gap: 14px;
      align-items: start;
    }
    .memory-layer-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }
    .memory-layer-card,
    .memory-profile,
    .memory-flow-step {
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: #fff;
      box-shadow: 0 1px 2px rgba(15,23,42,.035);
    }
    .memory-layer-card {
      display: grid;
      gap: 9px;
      min-height: 176px;
    }
    .memory-layer-top,
    .memory-profile-top,
    .memory-flow-top {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: flex-start;
    }
    .memory-layer-top strong,
    .memory-profile-top strong,
    .memory-flow-top strong {
      font-size: 14px;
      letter-spacing: -.01em;
    }
    .memory-scope,
    .memory-profile-type,
    .memory-flow-index {
      padding: 4px 7px;
      border-radius: 999px;
      color: var(--route-ink);
      background: var(--route-soft);
      font: 800 10px var(--mono);
      white-space: nowrap;
    }
    .memory-layer-card p,
    .memory-profile p,
    .memory-flow-step p {
      margin: 0;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.48;
    }
    .memory-layer-meta,
    .memory-profile-meta,
    .memory-effect-line {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }
    .memory-layer-meta span,
    .memory-profile-meta span,
    .memory-effect-line span {
      padding: 5px 7px;
      border: 1px solid rgba(15,23,42,.07);
      border-radius: 999px;
      color: var(--muted);
      background: #fff;
      font: 800 10px var(--mono);
    }
    .memory-profile-board {
      display: grid;
      gap: 10px;
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: var(--radius-lg);
      background: linear-gradient(180deg, #fff, var(--surface-2));
      box-shadow: var(--shadow-card);
    }
    .memory-profile-board h3 {
      margin: 0;
      font-size: 15px;
    }
    .memory-profile-board > p {
      margin: 0;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.5;
    }
    .memory-profile-list {
      display: grid;
      gap: 10px;
    }
    .memory-flow-grid {
      display: grid;
      grid-template-columns: minmax(0, 1.08fr) minmax(0, .92fr);
      gap: 14px;
      align-items: start;
    }
    .memory-flow-lane {
      display: grid;
      gap: 10px;
    }
    .memory-flow-step {
      display: grid;
      gap: 9px;
      position: relative;
      overflow: hidden;
    }
    .memory-flow-step::before {
      position: absolute;
      inset: 0 auto 0 0;
      width: 4px;
      background: var(--route-accent);
      opacity: .65;
      content: "";
    }
    .memory-evidence {
      display: grid;
      gap: 8px;
      padding: 10px;
      border: 1px solid rgba(15,23,42,.08);
      border-radius: 12px;
      background: rgba(255,255,255,.76);
    }
    .memory-evidence-head {
      display: flex;
      justify-content: space-between;
      gap: 8px;
      align-items: center;
    }
    .memory-evidence-head strong {
      font-size: 12px;
      font-family: var(--mono);
    }
    .memory-evidence-head span {
      color: var(--muted);
      font: 800 10px var(--mono);
    }
    .rider-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    .card {
      border: 1px solid var(--line);
      border-radius: var(--radius-lg);
      background: #fff;
      box-shadow: var(--shadow-card);
      overflow: hidden;
      backdrop-filter: blur(10px);
    }
    .card-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
      background:
        linear-gradient(90deg, rgba(255,255,255,.96), rgba(248,250,252,.94)),
        #fff;
    }
    .card-head h3 { margin: 0; font-size: 15px; font-weight: 850; letter-spacing: -.01em; }
    .card-head span { color: var(--muted); font-size: 12px; }
    .card-head span em { font-style: normal; }
    .card-body { padding: 14px 16px; }
    .control-dock {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 16px;
      background: rgba(255,255,255,.94);
      box-shadow: var(--shadow-card);
      position: sticky;
      top: 88px;
      z-index: 12;
      backdrop-filter: blur(14px);
    }
    .live-control-dock {
      position: relative;
      top: auto;
      z-index: 7;
      align-items: center;
      box-shadow: var(--shadow-card);
    }
    .live-control-dock .runtime-strip {
      flex: 1 1 420px;
      width: auto;
      grid-template-columns: repeat(5, minmax(86px, 1fr));
    }
    .live-control-dock .inference-progress {
      flex: 1 0 100%;
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
      border-radius: var(--radius-md);
      background: #fff;
      box-shadow: inset 0 1px rgba(255,255,255,.82);
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
      padding: 9px 14px;
      color: #172026;
      background: linear-gradient(180deg, #ffd76d, #ffb81c);
      box-shadow: 0 8px 18px rgba(255,184,28,.20);
      font-weight: 850;
    }
    .primary-button:hover:not([disabled]) { transform: translateY(-1px); box-shadow: 0 10px 22px rgba(255,184,28,.26); }
    .primary-button[disabled] {
      cursor: default;
      opacity: .62;
    }
    .ghost-button, .select-control {
      border: 1px solid var(--line-strong);
      border-radius: 11px;
      padding: 8px 11px;
      color: var(--ink);
      background: #fff;
    }
    .ghost-button:hover, .select-control:hover {
      border-color: var(--accent);
      background: #fff;
    }
    .map-panel { min-height: 520px; position: relative; }
    .real-map-stage,
    .schematic-map {
      position: relative;
      height: 478px;
      margin: 14px;
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: 18px;
      isolation: isolate;
      background:
        linear-gradient(90deg, rgba(148,163,184,.16) 1px, transparent 1px),
        linear-gradient(0deg, rgba(148,163,184,.16) 1px, transparent 1px),
        radial-gradient(circle at 60% 40%, rgba(15,118,110,.10), transparent 32%),
        #f8fafc;
      background-size: 44px 44px, 44px 44px, auto, auto;
      box-shadow: inset 0 0 0 1px rgba(255,255,255,.55);
    }
    .leaflet-live-map {
      position: absolute;
      inset: 0;
      z-index: 1;
      background: #e8eef2;
    }
    .leaflet-container {
      color: var(--ink);
      font-family: var(--font);
      filter: saturate(.74) contrast(.98) brightness(1.02);
    }
    .leaflet-control-attribution {
      color: rgba(38,53,65,.62);
      background: rgba(255,255,255,.74) !important;
      font-size: 9px;
    }
    .fallback-map-overlay {
      position: absolute;
      inset: 0;
      z-index: 2;
      opacity: 1;
      pointer-events: none;
      background:
        linear-gradient(90deg, rgba(148,163,184,.13) 1px, transparent 1px),
        linear-gradient(0deg, rgba(148,163,184,.13) 1px, transparent 1px),
        radial-gradient(circle at 56% 38%, rgba(15,118,110,.10), transparent 30%);
      background-size: 44px 44px, 44px 44px, auto;
      transition: opacity .22s ease;
    }
    .real-map-stage[data-real-map-status="leaflet"] .fallback-map-overlay {
      opacity: 0;
    }
    .real-map-stage[data-real-map-status="fallback"] .leaflet-live-map::after,
    .real-map-stage[data-real-map-status="loading"] .leaflet-live-map::after {
      position: absolute;
      inset: 50% auto auto 50%;
      transform: translate(-50%, -50%);
      padding: 7px 10px;
      border: 1px solid var(--line);
      border-radius: 999px;
      color: var(--muted);
      background: rgba(255,255,255,.82);
      font: 800 11px var(--mono);
      content: "匿名无标签底图加载中 / 备用底图就绪";
      white-space: nowrap;
    }
    .real-map-stage[data-real-map-status="fallback"] .leaflet-live-map::after {
      content: "匿名备用底图";
    }
    .leaflet-control-zoom {
      border: 1px solid rgba(15,23,42,.12) !important;
      border-radius: 12px !important;
      overflow: hidden;
      box-shadow: 0 10px 22px rgba(15,23,42,.12);
    }
    .leaflet-control-zoom a {
      color: var(--ink) !important;
      background: rgba(255,255,255,.92) !important;
    }
    .map-action-status {
      position: absolute;
      z-index: 6;
      left: 58px;
      top: 14px;
      display: grid;
      gap: 3px;
      max-width: min(360px, calc(100% - 204px));
      padding: 10px 12px 10px 14px;
      border: 1px solid rgba(15,23,42,.10);
      border-radius: 14px;
      color: var(--ink);
      background: rgba(255,255,255,.90);
      box-shadow: 0 10px 24px rgba(15,23,42,.10);
      backdrop-filter: blur(10px);
      pointer-events: none;
    }
    .map-action-status::before {
      position: absolute;
      inset: 11px auto 11px 0;
      width: 3px;
      border-radius: 999px;
      background: var(--route-accent, var(--accent));
      content: "";
    }
    .map-action-status strong {
      font-size: 13px;
      letter-spacing: -.01em;
    }
    .map-action-status span {
      color: var(--muted);
      font-size: 11px;
      line-height: 1.35;
    }
    .map-mode-chip {
      position: absolute;
      z-index: 5;
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
      z-index: 5;
      left: 14px;
      bottom: 14px;
      display: flex;
      flex-wrap: wrap;
      gap: 7px;
      max-width: 72%;
      padding: 7px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: rgba(255,255,255,.88);
      box-shadow: 0 8px 18px rgba(15,23,42,.07);
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
    .legend-dot {
      width: 9px;
      height: 9px;
      border-radius: 999px;
      border: 1px solid #fff;
      box-shadow: 0 0 0 1px rgba(15,23,42,.10);
      background: var(--blue);
    }
    .legend-dot[data-kind="rider"] { background: var(--accent); }
    .legend-dot[data-kind="merchant"] { background: var(--blue); }
    .legend-dot[data-kind="order"] { background: var(--amber); }
    .legend-dot[data-kind="hotspot"] {
      background: rgba(183,121,31,.44);
      box-shadow: 0 0 0 5px rgba(183,121,31,.12);
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
      filter: drop-shadow(0 1px 2px rgba(255,255,255,.86));
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
    .route-line[data-lane="active-progress"] {
      stroke: #059669;
      stroke-width: 4.2;
      opacity: .95;
      stroke-dasharray: 5 6;
      animation: route-progress-flow 1.1s linear infinite;
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
    .map-dot[data-show-label="true"]::after {
      position: absolute;
      left: calc(100% + 4px);
      top: 50%;
      transform: translateY(-50%);
      padding: 2px 5px;
      border: 1px solid rgba(15,23,42,.08);
      border-radius: 999px;
      color: var(--ink-2);
      background: rgba(255,255,255,.88);
      box-shadow: 0 4px 10px rgba(15,23,42,.08);
      content: attr(data-map-label);
      font: 800 9px var(--mono);
      white-space: nowrap;
    }
    .map-dot[data-motion="moving"] {
      outline: 5px solid rgba(15,118,110,.10);
    }
    .map-dot[data-motion="moving"]::before {
      position: absolute;
      inset: -7px;
      border: 1px solid rgba(15,118,110,.18);
      border-radius: 999px;
      content: "";
      animation: rider-drive-ring 1.45s ease-out infinite;
    }
    .map-dot[data-motion="moving"]::after {
      content: attr(data-map-label) " 移动中";
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
    .leaflet-map-pin {
      border: 0;
      background: transparent;
    }
    .leaflet-map-pin-body {
      position: relative;
      display: block;
      width: 13px;
      height: 13px;
      border: 2px solid #fff;
      border-radius: 999px;
      background: var(--blue);
      box-shadow: 0 5px 14px rgba(15,23,42,.20);
    }
    .leaflet-map-pin-body[data-kind="rider"] {
      width: 16px;
      height: 16px;
      background: var(--accent);
      box-shadow: 0 0 0 6px rgba(15,118,110,.10), 0 7px 18px rgba(15,23,42,.18);
    }
    .leaflet-map-pin-body[data-kind="rider"][data-motion="moving"] {
      animation: rider-drive-ring 1.45s ease-out infinite;
    }
    .leaflet-map-pin-body[data-kind="rider"][data-motion="moving"]::after {
      position: absolute;
      left: 50%;
      top: 50%;
      transform: translate(-35%, -50%);
      color: #fff;
      content: "›";
      font: 900 14px var(--font);
      line-height: 1;
    }
    .leaflet-map-pin-body[data-kind="order"] {
      width: 12px;
      height: 12px;
      background: var(--amber);
    }
    .leaflet-map-pin-body[data-release="new"] {
      animation: order-enter-pulse 1.8s ease-in-out infinite;
    }
    .leaflet-map-pin-label {
      position: absolute;
      left: 18px;
      top: 50%;
      transform: translateY(-50%);
      padding: 2px 5px;
      border: 1px solid rgba(15,23,42,.08);
      border-radius: 999px;
      color: var(--ink-2);
      background: rgba(255,255,255,.86);
      box-shadow: 0 5px 12px rgba(15,23,42,.08);
      font: 800 9px var(--mono);
      white-space: nowrap;
    }
    .score-stack { display: grid; gap: 10px; }
    .live-side-rail,
    .decision-grid > aside,
    .operations-grid > aside {
      position: sticky;
      top: 88px;
      align-self: start;
    }
    .algorithm-pair {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }
    .score-card {
      padding: 13px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: #fff;
      box-shadow: inset 0 1px rgba(255,255,255,.75);
    }
    .score-card b { display: block; font-size: 22px; letter-spacing: -.03em; }
    .score-card span { color: var(--muted); font-size: 12px; }
    .score-card[data-tone="good"] { background: var(--green-soft); border-color: rgba(15,118,110,.24); }
    .score-card[data-tone="warn"] { background: var(--amber-soft); border-color: rgba(183,121,31,.24); }
    .score-card[data-tone="risk"] { background: var(--red-soft); border-color: rgba(180,35,24,.22); }
    .live-advantage-hero .algorithm-pair {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .live-advantage-hero .score-card {
      min-height: 0;
      padding: 10px;
      background: rgba(255,255,255,.78);
    }
    .live-advantage-hero .score-card b {
      margin: 3px 0 2px;
      font-size: 21px;
    }
    .live-advantage-hero .score-card span:last-child {
      display: block;
      max-height: 34px;
      overflow: hidden;
      line-height: 1.35;
    }
    .live-advantage-hero .score-card[data-tone="good"] {
      background: linear-gradient(180deg, rgba(230,244,241,.98), rgba(255,255,255,.86));
      border-color: rgba(15,118,110,.34);
    }
    .live-advantage-hero .score-card[data-tone="warn"] {
      background: linear-gradient(180deg, rgba(251,241,219,.98), rgba(255,255,255,.84));
    }
    .delta-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }
    .live-advantage-hero .delta-grid {
      grid-template-columns: repeat(5, minmax(0, 1fr));
    }
    .live-advantage-hero .delta-grid .score-card {
      min-height: 0;
    }
    .metric-strip {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 9px;
    }
    .live-run-panel .metric-strip {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .metric-chip {
      padding: 11px;
      border: 1px solid var(--line);
      border-radius: var(--radius-md);
      background: #fff;
      box-shadow: inset 0 1px rgba(255,255,255,.82);
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
    @keyframes route-progress-flow {
      to { stroke-dashoffset: -22; }
    }
    @keyframes rider-drive-ring {
      0% { box-shadow: 0 0 0 0 rgba(15,118,110,.24), 0 7px 18px rgba(15,23,42,.18); }
      100% { box-shadow: 0 0 0 11px rgba(15,118,110,0), 0 7px 18px rgba(15,23,42,.18); }
    }
    .event-list, .timeline-list, .memory-list, .compact-list {
      display: grid;
      gap: 9px;
    }
    .list-item {
      padding: 10px 11px;
      border: 1px solid var(--line);
      border-radius: var(--radius-md);
      background: #fff;
      box-shadow: 0 1px 2px rgba(15,23,42,.025);
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
    .timeline-item { text-align: left; width: 100%; border: 1px solid var(--line); background: #fff; border-radius: var(--radius-md); padding: 10px; box-shadow: 0 1px 2px rgba(15,23,42,.025); }
    .timeline-item:hover { border-color: rgba(15,118,110,.24); background: #fff; transform: translateY(-1px); }
    .timeline-item[data-active="true"] { border-color: rgba(15,118,110,.36); background: linear-gradient(180deg, rgba(230,244,241,.86), #fff); }
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
    .decision-advantage-hero,
    .input-command-center,
    .resource-command-center,
    .demand-command-center,
    .capacity-command-center {
      display: grid;
      grid-template-columns: minmax(260px, .8fr) minmax(0, 1.2fr);
      gap: 14px;
      padding: 14px;
      border: 1px solid rgba(15,23,42,.10);
      border-radius: 18px;
      background:
        linear-gradient(120deg, var(--route-soft, var(--green-soft)), rgba(255,255,255,.94) 44%),
        #fff;
      box-shadow: var(--shadow-card);
    }
    .decision-advantage-copy,
    .input-command-copy,
    .resource-command-copy,
    .demand-command-copy,
    .capacity-command-copy {
      display: grid;
      align-content: center;
      gap: 9px;
    }
    .decision-advantage-copy h3,
    .input-command-copy h3,
    .resource-command-copy h3,
    .demand-command-copy h3,
    .capacity-command-copy h3 {
      margin: 0;
      font-size: clamp(24px, 3vw, 42px);
      line-height: 1;
      letter-spacing: -.05em;
    }
    .decision-advantage-copy p,
    .input-command-copy p,
    .resource-command-copy p,
    .demand-command-copy p,
    .capacity-command-copy p {
      margin: 0;
      color: var(--ink-2);
      font-size: 13px;
      line-height: 1.55;
    }
    .reason-kicker,
    .input-kicker,
    .resource-kicker,
    .demand-kicker,
    .capacity-kicker {
      width: fit-content;
      padding: 5px 8px;
      border: 1px solid rgba(15,23,42,.08);
      border-radius: 999px;
      color: var(--route-ink, var(--accent-2));
      background: rgba(255,255,255,.72);
      font: 800 10px var(--mono);
      letter-spacing: .06em;
      text-transform: uppercase;
    }
    .decision-advantage-metrics,
    .input-signal-grid,
    .resource-signal-grid,
    .demand-signal-grid,
    .capacity-signal-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 9px;
    }
    .reason-graph {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }
    .reason-node {
      display: grid;
      gap: 7px;
      min-height: 146px;
      padding: 11px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: #fff;
      position: relative;
      overflow: hidden;
      box-shadow: 0 1px 2px rgba(15,23,42,.025);
    }
    .reason-node::before {
      position: absolute;
      inset: 0 0 auto;
      height: 4px;
      background: var(--route-accent, var(--accent));
      opacity: .76;
      content: "";
    }
    .reason-node[data-status="passed"] {
      border-color: rgba(15,118,110,.26);
      background: linear-gradient(180deg, rgba(230,244,241,.78), #fff);
    }
    .reason-node[data-status="rejected"] {
      border-color: rgba(148,163,184,.28);
      background: #f1f5f9;
      opacity: .76;
    }
    .reason-node[data-status="running"] {
      border-color: rgba(37,99,235,.26);
      background: linear-gradient(180deg, #dbeafe, #fff);
    }
    .reason-node-top,
    .candidate-path-top,
    .focus-card-top {
      display: flex;
      justify-content: space-between;
      gap: 8px;
      align-items: flex-start;
    }
    .reason-node-top strong,
    .candidate-path-top strong,
    .focus-card-top strong {
      font-size: 13px;
    }
    .reason-node-index,
    .path-status,
    .focus-badge {
      padding: 4px 7px;
      border-radius: 999px;
      color: var(--route-ink, var(--accent-2));
      background: var(--route-soft, var(--green-soft));
      font: 800 10px var(--mono);
      white-space: nowrap;
    }
    .reason-node p,
    .candidate-path p,
    .order-focus-card p,
    .rider-focus-card p {
      margin: 0;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
    }
    .candidate-path-board {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }
    .candidate-path {
      display: grid;
      gap: 8px;
      padding: 11px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: #fff;
    }
    .candidate-path[data-status="selected"] {
      border-color: rgba(15,118,110,.34);
      background: linear-gradient(180deg, rgba(230,244,241,.90), #fff);
      box-shadow: inset 0 0 0 1px rgba(15,118,110,.08);
    }
    .candidate-path[data-status="rejected"] {
      background: #f8fafc;
      opacity: .82;
    }
    .decision-step-flow {
      display: grid;
      gap: 10px;
    }
    .decision-step-card {
      display: grid;
      grid-template-columns: 42px minmax(0, 1fr);
      gap: 12px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 15px;
      background: #fff;
      box-shadow: 0 1px 2px rgba(15,23,42,.03), 0 8px 18px rgba(15,23,42,.035);
    }
    .decision-step-card[data-step-status="final"] {
      border-color: rgba(15,118,110,.28);
      background: linear-gradient(180deg, rgba(230,244,241,.84), #fff);
    }
    .decision-step-index {
      display: grid;
      place-items: center;
      width: 34px;
      height: 34px;
      border-radius: 12px;
      color: #fff;
      background: var(--route-accent, var(--accent));
      font: 900 13px var(--mono);
      box-shadow: 0 8px 18px rgba(15,118,110,.16);
    }
    .decision-step-body {
      display: grid;
      gap: 7px;
      min-width: 0;
    }
    .decision-step-top {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: flex-start;
    }
    .decision-step-top strong {
      font-size: 14px;
      letter-spacing: -.01em;
    }
    .decision-step-top span,
    .decision-plan-status {
      padding: 4px 7px;
      border-radius: 999px;
      color: var(--route-ink, var(--accent-2));
      background: var(--route-soft, var(--green-soft));
      font: 800 10px var(--mono);
      white-space: nowrap;
    }
    .decision-step-card p,
    .decision-plan-card p {
      margin: 0;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.5;
    }
    .decision-plan-board {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }
    .decision-plan-card {
      display: grid;
      align-content: start;
      gap: 8px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 15px;
      background: #fff;
      box-shadow: 0 1px 2px rgba(15,23,42,.025);
    }
    .decision-plan-card[data-plan="accepted"] {
      border-color: rgba(15,118,110,.32);
      background: linear-gradient(180deg, rgba(230,244,241,.90), #fff);
    }
    .decision-plan-card[data-plan="rejected"] {
      background: #f8fafc;
    }
    .decision-plan-top {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: flex-start;
    }
    .decision-plan-top strong {
      font-size: 14px;
    }
    .decision-proof-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 9px;
    }
    .decision-evidence-grid,
    .order-focus-list,
    .rider-focus-list,
    .coverage-grid {
      display: grid;
      gap: 9px;
    }
    .decision-evidence-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .order-focus-list,
    .rider-focus-list {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .order-focus-card,
    .rider-focus-card,
    .coverage-card {
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: #fff;
      box-shadow: 0 1px 2px rgba(15,23,42,.025);
    }
    .order-focus-card[data-risk="high"] {
      border-color: rgba(180,35,24,.18);
      background: linear-gradient(180deg, rgba(254,228,226,.48), #fff 54%);
    }
    .rider-focus-card[data-state="available"] {
      border-color: rgba(15,118,110,.18);
      background: linear-gradient(180deg, rgba(230,244,241,.56), #fff 54%);
    }
    .coverage-card {
      display: grid;
      gap: 8px;
      background: #fff;
    }
    .coverage-card b {
      display: block;
      font-size: 13px;
    }
    .coverage-bar {
      height: 8px;
      overflow: hidden;
      border-radius: 999px;
      background: #e2e8f0;
    }
    .coverage-bar span {
      display: block;
      width: calc(var(--coverage) * 100%);
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, var(--route-accent, var(--accent)), #22c55e);
    }
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
      box-shadow: 0 1px 2px rgba(15,23,42,.025);
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
      box-shadow: var(--shadow-card);
    }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { padding: 10px 12px; border-bottom: 1px solid var(--line); text-align: left; white-space: nowrap; }
    th { position: sticky; top: 0; z-index: 1; color: var(--muted); background: #f8fafc; font: 800 11px var(--mono); }
    tbody tr:hover { background: rgba(15,118,110,.035); }
    td span { color: var(--muted); font-size: 12px; }
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
      background: rgba(255,255,255,.94);
      box-shadow: var(--shadow-card);
    }
    .input-workspace, .resource-workspace, .demand-workspace, .capacity-workspace { grid-template-columns: 1fr; }
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
    .operations-grid[data-density="summary-first"] {
      grid-template-columns: minmax(0, 1fr) 360px;
    }
    .orders-table-shell { max-height: 430px; }
    .orders-table-shell[data-evidence-role="secondary"],
    .rider-board[data-evidence-role="secondary"] {
      box-shadow: var(--shadow-tight);
    }
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
    .rider-evidence-shell {
      display: grid;
      overflow: hidden;
    }
    .rider-evidence-shell .rider-board {
      padding: 14px;
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
      border-radius: var(--radius-md);
      background:
        linear-gradient(90deg, rgba(148,163,184,.14) 1px, transparent 1px),
        linear-gradient(0deg, rgba(148,163,184,.14) 1px, transparent 1px),
        radial-gradient(circle at 68% 34%, rgba(15,118,110,.08), transparent 30%),
        #f8fafc;
      background-size: 24px 24px;
    }
    .route-empty {
      padding: 30px;
      color: var(--muted);
      text-align: center;
    }
    @media (max-width: 1180px) {
      .workbench-shell { grid-template-columns: 184px minmax(0, 1fr); }
      .brand { grid-template-columns: 40px 1fr; }
      .brand span, .nav-section-title, .nav-meta, .nav-hint, .nav-module, .nav-role { display: none; }
      .nav-link { grid-template-columns: 40px 1fr; justify-items: stretch; }
      .nav-copy { display: block; min-width: 0; }
      .nav-title-line strong { font-size: 13px; }
      .live-grid, .decision-grid, .memory-grid, .rider-grid { grid-template-columns: 1fr; }
      .live-advantage-hero, .live-ops-shell, .decision-grid, .decision-advantage-hero, .input-command-center, .resource-command-center, .demand-command-center, .capacity-command-center, .memory-command-center, .memory-operating-grid, .memory-flow-grid { grid-template-columns: 1fr; }
      .live-side-rail, .decision-grid > aside, .operations-grid > aside, .control-dock { position: static; }
      .topbar { grid-template-columns: 1fr; }
      .topbar-stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .runtime-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .metric-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .live-advantage-hero .delta-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
      .operations-overview, .operations-grid, .operations-grid[data-density="summary-first"], .rider-board, .reason-graph, .candidate-path-board, .decision-plan-board, .decision-evidence-grid, .decision-proof-grid, .order-focus-list, .rider-focus-list { grid-template-columns: 1fr; }
      .memory-overview, .memory-command-metrics, .memory-layer-grid, .recall-lane { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (max-width: 720px) {
      .workbench-shell { grid-template-columns: minmax(0, 1fr); }
      .workbench-nav { position: sticky; top: 0; z-index: 30; height: auto; padding: 10px 12px 12px; }
      .brand { padding: 4px 4px 10px; border-bottom-color: rgba(255,255,255,.08); }
      .nav-list { grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 6px; }
      .nav-link { grid-template-columns: 1fr; padding: 8px 4px; text-align: center; border-radius: 12px; }
      .nav-link[aria-current="page"]::before { inset: auto 18px 0; width: auto; height: 3px; }
      .nav-icon { display: none; }
      .nav-copy { display: block; }
      .nav-title-line strong { display: block; font-size: 12px; line-height: 1.2; }
      .route-view { padding: 14px 12px 18px; }
      .topbar { padding: 12px 14px; }
      .filter-bar .select-control { flex: 1 1 160px; min-width: 0; }
      .filter-bar .filter-count { width: 100%; margin-left: 0; }
      .page-head { grid-template-columns: 1fr; padding: 14px; border-radius: 18px; }
      .page-role-card { padding: 10px; }
      .algorithm-pair, .delta-grid, .metric-strip { grid-template-columns: 1fr; }
      .live-advantage-hero { padding: 12px; border-radius: 18px; }
      .live-advantage-hero .algorithm-pair, .live-advantage-hero .delta-grid { grid-template-columns: 1fr; }
      .live-control-dock .runtime-strip { flex-basis: 100%; grid-template-columns: 1fr; }
      .operations-overview { grid-template-columns: 1fr; }
      .memory-overview, .memory-command-metrics, .memory-layer-grid, .recall-lane, .memory-field-grid, .context-metric-grid, .decision-advantage-metrics, .input-signal-grid, .resource-signal-grid, .demand-signal-grid, .capacity-signal-grid, .reason-graph, .candidate-path-board, .decision-plan-board, .decision-evidence-grid, .decision-proof-grid, .order-focus-list, .rider-focus-list { grid-template-columns: 1fr; }
      .schematic-map, .real-map-stage { height: 360px; margin: 10px; }
      .map-action-status { left: 12px; top: 58px; max-width: calc(100% - 24px); }
      .map-mode-chip { right: 10px; top: 10px; }
      .map-legend { left: 10px; right: 10px; max-width: none; bottom: 10px; }
      .action-grid, .runtime-strip { grid-template-columns: 1fr; }
      .score-row, .stage-row, .time-lane-item { grid-template-columns: 1fr; }
    }
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after {
        animation-duration: .001ms !important;
        animation-iteration-count: 1 !important;
        scroll-behavior: auto !important;
        transition-duration: .001ms !important;
      }
    }
  </style>
</head>
<body data-shell="dispatch-workbench-shell" data-visual-system="enterprise-dispatch-v2" data-visual-polish="chinese-enterprise-workbench-v3" data-density="high-information" data-secret-handling="env-only-redacted">
  <div id="dispatch-workbench-shell" class="workbench-shell" data-product-reference="kandbox-dispatch">
    <aside class="workbench-nav" aria-label="调度工作台导航">
      <div class="brand">
        <div class="brand-mark">调度</div>
        <div>
          <strong>外卖调度</strong>
          <span>智能推演工作台</span>
        </div>
      </div>
      <div class="nav-section-title">核心页面</div>
      <nav id="route-nav" class="nav-list"></nav>
      <div class="nav-meta">
        <strong>工作台导览</strong><br>
        先看实时推理优势，再追溯决策过程、长期记忆、订单池和骑手运力。
      </div>
    </aside>
    <main class="workbench-main">
      <header class="topbar">
        <div>
          <h1 id="route-title">外卖配送智能调度工作台</h1>
          <p id="route-subtitle">围绕订单、骑手、地图、决策和记忆构建的实时调度工作台。</p>
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
        icon: "推",
        title: "实时推理",
        navLabel: "实时推理",
        navRole: "主控台",
        navHint: "看系统自动推演、地图动作和累计优势。",
        module: "地图推演",
        outcome: "自动推演 + 优势证明",
        subtitle: "订单释放、骑手移动、路线变化和累计对比在同一个运营视图中联动。"
      },
      decisions: {
        icon: "决",
        title: "决策过程",
        navLabel: "决策过程",
        navRole: "可追溯",
        navHint: "看每一轮为什么这样派、放弃了什么。",
        module: "推导链路",
        outcome: "评分过程 + 动作回写",
        subtitle: "每一轮触发、过滤、评分、派单动作和结果回写独立成页。"
      },
      memory: {
        icon: "忆",
        title: "长期记忆",
        navLabel: "长期记忆",
        navRole: "长期记忆",
        navHint: "看系统沉淀、召回和验证的调度经验。",
        module: "经验沉淀",
        outcome: "记忆沉淀 + 召回反馈",
        subtitle: "长期记忆视图：展示新沉淀、已整理、当前命中和效果反馈，而不是资产表。"
      },
      orders: {
        icon: "单",
        title: "订单池",
        navLabel: "订单池",
        navRole: "需求视图",
        navHint: "看全天订单、时段、风险和进入推理状态。",
        module: "订单池",
        outcome: "需求全集 + 风险筛选",
        subtitle: "全天订单全集已预置，只用于调度可见性、筛选和风险判断。"
      },
      riders: {
        icon: "骑",
        title: "骑手运力",
        navLabel: "骑手运力",
        navRole: "供给视图",
        navHint: "看骑手班次、位置、负载和任务链。",
        module: "运力池",
        outcome: "供给盘点 + 负载判断",
        subtitle: "骑手班次、在线状态、位置、负载和任务链统一盘点。"
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
    const statusLabels = {
      scheduled: "待释放",
      entered_inference: "已进推理",
      assigned: "已分配",
      delivered: "已送达",
      late_risk: "超时风险"
    };
    const riskLabels = {
      low: "低风险",
      medium: "中风险",
      high: "高风险"
    };
    const riderStateLabels = {
      available: "可接单",
      busy: "配送中",
      ending_shift: "临近下线",
      offline: "离线"
    };
    const memoryStageLabels = {
      new: "新沉淀",
      curated: "已整理",
      active: "命中中",
      feedback: "效果反馈"
    };
    const memoryScopeLabels = {
      GLOBAL: "全局",
      PROFILE: "画像",
      recall: "召回",
      working: "工作记忆",
      profile: "画像",
      policy: "策略"
    };
    const memoryChannelLabels = {
      "recall-before-scoring": "评分前召回",
      "decision-result-writeback": "结果回写",
      "future-policy-shift": "策略整理",
      memory_writeback: "记忆写入",
      memory_recall: "记忆召回",
      future_policy_shift: "策略整理",
      feedback: "效果反馈"
    };
    const profileTypeLabels = {
      rider: "骑手画像",
      area: "商圈画像",
      order: "订单画像"
    };
    const stageLabels = {
      order_release: "订单释放",
      rider_pool: "骑手池",
      time_window: "时间窗口",
      area_and_shift: "区域与班次",
      risk_guardrail: "风险保护",
      candidate_filter: "候选过滤",
      feasibility: "可行性",
      scoring: "综合评分",
      assignment: "派单输出",
      memory: "记忆回写"
    };
    const demandPhaseLabels = {
      breakfast: "早餐时段",
      "pre-dispatch": "推理开始前",
      lunch_peak: "午高峰",
      afternoon_tea: "下午茶",
      dinner_peak: "晚高峰",
      night_supply_gap: "夜间供给缺口"
    };
    const weatherLabels = {
      clear: "晴天",
      mixed: "混合天气",
      rain: "雨天",
      light_rain: "小雨",
      heavy_rain: "强降雨"
    };
    const shockLabels = {
      rain_slowdown: "降雨降速",
      merchant_burst: "商家爆单",
      courier_shortage: "骑手短缺",
      traffic_block: "道路拥堵"
    };
    const liveTileLayer = {
      id: "cartodb-light-nolabels",
      url: "https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png",
      attribution: "&copy; OpenStreetMap contributors &copy; CARTO",
      subdomains: "abcd"
    };
    let liveLeafletMap = null;
    let liveLeafletOverlayGroup = null;
    let liveMapHydrationToken = "";

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

    function fmtSavedDistance(valueKm) {
      const numberValue = Number(valueKm) || 0;
      if (numberValue > 0) return `节省 ${fmtNumber(numberValue, 2)} km`;
      if (numberValue < 0) return `增加 ${fmtNumber(Math.abs(numberValue), 2)} km`;
      return `持平 ${fmtNumber(0, 2)} km`;
    }

    function displayFrom(map, value) {
      return map[value] || value || "-";
    }

    function displayStatus(value) {
      return displayFrom(statusLabels, value);
    }

    function displayRisk(value) {
      return displayFrom(riskLabels, value);
    }

    function displayRiderState(value) {
      return displayFrom(riderStateLabels, value);
    }

    function displayMemoryStage(value) {
      return displayFrom(memoryStageLabels, value);
    }

    function displayMemoryScope(value) {
      return displayFrom(memoryScopeLabels, value);
    }

    function displayMemoryChannel(value) {
      return displayFrom(memoryChannelLabels, value);
    }

    function displayProfileType(value) {
      return displayFrom(profileTypeLabels, value);
    }

    function displayStage(value) {
      return displayFrom(stageLabels, value);
    }

    function displayDemandPhase(value) {
      return displayFrom(demandPhaseLabels, value);
    }

    function displayWeather(value) {
      return displayFrom(weatherLabels, value);
    }

    function displayShock(value) {
      return displayFrom(shockLabels, value);
    }

    function displayTag(value) {
      return displayShock(displayWeather(displayDemandPhase(value)));
    }

    function displayTriggerReason(value) {
      const text = String(value || "");
      if (!text) return "-";
      if (text.startsWith("Pressure change:")) return `压力变化：${text.replace("Pressure change:", "").replace(".", "").trim()}`;
      if (text === "Planner comparison due under current order pressure.") return "当前订单压力达到阈值，触发算法对比。";
      const scheduled = text.match(/^Scheduled (.+) dispatch round\\.$/);
      if (scheduled) return `按计划进入${displayDemandPhase(scheduled[1])}派单轮次。`;
      return text;
    }

    function displayDecisionSummary(value) {
      const text = String(value || "");
      if (!text) return "-";
      const autoMatch = text.match(/^AutoSolver assigned (\\d+) orders with risk-aware availability scoring; avg ETA ([0-9.]+) min\\.$/);
      if (autoMatch) return `我方方案分配 ${autoMatch[1]} 单，综合骑手可用性和超时风险，平均预计 ${autoMatch[2]} 分钟。`;
      const greedyMatch = text.match(/^Nearest greedy assigned (\\d+) orders by pickup distance; avg ETA ([0-9.]+) min\\.$/);
      if (greedyMatch) return `最近距离基线分配 ${greedyMatch[1]} 单，只按取餐距离排序，平均预计 ${greedyMatch[2]} 分钟。`;
      if (text === "No orders in this time slice.") return "当前时间片没有新订单。";
      if (text === "Uses memory recall and risk scoring to choose a lower-timeout route.") return "召回历史经验并结合风险评分，选择更低超时风险的路线。";
      if (text === "Dispatches by nearest distance while ignoring rain congestion and future order pressure.") return "只按最近距离派单，未考虑雨天拥堵和后续订单压力。";
      if (text === "Decision outcome updates dispatch memory when the challenger improves cumulative cost or risk.") return "当我方方案改善累计成本或风险时，把结果写回调度记忆。";
      return text;
    }

    function displayCandidateReason(value) {
      const text = String(value || "");
      if (!text) return "-";
      if (text === "Baseline optimizes nearest pickup, so queueing and deadline risk can accumulate.") return "基线只优化最近取餐点，排队和承诺时效风险容易累积。";
      if (text === "AutoSolver evaluates availability, congestion, route cost and deadline pressure.") return "我方同时评估骑手可用性、拥堵、路线成本和承诺时效压力。";
      if (text === "Nearest distance gives a quick feasible answer but carries high rain congestion risk.") return "最近距离能快速给出可行解，但在雨天和拥堵下超时风险偏高。";
      if (text === "Memory recall matches rainy lunch peak and reduces timeout risk.") return "召回雨天午高峰经验后，超时风险更低。";
      return text;
    }

    function displayActionReason(value) {
      const text = String(value || "");
      if (!text || text === "Baseline nearest-only assignment was rejected by risk-balanced scoring.") {
        return "基线只看最近距离，本轮被我方综合时效、成本和风险评分淘汰。";
      }
      return displayCandidateReason(text);
    }

    function displayMemoryText(value) {
      const text = String(value || "");
      if (!text) return "-";
      const linkedDecision = text.match(/^linked decision (.+)$/);
      if (linkedDecision) return `关联${readableDecisionLabel(linkedDecision[1])}`;
      if (text === "Positive policy shift retained for similar contexts.") return "相似场景下保留正向策略调整。";
      if (text === "Historical context recalled before scoring candidates.") return "评分候选骑手前已召回历史上下文。";
      if (text === "Writeback confidence updated after round outcome.") return "本轮结果产生后，已更新回写置信度。";
      if (text.startsWith("For ") && text.includes("prefer AutoSolver risk-balanced dispatch over nearest greedy.")) {
        const match = text.match(/^For (.+) with (.+) and congestion ([0-9.]+), prefer AutoSolver risk-balanced dispatch over nearest greedy\\.$/);
        if (match) return `${displayDemandPhase(match[1])}、${displayWeather(match[2])}、拥堵 ${match[3]} 时，优先使用我方风险均衡派单，而不是最近距离基线。`;
      }
      if (text.startsWith("For ") && text.includes("keep greedy as a guardrail")) {
        const match = text.match(/^For (.+), keep greedy as a guardrail when risk-balanced dispatch has weak savings\\.$/);
        if (match) return `${displayDemandPhase(match[1])}下，如果风险均衡方案收益不明显，保留贪心基线作为保护。`;
      }
      if (text.startsWith("Future policy: assign ")) {
        const match = text.match(/^Future policy: assign (.+) priority to AutoSolver when context matches (.+) and courier supply is (\\d+)\\.$/);
        if (match) return `未来相似${displayDemandPhase(match[2])}且骑手供给为 ${match[3]} 时，提高我方方案优先级。`;
      }
      if (text.startsWith("Recall ") && text.includes("nearest-only matching")) return "召回相似历史场景，优先排序风险均衡派单，再比较最近距离方案。";
      if (text.includes("congestion") && text.includes("riders")) {
        return text
          .replaceAll("breakfast", "早餐时段")
          .replaceAll("lunch_peak", "午高峰")
          .replaceAll("afternoon_tea", "下午茶")
          .replaceAll("dinner_peak", "晚高峰")
          .replaceAll("night_supply_gap", "夜间供给缺口")
          .replaceAll("mixed", "混合天气")
          .replaceAll("clear", "晴天")
          .replaceAll("rain", "雨天")
          .replace("congestion", "拥堵")
          .replace("with", "，")
          .replace("riders under shock pressure", "名骑手，存在冲击压力")
          .replace("riders under steady pressure", "名骑手，压力稳定");
      }
      return text;
    }

    function displayMemoryScenario(value) {
      const text = String(value || "");
      if (!text) return "-";
      const labels = {
        breakfast: "早餐时段",
        lunch_peak: "午高峰",
        afternoon_tea: "下午茶",
        dinner_peak: "晚高峰",
        night_supply_gap: "夜间供给缺口",
        clear: "晴天",
        rain: "雨天",
        mixed: "混合天气",
        low_congestion: "低拥堵",
        medium_congestion: "中等拥堵",
        high_congestion: "高拥堵",
        scarce_supply: "供给偏紧",
        balanced_supply: "供给平衡",
        abundant_supply: "供给充足",
        shock: "有冲击事件",
        steady: "压力稳定"
      };
      if (text.includes("|")) {
        return text.split("|").map((item) => labels[item] || displayMemoryText(item)).join(" / ");
      }
      return displayMemoryText(text);
    }

    function displayMemoryStepSummary(step) {
      if (!step) return "-";
      if (step.id === "hit") return displayMemoryScenario(step.summary);
      return displayMemoryText(step.summary);
    }

    function displayRiderPerformance(value) {
      const text = String(value || "");
      if (text === "High-throughput rider with stable willingness during peaks.") return "高峰期承载能力稳定，接单意愿较高。";
      if (text === "Balanced rider used across multiple dispatch rounds.") return "多轮派单表现均衡，可作为稳定运力。";
      if (text === "Reserve capacity for local-area pressure relief.") return "本地商圈储备运力，可用于缓解局部压力。";
      return text;
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
        trigger_reason: "等待首轮规划决策触发。",
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
          summary: "首轮规划前暂无记忆回写。"
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
      const previousRoutes = previous ? routeRowsForFrame(previous, "ours").slice(0, 2).map((route) => ({...route, renderLane: "previous"})) : [];
      const ours = routeRowsForFrame(frame, "ours");
      const baseline = routeRowsForFrame(frame, "baseline");
      const diffIds = differentialOrderIds(frame);
      if (inferenceState.mode === "overlay") {
        const diffOurs = ours.filter((route) => diffIds.has(route.order_id)).slice(0, 5).map((route) => ({...route, renderLane: "difference"}));
        const diffBaseline = baseline.filter((route) => diffIds.has(route.order_id)).slice(0, 3).map((route) => ({...route, renderLane: "baseline"}));
        return [...previousRoutes, ...(diffOurs.length ? diffOurs : ours.slice(0, 4).map((route) => ({...route, renderLane: "ours"}))), ...diffBaseline];
      }
      if (inferenceState.mode === "compare") {
        const diffBaseline = baseline.filter((route) => diffIds.has(route.order_id)).slice(0, 3).map((route) => ({...route, renderLane: "baseline"}));
        return [...previousRoutes, ...ours.slice(0, 5).map((route) => ({...route, renderLane: "ours"})), ...diffBaseline];
      }
      return [...previousRoutes, ...ours.slice(0, 6).map((route) => ({...route, renderLane: "ours"}))];
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
        <div class="page-head" data-page-identity="${escapeHtml(routeId)}" data-page-module="${escapeHtml(copy.module)}">
          <div>
            <div class="eyebrow">${escapeHtml(eyebrow)}</div>
            <h2>${escapeHtml(copy.title)}</h2>
            <p>${escapeHtml(description || copy.subtitle)}</p>
            <div class="page-role-strip" data-page-role-strip="${escapeHtml(routeId)}">
              <span>${escapeHtml(copy.navRole)}</span>
              <span>${escapeHtml(copy.module)}</span>
              <span>${escapeHtml(copy.outcome)}</span>
            </div>
          </div>
          <aside class="page-role-card" aria-label="当前页面说明">
            <b>${escapeHtml(copy.navLabel)}</b>
            <span>${escapeHtml(copy.navHint)}</span>
            <em>全天预置数据回放</em>
          </aside>
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

    function stopLiveRuntime() {
      inferenceState.running = false;
      clearInferenceTimer();
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
      const inferenceFinished = inferenceState.started && inferenceState.currentTimeS >= workbench.timeline.end_s;
      const stateLabel = inferenceState.running ? "自动推理中" : inferenceFinished ? "推演完成" : inferenceState.started ? "已暂停" : "未开始";
      const events = releasedEvents(inferenceState.currentTimeS);
      const currentScore = scoreForTime(inferenceState.currentTimeS);
      const currentDecision = decisionForTime(inferenceState.currentTimeS);
      liveGrid.dataset.inferenceState = inferenceState.running ? "running" : inferenceState.started ? "paused" : "ready";
      setText("inference-state-label", stateLabel);
      setText("inference-clock", clock(inferenceState.currentTimeS));
      setText("inference-speed-label", `${inferenceState.speed}x`);
      setText("inference-mode-label", inferenceModeLabels[inferenceState.mode]);
      setText("inference-event-count", events.length);
      setText("live-advantage-headline", liveAdvantageHeadline(currentScore));
      setText("live-advantage-copy", liveAdvantageCopy(currentScore));
      const targetRow = document.getElementById("advantage-target-row");
      if (targetRow) targetRow.innerHTML = renderAdvantageTargetRow(currentScore);
      setText("map-runtime-hint", `${stateLabel} / ${clock(inferenceState.currentTimeS)} / ${inferenceModeLabels[inferenceState.mode]}`);
      setText("event-flow-caption", `${events.length} 个事件已自动释放`);
      setText("cumulative-metrics-caption", `${currentScore.time_label} 累计优势`);
      setText("round-summary-time", currentDecision.trigger_time_label);
      const progressBar = document.getElementById("inference-progress-bar");
      if (progressBar) progressBar.style.setProperty("--progress", `${inferenceProgressPct()}%`);
      const mapStage = document.getElementById("live-map-stage");
      if (mapStage) {
        const frame = frameForTime(inferenceState.currentTimeS);
        const routes = mapRouteRows(frame);
        const riders = riderPositionsForFrame(frame);
        const orders = ordersForMap(frame);
        mapStage.dataset.mapMode = inferenceState.mode;
        mapStage.dataset.frameId = frame.id;
        const actionStatus = mapStage.querySelector("#map-action-status");
        if (actionStatus) actionStatus.innerHTML = renderMapActionStatus(frame, routes, riders, orders);
        if (!updateLiveLeafletOverlay(frame, routes, riders, orders)) {
          destroyLiveMap();
          mapStage.innerHTML = renderLiveMapLayer(frame, routes, riders, orders);
          queueLiveMapHydration(frame, routes, riders, orders);
        }
      }
      const startButton = document.getElementById("start-inference");
      if (startButton) {
        startButton.disabled = inferenceState.started && inferenceState.running;
        startButton.textContent = inferenceState.started ? "重新开始" : "开始推理";
      }
      const pauseButton = document.getElementById("pause-inference");
      if (pauseButton) {
        pauseButton.textContent = inferenceState.running ? "暂停" : inferenceFinished ? "已完成" : "继续";
        pauseButton.disabled = inferenceFinished && !inferenceState.running;
      }
      const scoreStack = document.getElementById("live-score-stack");
      if (scoreStack) scoreStack.innerHTML = renderLiveScoreCards(currentScore);
      const eventFlow = document.getElementById("live-event-flow");
      if (eventFlow) eventFlow.innerHTML = events.slice(-4).reverse().map(renderEventItem).join("") || `<div class="list-item"><strong>等待开始</strong><p>点击开始推理后，订单进入、候选分配和累计结果将自动释放。</p></div>`;
      const cumulativeMetrics = document.getElementById("live-cumulative-metrics");
      if (cumulativeMetrics) cumulativeMetrics.innerHTML = renderLiveCumulativeMetrics(currentScore);
      const summary = document.getElementById("live-round-summary");
      if (summary) summary.innerHTML = renderRoundSummary(currentDecision, true);
    }

    function setText(id, value) {
      const node = document.getElementById(id);
      if (node) node.textContent = String(value);
    }

    function renderTopbarStats() {
      const stats = workbench.inspection;
      document.getElementById("topbar-stats").innerHTML = [
        ["订单", stats.order_count],
        ["骑手", stats.rider_count],
        ["决策轮次", stats.decision_count],
        ["优势验证", "开始后累计"]
      ].map(([label, value]) => `
        <div class="stat-pill"><b>${escapeHtml(value)}</b><span>${escapeHtml(label)}</span></div>
      `).join("");
    }

    function liveAdvantageHeadline(score) {
      const delta = score.deltas || {};
      const timeSaved = Number(delta.time_saved_min || 0);
      if (!inferenceState.started) {
        return "等待开始推理";
      }
      if (inferenceState.currentTimeS >= workbench.timeline.end_s) {
        return `全日推演完成：节省 ${fmtNumber(timeSaved, 1)} 分钟`;
      }
      if (timeSaved <= 0) {
        return "正在等待首轮有效优势";
      }
      return `已节省 ${fmtNumber(timeSaved, 1)} 分钟`;
    }

    function liveAdvantageCopy(score) {
      const delta = score.deltas || {};
      const finalDelta = workbench.metrics.final.deltas;
      const timeSaved = Number(delta.time_saved_min || 0);
      const moneySaved = Number(delta.money_saved_yuan || 0);
      const timeoutText = fmtFewer(delta.timeout_order_delta || 0, "单");
      if (!inferenceState.started) {
        return "点击开始推理后，系统会按全天时间线自动释放订单、移动骑手、重算路线，并实时累计我方相对基线的优势。";
      }
      if (timeSaved <= 0) {
        return "推理已开始，当前仍在等待首轮规划评分。优势卡片只展示已经推演到的累计结果，不提前展示全日结论。";
      }
      if (inferenceState.currentTimeS >= workbench.timeline.end_s) {
        return `全日回放已完成：我方比基线少 ${fmtNumber(finalDelta.time_saved_min, 1)} 分钟、少 ${fmtNumber(finalDelta.money_saved_yuan, 1)} 元成本，超时单${fmtFewer(finalDelta.timeout_order_delta, "单")}。`;
      }
      return `推理正在自动推进：当前累计少 ${fmtNumber(moneySaved, 1)} 元成本，超时单${timeoutText}，地图只展示我方动作和差异路线。`;
    }

    function renderAdvantageTargetRow(score) {
      if (!inferenceState.started) {
        return `
          <span>开始后累计验证</span>
          <span>全日结论暂不展示</span>
          <span>地图将自动推进</span>
        `;
      }
      const delta = score.deltas || {};
      if (inferenceState.currentTimeS >= workbench.timeline.end_s) {
        const finalDelta = workbench.metrics.final.deltas;
        return `
          <span>全日节省 ${fmtNumber(finalDelta.time_saved_min, 1)} 分钟</span>
          <span>成本优势 ${fmtNumber(finalDelta.money_saved_yuan, 1)} 元</span>
          <span>超时单${fmtFewer(finalDelta.timeout_order_delta, "单")}</span>
        `;
      }
      return `
        <span>当前进度 ${fmtNumber(inferenceProgressPct(), 1)}%</span>
        <span>已累计 ${fmtNumber(delta.time_saved_min || 0, 1)} 分钟</span>
        <span>成本 ${fmtNumber(delta.money_saved_yuan || 0, 1)} 元</span>
      `;
    }

    function renderNav() {
      document.getElementById("route-nav").innerHTML = workbench.routes.map((route) => {
        const copy = routeCopy[route.id];
        const roleBadge = copy.navRole && copy.navRole !== copy.navLabel ? `<em class="nav-role">${escapeHtml(copy.navRole)}</em>` : "";
        return `
          <a class="nav-link" href="${escapeHtml(route.path)}" data-route-link="${escapeHtml(route.id)}" data-route-role="${escapeHtml(copy.navRole)}" data-kandbox-module="${escapeHtml(copy.module)}" aria-label="${escapeHtml(`${copy.navLabel}：${copy.navHint}`)}">
            <span class="nav-icon">${escapeHtml(copy.icon)}</span>
            <div class="nav-copy">
              <span class="nav-title-line"><strong>${escapeHtml(copy.navLabel || route.label)}</strong>${roleBadge}</span>
              <span class="nav-hint">${escapeHtml(copy.navHint)}</span>
              <span class="nav-module">${escapeHtml(copy.module || route.kandbox_module)}</span>
            </div>
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
      if (routeId !== "live") stopLiveRuntime();
      destroyLiveMap();
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
      const events = releasedEvents(inferenceState.currentTimeS).slice(-4).reverse();
      const currentDecision = decisionForTime(inferenceState.currentTimeS);
      const currentFrame = frameForTime(inferenceState.currentTimeS);
      return `
        ${pageHeader("live", "实时推演总览", "首屏先回答算法是否更强：实时地图承接推理动作，右侧只保留当前决策和运行信号。")}
        <div class="page-grid live-grid" data-page="live" data-inference-state="${inferenceState.running ? "running" : inferenceState.started ? "paused" : "ready"}">
          <section id="live-advantage-hero" class="live-advantage-hero" data-live-priority="advantage-first">
            <div class="advantage-lead">
              <span class="advantage-kicker">实时累计对比栏</span>
              <h3 id="live-advantage-headline">${escapeHtml(liveAdvantageHeadline(currentScore))}</h3>
              <p id="live-advantage-copy">${escapeHtml(liveAdvantageCopy(currentScore))}</p>
              <div id="advantage-target-row" class="advantage-target-row" aria-label="全天最终优势目标">
                ${renderAdvantageTargetRow(currentScore)}
              </div>
            </div>
            <div id="live-score-stack" class="live-advantage-metrics" data-score-role="dominant-advantage">
              ${renderLiveScoreCards(currentScore)}
            </div>
          </section>
          <div class="live-ops-shell">
            <div class="live-primary-column">
              <div class="control-dock live-control-dock" data-control-strip="live">
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
              <div class="card-head"><h3>实时地图层</h3><span id="map-runtime-hint">商家 / 订单 / 骑手 / 路线 / 热点</span></div>
              <div id="live-map-stage" class="real-map-stage schematic-map" data-map-layer="primary" data-real-map-provider="leaflet" data-tile-layer="cartodb-light-nolabels" data-real-map-status="loading" data-map-mode="${escapeHtml(inferenceState.mode)}" data-frame-id="${escapeHtml(currentFrame.id)}">
                ${renderLiveMapLayer(currentFrame)}
              </div>
              </div>
            </div>
            <aside class="live-side-rail">
              <div class="card">
                <div class="card-head"><h3>当前决策摘要</h3><span id="round-summary-time">${escapeHtml(currentDecision.trigger_time_label)}</span></div>
                <div id="live-round-summary" class="card-body compact-list">
                  ${renderRoundSummary(currentDecision, true)}
                </div>
              </div>
              <div class="card live-run-panel">
                <div class="card-head"><h3>运行信号</h3><span><em id="cumulative-metrics-caption">${escapeHtml(currentScore.time_label)} 累计优势</em> / <em id="event-flow-caption">按全天推演时间释放</em></span></div>
                <div class="card-body">
                  <div id="live-cumulative-metrics" class="metric-strip" aria-label="compact cumulative advantage">
                    ${renderLiveCumulativeMetrics(currentScore)}
                  </div>
                  <div id="live-event-flow" class="event-list">${events.map(renderEventItem).join("") || `<div class="list-item"><strong>等待开始</strong><p>点击开始推理后，订单进入、候选分配和累计结果将自动释放。</p></div>`}</div>
                </div>
              </div>
            </aside>
          </div>
        </div>
      `;
    }

    function renderDecisionsPage() {
      const decision = selectedDecision();
      return `
        ${pageHeader("decisions", "算法推理过程", "按时间回放每一轮派单推理：先看为什么触发，再看订单、骑手、过滤、评分、采纳和放弃原因。")}
        <div class="page-grid decision-grid" data-page="decisions" data-decision-route="reasoning">
          <div class="card">
            <div class="card-head"><h3>决策轮次时间线</h3><span id="decision-route-status">${workbench.decisions.length} 轮决策</span></div>
            <div id="decision-timeline" class="card-body timeline-list decision-scroll">
              ${renderDecisionTimeline(decision.id)}
            </div>
          </div>
          <div class="card">
            <div class="card-head"><h3>本轮推理说明</h3><span id="decision-reasoning-phase">${escapeHtml(displayDemandPhase(decision.context.demand_phase))}</span></div>
            <div id="decision-reasoning-canvas" class="card-body decision-canvas">
              ${renderDecisionReasoning(decision)}
            </div>
          </div>
          <aside class="card">
            <div class="card-head"><h3>本轮输入与输出</h3><span id="decision-context-slice">${escapeHtml(displayDemandPhase(decision.context.demand_phase))}场景</span></div>
            <div id="decision-context-pane" class="card-body compact-list">
              ${renderDecisionContext(decision)}
            </div>
          </aside>
        </div>
      `;
    }

    function renderMemoryPage() {
      const byId = Object.fromEntries(workbench.memory.items.map((item) => [item.id, item]));
      const stats = memoryStats();
      const system = workbench.memory.system || {};
      const layers = workbench.memory.layers || [];
      const profiles = workbench.memory.profiles || [];
      const recallChain = workbench.memory.recall_chain || [];
      const writebackLoop = workbench.memory.writeback_loop || [];
      return `
        ${pageHeader("memory", "长期记忆中心", "把调度经验组织为长期记忆、画像、召回链和回写反馈，展示记忆如何让下一轮派单更强。")}
        <div class="page-grid memory-workspace hermes-memory-workspace" data-page="memory" data-memory-route="hermes-long-term" data-memory-model="global-profile-recall-feedback">
          <section id="memory-command-center" class="memory-command-center" aria-label="Hermes-style long term memory command center">
            <div class="memory-command-copy">
              <span class="memory-kicker">长期记忆视图</span>
              <h3>长期记忆中枢</h3>
              <p>这里不是日志列表、资产表或文档中心。系统把每天推理中的有效经验沉淀为全局策略记忆和画像记忆，再在新一轮规划评分前召回，最后用调度结果回写置信度。</p>
              <div class="memory-model-row">
                <span>全局记忆</span>
                <span>画像记忆</span>
                <span>召回链</span>
                <span>回写反馈</span>
              </div>
            </div>
            <div id="memory-overview" class="memory-command-metrics">
              ${renderMemoryOverview(stats, system)}
            </div>
          </section>
          <div class="memory-operating-grid">
            <section id="memory-layer-board" class="card" data-memory-surface="memory-layers">
              <div class="card-head"><h3>记忆层结构</h3><span>全局策略 / 画像记忆</span></div>
              <div class="card-body memory-layer-grid">
                ${layers.map(renderMemoryLayerCard).join("")}
              </div>
            </section>
            <aside id="memory-profile-board" class="memory-profile-board" data-memory-surface="profiles">
              <h3>画像记忆</h3>
              <p>画像不是人员档案，而是系统在历史推理中沉淀的供给、商圈和订单风险模式。</p>
              <div class="memory-profile-list">
                ${profiles.map(renderMemoryProfile).join("")}
              </div>
            </aside>
          </div>
          <div class="memory-flow-grid">
            <section id="memory-recall-chain" class="card" data-memory-surface="recall-chain">
              <div class="card-head"><h3>当前召回链路</h3><span>命中 -> 注入 -> 决策 -> 回写</span></div>
              <div class="card-body memory-flow-lane">
                ${recallChain.map((step, index) => renderMemoryRecallStep(step, byId, index)).join("")}
              </div>
            </section>
            <section id="memory-writeback-loop" class="card" data-memory-surface="writeback-loop">
              <div class="card-head"><h3>记忆形成与反馈闭环</h3><span>新沉淀 / 已整理 / 命中中 / 效果反馈</span></div>
              <div class="card-body memory-flow-lane">
                ${writebackLoop.map((step, index) => renderMemoryWritebackStep(step, byId, index)).join("")}
              </div>
            </section>
          </div>
        </div>
      `;
    }

    function renderOrdersPage() {
      const orders = filteredOrders();
      return `
        ${pageHeader("orders", "订单池看板", "全天订单已经预置并按时间进入推理，这里只看需求压力、风险结构和算法结果。")}
        <div class="page-grid demand-workspace" data-page="orders" data-orders-route="preloaded-demand-pool">
          <section id="orders-command" class="demand-command-center" data-orders-surface="preloaded-order-pool">
            <div class="demand-command-copy">
              <span class="demand-kicker">只读订单池</span>
              <h3>今天订单怎么来</h3>
              <p>不录入、不编辑。调度员只按时间段、商圈、状态和风险筛选，先判断哪批订单会影响超时、成本和骑手负载。</p>
            </div>
            <div id="orders-overview" class="demand-signal-grid">
              ${renderOrdersOverview(orders)}
            </div>
          </section>
          <div id="orders-filter-bar" class="filter-bar" data-filter-bar="orders">
            <select id="orders-filter-time" class="select-control" data-order-filter="timeBand">
              <option value="all">全部时间段</option>
              ${workbench.filters.order_time_bands.map((item) => `<option value="${escapeHtml(item.id)}"${item.id === orderFilterState.timeBand ? " selected" : ""}>${escapeHtml(displayDemandPhase(item.id))} / ${escapeHtml(item.time_label)}</option>`).join("")}
            </select>
            <select id="orders-filter-area" class="select-control" data-order-filter="area">
              <option value="all">全部商圈</option>
              ${workbench.filters.areas.map((item) => `<option value="${escapeHtml(item)}"${item === orderFilterState.area ? " selected" : ""}>${escapeHtml(item)}</option>`).join("")}
            </select>
            <select id="orders-filter-status" class="select-control" data-order-filter="status">
              <option value="all">全部状态</option>
              ${workbench.filters.statuses.map((item) => `<option value="${escapeHtml(item)}"${item === orderFilterState.status ? " selected" : ""}>${escapeHtml(displayStatus(item))}</option>`).join("")}
            </select>
            <select id="orders-filter-risk" class="select-control" data-order-filter="risk">
              <option value="all">全部风险</option>
              ${workbench.filters.risk_levels.map((item) => `<option value="${escapeHtml(item)}"${item === orderFilterState.risk ? " selected" : ""}>${escapeHtml(displayRisk(item))}</option>`).join("")}
            </select>
            <span id="orders-result-count" class="filter-count">${orders.length} / ${workbench.entities.orders.length} 单</span>
          </div>
          <div class="operations-grid" data-density="summary-first">
            <div class="card" id="orders-priority-panel" data-orders-surface="priority-demand">
              <div class="card-head"><h3>优先关注订单</h3><span>先看可能影响超时和收益的订单</span></div>
              <div id="orders-priority-list" class="card-body order-focus-list">
                ${renderOrderFocusList(orders)}
              </div>
            </div>
            <aside class="card" id="orders-context-panel">
              ${renderOrdersContext(orders)}
            </aside>
          </div>
          <div class="table-shell orders-table-shell" data-order-universe="full-day" data-evidence-role="secondary">
              <div class="card-head"><h3>订单全集核对</h3><span>只读证据，不做录入维护</span></div>
              <table>
                <thead><tr><th>订单</th><th>商家/商圈</th><th>时间窗口</th><th>状态/风险</th><th>推理状态</th><th>基线结果</th><th>我方结果</th></tr></thead>
                <tbody id="orders-table-body">${orders.map(renderOrderRow).join("")}</tbody>
              </table>
          </div>
        </div>
      `;
    }

    function renderRidersPage() {
      const riders = filteredRiders();
      return `
        ${pageHeader("riders", "骑手运力看板", "全天骑手班次已经预置，这里只看当前可用性、区域覆盖、负载和预计空闲。")}
        <div class="page-grid capacity-workspace" data-page="riders" data-riders-route="capacity-board">
          <section id="riders-command" class="capacity-command-center" data-riders-surface="capacity-board">
            <div class="capacity-command-copy">
              <span class="capacity-kicker">只读运力池</span>
              <h3>现在运力够不够</h3>
              <p>不是人事后台。调度员先看哪些区域有可接单骑手、哪些骑手负载偏高、哪些班次快结束，再进入候选骑手判断。</p>
            </div>
            <div id="riders-overview" class="capacity-signal-grid">
              ${renderRidersOverview(riders)}
            </div>
          </section>
          <div id="riders-filter-bar" class="filter-bar" data-filter-bar="riders">
            <select id="riders-filter-area" class="select-control" data-rider-filter="area">
              <option value="all">全部区域</option>
              ${workbench.filters.areas.map((item) => `<option value="${escapeHtml(item)}"${item === riderFilterState.area ? " selected" : ""}>${escapeHtml(item)}</option>`).join("")}
            </select>
            <select id="riders-filter-state" class="select-control" data-rider-filter="state">
              <option value="all">全部在线状态</option>
              ${workbench.filters.rider_states.map((item) => `<option value="${escapeHtml(item)}"${item === riderFilterState.state ? " selected" : ""}>${escapeHtml(displayRiderState(item))}</option>`).join("")}
            </select>
            <span id="riders-result-count" class="filter-count">${riders.length} / ${workbench.entities.riders.length} 名骑手</span>
          </div>
          <div class="operations-grid" data-density="summary-first">
            <div class="card" id="riders-capacity-panel" data-riders-surface="capacity-focus">
              <div class="card-head"><h3>优先可用骑手</h3><span>先看状态、负载和预计空闲</span></div>
              <div id="riders-capacity-list" class="card-body rider-focus-list">
                ${renderRiderFocusList(riders)}
              </div>
            </div>
            <aside class="card" id="rider-context-panel">
              ${renderRidersContext(riders)}
            </aside>
          </div>
          <section class="card rider-evidence-shell" id="rider-evidence-panel" data-evidence-role="secondary">
            <div class="card-head"><h3>骑手小地图核对</h3><span>位置、负载和任务链，仅作二级证据</span></div>
            <div id="rider-resource-board" class="rider-board">
              ${riders.slice(0, 8).map(renderRiderCard).join("")}
            </div>
          </section>
        </div>
      `;
    }

    function renderLiveMapLayer(frame, routes = mapRouteRows(frame), riders = riderPositionsForFrame(frame), orders = ordersForMap(frame)) {
      return `
        <div id="map-action-status" class="map-action-status" data-map-action="active">${renderMapActionStatus(frame, routes, riders, orders)}</div>
        <div class="map-mode-chip">${escapeHtml(inferenceModeLabels[inferenceState.mode])} / ${escapeHtml(frame.id)}</div>
        <div id="leaflet-live-map" class="leaflet-live-map" data-leaflet-map="live" data-tile-provider="${escapeHtml(workbench.map.tile_provider || liveTileLayer.id)}" aria-label="匿名无标签真实地图"></div>
        <div class="fallback-map-overlay" data-fallback-map="screen-coordinate" aria-hidden="true">
          ${renderMapRoutes(routes, riders)}
          ${renderHotspots()}
          ${renderMapDots("merchant", workbench.map.anchors.merchants.slice(0, 16), "position")}
          ${renderMapDots("rider", riders.slice(0, 14), "position")}
          ${renderMapDots("order", orders.slice(0, 22), "dropoff")}
        </div>
        ${renderMapLegend()}
      `;
    }

    function renderMapRoutes(routes, riders = []) {
      if (!routes.length) return "";
      const progressLines = activeProgressRoutes(routes, riders);
      return `
        <svg class="map-route" data-route-count="${routes.length}" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          ${routes.map((route) => {
            const points = route.polyline.map((point) => `${point.screen_x},${point.screen_y}`).join(" ");
            return `<polyline class="route-line" data-lane="${escapeHtml(route.renderLane || route.lane)}" data-order-ref="${escapeHtml(mapEntityLabel("order", {id: route.order_id}))}" data-rider-ref="${escapeHtml(mapEntityLabel("rider", {id: route.courier_id}))}" points="${escapeHtml(points)}"></polyline>`;
          }).join("")}
          ${progressLines.map((route) => {
            const points = route.progressPolyline.map((point) => `${point.screen_x},${point.screen_y}`).join(" ");
            return `<polyline class="route-line" data-lane="active-progress" data-order-ref="${escapeHtml(mapEntityLabel("order", {id: route.order_id}))}" data-rider-ref="${escapeHtml(mapEntityLabel("rider", {id: route.courier_id}))}" points="${escapeHtml(points)}"></polyline>`;
          }).join("")}
        </svg>
      `;
    }

    function activeMapRider(riders = []) {
      return riders.find((rider) => rider.motion === "moving") || null;
    }

    function activeProgressRoutes(routes = [], riders = []) {
      const movingByPair = new Map(riders.filter((rider) => rider.motion === "moving").map((rider) => [`${rider.id}:${rider.order_id}`, rider]));
      return routes
        .filter((route) => !["baseline", "previous"].includes(route.renderLane || route.lane))
        .map((route) => {
          const rider = movingByPair.get(`${route.courier_id}:${route.order_id}`);
          if (!rider) return null;
          const progressPolyline = progressPolylineForRoute(route, rider);
          return progressPolyline.length >= 2 ? {...route, progressPolyline} : null;
        })
        .filter(Boolean)
        .slice(0, 4);
    }

    function progressPolylineForRoute(route, rider) {
      const points = route.polyline || [];
      if (points.length < 2) return [];
      const progress = clamp(Number(rider.progress || 0), 0, 1);
      const keep = Math.max(1, Math.ceil((points.length - 1) * progress));
      const polyline = points.slice(0, keep + 1);
      if (rider.position) polyline.push(rider.position);
      return polyline;
    }

    function renderMapActionStatus(frame, routes = [], riders = [], orders = []) {
      if (!inferenceState.started) {
        return `<strong>等待开始推理</strong><span>点击开始后，订单、骑手、路线和优势指标会按全天时间自动推进。</span>`;
      }
      const moving = activeMapRider(riders);
      if (moving) {
        const orderLabel = moving.order_id ? mapEntityLabel("order", {id: moving.order_id}) : "当前订单";
        const riderLabel = mapEntityLabel("rider", moving);
        return `<strong>${escapeHtml(riderLabel)} 正在执行 ${escapeHtml(orderLabel)}</strong><span>路线进度 ${fmtNumber((moving.progress || 0) * 100, 0)}%，地图只突出我方动作和必要差异。</span>`;
      }
      const route = routes.find((item) => (item.renderLane || item.lane) === "ours") || routes[0];
      if (route) {
        return `<strong>本轮路线已接管</strong><span>${escapeHtml(mapEntityLabel("rider", {id: route.courier_id}))} -> ${escapeHtml(mapEntityLabel("order", {id: route.order_id}))}，等待下一次路线重算。</span>`;
      }
      return `<strong>等待首轮路线</strong><span>已释放 ${orders.length} 个地图订单点，系统正在等待可评分的派单窗口。</span>`;
    }

    function renderHotspots() {
      return workbench.map.hotspots.map((hotspot, index) => {
        const active = hotspot.start_s <= inferenceState.currentTimeS && inferenceState.currentTimeS <= hotspot.end_s;
        const label = mapEntityLabel("hotspot", hotspot, index);
        return `<div class="hotspot" data-active="${active}" data-map-ref="${escapeHtml(label)}" title="${escapeHtml(mapEntityTitle("hotspot", label, {phase: active ? "active" : "inactive"}))}" style="--x:${hotspot.center.screen_x};--y:${hotspot.center.screen_y};--severity:${hotspot.severity}"></div>`;
      }).join("");
    }

    function renderMapDots(kind, items, positionKey) {
      return items.map((item, index) => {
        const pos = item[positionKey];
        const release = kind === "order" && item.created_at_s >= inferenceState.currentTimeS - 900 ? "new" : "stable";
        const motion = kind === "rider" ? (item.motion || "snapshot") : "";
        const label = mapEntityLabel(kind, item, index);
        const showLabel = kind === "rider" || (kind === "order" && index < 4);
        return `<span class="map-dot" data-kind="${escapeHtml(kind)}" data-map-ref="${escapeHtml(label)}" data-map-label="${escapeHtml(label)}" data-show-label="${showLabel}" data-release="${escapeHtml(release)}" data-motion="${escapeHtml(motion)}" data-phase="${escapeHtml(item.phase || "")}" title="${escapeHtml(mapEntityTitle(kind, label, item))}" aria-label="${escapeHtml(mapEntityTitle(kind, label, item))}" style="--x:${pos.screen_x};--y:${pos.screen_y}"></span>`;
      }).join("");
    }

    function renderMapLegend() {
      const routeItems = [
        ["ours", "我方路线"],
        ["previous", "旧路线淡出"],
        ["baseline", "基线差异"],
        ["difference", "叠加差异"]
      ];
      const entityItems = [
        ["rider", "骑手"],
        ["merchant", "商家"],
        ["order", "订单"],
        ["hotspot", "热点"]
      ];
      return `
        <div class="map-legend">
          ${entityItems.map(([kind, label]) => `<span class="legend-item"><i class="legend-dot" data-kind="${escapeHtml(kind)}"></i>${escapeHtml(label)}</span>`).join("")}
          ${routeItems.map(([lane, label]) => `<span class="legend-item"><i class="legend-swatch" data-lane="${escapeHtml(lane)}"></i>${escapeHtml(label)}</span>`).join("")}
        </div>
      `;
    }

    function mapEntityLabel(kind, item = {}, index = 0) {
      const id = item.id || item.courier_id || item.order_id || item.merchant_id || "";
      const aliasBuckets = workbench.map.aliases || {};
      const bucketName = kind === "merchant" ? "merchants" : kind === "rider" ? "riders" : kind === "order" ? "orders" : "";
      if (item.map_label) return item.map_label;
      if (bucketName && aliasBuckets[bucketName] && aliasBuckets[bucketName][id]) return aliasBuckets[bucketName][id];
      const prefix = kind === "merchant" ? "M" : kind === "rider" ? "R" : kind === "order" ? "O" : "H";
      const width = kind === "order" ? 3 : 2;
      return `${prefix}-${String(index + 1).padStart(width, "0")}`;
    }

    function mapEntityTitle(kind, label, item = {}) {
      const kindLabel = {
        merchant: "商家",
        rider: "骑手",
        order: "订单",
        hotspot: "热点"
      }[kind] || "实体";
      const details = [];
      if (item.risk_level) details.push(`风险:${displayRisk(item.risk_level)}`);
      if (item.phase) details.push(displayRiderState(item.phase));
      return `${kindLabel} ${label}${details.length ? ` / ${details.join(" / ")}` : ""}`;
    }

    function queueLiveMapHydration(frame, routes, riders, orders) {
      const token = `${frame.id}:${Math.round(inferenceState.currentTimeS)}:${inferenceState.mode}`;
      liveMapHydrationToken = token;
      window.requestAnimationFrame(() => {
        if (liveMapHydrationToken === token) hydrateLiveMap(frame, routes, riders, orders);
      });
    }

    function destroyLiveMap() {
      liveMapHydrationToken = "";
      liveLeafletOverlayGroup = null;
      if (liveLeafletMap) {
        liveLeafletMap.remove();
        liveLeafletMap = null;
      }
    }

    function updateLiveLeafletOverlay(frame, routes, riders, orders) {
      const stage = document.getElementById("live-map-stage");
      if (!window.L || !stage || !liveLeafletMap || !liveLeafletOverlayGroup || stage.dataset.realMapStatus !== "leaflet") return false;
      try {
        stage.dataset.leafletRouteCount = String(routes.length);
        stage.dataset.leafletMarkerCount = String(workbench.map.anchors.merchants.slice(0, 16).length + riders.slice(0, 14).length + orders.slice(0, 22).length);
        const chip = stage.querySelector(".map-mode-chip");
        if (chip) chip.textContent = `${inferenceModeLabels[inferenceState.mode]} / ${frame.id}`;
        liveLeafletOverlayGroup.clearLayers();
        renderLeafletMapLayers(liveLeafletOverlayGroup, routes, riders, orders);
        return true;
      } catch (error) {
        console.warn("Live map overlay update fell back to rebuild", error);
        return false;
      }
    }

    function hydrateLiveMap(frame, routes, riders, orders) {
      const stage = document.getElementById("live-map-stage");
      const container = document.getElementById("leaflet-live-map");
      if (!stage || !container) return;
      if (!window.L) {
        stage.dataset.realMapStatus = "fallback";
        stage.dataset.leafletRouteCount = "0";
        stage.dataset.leafletMarkerCount = "0";
        return;
      }
      try {
        stage.dataset.realMapStatus = "loading";
        stage.dataset.leafletRouteCount = String(routes.length);
        stage.dataset.leafletMarkerCount = String(workbench.map.anchors.merchants.slice(0, 16).length + riders.slice(0, 14).length + orders.slice(0, 22).length);
        const map = window.L.map(container, {
          attributionControl: true,
          boxZoom: true,
          doubleClickZoom: true,
          preferCanvas: true,
          scrollWheelZoom: true,
          zoomControl: false
        });
        liveLeafletMap = map;
        window.L.control.zoom({ position: "bottomright" }).addTo(map);
        window.L.tileLayer(liveTileLayer.url, {
          attribution: liveTileLayer.attribution,
          maxZoom: 19,
          subdomains: liveTileLayer.subdomains
        }).addTo(map);
        const bounds = mapBounds();
        if (bounds) map.fitBounds(bounds, { animate: false, padding: [18, 18] });
        else map.setView(mapPoint(workbench.map.center), 14);
        liveLeafletOverlayGroup = window.L.layerGroup().addTo(map);
        renderLeafletMapLayers(liveLeafletOverlayGroup, routes, riders, orders);
        stage.dataset.realMapStatus = "leaflet";
        window.setTimeout(() => {
          if (liveLeafletMap === map && container.isConnected) map.invalidateSize(false);
        }, 0);
      } catch (error) {
        console.warn("Live map fell back to deterministic anonymous layer", error);
        destroyLiveMap();
        stage.dataset.realMapStatus = "fallback";
        stage.dataset.leafletRouteCount = "0";
        stage.dataset.leafletMarkerCount = "0";
      }
    }

    function renderLeafletMapLayers(layerGroup, routes, riders, orders) {
      renderLeafletHotspots(layerGroup);
      renderLeafletRoutes(layerGroup, routes, riders);
      renderLeafletMarkers(layerGroup, "merchant", workbench.map.anchors.merchants.slice(0, 16), "position");
      renderLeafletMarkers(layerGroup, "rider", riders.slice(0, 14), "position");
      renderLeafletMarkers(layerGroup, "order", orders.slice(0, 22), "dropoff");
    }

    function mapBounds() {
      if (!window.L || !workbench.map.bounds || workbench.map.bounds.length < 2) return null;
      return window.L.latLngBounds(workbench.map.bounds.map(mapPoint));
    }

    function mapPoint(point) {
      return [Number(point.lat), Number(point.lng)];
    }

    function renderLeafletHotspots(map) {
      workbench.map.hotspots.forEach((hotspot, index) => {
        const active = hotspot.start_s <= inferenceState.currentTimeS && inferenceState.currentTimeS <= hotspot.end_s;
        const label = mapEntityLabel("hotspot", hotspot, index);
        window.L.circle(mapPoint(hotspot.center), {
          radius: 230 + Number(hotspot.severity || 1) * 220,
          color: active ? "#b7791f" : "#94a3b8",
          fillColor: active ? "#b7791f" : "#94a3b8",
          fillOpacity: active ? .13 : .08,
          opacity: active ? .34 : .18,
          weight: 1
        }).bindTooltip(escapeHtml(mapEntityTitle("hotspot", label, {phase: active ? "active" : "inactive"})), { sticky: true }).addTo(map);
      });
    }

    function renderLeafletRoutes(map, routes, riders = []) {
      const progressRoutes = activeProgressRoutes(routes, riders);
      for (const route of routes) {
        const points = (route.polyline || []).map(mapPoint).filter(([lat, lng]) => Number.isFinite(lat) && Number.isFinite(lng));
        if (points.length < 2) continue;
        const lane = route.renderLane || route.lane;
        window.L.polyline(points, routeHaloStyle(lane)).addTo(map);
        window.L.polyline(points, routeStyle(lane)).bindTooltip(escapeHtml(routeTooltip(route)), { sticky: true }).addTo(map);
      }
      for (const route of progressRoutes) {
        const points = route.progressPolyline.map(mapPoint).filter(([lat, lng]) => Number.isFinite(lat) && Number.isFinite(lng));
        if (points.length < 2) continue;
        window.L.polyline(points, routeProgressStyle()).bindTooltip(escapeHtml(`当前执行 / ${routeTooltip(route)}`), { sticky: true }).addTo(map);
      }
    }

    function routeStyle(lane) {
      const styles = {
        ours: { color: "#0f766e", weight: 4, opacity: .78 },
        previous: { color: "#64748b", weight: 2, opacity: .28, dashArray: "3 8" },
        baseline: { color: "#b42318", weight: 3, opacity: .34, dashArray: "5 7" },
        difference: { color: "#b7791f", weight: 5, opacity: .82 }
      };
      return styles[lane] || styles.ours;
    }

    function routeHaloStyle(lane) {
      const style = routeStyle(lane);
      return {
        color: "#ffffff",
        weight: Number(style.weight || 3) + 5,
        opacity: lane === "previous" ? .18 : .62,
        dashArray: style.dashArray || null,
        interactive: false
      };
    }

    function routeProgressStyle() {
      return {
        color: "#059669",
        dashArray: "5 7",
        interactive: false,
        opacity: .94,
        weight: 6
      };
    }

    function routeTooltip(route) {
      const laneLabel = {
        ours: "我方路线",
        previous: "旧路线",
        baseline: "基线差异",
        difference: "叠加差异"
      }[route.renderLane || route.lane] || "路线";
      return `${laneLabel} / ${mapEntityLabel("rider", {id: route.courier_id})} -> ${mapEntityLabel("order", {id: route.order_id})}`;
    }

    function renderLeafletMarkers(map, kind, items, positionKey) {
      items.forEach((item, index) => {
        const pos = item[positionKey];
        if (!pos || !Number.isFinite(Number(pos.lat)) || !Number.isFinite(Number(pos.lng))) return;
        const label = mapEntityLabel(kind, item, index);
        const release = kind === "order" && item.created_at_s >= inferenceState.currentTimeS - 900 ? "new" : "stable";
        const motion = kind === "rider" ? (item.motion || "snapshot") : "";
        window.L.marker(mapPoint(pos), {
          icon: renderLeafletMarker(kind, label, release, motion, index),
          keyboard: false,
          zIndexOffset: kind === "rider" ? 500 : kind === "order" ? 300 : 100
        }).bindTooltip(escapeHtml(mapEntityTitle(kind, label, item)), { direction: "top", opacity: .92, sticky: true }).addTo(map);
      });
    }

    function renderLeafletMarker(kind, label, release, motion, index = 0) {
      const showLabel = kind === "rider" || (kind === "order" && index < 4);
      return window.L.divIcon({
        className: "leaflet-map-pin",
        html: `<span class="leaflet-map-pin-body" data-kind="${escapeHtml(kind)}" data-release="${escapeHtml(release)}" data-motion="${escapeHtml(motion)}"></span>${showLabel ? `<span class="leaflet-map-pin-label">${escapeHtml(label)}</span>` : ""}`,
        iconAnchor: [8, 8],
        iconSize: [16, 16]
      });
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
          ${renderScoreCard("空驶里程差异", fmtSavedDistance(score.deltas.empty_mileage_saved_km), "对比/叠加模式只强调差异路线", emptyTone, "metric-empty-mileage-delta")}
          ${renderScoreCard("收益/成本差异", `${fmtSigned(score.deltas.profit_delta_yuan, 1)} 元`, `收入 ${fmtSigned(score.deltas.revenue_delta_yuan, 1)} 元 / 成本节省 ${fmtNumber(score.deltas.money_saved_yuan, 1)} 元`, profitTone, "metric-profit-delta")}
        </div>
      `;
    }

    function renderMetricChip(metricId, label, value, detail) {
      return `<div class="metric-chip" id="metric-chip-${escapeHtml(metricId)}" data-metric="${escapeHtml(metricId)}"><span>${escapeHtml(label)}</span><b>${escapeHtml(value)}</b><span>${escapeHtml(detail)}</span></div>`;
    }

    function renderLiveCumulativeMetrics(score) {
      return [
        renderMetricChip("time-delta", "时间差异", `${fmtNumber(score.deltas.time_saved_min, 1)} 分钟`, `基线 ${fmtNumber(score.baseline.total_time_cost_min, 1)} / 我方 ${fmtNumber(score.ours.total_time_cost_min, 1)}`),
        renderMetricChip("money-delta", "金钱差异", `${fmtNumber(score.deltas.money_saved_yuan, 1)} 元`, `基线 ${fmtNumber(score.baseline.total_cost_yuan, 1)} / 我方 ${fmtNumber(score.ours.total_cost_yuan, 1)}`),
        renderMetricChip("timeout-delta", "超时单差异", fmtFewer(score.deltas.timeout_order_delta, "单"), `基线 ${score.baseline.late_orders} / 我方 ${score.ours.late_orders}`),
        renderMetricChip("empty-mileage-delta", "空驶里程差异", fmtSavedDistance(score.deltas.empty_mileage_saved_km), `总距离差异 ${fmtSigned(score.deltas.empty_mileage_saved_m, 0)} m`),
        renderMetricChip("profit-delta", "收益/成本差异", `${fmtSigned(score.deltas.profit_delta_yuan, 1)} 元`, `收益 ${fmtSigned(score.deltas.revenue_delta_yuan, 1)} / 成本 ${fmtNumber(score.deltas.money_saved_yuan, 1)}`)
      ].join("");
    }

    function actionSummary(actions, limit = 3) {
      if (!actions || !actions.length) return "暂无动作";
      const preview = actions.slice(0, limit).map((item) => {
        const eta = item.total_eta_min === undefined ? "" : ` / ${fmtNumber(item.total_eta_min, 1)}分钟`;
        return `${item.order_id}->${item.courier_id}${eta}`;
      }).join(", ");
      return actions.length > limit ? `${preview} +${actions.length - limit} 项` : preview;
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
      setText("decision-route-status", `${decision.trigger_time_label} / ${readableDecisionLabel(decision.id)}`);
      setText("decision-reasoning-phase", displayDemandPhase(decision.context.demand_phase));
      setText("decision-context-slice", `${displayDemandPhase(decision.context.demand_phase)}场景`);
      const reasoning = document.getElementById("decision-reasoning-canvas");
      if (reasoning) reasoning.innerHTML = renderDecisionReasoning(decision);
      const contextPane = document.getElementById("decision-context-pane");
      if (contextPane) contextPane.innerHTML = renderDecisionContext(decision);
    }

    function renderDecisionTimeline(activeId) {
      return workbench.decisions.map((item, index) => `
        <button class="timeline-item" data-decision-id="${escapeHtml(item.id)}" data-active="${item.id === activeId}">
          <strong>第 ${index + 1} 轮 / ${escapeHtml(item.trigger_time_label)}</strong>
          <span>${escapeHtml(displayTriggerReason(item.trigger_reason))}</span>
          <span class="timeline-meta">
            <em>${item.input_order_ids.length} 单</em>
            <em>${item.candidate_rider_ids.length} 名骑手</em>
            <em>${escapeHtml(displayDemandPhase(item.context.demand_phase))}</em>
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

    function readableDecisionLabel(decisionId) {
      const index = workbench.decisions.findIndex((item) => item.id === decisionId);
      return index >= 0 ? `第 ${index + 1} 轮` : "当前轮次";
    }

    function readableMemoryLabel(memoryId) {
      const index = workbench.memory.items.findIndex((item) => item.id === memoryId);
      if (index >= 0) return `记忆 ${String(index + 1).padStart(2, "0")}`;
      const text = String(memoryId || "");
      if (text.includes("recall")) return "召回记忆";
      if (text.includes("writeback")) return "回写记忆";
      if (text.includes("policy")) return "策略记忆";
      return "调度记忆";
    }

    function renderMemoryChipList(memoryIds, emptyLabel = "无回写记忆") {
      return renderChipList((memoryIds || []).map(readableMemoryLabel), emptyLabel);
    }

    function memoryReferenceText(memoryIds) {
      const values = (memoryIds || []).filter(Boolean);
      if (!values.length) return "无";
      return values.map(readableMemoryLabel).join("、");
    }

    function recalledCaseText(caseIds) {
      const count = (caseIds || []).filter(Boolean).length;
      return count ? `${count} 个相似场景` : "暂无召回样本";
    }

    function renderDecisionScoreRows(scores) {
      if (!scores.length) return `<p>等待评分</p>`;
      const maxScore = Math.max(...scores.map((item) => Number(item.score) || 0), 1);
      return scores.map((item) => {
        const normalized = clamp((Number(item.score) || 0) / maxScore, 0.04, 1);
        return `
          <div class="score-row" data-algorithm-id="${escapeHtml(item.algorithm_id)}">
            <b>${escapeHtml(candidateLabel(item.algorithm_id))}</b>
            <div>
              <div class="score-bar" style="--score:${normalized}"><span></span></div>
              <p>${escapeHtml(displayCandidateReason(item.reason))}</p>
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
          ? `预计 ${fmtNumber(item.total_eta_min, 1)} 分钟 / 成本 ${fmtNumber(item.expected_cost_yuan, 1)} 元 / 风险 ${fmtNumber(item.timeout_risk, 3)}`
          : displayActionReason(item.reason);
        return `
          <div class="action-card" data-action-kind="${escapeHtml(kind)}">
            <strong>${escapeHtml(item.order_id)} -> ${escapeHtml(item.courier_id)}</strong>
            <p>${escapeHtml(detail)}</p>
          </div>
        `;
      }).join("")}</div>`;
    }

    function decisionInputOrderIds(decision) {
      return (decision.input_orders || []).length ? decision.input_orders.map((item) => item.id) : (decision.input_order_ids || []);
    }

    function decisionCandidateRiderIds(decision) {
      return (decision.candidate_riders || []).length ? decision.candidate_riders.map((item) => item.id) : (decision.candidate_rider_ids || []);
    }

    function topDecisionScore(decision) {
      return [...(decision.scoring_process || [])].sort((left, right) => Number(right.score || 0) - Number(left.score || 0))[0] || null;
    }

    function decisionFilterSentence(decision) {
      const parts = (decision.filtering_process || []).map((stage) => `${displayStage(stage.stage)}后剩 ${stage.remaining}`);
      return parts.length ? parts.join("，") : "暂无过滤记录";
    }

    function decisionScoreSentence(decision) {
      const scores = decision.scoring_process || [];
      if (!scores.length) return "当前轮还没有评分结果。";
      const best = topDecisionScore(decision);
      const compared = scores.map((item) => `${candidateLabel(item.algorithm_id)} ${fmtNumber(item.score, 3)}`).join("，");
      return `综合比较时间、成本、风险和可用性：${compared}。本轮保留 ${candidateLabel(best.algorithm_id)}。`;
    }

    function decisionActionSentence(actions, limit = 3) {
      if (!actions || !actions.length) return "暂无动作";
      const text = actions.slice(0, limit).map((item) => {
        const eta = item.total_eta_min === undefined ? "" : `，预计 ${fmtNumber(item.total_eta_min, 1)} 分钟`;
        return `${item.order_id} 派给 ${item.courier_id}${eta}`;
      }).join("；");
      return actions.length > limit ? `${text}；另有 ${actions.length - limit} 个动作` : text;
    }

    function decisionAdvantageHeadline(decision) {
      const result = decision.round_result || {};
      return `本轮节省 ${fmtNumber(result.time_saved_min || 0, 1)} 分钟`;
    }

    function renderDecisionAdvantageHero(decision) {
      const result = decision.round_result || {};
      return `
        <section class="decision-advantage-hero" data-reasoning-surface="advantage-first">
          <div class="decision-advantage-copy">
            <span class="reason-kicker">本轮结论</span>
            <h3>${escapeHtml(decisionAdvantageHeadline(decision))}</h3>
            <p>先解释为什么我方方案优于基线：候选策略经过场景识别、可行性校验、风险评分和结果回写，最终保留能降低时间、成本和超时风险的动作。</p>
          </div>
          <div class="decision-advantage-metrics">
            ${renderMetricChip("reason-time-advantage", "时间优势", `${fmtNumber(result.time_saved_min || 0, 1)} 分钟`, "相对最近距离基线")}
            ${renderMetricChip("reason-cost-advantage", "成本优势", `${fmtNumber(result.cost_saved_yuan || 0, 1)} 元`, "兼顾风险后的成本")}
            ${renderMetricChip("reason-risk-advantage", "超时风险变化", fmtSigned(result.timeout_risk_delta || 0, 3), "数值越低越好")}
            ${renderMetricChip("reason-actions", "最终动作", `${decision.final_actions.length}`, `${decision.abandoned_actions.length} 个被放弃`)}
          </div>
        </section>
      `;
    }

    function renderDecisionStep(stepId, index, title, status, body, metaItems = []) {
      return `
        <article class="decision-step-card" id="${escapeHtml(stepId)}" data-decision-step="${escapeHtml(stepId)}" data-step-status="${escapeHtml(status)}">
          <div class="decision-step-index">${index}</div>
          <div class="decision-step-body">
            <div class="decision-step-top"><strong>${escapeHtml(title)}</strong><span>${escapeHtml(status === "final" ? "已输出" : "已完成")}</span></div>
            <p>${body}</p>
            ${renderChipList(metaItems, "暂无补充信息")}
          </div>
        </article>
      `;
    }

    function renderDecisionStepFlow(decision) {
      const inputOrderIds = decisionInputOrderIds(decision);
      const candidateRiderIds = decisionCandidateRiderIds(decision);
      const bestScore = topDecisionScore(decision);
      return `
        <section id="decision-step-flow" class="decision-step-flow" data-reasoning-pattern="plain-six-step">
          ${renderDecisionStep("decision-trigger-time", 1, "为什么触发这一轮", "done", `${escapeHtml(decision.trigger_time_label)}，${escapeHtml(displayTriggerReason(decision.trigger_reason))}`, [readableDecisionLabel(decision.id), displayDemandPhase(decision.context.demand_phase)])}
          ${renderDecisionStep("decision-input-orders", 2, "看哪些订单", "done", `本轮把 ${inputOrderIds.length} 个已经进入推理窗口的订单放进同一批判断，不让单个订单孤立决策。`, inputOrderIds.slice(0, 8))}
          ${renderDecisionStep("decision-candidate-riders", 3, "候选骑手怎么选", "done", `系统只从在线、同区域或可及时赶到的骑手里选候选，共 ${candidateRiderIds.length} 名。`, candidateRiderIds.slice(0, 8))}
          ${renderDecisionStep("decision-filtering-process", 4, "先过滤不可行方案", "done", `先按时间窗口、区域班次、拥堵和承诺送达时间过滤，${escapeHtml(decisionFilterSentence(decision))}。`, (decision.filtering_process || []).map((stage) => `${displayStage(stage.stage)} ${stage.remaining}`))}
          ${renderDecisionStep("decision-scoring-process", 5, "再给可行方案打分", "done", `${escapeHtml(decisionScoreSentence(decision))}`, bestScore ? [candidateLabel(bestScore.algorithm_id), `评分 ${fmtNumber(bestScore.score, 3)}`, `风险 ${fmtNumber(bestScore.risk_score, 3)}`] : ["等待评分"])}
          ${renderDecisionStep("decision-final-actions", 6, "输出派单并回写记忆", "final", `最终输出 ${decision.final_actions.length} 个派单动作，放弃 ${decision.abandoned_actions.length} 个基线动作；本轮节省 ${fmtNumber(decision.round_result.time_saved_min, 1)} 分钟，回写 ${decision.result_writeback.writeback_count} 条有效记忆。`, [`成本优势 ${fmtNumber(decision.round_result.cost_saved_yuan, 1)} 元`, `风险变化 ${fmtSigned(decision.round_result.timeout_risk_delta, 3)}`])}
        </section>
      `;
    }

    function candidateStatus(score, index, scores) {
      const best = Math.max(...scores.map((item) => Number(item.score) || 0), 0);
      if ((Number(score.score) || 0) >= best && best > 0) return "selected";
      return index === 0 ? "rejected" : "rejected";
    }

    function candidateLabel(algorithmId) {
      if (algorithmId === "nearest_greedy") return "最近距离基线";
      if (algorithmId === "cost_greedy") return "成本优先基线";
      if (algorithmId === "risk_aware_greedy") return "风险感知基线";
      if (algorithmId === "min_cost_matching") return "最小成本匹配";
      if (algorithmId === "flow_mcf") return "流式最小成本方案";
      if (algorithmId === "autosolver_agent") return "我方智能调度方案";
      return algorithmId.replaceAll("_", " ");
    }

    function candidateRejectReason(score) {
      if (score.algorithm_id === "nearest_greedy") return "路线和距离局部最短，但没有同时保护承诺时效、骑手负载和后续风险。";
      return "未成为当前最高综合评分候选。";
    }

    function renderDecisionPlanComparison(decision) {
      const scores = decision.scoring_process || [];
      const acceptedScore = topDecisionScore(decision);
      return `
        <section id="decision-plan-comparison" class="decision-plan-board" data-reasoning-pattern="accepted-and-rejected">
          <article id="decision-accepted-plan" class="decision-plan-card" data-plan="accepted">
            <div class="decision-plan-top">
              <strong>采纳方案</strong>
              <span class="decision-plan-status">${escapeHtml(acceptedScore ? candidateLabel(acceptedScore.algorithm_id) : "等待评分")}</span>
            </div>
            <p>${escapeHtml(acceptedScore ? displayCandidateReason(acceptedScore.reason) : "等待评分结果。")}</p>
            <p>${escapeHtml(decisionActionSentence(decision.final_actions, 4))}</p>
            <div class="context-metric-grid">
              ${renderMetricChip("accepted-score", "综合评分", acceptedScore ? fmtNumber(acceptedScore.score, 3) : "-", "分数高者保留")}
              ${renderMetricChip("accepted-risk", "超时风险", acceptedScore ? fmtNumber(acceptedScore.risk_score, 3) : "-", "风险越低越好")}
              ${renderMetricChip("accepted-time", "时间优势", `${fmtNumber(decision.round_result.time_saved_min, 1)} 分钟`, "相对基线")}
              ${renderMetricChip("accepted-cost", "成本优势", `${fmtNumber(decision.round_result.cost_saved_yuan, 1)} 元`, "本轮")}
            </div>
          </article>
          <article id="decision-rejected-plan" class="decision-plan-card" data-plan="rejected">
            <div class="decision-plan-top">
              <strong>放弃方案</strong>
              <span class="decision-plan-status">基线备选</span>
            </div>
            <p>${escapeHtml(decision.abandoned_actions.length ? "以下动作来自最近距离基线，但在综合时效、成本和风险评分中被淘汰。" : "本轮没有需要放弃的基线动作。")}</p>
            ${renderDecisionActions(decision.abandoned_actions.slice(0, 4), "abandoned")}
          </article>
          <article id="decision-score-comparison" class="decision-plan-card" data-plan="scores">
            <div class="decision-plan-top">
              <strong>评分对比</strong>
              <span class="decision-plan-status">${scores.length} 个方案</span>
            </div>
            ${renderDecisionScoreRows(scores)}
          </article>
        </section>
      `;
    }

    function renderDecisionEvidence(decision) {
      const inputOrderIds = decisionInputOrderIds(decision);
      const candidateRiderIds = decisionCandidateRiderIds(decision);
      return `
        <section id="decision-proof-panel" class="decision-proof-grid" data-reasoning-surface="required-fields">
          ${renderDecisionStage("decision-trigger-reason", "触发时间与原因", decision.trigger_time_label, `<p>${escapeHtml(displayTriggerReason(decision.trigger_reason))}</p>`)}
          ${renderDecisionStage("decision-input-orders", "输入订单集合", `${inputOrderIds.length} 单`, renderChipList(inputOrderIds.slice(0, 20), "当前轮无释放订单"))}
          ${renderDecisionStage("decision-candidate-riders", "候选骑手集合", `${candidateRiderIds.length} 名骑手`, renderChipList(candidateRiderIds.slice(0, 20), "暂无候选骑手"))}
          ${renderDecisionStage("decision-filtering-process", "过滤过程", `${(decision.filtering_process || []).length} 步`, `<p>${escapeHtml(decisionFilterSentence(decision))}</p>`)}
          ${renderDecisionStage("decision-scoring-process", "评分过程", `${(decision.scoring_process || []).length} 个方案`, `<p>${escapeHtml(decisionScoreSentence(decision))}</p>`)}
          ${renderDecisionStage("decision-abandoned-actions", "被放弃动作", `${decision.abandoned_actions.length} 个备选`, renderDecisionActions(decision.abandoned_actions.slice(0, 4), "abandoned"))}
          ${renderDecisionStage("decision-round-result", "本轮结果", `节省 ${fmtNumber(decision.round_result.time_saved_min, 1)} 分钟`, `<p>${escapeHtml(displayDecisionSummary(decision.round_result.summary))}</p>`)}
          ${renderDecisionStage("decision-result-writeback", "结果回写", `${decision.result_writeback.writeback_count} 次回写`, `<p>${escapeHtml(displayDecisionSummary(decision.result_writeback.summary))}</p>${renderMemoryChipList(decision.result_writeback.memory_event_ids, "无回写记忆")}`)}
        </section>
      `;
    }

    function renderDecisionReasoning(decision) {
      return `
        ${renderDecisionAdvantageHero(decision)}
        ${renderDecisionStepFlow(decision)}
        ${renderDecisionPlanComparison(decision)}
        ${renderDecisionEvidence(decision)}
      `;
    }

    function renderDecisionContext(decision) {
      const inputOrderIds = decisionInputOrderIds(decision);
      const candidateRiderIds = decisionCandidateRiderIds(decision);
      return `
        <div class="list-item" id="decision-context-input">
          <strong>这轮发生在什么场景</strong>
          <p>${escapeHtml(decision.trigger_time_label)} / ${escapeHtml(displayDemandPhase(decision.context.demand_phase))} / ${escapeHtml(displayWeather(decision.context.weather))} / 拥堵 ${fmtNumber(decision.context.congestion_level, 2)} / 在线供给 ${decision.context.courier_supply} 名</p>
          <p>冲击事件：${decision.context.shock_ids.length ? decision.context.shock_ids.map((item) => escapeHtml(displayShock(item))).join(", ") : "无"}</p>
        </div>
        <div class="list-item" id="decision-context-orders">
          <strong>输入订单</strong>
          <p>${inputOrderIds.length} 单进入本轮推理。</p>
          ${renderChipList(inputOrderIds.slice(0, 8), "暂无订单")}
        </div>
        <div class="list-item" id="decision-context-riders">
          <strong>候选骑手</strong>
          <p>${candidateRiderIds.length} 名骑手进入候选集合。</p>
          ${renderChipList(candidateRiderIds.slice(0, 8), "暂无骑手")}
        </div>
        <div class="list-item" id="decision-output-result">
          <strong>输出结果</strong>
          <p>${escapeHtml(displayDecisionSummary(decision.round_result.summary))}</p>
        </div>
        <div class="context-metric-grid">
          ${renderMetricChip("decision-time-saved", "时间收益", `${fmtNumber(decision.round_result.time_saved_min, 1)} 分钟`, "本轮")}
          ${renderMetricChip("decision-cost-saved", "成本收益", `${fmtNumber(decision.round_result.cost_saved_yuan, 1)} 元`, "本轮")}
          ${renderMetricChip("decision-risk-delta", "风险变化", fmtSigned(decision.round_result.timeout_risk_delta, 3), "超时风险")}
          ${renderMetricChip("decision-extra-delivered", "额外交付", `${decision.round_result.extra_delivered_orders} 单`, "相对基线")}
        </div>
        <div class="list-item" id="decision-round-summary">
          <strong>最终动作</strong>
          <p>${escapeHtml(decisionActionSentence(decision.final_actions, 5))}</p>
        </div>
        <div class="list-item" id="decision-abandoned-summary">
          <strong>被放弃动作</strong>
          <p>输入 ${decision.input_order_ids.length} 单，候选 ${decision.candidate_rider_ids.length} 名骑手，最终 ${decision.final_actions.length} 个动作，放弃 ${decision.abandoned_actions.length} 个基线动作。</p>
        </div>
        <div class="list-item" id="decision-writeback-summary">
          <strong>结果回写</strong>
          <p>${decision.result_writeback.writeback_count} 次有效回写，形成 ${decision.result_writeback.memory_event_ids.length} 条可召回记忆。</p>
        </div>
      `;
    }

    function renderRoundSummary(decision, compact = false) {
      const finalActions = actionSummary(decision.final_actions, 3);
      const abandonedActions = actionSummary(decision.abandoned_actions, 3);
      const filterSummary = decision.filtering_process.slice(0, 3).map((stage) => `${displayStage(stage.stage)}: ${stage.remaining}`).join(" / ");
      const scoreSummary = decision.scoring_process.slice(0, 3).map((item) => `${candidateLabel(item.algorithm_id)} ${fmtNumber(item.score, 3)}`).join(" / ") || "等待评分";
      const writebackIds = memoryReferenceText(decision.result_writeback.memory_event_ids.slice(0, 4));
      if (compact) {
        return `
          <div class="round-summary-grid" data-decision-id="${escapeHtml(decision.id)}" data-density="compact">
            <div class="list-item" id="round-trigger"><strong>触发原因</strong><p>${escapeHtml(displayTriggerReason(decision.trigger_reason))}</p></div>
            <div class="list-item" id="round-final-actions"><strong>最终动作</strong><p>${escapeHtml(finalActions)}</p></div>
            <div class="list-item" id="round-abandoned-actions"><strong>被放弃动作</strong><p>${escapeHtml(abandonedActions)}</p></div>
            <div class="list-item" id="round-writeback"><strong>结果回写</strong><p>${decision.result_writeback.writeback_count} 次回写 / ${escapeHtml(writebackIds)}</p></div>
            <div class="list-item" id="round-metric-impact"><strong>本轮结果</strong><p>${escapeHtml(displayDecisionSummary(decision.round_result.summary))}；节省 ${fmtNumber(decision.round_result.time_saved_min, 1)} 分钟，成本优势 ${fmtNumber(decision.round_result.cost_saved_yuan, 1)} 元。</p></div>
          </div>
        `;
      }
      return `
        <div class="round-summary-grid" data-decision-id="${escapeHtml(decision.id)}">
          <div class="list-item" id="round-trigger"><strong>触发原因</strong><p>${escapeHtml(displayTriggerReason(decision.trigger_reason))}</p></div>
          <div class="list-item" id="round-input-context"><strong>输入上下文</strong><p>${decision.input_order_ids.length} 单 / ${decision.candidate_rider_ids.length} 名骑手 / ${escapeHtml(displayWeather(decision.context.weather))} / 拥堵 ${fmtNumber(decision.context.congestion_level, 2)}</p></div>
          <div class="list-item" id="round-filtering"><strong>过滤过程</strong><p>${escapeHtml(filterSummary)}</p></div>
          <div class="list-item" id="round-scoring"><strong>评分过程</strong><p>${escapeHtml(scoreSummary)}</p></div>
          <div class="list-item" id="round-final-actions"><strong>最终动作</strong><p>${escapeHtml(finalActions)}</p></div>
          <div class="list-item" id="round-abandoned-actions"><strong>被放弃动作</strong><p>${escapeHtml(abandonedActions)}</p></div>
          <div class="list-item" id="round-writeback"><strong>结果回写</strong><p>${decision.result_writeback.writeback_count} 次回写 / ${escapeHtml(writebackIds)}</p></div>
          <div class="list-item" id="round-metric-impact"><strong>本轮结果</strong><p>${escapeHtml(displayDecisionSummary(decision.round_result.summary))}；节省 ${fmtNumber(decision.round_result.time_saved_min, 1)} 分钟，节省 ${fmtNumber(decision.round_result.cost_saved_yuan, 1)} 元，风险差异 ${fmtSigned(decision.round_result.timeout_risk_delta, 3)}。</p></div>
        </div>
      `;
    }

    function renderEventItem(event) {
      const meta = eventMeta[event.type] || { label: event.type, family: "decision" };
      const typeClass = eventTypeClasses[event.type] || "event-type-other";
      const detailParts = [];
      if (event.order_id) detailParts.push(`订单 ${event.order_id}`);
      if (event.order_ids) detailParts.push(`${event.order_ids.length} 单`);
      if (event.courier_ids) detailParts.push(`${event.courier_ids.length} 名骑手`);
      if (event.business_area) detailParts.push(event.business_area);
      if (event.memory_id) detailParts.push(`记忆 ${event.memory_id}`);
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
      return `<div class="stage-row"><b>${escapeHtml(label)}</b><span>${escapeHtml(summary || "待处理")}</span><em>${escapeHtml(count)}</em></div>`;
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

    function renderMemoryOverview(stats, system = {}) {
      const total = system.memory_count ?? stats.total;
      const avgConfidence = system.avg_confidence ?? stats.avgConfidence;
      const totalRecalls = system.recall_count ?? stats.totalRecalls;
      const latestHit = system.latest_hit_time_label || stats.latestHitLabel;
      return [
        renderMetricChip("memory-total", "长期记忆总量", `${total}`, "来自全天推演回放"),
        renderMetricChip("memory-confidence", "平均置信度", fmtNumber(avgConfidence, 2), "全局 / 画像 / 召回 / 反馈"),
        renderMetricChip("memory-recalls", "累计召回", `${totalRecalls}`, "评分前命中的历史经验"),
        renderMetricChip("memory-latest-hit", "最近命中", latestHit, `${system.linked_decision_count ?? stats.linkedDecisionCount} 个关联决策`)
      ].join("");
    }

    function renderMemoryLayerCard(layer) {
      const confidence = Number(layer.avg_confidence || 0);
      return `
        <article class="memory-layer-card" data-memory-layer="${escapeHtml(layer.id)}">
          <div class="memory-layer-top">
            <strong>${escapeHtml(layer.label)}</strong>
            <span class="memory-scope">${escapeHtml(displayMemoryScope(layer.scope))}</span>
          </div>
          <div class="memory-layer-meta">
            <span>${escapeHtml(layer.memory_count)} 条记忆</span>
            <span>${escapeHtml(layer.recall_count)} 次召回</span>
            <span>${escapeHtml(layer.latest_hit_time_label)}</span>
          </div>
          <p>${escapeHtml(layer.summary)}</p>
          <div class="memory-meter" style="--confidence:${clamp(confidence, 0, 1)}"><span></span></div>
          <p><b>用于调度：</b>${escapeHtml(layer.dispatch_use)}</p>
          <div class="memory-effect-line"><span>${escapeHtml(layer.effect)}</span></div>
        </article>
      `;
    }

    function renderMemoryProfile(profile) {
      return `
        <article class="memory-profile" data-memory-profile="${escapeHtml(profile.id)}" data-profile-type="${escapeHtml(profile.profile_type)}">
          <div class="memory-profile-top">
            <strong>${escapeHtml(profile.label)}</strong>
            <span class="memory-profile-type">${escapeHtml(displayProfileType(profile.profile_type))}</span>
          </div>
          <p>${escapeHtml(displayMemoryText(profile.context))}</p>
          <p><b>策略摘要：</b>${escapeHtml(displayMemoryText(profile.strategy))}</p>
          <div class="memory-profile-meta">
            <span>置信度 ${fmtNumber(profile.confidence || 0, 2)}</span>
            <span>最近命中 ${escapeHtml(profile.latest_hit_time_label)}</span>
          </div>
          <p>${escapeHtml(displayMemoryText(profile.dispatch_effect))}</p>
        </article>
      `;
    }

    function memoryItemsByIds(itemIds, byId, limit = 1) {
      return (itemIds || [])
        .map((id) => byId[id])
        .filter(Boolean)
        .slice(0, limit);
    }

    function renderMemoryRecallStep(step, byId, index) {
      const evidence = memoryItemsByIds(step.item_ids, byId, 1)[0];
      return `
        <article class="memory-flow-step" data-memory-chain-step="${escapeHtml(step.id)}">
          <div class="memory-flow-top">
            <strong>${escapeHtml(step.label)}</strong>
            <span class="memory-flow-index">${index + 1}</span>
          </div>
          <p>${escapeHtml(displayMemoryStepSummary(step))}</p>
          <p>${escapeHtml(displayMemoryText(step.evidence))}</p>
          ${renderMemoryEvidenceItem(evidence)}
        </article>
      `;
    }

    function renderMemoryWritebackStep(step, byId, index) {
      const evidence = memoryItemsByIds(step.item_ids, byId, 1)[0];
      const sectionId = step.id.replace("-memory", "");
      return `
        <article class="memory-flow-step" data-memory-section="${escapeHtml(sectionId)}" data-memory-loop-step="${escapeHtml(step.id)}">
          <div class="memory-flow-top">
            <strong>${escapeHtml(step.label)}</strong>
            <span class="memory-flow-index">${index + 1}</span>
          </div>
          <p>${escapeHtml(displayMemoryStepSummary(step))}</p>
          ${renderMemoryEvidenceItem(evidence)}
        </article>
      `;
    }

    function renderMemoryEvidenceItem(item) {
      if (!item) {
        return `<div class="memory-evidence"><p>等待推理产生可验证的记忆证据。</p></div>`;
      }
      return `
        <div class="memory-evidence" data-memory-id="${escapeHtml(item.id)}" data-memory-stage="${escapeHtml(item.stage)}" data-memory-scope="${escapeHtml(item.memory_scope || "")}">
          <div class="memory-evidence-head">
            <strong>${escapeHtml(item.latest_hit_time_label)} / ${escapeHtml(readableMemoryLabel(item.id))}</strong>
            <span>${escapeHtml(displayMemoryChannel(item.formation_channel || item.event_type))}</span>
          </div>
          <div class="memory-field-grid">
            ${renderMemoryField("触发场景", displayMemoryScenario(item.trigger_scenario))}
            ${renderMemoryField("上下文摘要", displayMemoryText(item.context_summary))}
            ${renderMemoryField("策略摘要", displayMemoryText(item.strategy_summary))}
            ${renderMemoryField("决策结果", displayDecisionSummary(item.decision_result))}
            ${renderMemoryField("效果反馈", displayMemoryText(item.effect_feedback))}
            ${renderMemoryField("最近命中时间", item.latest_hit_time_label)}
          </div>
          <div class="context-metric-grid">
            ${renderMetricChip(`${item.id}-confidence`, "置信度", fmtNumber(item.confidence, 2), `更新前 ${fmtNumber(item.confidence_before, 2)} / 更新后 ${fmtNumber(item.confidence_after, 2)}`)}
            ${renderMetricChip(`${item.id}-recall`, "召回次数", `${item.recall_count}`, recalledCaseText(item.recalled_case_ids))}
          </div>
        </div>
      `;
    }

    function renderMemoryRecallCard(item) {
      if (!item) return "";
      return `
        <div class="recall-card" data-memory-id="${escapeHtml(item.id)}" data-memory-recall="active">
          <strong>${escapeHtml(item.latest_hit_time_label)} / ${escapeHtml(displayMemoryScenario(item.trigger_scenario))}</strong>
          <p>${escapeHtml(displayMemoryText(item.strategy_summary))}</p>
          <div class="memory-meter" style="--confidence:${clamp(item.confidence, 0, 1)}"><span></span></div>
          <p>关联${escapeHtml(readableDecisionLabel(item.linked_decision_id))} / 召回 ${item.recall_count} 次</p>
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
            <strong>${escapeHtml(item.latest_hit_time_label)} / ${escapeHtml(readableMemoryLabel(item.id))}</strong>
            <span class="memory-stage" data-stage="${escapeHtml(item.stage)}">${escapeHtml(displayMemoryStage(item.stage))}</span>
          </div>
          <div class="memory-field-grid">
            ${renderMemoryField("触发场景", displayMemoryScenario(item.trigger_scenario))}
            ${renderMemoryField("上下文摘要", displayMemoryText(item.context_summary))}
            ${renderMemoryField("策略摘要", displayMemoryText(item.strategy_summary))}
            ${renderMemoryField("决策结果", displayDecisionSummary(item.decision_result))}
            ${renderMemoryField("效果反馈", displayMemoryText(item.effect_feedback))}
            ${renderMemoryField("最近命中时间", item.latest_hit_time_label)}
          </div>
          <div class="context-metric-grid">
            ${renderMetricChip(`${item.id}-confidence`, "置信度", fmtNumber(item.confidence, 2), `更新前 ${fmtNumber(item.confidence_before, 2)} / 更新后 ${fmtNumber(item.confidence_after, 2)}`)}
            ${renderMetricChip(`${item.id}-recall`, "召回次数", `${item.recall_count}`, recalledCaseText(item.recalled_case_ids))}
          </div>
          <div class="chip-list">
            <span class="data-chip">关联${escapeHtml(readableDecisionLabel(item.linked_decision_id))}</span>
            ${item.tags.map((tag) => `<span class="data-chip">${escapeHtml(displayTag(tag))}</span>`).join("")}
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
        renderMetricChip("orders-visible", "当前可见", `${orders.length}`, `全天 ${workbench.entities.orders.length} 单`),
        renderMetricChip("orders-entered", "已进入推理", `${entered}`, "按下单时间释放"),
        renderMetricChip("orders-high-risk", "高风险", `${highRisk}`, "优先保护承诺送达"),
        renderMetricChip("orders-improved", "已见改善", `${improved}/${assigned}`, "我方预计更快")
      ].join("");
    }

    function orderEtaAdvantage(order) {
      const ours = Number(order.our_result?.eta_min);
      const baseline = Number(order.baseline_result?.eta_min);
      if (!Number.isFinite(ours) || !Number.isFinite(baseline)) return 0;
      return baseline - ours;
    }

    function orderFocusScore(order) {
      const riskWeight = order.risk_level === "high" ? 100 : order.risk_level === "medium" ? 45 : 0;
      const enteredWeight = order.entered_inference ? 20 : 0;
      return riskWeight + enteredWeight + Math.max(0, orderEtaAdvantage(order));
    }

    function renderOrderFocusList(orders) {
      const focusOrders = [...orders]
        .sort((left, right) => orderFocusScore(right) - orderFocusScore(left) || left.created_at_s - right.created_at_s)
        .slice(0, 6);
      if (!focusOrders.length) {
        return `<div class="list-item"><strong>当前筛选无订单</strong><p>调整时间段、商圈、状态或风险筛选。</p></div>`;
      }
      return focusOrders.map((order) => {
        const etaGain = orderEtaAdvantage(order);
        const advantage = etaGain > 0 ? `我方预计快 ${fmtNumber(etaGain, 1)} 分钟` : "等待对比结果";
        return `
          <article class="order-focus-card" data-order-focus="${escapeHtml(order.id)}" data-risk="${escapeHtml(order.risk_level)}">
            <div class="focus-card-top">
              <strong>${escapeHtml(order.id)}</strong>
              <span class="focus-badge">${escapeHtml(displayRisk(order.risk_level))}</span>
            </div>
            <p>${escapeHtml(order.merchant_label)} / ${escapeHtml(order.business_area)}</p>
            <p>${escapeHtml(order.created_at_label)} 下单，${escapeHtml(order.promised_at_label)} 前送达。</p>
            <p>${escapeHtml(advantage)}；${order.entered_inference ? "已进入推理" : "等待按时间释放"}。</p>
            <div class="chip-list">
              <span class="data-chip">基线 ${escapeHtml(displayStatus(order.baseline_result?.state || "scheduled"))}</span>
              <span class="data-chip">我方 ${escapeHtml(displayStatus(order.our_result?.state || "scheduled"))}</span>
            </div>
          </article>
        `;
      }).join("");
    }

    function countBy(items, keyFn) {
      return items.reduce((counts, item) => {
        const key = keyFn(item) || "-";
        counts[key] = (counts[key] || 0) + 1;
        return counts;
      }, {});
    }

    function renderCountChips(counts, limit = 6, labelFn = null) {
      const rows = Object.entries(counts).sort((left, right) => right[1] - left[1]).slice(0, limit);
      if (!rows.length) return `<p>当前筛选无数据</p>`;
      return `<div class="chip-list">${rows.map(([key, value]) => `<span class="data-chip">${escapeHtml(labelFn ? labelFn(key) : key)} ${value}</span>`).join("")}</div>`;
    }

    function renderOrderTimeLane(orders) {
      const maxCount = Math.max(...workbench.filters.order_time_bands.map((band) => orders.filter((order) => order.created_at_s >= band.start_s && order.created_at_s <= band.end_s).length), 1);
      return `
        <div class="time-lane">
          ${workbench.filters.order_time_bands.map((band) => {
            const count = orders.filter((order) => order.created_at_s >= band.start_s && order.created_at_s <= band.end_s).length;
            return `
              <div class="time-lane-item" data-order-time-band="${escapeHtml(band.id)}">
                <b>${escapeHtml(displayDemandPhase(band.id))}</b>
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
        <div class="card-head"><h3>需求概览</h3><span id="orders-context-count">${orders.length} 单可见</span></div>
        <div class="card-body order-context-list">
          <div class="list-item" id="orders-time-distribution"><strong>释放节奏</strong>${renderOrderTimeLane(orders)}</div>
          <div class="list-item" id="orders-area-distribution"><strong>商圈热度</strong>${renderCountChips(areaCounts)}</div>
          <div class="list-item" id="orders-risk-distribution"><strong>风险结构</strong>${renderCountChips(riskCounts, 6, displayRisk)}</div>
          <div class="list-item" id="orders-status-distribution"><strong>推理进度</strong>${renderCountChips(statusCounts, 6, displayStatus)}<p>订单全集只用于解释推理，不作为数据维护主叙事。</p></div>
        </div>
      `;
    }

    function renderAlgorithmResult(result) {
      if (!result || result.state !== "assigned") {
        return `<div class="result-pair"><b>未释放</b><span>${escapeHtml(candidateLabel(result?.algorithm_id || "-"))}</span></div>`;
      }
      return `
        <div class="result-pair">
          <b>${escapeHtml(result.courier_id)} / ${fmtNumber(result.eta_min, 1)} 分钟</b>
          <span>${fmtNumber(result.expected_cost_yuan, 1)} 元 / 风险 ${fmtNumber(result.timeout_risk, 3)}</span>
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
      const priority = document.getElementById("orders-priority-list");
      if (priority) priority.innerHTML = renderOrderFocusList(orders);
      const body = document.getElementById("orders-table-body");
      if (body) body.innerHTML = orders.map(renderOrderRow).join("") || `<tr><td colspan="7">当前筛选无订单，调整时间段、商圈、状态或风险。</td></tr>`;
      const context = document.getElementById("orders-context-panel");
      if (context) context.innerHTML = renderOrdersContext(orders);
      setText("orders-result-count", `${orders.length} / ${workbench.entities.orders.length} 单`);
    }

    function renderCoverageCards(counts, total, limit = 5) {
      const rows = Object.entries(counts).sort((left, right) => right[1] - left[1]).slice(0, limit);
      if (!rows.length) return `<p>当前筛选无区域供给。</p>`;
      const max = Math.max(...rows.map((row) => row[1]), 1);
      return `
        <div class="coverage-grid">
          ${rows.map(([area, value]) => `
            <div class="coverage-card" data-coverage-area="${escapeHtml(area)}">
              <b>${escapeHtml(area)}</b>
              <div class="coverage-bar" style="--coverage:${value / max}"><span></span></div>
              <p>${value} 名骑手 / 可见供给 ${fmtNumber(value / Math.max(1, total) * 100, 1)}%</p>
            </div>
          `).join("")}
        </div>
      `;
    }

    function renderRidersOverview(riders) {
      const busy = riders.filter((rider) => rider.online_state === "busy").length;
      const available = riders.filter((rider) => rider.online_state === "available").length;
      const ending = riders.filter((rider) => rider.online_state === "ending_shift").length;
      const avgLoad = riders.length ? riders.reduce((sum, rider) => sum + rider.current_load / Math.max(1, rider.capacity), 0) / riders.length : 0;
      return [
        renderMetricChip("riders-visible", "当前可见", `${riders.length}`, `全天 ${workbench.entities.riders.length} 名`),
        renderMetricChip("riders-available", "可接单", `${available}`, "可进入候选集合"),
        renderMetricChip("riders-busy", "配送中", `${busy}`, `${ending} 名临近下线`),
        renderMetricChip("riders-avg-load", "平均负载", fmtNumber(avgLoad, 2), "当前负载 / 容量")
      ].join("");
    }

    function riderFocusScore(rider) {
      const stateWeight = rider.online_state === "available" ? 70 : rider.online_state === "busy" ? 42 : rider.online_state === "ending_shift" ? 12 : 0;
      const loadRatio = rider.current_load / Math.max(1, rider.capacity);
      return stateWeight + (1 - loadRatio) * 30 + Math.min(12, rider.task_chain_size);
    }

    function renderRiderFocusList(riders) {
      const focusRiders = [...riders]
        .sort((left, right) => riderFocusScore(right) - riderFocusScore(left) || left.id.localeCompare(right.id))
        .slice(0, 6);
      if (!focusRiders.length) {
        return `<div class="list-item"><strong>当前筛选无骑手</strong><p>调整区域或在线状态筛选。</p></div>`;
      }
      return focusRiders.map((rider) => {
        const loadRatio = clamp(rider.current_load / Math.max(1, rider.capacity), 0, 1);
        return `
          <article class="rider-focus-card" data-rider-focus="${escapeHtml(rider.id)}" data-state="${escapeHtml(rider.online_state)}">
            <div class="focus-card-top">
              <strong>骑手 ${escapeHtml(rider.id)}</strong>
              <span class="focus-badge">${escapeHtml(displayRiderState(rider.online_state))}</span>
            </div>
            <div class="rider-load" style="--load:${loadRatio}"><span></span></div>
            <p>${escapeHtml(rider.business_area)} / 班次 ${escapeHtml(rider.shift_label)}</p>
            <p>当前负载 ${rider.current_load}/${rider.capacity}；${escapeHtml(rider.estimated_free_at_label)} 预计空闲；任务链 ${rider.task_chain_size} 单。</p>
          </article>
        `;
      }).join("");
    }

    function renderRidersContext(riders) {
      const stateCounts = countBy(riders, (rider) => rider.online_state);
      const areaCounts = countBy(riders, (rider) => rider.business_area);
      const topChains = [...riders].sort((left, right) => right.task_chain_size - left.task_chain_size).slice(0, 5);
      return `
        <div class="card-head"><h3>区域覆盖与班次压力</h3><span id="riders-context-count">${riders.length} 名可见</span></div>
        <div class="card-body rider-context-list">
          <div class="list-item" id="rider-state-distribution"><strong>在线状态</strong>${renderCountChips(stateCounts, 6, displayRiderState)}</div>
          <div class="list-item" id="rider-area-distribution"><strong>区域覆盖</strong>${renderCoverageCards(areaCounts, riders.length)}</div>
          <div class="list-item" id="rider-chain-focus">
            <strong>任务链较长</strong>
            ${topChains.length ? topChains.map((rider) => `<p>骑手 ${escapeHtml(rider.id)} / ${rider.task_chain_size} 单任务 / ${escapeHtml(rider.estimated_free_at_label)} 空闲</p>`).join("") : "<p>当前筛选无骑手</p>"}
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
      const focus = document.getElementById("riders-capacity-list");
      if (focus) focus.innerHTML = renderRiderFocusList(riders);
      const board = document.getElementById("rider-resource-board");
      if (board) board.innerHTML = riders.slice(0, 8).map(renderRiderCard).join("") || `<div class="list-item"><strong>当前筛选无骑手</strong><p>调整区域或在线状态筛选。</p></div>`;
      const context = document.getElementById("rider-context-panel");
      if (context) context.innerHTML = renderRidersContext(riders);
      setText("riders-result-count", `${riders.length} / ${workbench.entities.riders.length} 名骑手`);
    }

    function renderOrderRow(order) {
      return `
        <tr data-order-id="${escapeHtml(order.id)}" data-order-status="${escapeHtml(order.status)}" data-order-risk="${escapeHtml(order.risk_level)}" data-order-area="${escapeHtml(order.business_area)}">
          <td>${escapeHtml(order.id)}</td>
          <td>${escapeHtml(order.merchant_label)}<br><span>${escapeHtml(order.business_area)}</span></td>
          <td>${escapeHtml(order.created_at_label)} 下单<br><span>${escapeHtml(order.promised_at_label)} 承诺送达</span></td>
          <td><span class="badge" data-state="${escapeHtml(order.status)}">${escapeHtml(displayStatus(order.status))}</span><br><span class="badge" data-risk="${escapeHtml(order.risk_level)}">${escapeHtml(displayRisk(order.risk_level))}</span></td>
          <td>${order.entered_inference ? "已进入" : "等待释放"}</td>
          <td>${renderAlgorithmResult(order.baseline_result)}</td>
          <td>${renderAlgorithmResult(order.our_result)}</td>
        </tr>
      `;
    }

    function renderRiderMiniMap(rider) {
      const linkedOrders = rider.mini_map.linked_order_ids.map((orderId) => orderIndex[orderId]).filter(Boolean).slice(0, 4);
      const riderMapLabel = mapEntityLabel("rider", rider);
      return `
        <div class="mini-map" data-rider-mini-map="${escapeHtml(rider.id)}">
          <span class="map-dot" data-kind="home" title="驻点" style="--x:${rider.mini_map.home.screen_x};--y:${rider.mini_map.home.screen_y}"></span>
          <span class="map-dot" data-kind="rider" data-map-ref="${escapeHtml(riderMapLabel)}" title="${escapeHtml(mapEntityTitle("rider", riderMapLabel, {phase: rider.online_state}))}" style="--x:${rider.position.screen_x};--y:${rider.position.screen_y}"></span>
          ${linkedOrders.map((order) => {
            const orderMapLabel = mapEntityLabel("order", order);
            return `<span class="map-dot" data-kind="linked-order" data-map-ref="${escapeHtml(orderMapLabel)}" title="${escapeHtml(mapEntityTitle("order", orderMapLabel, {risk_level: order.risk_level}))}" style="--x:${order.dropoff_position.screen_x};--y:${order.dropoff_position.screen_y}"></span>`;
          }).join("")}
        </div>
      `;
    }

    function renderRiderCard(rider) {
      const loadRatio = clamp(rider.current_load / Math.max(1, rider.capacity), 0, 1);
      return `
        <article class="card rider-card" data-rider-id="${escapeHtml(rider.id)}" data-state="${escapeHtml(rider.online_state)}" data-area="${escapeHtml(rider.business_area)}">
          <div class="card-head"><h3>骑手 ${escapeHtml(rider.id)}</h3><span>${escapeHtml(displayRiderState(rider.online_state))} / ${escapeHtml(rider.business_area)}</span></div>
          <div class="card-body">
            ${renderRiderMiniMap(rider)}
            <div class="rider-load" style="--load:${loadRatio}"><span></span></div>
            <div class="compact-list">
              <div class="list-item"><strong>班次与负载</strong><p>${escapeHtml(rider.shift_label)} / ${rider.current_load}/${rider.capacity} / ${escapeHtml(rider.estimated_free_at_label)} 空闲</p></div>
              <div class="list-item"><strong>当前任务链 ${rider.task_chain_size} 单</strong><p>${rider.task_chain.slice(0, 5).map((item) => `${item.order_id}(${fmtNumber(item.eta_min, 1)}分钟)`).join(", ") || "暂无任务"}</p></div>
              <div class="list-item"><strong>历史表现摘要</strong><p>${escapeHtml(displayRiderPerformance(rider.performance.summary))} / 接单意愿 ${fmtNumber(rider.performance.willingness, 2)}</p></div>
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
      renderDecisionAdvantageHero,
      renderDecisionStepFlow,
      renderDecisionPlanComparison,
      hydrateDecisionPage,
      selectDecisionRound,
      renderMemoryPage,
      memoryStats,
      memoryItemsForSection,
      renderMemoryLayerCard,
      renderMemoryProfile,
      renderMemoryRecallStep,
      renderMemoryWritebackStep,
      renderMemoryEvidenceItem,
      renderMemoryRecallCard,
      renderMemoryItem,
      renderOrdersPage,
      hydrateOrdersPage,
      updateOrdersView,
      filteredOrders,
      orderFilterState,
      renderOrderFocusList,
      renderOrdersOverview,
      renderOrdersContext,
      renderRidersPage,
      hydrateRidersPage,
      updateRidersView,
      filteredRiders,
      riderFilterState,
      renderCoverageCards,
      renderRiderFocusList,
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
