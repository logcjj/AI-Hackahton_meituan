from __future__ import annotations

import argparse
import json
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from web_agent_demo.dispatch_story_v3 import build_dispatch_story_v3, build_placeholder_story_v3
from web_agent_demo.server import list_cases, run_case_agent


def build_dispatch_payload_v3(case_id: str, budget_s: float = 10.0) -> dict[str, object]:
    report = run_case_agent(case_id, budget_s=budget_s)
    return {"status": "ok", "report": report, "story": build_dispatch_story_v3(report)}


def render_dispatch_index_v3() -> str:
    placeholder = json.dumps(build_placeholder_story_v3(), ensure_ascii=False)
    template = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AutoSolver Agent 即时履约智能调度指挥舱</title>
  <style>
    :root {
      --bg: #03101c;
      --panel: rgba(6, 25, 38, .86);
      --panel2: rgba(8, 35, 52, .74);
      --line: rgba(77, 217, 255, .22);
      --line2: rgba(22, 255, 210, .32);
      --text: #ecfbff;
      --muted: #8fb7c3;
      --cyan: #19ead2;
      --blue: #36b8ff;
      --yellow: #ffd02f;
      --orange: #ff7a32;
      --green: #35f29a;
      --red: #ff4f52;
      --shadow: 0 28px 70px rgba(0, 0, 0, .42);
      --mono: "SFMono-Regular", "Cascadia Code", Consolas, monospace;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      color: var(--text);
      font-family: "Avenir Next", "PingFang SC", "Hiragino Sans GB", sans-serif;
      background:
        radial-gradient(circle at 12% 8%, rgba(25, 234, 210, .14), transparent 24rem),
        radial-gradient(circle at 82% 10%, rgba(255, 122, 50, .14), transparent 22rem),
        linear-gradient(135deg, #020914 0%, #061a2b 42%, #03111f 100%);
      overflow-x: hidden;
    }
    body:before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image:
        linear-gradient(rgba(54,184,255,.06) 1px, transparent 1px),
        linear-gradient(90deg, rgba(54,184,255,.05) 1px, transparent 1px);
      background-size: 38px 38px;
      mask-image: linear-gradient(to bottom, black, transparent 86%);
    }
    #app-shell {
      width: min(1840px, calc(100vw - 24px));
      min-height: 100vh;
      margin: 0 auto;
      padding: 14px 0 22px;
      position: relative;
      z-index: 1;
    }
    .card {
      background: linear-gradient(180deg, rgba(10, 35, 54, .88), rgba(4, 19, 31, .82));
      border: 1px solid var(--line);
      border-radius: 14px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(18px);
    }
    .topbar {
      display: grid;
      grid-template-columns: 570px 1fr 360px;
      gap: 12px;
      align-items: stretch;
      margin-bottom: 12px;
    }
    .brand {
      display: grid;
      grid-template-columns: 78px 1fr;
      gap: 14px;
      align-items: center;
      padding: 14px;
      background: transparent;
      border: 0;
      box-shadow: none;
    }
    .logo-mark {
      width: 76px;
      height: 76px;
      border-radius: 50%;
      border: 2px solid var(--yellow);
      display: grid;
      place-items: center;
      color: var(--green);
      font-weight: 1000;
      font-size: 50px;
      line-height: 1;
      background: radial-gradient(circle, rgba(25,234,210,.16), rgba(0,0,0,.18));
    }
    h1 {
      margin: 2px 0 7px;
      font-size: 34px;
      line-height: 1.05;
      letter-spacing: -.055em;
    }
    h1 span { color: var(--yellow); }
    .subtitle {
      margin: 0;
      color: #9eeaf0;
      font-size: 15px;
      letter-spacing: .02em;
    }
    .status-strip {
      display: grid;
      grid-template-columns: repeat(2, 1fr) 2.2fr;
      gap: 12px;
    }
    .status-card {
      padding: 14px 18px;
      min-height: 90px;
    }
    .status-card small {
      color: var(--muted);
      display: block;
      margin-bottom: 8px;
      font-size: 13px;
    }
    .status-card strong {
      color: var(--cyan);
      font-size: 22px;
      font-family: var(--mono);
    }
    #scene-intelligence {
      padding: 10px 14px;
    }
    .scene-title {
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 7px;
    }
    .feature-row {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
    }
    .feature {
      min-height: 58px;
      border: 1px solid var(--line);
      border-radius: 13px;
      display: grid;
      grid-template-columns: 44px 1fr;
      align-items: center;
      padding: 8px;
      background: rgba(0,0,0,.2);
    }
    .feature-icon {
      width: 34px;
      height: 34px;
      border-radius: 50%;
      border: 2px solid currentColor;
      display: grid;
      place-items: center;
      font-weight: 900;
    }
    .feature b { display: block; font-size: 14px; }
    .feature span { color: var(--muted); font-size: 12px; }
    .controls {
      padding: 12px;
      display: grid;
      gap: 9px;
    }
    .control-row {
      display: grid;
      grid-template-columns: 1fr 78px;
      gap: 8px;
    }
    select, input, button {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: rgba(0,0,0,.28);
      color: var(--text);
      padding: 10px 11px;
      font-size: 14px;
      outline: none;
    }
    button {
      border: 0;
      cursor: pointer;
      color: #02120e;
      font-weight: 950;
      background: linear-gradient(135deg, #36f2a2, #0f8f62);
      box-shadow: 0 16px 36px rgba(53,242,154,.22);
    }
    button.secondary {
      color: var(--text);
      background: linear-gradient(135deg, rgba(54,184,255,.36), rgba(54,184,255,.12));
      border: 1px solid var(--line);
      box-shadow: none;
    }
    button:disabled { opacity: .55; cursor: wait; }
    #run-status {
      color: var(--yellow);
      font-weight: 900;
      min-height: 20px;
    }
    .metric-strip {
      display: grid;
      grid-template-columns: repeat(6, 1fr);
      gap: 0;
      margin-bottom: 12px;
      overflow: hidden;
    }
    .metric {
      padding: 14px 20px;
      min-height: 112px;
      border-right: 1px solid rgba(77,217,255,.14);
      background: rgba(4, 18, 30, .62);
    }
    .metric:last-child { border-right: 0; }
    .metric small {
      display: block;
      color: var(--muted);
      margin-bottom: 6px;
    }
    .metric b {
      display: block;
      font-size: 34px;
      letter-spacing: -.05em;
      color: #dffeff;
    }
    .metric em {
      color: var(--green);
      font-style: normal;
      font-size: 13px;
    }
    .main-grid {
      display: grid;
      grid-template-columns: 280px minmax(760px, 1fr) 420px;
      gap: 12px;
      align-items: stretch;
    }
    .side-panel { padding: 12px; }
    h2 {
      margin: 0 0 10px;
      color: #c6fdff;
      font-size: 17px;
      letter-spacing: -.025em;
    }
    #scenario-rail {
      display: grid;
      gap: 9px;
      margin-bottom: 12px;
    }
    .scenario-card {
      display: grid;
      grid-template-columns: 38px 1fr;
      gap: 10px;
      align-items: center;
      min-height: 66px;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: rgba(255,255,255,.035);
    }
    .scenario-card.active {
      border-color: var(--yellow);
      background: linear-gradient(90deg, rgba(255,208,47,.12), rgba(0,0,0,.08));
    }
    .scenario-rank {
      width: 34px;
      height: 34px;
      border-radius: 10px;
      display: grid;
      place-items: center;
      color: var(--yellow);
      border: 1px solid rgba(255,208,47,.48);
      font-family: var(--mono);
      font-weight: 900;
    }
    .scenario-card b { display: block; font-size: 15px; }
    .scenario-card small { color: var(--muted); line-height: 1.35; }
    #risk-portrait, #strategy-policy {
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 10px;
      margin-top: 10px;
      background: rgba(0,0,0,.15);
    }
    .risk-line {
      display: flex;
      justify-content: space-between;
      gap: 8px;
      padding: 5px 0;
      color: var(--muted);
      font-size: 13px;
    }
    .risk-line strong { color: var(--orange); }
    .map-panel {
      padding: 12px;
      min-width: 0;
    }
    .map-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 8px;
    }
    .legend {
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
      color: var(--muted);
      font-size: 13px;
    }
    .legend span:before {
      content: "";
      width: 9px;
      height: 9px;
      border-radius: 50%;
      background: currentColor;
      display: inline-block;
      margin-right: 6px;
    }
    .map-wrap {
      height: 510px;
      border: 1px solid var(--line);
      border-radius: 12px;
      overflow: hidden;
      position: relative;
      background:
        radial-gradient(circle at 58% 34%, rgba(255,208,47,.15), transparent 13rem),
        radial-gradient(circle at 76% 74%, rgba(25,234,210,.12), transparent 14rem),
        linear-gradient(145deg, rgba(8,34,56,.95), rgba(2,12,24,.98));
    }
    .mapbox-like-grid:before {
      content: "";
      position: absolute;
      inset: 0;
      background-image:
        linear-gradient(24deg, transparent 47%, rgba(54,184,255,.16) 49%, transparent 51%),
        linear-gradient(154deg, transparent 48%, rgba(255,255,255,.09) 50%, transparent 52%),
        linear-gradient(90deg, rgba(54,184,255,.05) 1px, transparent 1px),
        linear-gradient(rgba(54,184,255,.05) 1px, transparent 1px);
      background-size: 150px 92px, 130px 104px, 42px 42px, 42px 42px;
      opacity: .7;
    }
    .map-tools {
      position: absolute;
      left: 12px;
      bottom: 52px;
      display: grid;
      gap: 7px;
      z-index: 2;
    }
    .map-tool {
      width: 34px;
      height: 34px;
      border: 1px solid var(--line);
      display: grid;
      place-items: center;
      border-radius: 8px;
      background: rgba(0,0,0,.36);
      color: var(--text);
      font-family: var(--mono);
    }
    #operation-map {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      z-index: 1;
    }
    .edge {
      fill: none;
      stroke-width: 2.2;
      stroke-dasharray: 7 6;
      opacity: .9;
      animation: flow 2.4s linear infinite;
    }
    .edge.allocated_plan {
      stroke-width: 3.1;
      stroke-dasharray: 1 0;
      filter: drop-shadow(0 0 6px rgba(25,234,210,.8));
    }
    @keyframes flow { to { stroke-dashoffset: -26; } }
    .node { cursor: pointer; }
    .node circle { filter: drop-shadow(0 0 7px currentColor); }
    .node text {
      fill: var(--text);
      paint-order: stroke;
      stroke: rgba(0,0,0,.86);
      stroke-width: .7px;
      font-size: 2.15px;
      font-weight: 900;
      pointer-events: none;
    }
    .node .sub {
      fill: #aee7ef;
      font-size: 1.65px;
      stroke-width: .45px;
      font-weight: 700;
    }
    .callout {
      position: absolute;
      right: 280px;
      top: 168px;
      z-index: 2;
      width: 210px;
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 10px;
      background: rgba(3,16,28,.78);
      color: var(--muted);
      font-size: 13px;
      line-height: 1.55;
    }
    .callout b { color: var(--text); }
    .decision-panel {
      padding: 12px;
      display: grid;
      gap: 9px;
    }
    .decision-card {
      border: 1px solid var(--line);
      border-radius: 10px;
      background: rgba(255,255,255,.035);
      padding: 10px;
    }
    .decision-card h3 {
      margin: 0 0 8px;
      font-size: 16px;
    }
    .kv-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 7px;
    }
    .kv {
      padding: 8px;
      border-radius: 8px;
      background: rgba(0,0,0,.18);
      border: 1px solid rgba(77,217,255,.16);
      color: var(--muted);
      font-size: 12px;
    }
    .kv b {
      display: block;
      color: var(--text);
      font-family: var(--mono);
      font-size: 13px;
      margin-top: 3px;
    }
    .courier-list {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 8px;
    }
    .courier {
      border: 1px solid var(--line2);
      border-radius: 10px;
      padding: 9px;
      background: rgba(25,234,210,.07);
      font-size: 12px;
      color: var(--muted);
    }
    .courier b { display: block; color: var(--text); margin-bottom: 5px; }
    .reason-list {
      margin: 0;
      padding-left: 18px;
      color: var(--muted);
      line-height: 1.6;
      font-size: 13px;
    }
    .plan-line {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      color: var(--muted);
      padding: 7px 0;
      border-bottom: 1px solid rgba(77,217,255,.12);
      font-size: 13px;
    }
    .plan-line b { color: var(--red); }
    .bottom-grid {
      display: grid;
      grid-template-columns: 1.22fr .78fr .92fr 1.05fr;
      gap: 12px;
      margin-top: 12px;
    }
    .bottom-card { padding: 12px; min-height: 174px; }
    #workflow-strip {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 8px;
    }
    .flow-step {
      border-right: 1px solid rgba(77,217,255,.14);
      min-height: 112px;
      padding: 8px;
      text-align: center;
      color: var(--muted);
    }
    .flow-step:last-child { border-right: 0; }
    .flow-icon {
      width: 34px;
      height: 34px;
      border: 1px solid var(--line2);
      border-radius: 50%;
      margin: 0 auto 7px;
      display: grid;
      place-items: center;
      color: var(--cyan);
      font-family: var(--mono);
      font-weight: 900;
    }
    .flow-step b { display: block; color: var(--text); margin-bottom: 4px; }
    .flow-step small { display: block; line-height: 1.35; }
    .eval-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
    }
    .eval-card {
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 10px;
      background: rgba(0,0,0,.15);
      color: var(--muted);
      font-size: 12px;
    }
    .eval-card.hit {
      border-color: rgba(53,242,154,.68);
      background: rgba(53,242,154,.08);
    }
    .eval-card b { color: var(--text); display: block; font-size: 15px; margin-bottom: 5px; }
    .data-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
      color: var(--muted);
    }
    .data-table th, .data-table td {
      padding: 6px;
      border: 1px solid rgba(77,217,255,.12);
      text-align: left;
    }
    .data-table th {
      color: var(--text);
      background: rgba(255,255,255,.035);
    }
    .data-table td:nth-child(3), .data-table td:nth-child(4) { color: var(--green); }
    .memory-list {
      display: grid;
      gap: 6px;
    }
    .memory-item {
      display: grid;
      grid-template-columns: 44px 44px 1fr;
      gap: 6px;
      align-items: center;
      color: var(--muted);
      font-size: 12px;
    }
    .badge {
      border-radius: 6px;
      padding: 3px 5px;
      text-align: center;
      font-weight: 900;
      color: #03110e;
      background: var(--green);
    }
    .badge.fail { background: var(--red); color: #fff; }
    #commercial-roi {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
    }
    .roi-box {
      border: 1px solid var(--line2);
      border-radius: 10px;
      padding: 11px;
      background: rgba(25,234,210,.07);
      color: var(--muted);
      min-height: 70px;
    }
    .roi-box b {
      display: block;
      color: var(--green);
      font-size: 24px;
      letter-spacing: -.04em;
      margin-top: 4px;
    }
    .boundary {
      margin-top: 12px;
      padding: 10px 12px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.5;
    }
    @media (max-width: 1350px) {
      .topbar, .main-grid, .bottom-grid { grid-template-columns: 1fr; }
      .metric-strip { grid-template-columns: repeat(2, 1fr); }
      .feature-row, #workflow-strip, .eval-grid, #commercial-roi { grid-template-columns: 1fr; }
      .map-wrap { height: 520px; }
    }
  </style>
