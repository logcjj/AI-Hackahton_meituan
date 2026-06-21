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

from web_agent_demo.dispatch_story_v2 import build_dispatch_story_v2, build_placeholder_story_v2
from web_agent_demo.server import list_cases, run_case_agent


def build_dispatch_payload_v2(case_id: str, budget_s: float = 10.0) -> dict[str, object]:
    report = run_case_agent(case_id, budget_s=budget_s)
    return {"status": "ok", "report": report, "story": build_dispatch_story_v2(report)}


def render_dispatch_index_v2() -> str:
    placeholder = json.dumps(build_placeholder_story_v2(), ensure_ascii=False)
    template = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AutoSolver 即时履约 Agent 作战沙盘</title>
  <style>
    :root {
      --bg0: #07120f;
      --bg1: #0d241c;
      --bg2: #162f25;
      --panel: rgba(8, 25, 22, .78);
      --panel-strong: rgba(12, 35, 30, .94);
      --glass: rgba(255, 255, 255, .06);
      --line: rgba(148, 255, 215, .18);
      --line-strong: rgba(148, 255, 215, .34);
      --text: #ecfff8;
      --muted: #9cc3b6;
      --green: #3cf4a6;
      --cyan: #49d9ff;
      --amber: #ffc857;
      --orange: #ff9650;
      --red: #ff5d6c;
      --ink: #04110f;
      --shadow: 0 28px 90px rgba(0, 0, 0, .48);
      --mono: "SFMono-Regular", "Cascadia Code", Consolas, monospace;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      color: var(--text);
      font-family: "Avenir Next", "PingFang SC", "Hiragino Sans GB", sans-serif;
      background:
        radial-gradient(circle at 16% 9%, rgba(255, 200, 87, .28), transparent 25rem),
        radial-gradient(circle at 80% 5%, rgba(73, 217, 255, .22), transparent 30rem),
        radial-gradient(circle at 68% 86%, rgba(60, 244, 166, .18), transparent 34rem),
        linear-gradient(135deg, var(--bg0) 0%, var(--bg1) 44%, #05120f 100%);
      overflow-x: hidden;
    }
    body:before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image:
        linear-gradient(rgba(148,255,215,.06) 1px, transparent 1px),
        linear-gradient(90deg, rgba(148,255,215,.05) 1px, transparent 1px),
        radial-gradient(circle, rgba(255,255,255,.08) 1px, transparent 1.5px);
      background-size: 52px 52px, 52px 52px, 26px 26px;
      mask-image: linear-gradient(to bottom, black, transparent 90%);
    }
    main {
      width: min(1660px, calc(100vw - 24px));
      margin: 0 auto;
      padding: 16px 0 26px;
      position: relative;
      z-index: 1;
    }
    .card {
      border: 1px solid var(--line);
      background: var(--panel);
      box-shadow: var(--shadow);
      border-radius: 26px;
      backdrop-filter: blur(18px);
    }
    .hero {
      display: grid;
      grid-template-columns: minmax(360px, .88fr) minmax(580px, 1.55fr) 360px;
      gap: 12px;
      align-items: stretch;
    }
    .title-card {
      min-height: 190px;
      padding: 22px;
      overflow: hidden;
      position: relative;
    }
    .title-card:after {
      content: "";
      position: absolute;
      width: 220px;
      height: 220px;
      right: -80px;
      bottom: -110px;
      border-radius: 999px;
      background: radial-gradient(circle, rgba(60,244,166,.34), transparent 64%);
    }
    .eyebrow {
      color: var(--green);
      font-weight: 950;
      letter-spacing: .17em;
      text-transform: uppercase;
      font-size: 12px;
    }
    h1 {
      margin: 10px 0 10px;
      font-size: clamp(34px, 4vw, 58px);
      line-height: .92;
      letter-spacing: -.07em;
    }
    .lead {
      color: var(--muted);
      margin: 0;
      line-height: 1.7;
      font-size: 15px;
      position: relative;
      z-index: 1;
    }
    #hero-metrics {
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 10px;
      padding: 12px;
    }
    .metric-tile {
      min-height: 106px;
      padding: 13px;
      border-radius: 20px;
      border: 1px solid var(--line);
      background:
        linear-gradient(145deg, rgba(255,255,255,.08), rgba(255,255,255,.025)),
        rgba(0,0,0,.18);
      position: relative;
      overflow: hidden;
    }
    .metric-tile:before {
      content: "";
      position: absolute;
      inset: -1px;
      background: linear-gradient(120deg, transparent, rgba(60,244,166,.13), transparent);
      transform: translateX(-110%);
      animation: sweep 5.6s ease-in-out infinite;
    }
    @keyframes sweep {
      45%, 100% { transform: translateX(110%); }
    }
    .metric-tile span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
      position: relative;
    }
    .metric-tile b {
      display: block;
      margin: 8px 0 5px;
      font-size: clamp(24px, 2.5vw, 38px);
      letter-spacing: -.055em;
      position: relative;
    }
    .controls {
      padding: 16px;
      display: grid;
      gap: 10px;
    }
    label {
      display: grid;
      gap: 6px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 850;
    }
    .control-row {
      display: grid;
      grid-template-columns: 1fr 92px;
      gap: 8px;
    }
    select, input, button {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 15px;
      padding: 12px 12px;
      color: var(--text);
      background: rgba(0, 0, 0, .28);
      font-size: 14px;
      outline: none;
    }
    button {
      border: 0;
      cursor: pointer;
      font-weight: 950;
      letter-spacing: .03em;
      background: linear-gradient(135deg, #35e99b, #0c6d45 60%, #063d2a);
      color: #02120d;
      box-shadow: 0 18px 48px rgba(60,244,166,.22);
    }
    button.secondary {
      color: var(--text);
      background: linear-gradient(135deg, rgba(73,217,255,.38), rgba(73,217,255,.12));
      border: 1px solid var(--line);
      box-shadow: none;
    }
    button:disabled {
      cursor: wait;
      opacity: .58;
    }
    #status {
      color: var(--amber);
      font-weight: 900;
      min-height: 20px;
    }
    .dashboard {
      display: grid;
      grid-template-columns: 310px minmax(0, 1fr) 360px;
      gap: 12px;
      margin-top: 12px;
    }
    .panel-pad { padding: 14px; }
    h2 {
      margin: 0 0 12px;
      font-size: 18px;
      letter-spacing: -.035em;
    }
    .profile-card {
      padding: 14px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,.045);
      border-radius: 18px;
      margin-bottom: 10px;
    }
    .profile-card strong {
      display: block;
      font-size: 20px;
      letter-spacing: -.04em;
      margin-bottom: 6px;
    }
    .tags {
      display: grid;
      gap: 8px;
    }
    .tag {
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 10px;
      background: rgba(0,0,0,.2);
    }
    .tag b { display: block; }
    .tag small { color: var(--muted); line-height: 1.5; }
    .map-card {
      padding: 14px;
      min-width: 0;
    }
    .map-shell {
      position: relative;
      height: 650px;
      border: 1px solid var(--line-strong);
      border-radius: 24px;
      overflow: hidden;
      background:
        radial-gradient(circle at 46% 40%, rgba(73,217,255,.24), transparent 23rem),
        radial-gradient(circle at 72% 72%, rgba(255,200,87,.16), transparent 19rem),
        linear-gradient(140deg, rgba(11,46,50,.92), rgba(5,15,24,.96));
    }
    .map-shell:before {
      content: "";
      position: absolute;
      inset: 0;
      background-image:
        linear-gradient(28deg, transparent 47%, rgba(148,255,215,.1) 49%, transparent 51%),
        linear-gradient(145deg, transparent 48%, rgba(255,255,255,.055) 50%, transparent 52%);
      background-size: 180px 104px, 148px 118px;
      opacity: .62;
    }
    .map-topline {
      position: absolute;
      top: 12px;
      left: 12px;
      right: 12px;
      z-index: 2;
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: flex-start;
      pointer-events: none;
    }
    .legend {
      display: flex;
      flex-wrap: wrap;
      gap: 7px;
    }
    .pill {
      border: 1px solid var(--line);
      background: rgba(0, 0, 0, .32);
      border-radius: 999px;
      padding: 6px 8px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 850;
    }
    .map-note {
      max-width: 270px;
      color: var(--muted);
      text-align: right;
      font-size: 12px;
      line-height: 1.5;
    }
    #map-canvas {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
    }
    .edge {
      fill: none;
      stroke-width: 2.6;
      stroke-linecap: round;
      opacity: .86;
      stroke-dasharray: 8 8;
      animation: dash 2.6s linear infinite;
    }
    .edge.accepted {
      stroke-width: 4.3;
      stroke-dasharray: 1 0;
      filter: drop-shadow(0 0 6px rgba(60,244,166,.62));
    }
    @keyframes dash { to { stroke-dashoffset: -34; } }
    .node { cursor: pointer; }
    .node:hover circle { stroke-width: 1.25; }
    .node-label {
      fill: var(--text);
      font-size: 2.3px;
      font-weight: 900;
      paint-order: stroke;
      stroke: rgba(0,0,0,.72);
      stroke-width: .62px;
      pointer-events: none;
    }
    .node-sub {
      fill: var(--muted);
      font-size: 1.8px;
      paint-order: stroke;
      stroke: rgba(0,0,0,.72);
      stroke-width: .48px;
      pointer-events: none;
    }
    #decision-stack {
      display: grid;
      gap: 10px;
    }
    .decision-card {
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 12px;
      background: rgba(255,255,255,.045);
    }
    .decision-card.active {
      border-color: rgba(60,244,166,.64);
      box-shadow: 0 0 0 2px rgba(60,244,166,.08) inset;
    }
    .decision-card b {
      display: block;
      margin-bottom: 6px;
    }
    .decision-card p, .muted {
      color: var(--muted);
      line-height: 1.58;
      margin: 0;
    }
    .evidence-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 7px;
      margin-top: 10px;
    }
    .evidence {
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 8px;
      background: rgba(0,0,0,.18);
      font-family: var(--mono);
      font-size: 12px;
    }
    .evidence span {
      display: block;
      color: var(--muted);
      font-family: inherit;
      font-size: 10px;
      margin-bottom: 3px;
    }
    .bottom-grid {
      display: grid;
      grid-template-columns: 1.15fr .95fr 1fr;
      gap: 12px;
      margin-top: 12px;
    }
    #strategy-timeline {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 8px;
    }
    .step {
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 12px;
      background: rgba(0,0,0,.18);
      min-height: 118px;
      position: relative;
      overflow: hidden;
    }
    .step.active {
      border-color: rgba(255,200,87,.72);
      background: linear-gradient(145deg, rgba(255,200,87,.12), rgba(0,0,0,.2));
    }
    .step small {
      color: var(--muted);
      display: block;
      margin-top: 8px;
      line-height: 1.45;
    }
    .comparison {
      display: grid;
      gap: 9px;
    }
    .compare-row {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 8px;
      align-items: center;
      border-bottom: 1px solid var(--line);
      padding: 8px 0;
      color: var(--muted);
    }
    .compare-row b {
      color: var(--text);
      font-family: var(--mono);
    }
    #boundary-strip {
      margin-top: 12px;
      padding: 12px 14px;
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 12px;
      align-items: center;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.6;
    }
    #boundary-strip b {
      color: var(--green);
      white-space: nowrap;
    }
    .toast {
      position: fixed;
      right: 18px;
      bottom: 18px;
      z-index: 5;
      width: min(420px, calc(100vw - 36px));
      border: 1px solid var(--line);
      background: var(--panel-strong);
      box-shadow: var(--shadow);
      border-radius: 18px;
      padding: 12px;
      color: var(--muted);
      transform: translateY(120%);
      transition: transform .24s ease;
    }
    .toast.show { transform: translateY(0); }
    @media (max-width: 1250px) {
      .hero, .dashboard, .bottom-grid { grid-template-columns: 1fr; }
      #hero-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      #strategy-timeline { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .map-shell { height: 560px; }
    }
    @media (max-width: 680px) {
      main { width: min(100vw - 14px, 1660px); }
      #hero-metrics, #strategy-timeline { grid-template-columns: 1fr; }
      .control-row { grid-template-columns: 1fr; }
      .map-shell { height: 470px; }
      #boundary-strip { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
<main>
  <section class="hero">
    <div class="title-card card">
      <div class="eyebrow">AutoSolver Agent / Dispatch OS</div>
      <h1>AutoSolver 即时履约 Agent 作战沙盘</h1>
      <p class="lead">首屏默认展示脱敏沙盘，运行后用真实 Agent 报告刷新。这里重点讲“业务场景 -> 感知/规划/评估/记忆 -> 多派调度 -> 优于贪心 -> 商业价值”。</p>
    </div>
    <div class="card" id="hero-metrics"></div>
    <div class="controls card">
      <label>选择用例
        <select id="case-select"></select>
      </label>
      <div class="control-row">
        <label>预算秒数
          <input id="budget" value="10" inputmode="decimal">
        </label>
        <label>状态
          <div id="status">首屏默认展示</div>
        </label>
      </div>
      <button id="run-button">开始推理并刷新沙盘</button>
      <button id="reload-button" class="secondary">刷新用例列表</button>
    </div>
  </section>

  <section class="dashboard">
    <aside class="card panel-pad">
      <h2>场景画像</h2>
      <div id="scene-profile"></div>
      <h2>业务压力标签</h2>
      <div class="tags" id="scene-tags"></div>
    </aside>

    <section class="card map-card">
      <h2>任务组 - 骑手候选关系地图</h2>
      <div class="map-shell">
        <div class="map-topline">
          <div class="legend" id="map-legend"></div>
          <div class="map-note">地图坐标为演示映射；虚线表示候选派单，亮线表示 best-so-far 采纳关系。</div>
        </div>
        <svg id="map-canvas" viewBox="0 0 100 100" role="img" aria-label="dispatch sandbox map"></svg>
      </div>
    </section>

    <aside class="card panel-pad">
      <h2>决策解释</h2>
      <div id="decision-stack"></div>
    </aside>
  </section>

  <section class="bottom-grid">
    <section class="card panel-pad">
      <h2>Agent 策略时间线</h2>
      <div id="strategy-timeline"></div>
    </section>
    <section class="card panel-pad">
      <h2>Baseline vs AutoSolver</h2>
      <div id="baseline-compare" class="comparison"></div>
    </section>
    <section class="card panel-pad">
      <h2>商业价值 ROI 模拟器</h2>
      <div id="business-value" class="comparison"></div>
    </section>
  </section>

  <section class="card" id="boundary-strip">
    <b>脱敏业务场景沙盘</b>
    <span id="boundary-copy">任务/骑手/意愿/score/expected_cost 为真实赛题字段或派生解释指标；地图坐标、天气/商圈、金额换算为演示层。</span>
  </section>
</main>
<div class="toast" id="toast"></div>

<script>
const DEFAULT_STORY = __DEFAULT_STORY__;
const $ = (id) => document.getElementById(id);
let currentStory = DEFAULT_STORY;

function safe(value) {
  return String(value ?? '').replace(/[&<>"']/g, (ch) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;', "'":'&#39;'}[ch]));
}

function toneColor(tone, type) {
  if (type === 'merchant_group') return '#ff9650';
  if (type === 'courier') return tone === 'green' ? '#3cf4a6' : '#49d9ff';
  if (tone === 'red') return '#ff5d6c';
  if (tone === 'cyan') return '#49d9ff';
  if (tone === 'green') return '#3cf4a6';
  return '#ffc857';
}

function nodeById(story, id) {
  return story.map_layers.nodes.find((node) => node.id === id);
}

function paintHero(story) {
  const kpis = story.kpis_final;
  $('hero-metrics').innerHTML = kpis.map((item) => `
    <div class="metric-tile">
      <span>${safe(item.label)}</span>
      <b>${safe(item.value)}</b>
      <span>${safe(item.hint)}</span>
    </div>
  `).join('');
}

function paintScene(story) {
  const scene = story.scene_profile;
  $('scene-profile').innerHTML = `
    <div class="profile-card">
      <strong>${safe(scene.case_label)}</strong>
      <p class="muted">${safe(scene.one_liner)}</p>
    </div>
    <div class="profile-card">
      <strong>${safe(scene.risk_level)}</strong>
      <p class="muted">${safe(scene.scale)}</p>
    </div>
  `;
  $('scene-tags').innerHTML = scene.tags.map((tag) => `
    <div class="tag">
      <b>${safe(tag.label)}</b>
      <small>${safe(tag.note)}</small>
    </div>
  `).join('');
}

function curvePath(a, b, index) {
  const lift = 10 + (index % 4) * 4;
  const midX = (a.x + b.x) / 2;
  const midY = Math.min(a.y, b.y) - lift;
  return `M ${a.x} ${a.y} Q ${midX} ${midY} ${b.x} ${b.y}`;
}

function paintMap(story) {
  const zones = story.map_layers.nodes
    .filter((node) => node.type === 'risk_zone')
    .map((node) => `<circle cx="${node.x}" cy="${node.y}" r="${node.radius}" fill="${toneColor(node.tone, node.type)}" opacity=".12" stroke="${toneColor(node.tone, node.type)}" stroke-width=".35" stroke-dasharray="2 2"></circle>`)
    .join('');
  const edges = story.map_layers.edges.map((edge, index) => {
    const source = nodeById(story, edge.source);
    const target = nodeById(story, edge.target);
    if (!source || !target) return '';
    const color = edge.type === 'accepted' ? '#3cf4a6' : '#ffc857';
    return `<path class="edge ${safe(edge.type)}" d="${curvePath(source, target, index)}" stroke="${color}" data-edge="${safe(edge.id)}"></path>`;
  }).join('');
  const nodes = story.map_layers.nodes
    .filter((node) => node.type !== 'risk_zone')
    .map((node) => {
      const radius = node.type === 'merchant_group' ? 3.15 : 2.55;
      const sub = node.type === 'merchant_group' ? `${node.orders || 0}单` : `w=${node.willingness || ''}`;
      return `
        <g class="node" data-node="${safe(node.id)}">
          <circle cx="${node.x}" cy="${node.y}" r="${radius}" fill="${toneColor(node.tone, node.type)}" stroke="rgba(255,255,255,.82)" stroke-width=".48"></circle>
          <text class="node-label" x="${node.x + 3.7}" y="${node.y + .6}">${safe(node.label)}</text>
          <text class="node-sub" x="${node.x + 3.7}" y="${node.y + 3.1}">${safe(sub)}</text>
        </g>
      `;
    }).join('');
  $('map-canvas').innerHTML = zones + edges + nodes;
  document.querySelectorAll('.node').forEach((node) => {
    node.addEventListener('click', () => selectDecision(node.dataset.node || ''));
  });
  $('map-legend').innerHTML = story.map_layers.legend.map((item) => `<span class="pill">${safe(item.label)}：${safe(item.meaning)}</span>`).join('');
}

function cardIndexFromNode(nodeId) {
  return Math.abs(String(nodeId).split('').reduce((sum, ch) => sum + ch.charCodeAt(0), 0)) % Math.max(1, currentStory.decision_cards.length);
}

function paintDecisions(story, activeIndex = 0) {
  $('decision-stack').innerHTML = story.decision_cards.map((card, index) => `
    <article class="decision-card ${index === activeIndex ? 'active' : ''}" data-card="${index}">
      <b>${safe(card.title)}</b>
      <p>${safe(card.decision)}</p>
      <p class="muted">${safe(card.rationale[0])}</p>
      <div class="evidence-grid">
        ${Object.entries(card.field_evidence).map(([key, value]) => `<div class="evidence"><span>${safe(key)}</span>${safe(value)}</div>`).join('')}
      </div>
    </article>
  `).join('');
}

function selectDecision(nodeId) {
  const index = cardIndexFromNode(nodeId);
  paintDecisions(currentStory, index);
  showToast(`已选中 ${nodeId}，右侧切换到对应调度解释。`);
}

function paintTimeline(story) {
  $('strategy-timeline').innerHTML = story.strategy_timeline.map((step) => `
    <div class="step ${step.status === 'active' ? 'active' : ''}">
      <b>${safe(step.title)}</b>
      <small>${safe(step.message)}</small>
      <small>${safe(step.evidence)}</small>
    </div>
  `).join('');
}

function paintBaseline(story) {
  const b = story.baseline_compare;
  $('baseline-compare').innerHTML = `
    <div class="compare-row"><span>贪心基线</span><b>${Number(b.greedy.cost || 0).toFixed(2)}</b></div>
    <div class="compare-row"><span>AutoSolver best</span><b>${Number(b.autosolver.cost || 0).toFixed(2)}</b></div>
    <div class="compare-row"><span>相对降本</span><b>${Number(b.improvement_pct || 0).toFixed(1)}%</b></div>
    <p class="muted">${safe(b.note)}</p>
  `;
}

function paintBusiness(story) {
  const value = story.business_value;
  $('business-value').innerHTML = `
    <div class="compare-row"><span>公式</span><b>${safe(value.formula)}</b></div>
    <div class="compare-row"><span>日订单量假设</span><b>${Number(value.daily_orders).toLocaleString('zh-CN')}</b></div>
    <div class="compare-row"><span>单均改善</span><b>${safe(value.unit_delta)}</b></div>
    <div class="compare-row"><span>日节省模拟</span><b>¥${Number(value.estimated_saving_yuan).toLocaleString('zh-CN')}</b></div>
    <p class="muted">${safe(value.disclaimer)}</p>
  `;
}

function paintBoundary(story) {
  $('boundary-copy').textContent = `${story.data_boundary.real_fields.join('、')} 为真实赛题字段或派生解释指标；${story.data_boundary.demo_fields.join('、')} 为演示层。`;
}

function paintStory(story) {
  currentStory = story;
  paintHero(story);
  paintScene(story);
  paintMap(story);
  paintDecisions(story);
  paintTimeline(story);
  paintBaseline(story);
  paintBusiness(story);
  paintBoundary(story);
}

function showToast(message) {
  const toast = $('toast');
  toast.textContent = message;
  toast.classList.add('show');
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.remove('show'), 2200);
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
  $('status').textContent = '推理中';
  const caseId = $('case-select').value || 'large_seed301';
  const budget = $('budget').value || '10';
  try {
    const payload = await fetch(`/api/run?case=${encodeURIComponent(caseId)}&budget=${encodeURIComponent(budget)}`).then((res) => res.json());
    if (payload.status !== 'ok') throw new Error(payload.error || 'run failed');
    paintStory(payload.story);
    $('status').textContent = '运行完成';
    showToast(`已加载 ${caseId} 的 Agent 报告。`);
  } catch (error) {
    $('status').textContent = `运行失败：${error.message}`;
    showToast(error.message);
  } finally {
    button.disabled = false;
  }
}

$('run-button').addEventListener('click', runCase);
$('reload-button').addEventListener('click', loadCases);
paintStory(DEFAULT_STORY);
loadCases().catch((error) => showToast(error.message));
</script>
</body>
</html>"""
    return template.replace("__DEFAULT_STORY__", placeholder)


class DispatchV2RequestHandler(BaseHTTPRequestHandler):
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
                self._send_html(render_dispatch_index_v2())
                return
            if parsed.path == "/api/cases":
                self._send_json({"status": "ok", "cases": list_cases()})
                return
            if parsed.path == "/api/run":
                qs = parse_qs(parsed.query)
                case_id = qs.get("case", ["large_seed301"])[0]
                budget_s = float(qs.get("budget", ["10"])[0])
                self._send_json(build_dispatch_payload_v2(case_id, budget_s=budget_s))
                return
            self._send_json({"status": "error", "error": "not found"}, status=404)
        except Exception as exc:
            self._send_json(
                {"status": "error", "error": str(exc), "traceback": traceback.format_exc()},
                status=500,
            )

    def log_message(self, format: str, *args: object) -> None:
        print(f"[dispatch-v2] {self.address_string()} - {format % args}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local AutoSolver dispatch command center v2 demo.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8767)
    args = parser.parse_args(argv)
    server = ThreadingHTTPServer((args.host, args.port), DispatchV2RequestHandler)
    print(f"AutoSolver Dispatch Command Center v2 running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
