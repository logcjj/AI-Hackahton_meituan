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

from web_agent_demo.dispatch_story_v4 import build_dispatch_story_v4, build_placeholder_story_v4
from web_agent_demo.server import list_cases, run_case_agent


def build_dispatch_payload_v4(case_id: str, budget_s: float = 10.0) -> dict[str, object]:
    report = run_case_agent(case_id, budget_s=budget_s)
    return {"status": "ok", "report": report, "story": build_dispatch_story_v4(report)}


def render_dispatch_index_v4() -> str:
    placeholder = json.dumps(build_placeholder_story_v4(), ensure_ascii=False)
    template = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AutoSolver Agent 即时履约智能调度指挥舱</title>
  <style>
    :root {
      --stage-width: 1920px;
      --stage-height: 1080px;
      --stage-scale: 1;
      --bg: #020b16;
      --panel: rgba(6, 23, 37, .82);
      --panel2: rgba(8, 35, 55, .68);
      --line: rgba(71, 210, 255, .23);
      --line-hot: rgba(28, 244, 210, .42);
      --text: #effcff;
      --muted: #91aeba;
      --cyan: #1cf4d2;
      --blue: #2cb7ff;
      --yellow: #ffd32d;
      --orange: #ff7938;
      --green: #38f29c;
      --red: #ff4d56;
      --mono: "SFMono-Regular", "Cascadia Code", Consolas, monospace;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: calc(var(--stage-height) * var(--stage-scale));
      color: var(--text);
      font-family: "Avenir Next", "PingFang SC", "Hiragino Sans GB", sans-serif;
      background:
        radial-gradient(circle at 20% 8%, rgba(28,244,210,.12), transparent 24rem),
        radial-gradient(circle at 84% 18%, rgba(255,121,56,.12), transparent 24rem),
        linear-gradient(135deg, #020816 0%, #06172a 52%, #020b16 100%);
      overflow-x: hidden;
    }
    body:before {
      content: "";
      position: fixed;
      inset: 0;
      background-image:
        linear-gradient(rgba(44,183,255,.055) 1px, transparent 1px),
        linear-gradient(90deg, rgba(44,183,255,.045) 1px, transparent 1px);
      background-size: 38px 38px;
      pointer-events: none;
    }
    .presentation-scale {
      width: var(--stage-width);
      transform: scale(var(--stage-scale));
      transform-origin: top left;
      margin-left: calc((100vw - (var(--stage-width) * var(--stage-scale))) / 2);
    }
    .target-dashboard {
      width: var(--stage-width);
      height: var(--stage-height);
      padding: 20px;
      position: relative;
      overflow: hidden;
    }
    .card {
      border: 1px solid var(--line);
      border-radius: 14px;
      background: linear-gradient(180deg, rgba(8,31,50,.86), rgba(3,15,27,.84));
      box-shadow: 0 22px 70px rgba(0,0,0,.34);
      backdrop-filter: blur(18px);
    }
    .top-row {
      height: 118px;
      display: grid;
      grid-template-columns: 560px 1fr 350px;
      gap: 14px;
      margin-bottom: 14px;
    }
    .brand {
      display: grid;
      grid-template-columns: 84px 1fr;
      gap: 16px;
      align-items: center;
    }
    .logo {
      width: 78px;
      height: 78px;
      border: 2px solid var(--yellow);
      border-radius: 50%;
      display: grid;
      place-items: center;
      font-weight: 1000;
      font-size: 52px;
      color: var(--green);
      background: radial-gradient(circle, rgba(28,244,210,.2), rgba(0,0,0,.24));
    }
    h1 {
      margin: 0 0 8px;
      line-height: .98;
      font-size: 35px;
      letter-spacing: -.055em;
    }
    h1 span { color: var(--yellow); }
    .subline { color: #99f4ef; font-size: 15px; margin: 0; }
    .status-grid {
      display: grid;
      grid-template-columns: 170px 190px 1fr;
      gap: 14px;
    }
    .status-card { padding: 16px 18px; }
    .status-card small { display: block; color: var(--muted); margin-bottom: 8px; }
    .status-card b { color: var(--cyan); font-size: 27px; font-family: var(--mono); }
    #scene-intelligence { padding: 12px; }
    .scene-title { color: var(--muted); font-size: 13px; margin-bottom: 8px; }
    .feature-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 9px; }
    .feature {
      min-height: 58px;
      display: grid;
      grid-template-columns: 40px 1fr;
      align-items: center;
      gap: 8px;
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 8px;
      background: rgba(0,0,0,.22);
    }
    .feature i {
      width: 34px;
      height: 34px;
      border: 2px solid currentColor;
      border-radius: 50%;
      display: grid;
      place-items: center;
      font-style: normal;
      font-weight: 900;
    }
    .feature b { display: block; font-size: 14px; }
    .feature small { color: var(--muted); }
    .controls { padding: 12px; display: grid; gap: 8px; }
    .control-line { display: grid; grid-template-columns: 1fr 76px; gap: 8px; }
    select, input, button {
      border: 1px solid var(--line);
      border-radius: 11px;
      background: rgba(0,0,0,.3);
      color: var(--text);
      padding: 9px 10px;
      font-size: 13px;
      outline: none;
      width: 100%;
    }
    button {
      border: 0;
      background: linear-gradient(135deg, #40f4a2, #0f8c60);
      color: #02120e;
      cursor: pointer;
      font-weight: 950;
    }
    button.secondary {
      color: var(--text);
      background: linear-gradient(135deg, rgba(44,183,255,.34), rgba(44,183,255,.12));
      border: 1px solid var(--line);
    }
    button:disabled { opacity: .58; cursor: wait; }
    #run-status { color: var(--yellow); font-weight: 900; font-size: 13px; }
    #top-kpi-strip {
      height: 125px;
      display: grid;
      grid-template-columns: repeat(6, 1fr);
      overflow: hidden;
      margin-bottom: 14px;
    }
    .kpi {
      padding: 18px 22px;
      border-right: 1px solid rgba(71,210,255,.14);
      background: rgba(4, 18, 31, .58);
    }
    .kpi:last-child { border-right: 0; }
    .kpi small { color: var(--muted); display: block; margin-bottom: 6px; }
    .kpi b { font-size: 38px; letter-spacing: -.055em; display: block; }
    .kpi em { color: var(--green); font-size: 14px; font-style: normal; }
    .main-row {
      height: 520px;
      display: grid;
      grid-template-columns: 290px 1fr 420px;
      gap: 14px;
      margin-bottom: 14px;
    }
    .panel-pad { padding: 13px; }
    h2 { margin: 0 0 10px; font-size: 17px; color: #c6fbff; }
    #left-scene-rail { display: grid; gap: 9px; margin-bottom: 12px; }
    .scene-card {
      min-height: 68px;
      border: 1px solid var(--line);
      border-radius: 11px;
      background: rgba(255,255,255,.035);
      display: grid;
      grid-template-columns: 38px 1fr;
      gap: 10px;
      align-items: center;
      padding: 10px;
    }
    .scene-card.active { border-color: var(--yellow); background: linear-gradient(90deg, rgba(255,211,45,.13), rgba(0,0,0,.08)); }
    .rank {
      width: 34px;
      height: 34px;
      display: grid;
      place-items: center;
      border-radius: 9px;
      border: 1px solid rgba(255,211,45,.55);
      color: var(--yellow);
      font-family: var(--mono);
      font-weight: 900;
    }
    .scene-card b { display: block; }
    .scene-card small { color: var(--muted); line-height: 1.35; }
    #risk-portrait, #policy-box {
      border: 1px solid var(--line);
      border-radius: 11px;
      padding: 10px;
      background: rgba(0,0,0,.18);
      margin-top: 10px;
    }
    .risk-row { display: flex; justify-content: space-between; color: var(--muted); padding: 5px 0; }
    .risk-row b { color: var(--orange); }
    .map-card { padding: 13px; }
    .map-title { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .legend { display: flex; gap: 15px; color: var(--muted); font-size: 13px; }
    .legend span:before { content: ""; display: inline-block; width: 9px; height: 9px; border-radius: 50%; background: currentColor; margin-right: 6px; }
    #map-stage {
      height: 462px;
      position: relative;
      overflow: hidden;
      border-radius: 12px;
      border: 1px solid var(--line);
      background:
        radial-gradient(circle at 59% 36%, rgba(255,211,45,.18), transparent 13rem),
        radial-gradient(circle at 79% 71%, rgba(28,244,210,.15), transparent 14rem),
        linear-gradient(145deg, rgba(8,34,56,.96), rgba(2,12,24,.98));
    }
    #map-stage:before {
      content: "";
      position: absolute;
      inset: 0;
      background-image:
        linear-gradient(22deg, transparent 47%, rgba(44,183,255,.16) 49%, transparent 51%),
        linear-gradient(154deg, transparent 48%, rgba(255,255,255,.08) 50%, transparent 52%),
        linear-gradient(90deg, rgba(44,183,255,.04) 1px, transparent 1px),
        linear-gradient(rgba(44,183,255,.04) 1px, transparent 1px);
      background-size: 145px 92px, 132px 105px, 42px 42px, 42px 42px;
    }
    #operation-map { position: absolute; inset: 0; width: 100%; height: 100%; z-index: 1; }
    .edge { fill: none; stroke-width: 2.1; stroke-dasharray: 7 6; animation: dash 2.5s linear infinite; opacity: .9; }
    .edge.allocated_plan { stroke-width: 3.2; stroke-dasharray: 1 0; filter: drop-shadow(0 0 6px rgba(28,244,210,.78)); }
    @keyframes dash { to { stroke-dashoffset: -28; } }
    .node { cursor: pointer; }
    .node circle { filter: drop-shadow(0 0 7px currentColor); }
    .node text {
      fill: var(--text);
      paint-order: stroke;
      stroke: rgba(0,0,0,.86);
      stroke-width: .68px;
      font-size: 2.1px;
      font-weight: 900;
      pointer-events: none;
    }
    .node .sub { fill: #aee7ef; font-size: 1.62px; stroke-width: .45px; }
    .map-tools { position: absolute; left: 12px; bottom: 42px; display: grid; gap: 7px; z-index: 2; }
    .map-tool { width: 34px; height: 34px; border: 1px solid var(--line); border-radius: 8px; background: rgba(0,0,0,.36); display: grid; place-items: center; font-family: var(--mono); }
    #map-callout {
      position: absolute;
      right: 245px;
      top: 145px;
      width: 210px;
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 10px;
      background: rgba(3,16,28,.82);
      z-index: 2;
      color: var(--muted);
      line-height: 1.55;
    }
    #map-callout b { color: var(--text); }
    #right-decision-panel { padding: 13px; display: grid; gap: 9px; overflow: hidden; }
    .decision-box {
      border: 1px solid var(--line);
      border-radius: 11px;
      background: rgba(255,255,255,.035);
      padding: 10px;
      color: var(--muted);
      font-size: 13px;
    }
    .decision-box h3 { margin: 0 0 8px; color: var(--text); font-size: 16px; }
    .kv-grid, .couriers { display: grid; grid-template-columns: repeat(2, 1fr); gap: 7px; }
    .kv, .courier {
      border: 1px solid rgba(71,210,255,.16);
      border-radius: 8px;
      padding: 8px;
      background: rgba(0,0,0,.18);
    }
    .kv b, .courier b { display: block; color: var(--text); font-family: var(--mono); margin-top: 2px; }
    .reasons { margin: 0; padding-left: 17px; line-height: 1.5; }
    .reject-line { display: flex; justify-content: space-between; gap: 8px; border-bottom: 1px solid rgba(71,210,255,.13); padding: 6px 0; }
    .reject-line b { color: var(--red); }
    .bottom-row {
      height: 250px;
      display: grid;
      grid-template-columns: 1.16fr .75fr 1.05fr .86fr 1fr;
      gap: 14px;
    }
    .bottom-card { padding: 12px; overflow: hidden; }
    #workflow-strip { display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; }
    .flow { text-align: center; color: var(--muted); border-right: 1px solid rgba(71,210,255,.14); min-height: 112px; padding: 6px; }
    .flow:last-child { border-right: 0; }
    .flow i { width: 32px; height: 32px; border: 1px solid var(--line-hot); border-radius: 50%; display: grid; place-items: center; margin: 0 auto 6px; color: var(--cyan); font-family: var(--mono); font-style: normal; font-weight: 900; }
    .flow b { display: block; color: var(--text); }
    .flow small { display: block; line-height: 1.3; }
    .eval-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 7px; }
    .eval { border: 1px solid var(--line); border-radius: 10px; padding: 9px; color: var(--muted); background: rgba(0,0,0,.17); font-size: 12px; }
    .eval.hit { border-color: rgba(56,242,156,.7); background: rgba(56,242,156,.08); }
    .eval b { color: var(--text); display: block; font-size: 15px; margin-bottom: 5px; }
    .data-table { width: 100%; border-collapse: collapse; color: var(--muted); font-size: 12px; }
    .data-table th, .data-table td { border: 1px solid rgba(71,210,255,.13); padding: 5px 6px; text-align: left; }
    .data-table th { color: var(--text); background: rgba(255,255,255,.035); }
    .data-table td:nth-child(3), .data-table td:nth-child(4) { color: var(--green); }
    .memory-item, .review-item { display: grid; grid-template-columns: 42px 1fr; gap: 7px; align-items: start; color: var(--muted); font-size: 12px; margin-bottom: 7px; }
    .badge { border-radius: 6px; padding: 3px 5px; text-align: center; background: var(--green); color: #03110e; font-weight: 900; }
    .badge.fail { background: var(--red); color: #fff; }
    #commercial-roi { display: grid; gap: 8px; }
    .roi { border: 1px solid var(--line-hot); border-radius: 10px; padding: 9px; color: var(--muted); background: rgba(28,244,210,.07); }
    .roi b { display: block; color: var(--green); font-size: 21px; letter-spacing: -.04em; }
    #data-boundary { position: absolute; left: 20px; right: 20px; bottom: 7px; color: var(--muted); font-size: 11px; }
  </style>
</head>
<body>
<div class="presentation-scale">
<main class="target-dashboard">
  <section class="top-row">
    <div class="brand">
      <div class="logo">A</div>
      <div>
        <h1><span>AutoSolver</span> Agent<br>即时履约智能调度指挥舱</h1>
        <p class="subline">10 秒内生成高可靠派单方案，降低无人接单风险与履约成本</p>
      </div>
    </div>
    <div class="status-grid">
      <div class="status-card card"><small>系统状态</small><b id="system-status">调度运行中</b></div>
      <div class="status-card card"><small>已运行</small><b id="elapsed-time">00:00:07</b></div>
      <div class="card" id="scene-intelligence"></div>
    </div>
    <div class="controls card">
      <div class="control-line"><select id="case-select"></select><input id="budget" value="10"></div>
      <button id="run-button">开始推理并刷新指挥舱</button>
      <button id="reload-button" class="secondary">刷新用例列表</button>
      <div id="run-status">首屏默认展示</div>
    </div>
  </section>
  <section id="top-kpi-strip" class="card"></section>
  <section class="main-row">
    <aside class="card panel-pad">
      <h2>AI 场景识别</h2>
      <div id="left-scene-rail"></div>
      <h2>场景风险画像</h2>
      <div id="risk-portrait"></div>
      <div id="policy-box"></div>
    </aside>
    <section class="card map-card">
      <div class="map-title"><h2>调度可视化地图</h2><div class="legend" id="map-legend"></div></div>
      <div id="map-stage">
        <svg id="operation-map" viewBox="0 0 100 100" role="img" aria-label="operation map"></svg>
        <div class="map-tools"><div class="map-tool">□</div><div class="map-tool">◇</div><div class="map-tool">＋</div><div class="map-tool">－</div></div>
        <div id="map-callout"></div>
      </div>
    </section>
    <aside class="card" id="right-decision-panel">
      <h2>决策解释</h2>
      <div id="decision-panel"></div>
    </aside>
  </section>
  <section class="bottom-row">
    <section class="card bottom-card"><h2>Agent 工作流程</h2><div id="workflow-strip"></div></section>
    <section class="card bottom-card"><h2>候选方案评估</h2><div id="plan-evaluation"></div></section>
    <section class="card bottom-card"><h2>Baseline vs AutoSolver</h2><div id="baseline-table"></div></section>
    <section class="card bottom-card"><h2>策略记忆库</h2><div id="strategy-memory"></div></section>
    <section class="card bottom-card"><h2>商业价值 ROI</h2><div id="commercial-roi"></div></section>
  </section>
  <section class="card bottom-card" style="height:112px;margin-top:14px"><h2>评审标准对齐</h2><div id="review-alignment" style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px"></div></section>
  <div id="data-boundary"></div>
</main>
</div>
<script>
const DEFAULT_STORY = __DEFAULT_STORY__;
const $ = (id) => document.getElementById(id);
let currentStory = DEFAULT_STORY;
function safe(value) {
  return String(value ?? '').replace(/[&<>"']/g, (ch) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;', "'":'&#39;'}[ch]));
}
function updateScale() {
  const scale = Math.min(1, Math.max(0.34, (window.innerWidth - 20) / 1920, (window.innerHeight - 16) / 1080));
  document.documentElement.style.setProperty('--stage-scale', scale.toFixed(4));
}
function nodeById(story, id) {
  return story.operation_map.nodes.find((node) => node.id === id);
}
function toneColor(node) {
  if (node.type === 'order_high_risk') return '#ff7938';
  if (node.type === 'order_normal') return '#ffd32d';
  return node.tone === 'green' ? '#38f29c' : '#1cf4d2';
}
function renderTop(story) {
  const center = story.command_center;
  $('system-status').textContent = center.status;
  $('elapsed-time').textContent = center.elapsed;
  $('scene-intelligence').innerHTML = `
    <div class="scene-title">当前场景特征（AI 自动判断）</div>
    <div class="feature-grid">${center.scene_features.map((item) => `
      <div class="feature" style="color:${item.tone === 'green' ? 'var(--green)' : item.tone === 'orange' ? 'var(--orange)' : 'var(--yellow)'}">
        <i>${safe(item.label.slice(0, 1))}</i><div><b>${safe(item.label)}</b><small>${safe(item.delta)}</small></div>
      </div>`).join('')}</div>`;
}
function renderKpis(story) {
  $('top-kpi-strip').innerHTML = story.metric_strip.map((item) => `
    <div class="kpi"><small>${safe(item.label)}</small><b>${safe(item.value)}</b><em>${safe(item.trend)}</em></div>
  `).join('');
}
function renderLeft(story) {
  const judgement = story.ai_scene_judgement;
  $('left-scene-rail').innerHTML = judgement.cards.map((card, index) => `
    <div class="scene-card ${index === 0 ? 'active' : ''}"><div class="rank">${safe(card.rank)}</div><div><b>${safe(card.label)}</b><small>${safe(card.summary)} · ${safe(card.impact)}</small></div></div>
  `).join('');
  $('risk-portrait').innerHTML = judgement.risk_portrait.map((item) => `<div class="risk-row"><span>${safe(item.label)}</span><b>${safe(item.level)}</b></div>`).join('');
  $('policy-box').innerHTML = `<h2 style="margin-top:0">推荐 Agent 策略</h2><div style="color:var(--muted);line-height:1.5">${safe(judgement.recommended_policy)}</div>`;
}
function edgePath(a, b, index) {
  const bend = index % 2 === 0 ? -10 : 10;
  return `M ${a.x} ${a.y} Q ${(a.x + b.x) / 2 + bend} ${(a.y + b.y) / 2 - 8} ${b.x} ${b.y}`;
}
function renderMap(story) {
  const edges = story.operation_map.edges.map((edge, index) => {
    const source = nodeById(story, edge.source);
    const target = nodeById(story, edge.target);
    if (!source || !target) return '';
    const color = edge.type === 'allocated_plan' ? '#1cf4d2' : '#ffd32d';
    return `<path class="edge ${safe(edge.type)}" d="${edgePath(source, target, index)}" stroke="${color}"></path>`;
  }).join('');
  const nodes = story.operation_map.nodes.map((node) => {
    const color = toneColor(node);
    const radius = node.type === 'courier' ? 2.25 : 2.8;
    const sub = node.type === 'courier' ? `w=${node.willingness}` : `${node.orders}单`;
    const label = node.type === 'courier' ? node.label.replace('骑手 ', '') : node.label.replace('订单组 ', '');
    return `<g class="node" style="color:${color}"><circle cx="${node.x}" cy="${node.y}" r="${radius}" fill="${color}" stroke="rgba(255,255,255,.82)" stroke-width=".52"></circle><text x="${node.x + 3.2}" y="${node.y + .7}">${safe(label)}</text><text class="sub" x="${node.x + 3.2}" y="${node.y + 3.05}">${safe(sub)}</text></g>`;
  }).join('');
  $('operation-map').innerHTML = edges + nodes;
  $('map-legend').innerHTML = story.operation_map.legend.map((item) => `<span>${safe(item.label)}</span>`).join('');
  const focus = story.operation_map.focus;
  $('map-callout').innerHTML = `<b>${safe(focus.title)}</b><br>风险：${safe(focus.risk)}<br>候选方案：3 个`;
}
function renderDecision(story) {
  const decision = story.decision_panel;
  $('decision-panel').innerHTML = `
    <div class="decision-box"><h3>任务组 ${safe(decision.selected_order_group.id)} <span style="color:var(--red);font-size:12px">${safe(decision.selected_order_group.risk)}</span></h3><div class="kv-grid">${Object.entries(decision.selected_order_group).filter(([key]) => key !== 'id' && key !== 'risk').map(([key, value]) => `<div class="kv">${safe(key)}<b>${safe(value)}</b></div>`).join('')}</div></div>
    <div class="decision-box"><h3>选择的骑手</h3><div class="couriers">${decision.selected_couriers.map((item) => `<div class="courier"><b>${safe(item.id)}</b>接单意愿 ${safe(item.willingness)}<br>距离 ${safe(item.distance_km)}<br>score ${safe(item.score)}</div>`).join('')}</div></div>
    <div class="decision-box"><h3>决策原因</h3><ul class="reasons">${decision.decision_reason.map((item) => `<li>${safe(item)}</li>`).join('')}</ul></div>
    <div class="decision-box"><h3>未采用的方案</h3>${decision.rejected_plans.map((item) => `<div class="reject-line"><span>${safe(item.name)} · ${safe(item.reason)}</span><b>${safe(item.status)}</b></div>`).join('')}</div>`;
}
function renderBottom(story) {
  $('workflow-strip').innerHTML = story.agent_workflow.map((item) => `<div class="flow"><i>${safe(item.step)}</i><b>${safe(item.title)}</b><small>${safe(item.desc)}</small><small style="color:${item.status === '运行中' ? 'var(--yellow)' : 'var(--green)'}">${safe(item.status)}</small></div>`).join('');
  $('plan-evaluation').innerHTML = `<div class="eval-grid">${story.plan_evaluation.map((item) => `<div class="eval ${item.status === '已命中' ? 'hit' : ''}"><b>${safe(item.name)} <span style="float:right;color:${item.status === '已命中' ? 'var(--green)' : 'var(--red)'}">${safe(item.status)}</span></b>完成率 ${safe(item.completion)}<br>无人接单 ${safe(item.unassigned)}<br>成本 ${safe(item.cost)}<br>${safe(item.stars)}</div>`).join('')}</div>`;
  $('baseline-table').innerHTML = `<table class="data-table"><thead><tr><th>指标</th><th>贪心</th><th>Agent</th><th>改善</th></tr></thead><tbody>${story.baseline_table.rows.map((row) => `<tr><td>${safe(row.metric)}</td><td>${safe(row.baseline)}</td><td>${safe(row.autosolver)}</td><td>${safe(row.delta)}</td></tr>`).join('')}</tbody></table>`;
  $('strategy-memory').innerHTML = story.strategy_memory.items.map((item) => `<div class="memory-item"><span class="badge ${item.status === '失败' ? 'fail' : ''}">${safe(item.status)}</span><span>${safe(item.id)} ${safe(item.reason)}</span></div>`).join('');
  const roi = story.commercial_roi;
  $('commercial-roi').innerHTML = `<div class="roi">预计每日减少损失<b>${safe(roi.estimated_daily_saving)}</b></div><div class="roi">预计每月节省成本<b>${safe(roi.estimated_monthly_cost)}</b></div><div class="roi">履约稳定性提升<b>${safe(roi.stability_lift)}</b></div>`;
  $('review-alignment').innerHTML = story.review_alignment.map((item) => `<div class="review-item"><span class="badge">${safe(item.dimension)}</span><span>${safe(item.evidence)}</span></div>`).join('');
}
function renderBoundary(story) {
  $('data-boundary').textContent = `${story.data_boundary.claim}：${story.data_boundary.real_fields.join('、')} 为真实字段或派生解释指标；${story.data_boundary.demo_fields.join('、')} 为演示映射。`;
}
function renderStory(story) {
  currentStory = story;
  renderTop(story);
  renderKpis(story);
  renderLeft(story);
  renderMap(story);
  renderDecision(story);
  renderBottom(story);
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
  try {
    const payload = await fetch(`/api/run?case=${encodeURIComponent($('case-select').value || 'large_seed301')}&budget=${encodeURIComponent($('budget').value || '10')}`).then((res) => res.json());
    if (payload.status !== 'ok') throw new Error(payload.error || 'run failed');
    renderStory(payload.story);
    $('run-status').textContent = '运行完成';
  } catch (error) {
    $('run-status').textContent = `运行失败：${error.message}`;
  } finally {
    button.disabled = false;
  }
}
window.addEventListener('resize', updateScale);
$('run-button').addEventListener('click', runCase);
$('reload-button').addEventListener('click', loadCases);
updateScale();
renderStory(DEFAULT_STORY);
loadCases().catch((error) => { $('run-status').textContent = error.message; });
</script>
</body>
</html>"""
    return template.replace("__DEFAULT_STORY__", placeholder)


class DispatchV4RequestHandler(BaseHTTPRequestHandler):
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
                self._send_html(render_dispatch_index_v4())
                return
            if parsed.path == "/api/cases":
                self._send_json({"status": "ok", "cases": list_cases()})
                return
            if parsed.path == "/api/run":
                qs = parse_qs(parsed.query)
                case_id = qs.get("case", ["large_seed301"])[0]
                budget_s = float(qs.get("budget", ["10"])[0])
                self._send_json(build_dispatch_payload_v4(case_id, budget_s=budget_s))
                return
            self._send_json({"status": "error", "error": "not found"}, status=404)
        except Exception as exc:
            self._send_json(
                {"status": "error", "error": str(exc), "traceback": traceback.format_exc()},
                status=500,
            )

    def log_message(self, format: str, *args: object) -> None:
        print(f"[dispatch-v4] {self.address_string()} - {format % args}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local AutoSolver dispatch command center v4 demo.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8769)
    args = parser.parse_args(argv)
    server = ThreadingHTTPServer((args.host, args.port), DispatchV4RequestHandler)
    print(f"AutoSolver Dispatch Command Center v4 running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