</head>
<body>
<main id="app-shell">
  <section class="topbar">
    <div class="brand">
      <div class="logo-mark">A</div>
      <div>
        <h1><span>AutoSolver</span> Agent<br>即时履约智能调度指挥舱</h1>
        <p class="subtitle" id="brand-subtitle">10 秒内生成高可靠派单方案，降低无人接单风险与履约成本</p>
      </div>
    </div>
    <div class="status-strip">
      <div class="status-card card"><small>系统状态</small><strong id="system-status">调度运行中</strong></div>
      <div class="status-card card"><small>已运行</small><strong id="elapsed-time">00:00:07</strong></div>
      <div class="card" id="scene-intelligence"></div>
    </div>
    <div class="controls card">
      <div class="control-row">
        <select id="case-select"></select>
        <input id="budget" value="10" inputmode="decimal">
      </div>
      <button id="run-button">开始推理并刷新指挥舱</button>
      <button id="reload-button" class="secondary">刷新用例列表</button>
      <div id="run-status">首屏默认展示</div>
    </div>
  </section>

  <section class="metric-strip card" id="metric-strip"></section>

  <section class="main-grid">
    <aside class="side-panel card">
      <h2>AI 场景识别</h2>
      <div id="scenario-rail"></div>
      <h2>场景风险画像</h2>
      <div id="risk-portrait"></div>
      <div id="strategy-policy"></div>
    </aside>

    <section class="map-panel card">
      <div class="map-head">
        <h2>调度可视化地图</h2>
        <div class="legend" id="map-legend"></div>
      </div>
      <div class="map-wrap mapbox-like-grid">
        <svg id="operation-map" viewBox="0 0 100 100" role="img" aria-label="operation dispatch map"></svg>
        <div class="map-tools">
          <div class="map-tool">□</div>
          <div class="map-tool">◇</div>
          <div class="map-tool">＋</div>
          <div class="map-tool">－</div>
        </div>
        <div class="callout" id="map-callout"></div>
      </div>
    </section>

    <aside class="decision-panel card">
      <h2>决策解释</h2>
      <div id="decision-panel"></div>
    </aside>
  </section>

  <section class="bottom-grid">
    <section class="bottom-card card">
      <h2>Agent 工作流程</h2>
      <div id="workflow-strip"></div>
    </section>
    <section class="bottom-card card">
      <h2>候选方案评估</h2>
      <div id="plan-evaluation"></div>
    </section>
    <section class="bottom-card card">
      <h2>策略记忆库</h2>
      <div id="strategy-memory"></div>
    </section>
    <section class="bottom-card card">
      <h2>商业价值 ROI 模拟器</h2>
      <div id="commercial-roi"></div>
    </section>
  </section>

  <section class="bottom-card card" style="margin-top:12px">
    <h2>Baseline vs AutoSolver 对比</h2>
    <div id="baseline-table"></div>
  </section>

  <section class="boundary card" id="data-boundary"></section>
</main>

<script>
const DEFAULT_STORY = __DEFAULT_STORY__;
const $ = (id) => document.getElementById(id);
let currentStory = DEFAULT_STORY;

function safe(value) {
  return String(value ?? '').replace(/[&<>"']/g, (ch) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;', "'":'&#39;'}[ch]));
}

function toneColor(node) {
  if (node.type === 'order_high_risk') return '#ff7a32';
  if (node.type === 'order_normal') return '#ffd02f';
  if (node.tone === 'green') return '#35f29a';
  return '#19ead2';
}

function nodeById(story, id) {
  return story.operation_map.nodes.find((node) => node.id === id);
}

function renderScene(story) {
  const center = story.command_center;
  $('brand-subtitle').textContent = center.subtitle;
  $('system-status').textContent = center.status;
  $('elapsed-time').textContent = center.elapsed;
  $('scene-intelligence').innerHTML = `
    <div class="scene-title">当前场景特征（AI 自动判断）</div>
    <div class="feature-row">
      ${center.scene_features.map((item) => `
        <div class="feature" style="color:${item.tone === 'green' ? 'var(--green)' : item.tone === 'orange' ? 'var(--orange)' : 'var(--yellow)'}">
          <div class="feature-icon">${safe(item.label.slice(0, 1))}</div>
          <div><b>${safe(item.label)}</b><span>${safe(item.delta)}</span></div>
        </div>
      `).join('')}
    </div>
  `;
}

function renderMetrics(story) {
  $('metric-strip').innerHTML = story.metric_strip.map((item) => `
    <div class="metric">
      <small>${safe(item.label)}</small>
      <b>${safe(item.value)}</b>
      <em>${safe(item.trend)}</em>
    </div>
  `).join('');
}

function renderScenarioRail(story) {
  const judgement = story.ai_scene_judgement;
  $('scenario-rail').innerHTML = judgement.cards.map((card, index) => `
    <div class="scenario-card ${index === 0 ? 'active' : ''}">
      <div class="scenario-rank">${safe(card.rank)}</div>
      <div><b>${safe(card.label)}</b><small>${safe(card.summary)} · ${safe(card.impact)}</small></div>
    </div>
  `).join('');
  $('risk-portrait').innerHTML = judgement.risk_portrait.map((item) => `
    <div class="risk-line"><span>${safe(item.label)}</span><strong>${safe(item.level)}</strong></div>
  `).join('');
  $('strategy-policy').innerHTML = `
    <h2 style="margin-top:0">推荐 Agent 策略</h2>
    <p style="margin:0;color:var(--muted);line-height:1.55">${safe(judgement.recommended_policy)}</p>
  `;
}

function edgePath(a, b, index) {
  const bend = index % 2 === 0 ? -10 : 10;
  const midX = (a.x + b.x) / 2 + bend;
  const midY = (a.y + b.y) / 2 - 8;
  return `M ${a.x} ${a.y} Q ${midX} ${midY} ${b.x} ${b.y}`;
}

function renderMap(story) {
  const edges = story.operation_map.edges.map((edge, index) => {
    const source = nodeById(story, edge.source);
    const target = nodeById(story, edge.target);
    if (!source || !target) return '';
    const color = edge.type === 'allocated_plan' ? '#19ead2' : '#ffd02f';
    return `<path class="edge ${safe(edge.type)}" d="${edgePath(source, target, index)}" stroke="${color}" data-edge="${safe(edge.id)}"></path>`;
  }).join('');
  const nodes = story.operation_map.nodes.map((node) => {
    const color = toneColor(node);
    const radius = node.type === 'courier' ? 2.25 : 2.75;
    const sub = node.type === 'courier' ? `w=${node.willingness}` : `${node.orders}单`;
    return `
      <g class="node" style="color:${color}" data-node="${safe(node.id)}">
        <circle cx="${node.x}" cy="${node.y}" r="${radius}" fill="${color}" stroke="rgba(255,255,255,.82)" stroke-width=".52"></circle>
        <text x="${node.x + 3.2}" y="${node.y + .7}">${safe(node.type === 'courier' ? node.label.replace('R-', '') : node.label.replace('订单组 ', ''))}</text>
        <text class="sub" x="${node.x + 3.2}" y="${node.y + 3.05}">${safe(sub)}</text>
      </g>
    `;
  }).join('');
  $('operation-map').innerHTML = edges + nodes;
  $('map-legend').innerHTML = story.operation_map.legend.map((item) => `<span>${safe(item.label)}</span>`).join('');
  const focus = story.operation_map.focus;
  $('map-callout').innerHTML = `<b>${safe(focus.title)}</b><br>风险：${safe(focus.risk)}<br>候选方案：3 个`;
}

function renderDecision(story) {
  const decision = story.decision_panel;
  $('decision-panel').innerHTML = `
    <div class="decision-card">
      <h3>任务组 ${safe(decision.selected_order_group.id)} <span style="color:var(--red);font-size:12px">${safe(decision.selected_order_group.risk)}</span></h3>
      <div class="kv-grid">
        ${Object.entries(decision.selected_order_group).filter(([key]) => key !== 'id' && key !== 'risk').map(([key, value]) => `<div class="kv">${safe(key)}<b>${safe(value)}</b></div>`).join('')}
      </div>
    </div>
    <div class="decision-card">
      <h3>选择的骑手</h3>
      <div class="courier-list">
        ${decision.selected_couriers.map((item) => `<div class="courier"><b>${safe(item.id)}</b>接单意愿 ${safe(item.willingness)}<br>距离 ${safe(item.distance_km)}<br>score ${safe(item.score)}</div>`).join('')}
      </div>
    </div>
    <div class="decision-card">
      <h3>决策原因</h3>
      <ul class="reason-list">${decision.decision_reason.map((item) => `<li>${safe(item)}</li>`).join('')}</ul>
    </div>
    <div class="decision-card">
      <h3>未采用的方案</h3>
      ${decision.rejected_plans.map((item) => `<div class="plan-line"><span>${safe(item.name)} · ${safe(item.reason)}</span><b>${safe(item.status)}</b></div>`).join('')}
    </div>
  `;
}

function renderWorkflow(story) {
  $('workflow-strip').innerHTML = story.agent_workflow.map((item) => `
    <div class="flow-step">
      <div class="flow-icon">${safe(item.step)}</div>
      <b>${safe(item.title)}</b>
      <small>${safe(item.desc)}</small>
      <small style="color:${item.status === '运行中' ? 'var(--yellow)' : 'var(--green)'}">${safe(item.status)}</small>
    </div>
  `).join('');
}

function renderPlanEvaluation(story) {
  $('plan-evaluation').innerHTML = `<div class="eval-grid">${story.plan_evaluation.map((item) => `
    <div class="eval-card ${item.status === '已命中' ? 'hit' : ''}">
      <b>${safe(item.name)} <span style="float:right;color:${item.status === '已命中' ? 'var(--green)' : 'var(--red)'}">${safe(item.status)}</span></b>
      完成率 ${safe(item.completion)}<br>
      无人接单 ${safe(item.unassigned)}<br>
      成本 ${safe(item.cost)}<br>
      ${safe(item.stars)}
    </div>
  `).join('')}</div>`;
}

function renderBaseline(story) {
  $('baseline-table').innerHTML = `
    <table class="data-table">
      <thead><tr><th>对比指标</th><th>传统规则/贪心基线</th><th>AutoSolver Agent</th><th>改善幅度</th></tr></thead>
      <tbody>${story.baseline_table.rows.map((row) => `<tr><td>${safe(row.metric)}</td><td>${safe(row.baseline)}</td><td>${safe(row.autosolver)}</td><td>${safe(row.delta)}</td></tr>`).join('')}</tbody>
    </table>
  `;
}

function renderMemory(story) {
  const memory = story.strategy_memory;
  $('strategy-memory').innerHTML = `
    <p style="margin:0 0 8px;color:var(--muted);font-size:12px;line-height:1.45">${safe(memory.summary)}</p>
    <div class="memory-list">${memory.items.map((item) => `
      <div class="memory-item">
        <span>${safe(item.id)}</span>
        <span class="badge ${item.status === '失败' ? 'fail' : ''}">${safe(item.status)}</span>
        <span>${safe(item.text)} · ${safe(item.reason)}</span>
      </div>
    `).join('')}</div>
  `;
}

function renderRoi(story) {
  const roi = story.commercial_roi;
  $('commercial-roi').innerHTML = `
    <div class="roi-box">预计每日减少损失<b>${safe(roi.estimated_daily_saving)}</b></div>
    <div class="roi-box">预计每月节省成本<b>${safe(roi.estimated_monthly_cost)}</b></div>
    <div class="roi-box">履约稳定性提升<b>${safe(roi.stability_lift)}</b></div>
  `;
}

function renderBoundary(story) {
  $('data-boundary').textContent = `${story.data_boundary.claim}：${story.data_boundary.real_fields.join('、')} 为真实字段或派生解释指标；${story.data_boundary.demo_fields.join('、')} 为演示映射。`;
}

function renderStory(story) {
  currentStory = story;
  renderScene(story);
  renderMetrics(story);
  renderScenarioRail(story);
  renderMap(story);
  renderDecision(story);
  renderWorkflow(story);
  renderPlanEvaluation(story);
  renderBaseline(story);
  renderMemory(story);
  renderRoi(story);
  renderBoundary(story);
}

async function loadCases() {
  const payload = await fetch('/api/cases').then((res) => res.json());
  $('case-select').innerHTML = payload.cases.map((item) => `<option value="${safe(item.id)}">${safe(item.name)} · ${safe(item.type)}</option>`).join('');
  const preferred = Array.from($('case-select').options).find((option) => option.value === 'large_seed301');
  if (preferred) preferred.selected = true;
}

async function runCase() {
  const button = $('run-button');
  button.disabled = true;
  $('run-status').textContent = '推理中';
  const caseId = $('case-select').value || 'large_seed301';
  const budget = $('budget').value || '10';
  try {
    const payload = await fetch(`/api/run?case=${encodeURIComponent(caseId)}&budget=${encodeURIComponent(budget)}`).then((res) => res.json());
    if (payload.status !== 'ok') throw new Error(payload.error || 'run failed');
    renderStory(payload.story);
    $('run-status').textContent = '运行完成';
  } catch (error) {
    $('run-status').textContent = `运行失败：${error.message}`;
  } finally {
    button.disabled = false;
  }
}

$('run-button').addEventListener('click', runCase);
$('reload-button').addEventListener('click', loadCases);
renderStory(DEFAULT_STORY);
loadCases().catch((error) => { $('run-status').textContent = error.message; });
</script>
</body>
</html>"""
    return template.replace("__DEFAULT_STORY__", placeholder)


class DispatchV3RequestHandler(BaseHTTPRequestHandler):
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
                self._send_html(render_dispatch_index_v3())
                return
            if parsed.path == "/api/cases":
                self._send_json({"status": "ok", "cases": list_cases()})
                return
            if parsed.path == "/api/run":
                qs = parse_qs(parsed.query)
                case_id = qs.get("case", ["large_seed301"])[0]
                budget_s = float(qs.get("budget", ["10"])[0])
                self._send_json(build_dispatch_payload_v3(case_id, budget_s=budget_s))
                return
            self._send_json({"status": "error", "error": "not found"}, status=404)
        except Exception as exc:
            self._send_json(
                {"status": "error", "error": str(exc), "traceback": traceback.format_exc()},
                status=500,
            )

    def log_message(self, format: str, *args: object) -> None:
        print(f"[dispatch-v3] {self.address_string()} - {format % args}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local AutoSolver dispatch command center v3 demo.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8768)
    args = parser.parse_args(argv)
    server = ThreadingHTTPServer((args.host, args.port), DispatchV3RequestHandler)
    print(f"AutoSolver Dispatch Command Center v3 running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
