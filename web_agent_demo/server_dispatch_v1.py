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

from web_agent_demo.dispatch_story_v1 import build_dispatch_story
from web_agent_demo.server import list_cases, run_case_agent


def build_dispatch_payload(case_id: str, budget_s: float = 10.0) -> dict[str, object]:
    report = run_case_agent(case_id, budget_s=budget_s)
    return {"status": "ok", "report": report, "story": build_dispatch_story(report)}


def render_dispatch_index() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AutoSolver Agent 即时履约智能调度指挥舱</title>
  <style>
    :root {
      --bg: #071713;
      --panel: rgba(8, 34, 31, .82);
      --panel-2: rgba(10, 48, 44, .72);
      --line: rgba(97, 255, 211, .18);
      --text: #e9fff8;
      --muted: #91b8ad;
      --green: #46f0a8;
      --cyan: #43d5ff;
      --orange: #ff9f43;
      --yellow: #f4dc61;
      --red: #ff6b6b;
      --shadow: 0 28px 90px rgba(0, 0, 0, .42);
      --mono: "SFMono-Regular", "Cascadia Code", Consolas, monospace;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      color: var(--text);
      font-family: "Avenir Next", "PingFang SC", "Hiragino Sans GB", sans-serif;
      background:
        radial-gradient(circle at 20% 18%, rgba(67, 213, 255, .18), transparent 30rem),
        radial-gradient(circle at 72% 12%, rgba(70, 240, 168, .18), transparent 32rem),
        linear-gradient(135deg, #06100f 0%, #09231f 48%, #04110f 100%);
    }
    body:before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image:
        linear-gradient(rgba(97,255,211,.07) 1px, transparent 1px),
        linear-gradient(90deg, rgba(97,255,211,.06) 1px, transparent 1px);
      background-size: 48px 48px;
      mask-image: linear-gradient(to bottom, black, transparent 88%);
    }
    main { width: min(1540px, calc(100vw - 28px)); margin: 0 auto; padding: 18px 0 28px; position: relative; }
    .shell { display: grid; gap: 12px; }
    .card {
      border: 1px solid var(--line);
      background: var(--panel);
      box-shadow: var(--shadow);
      border-radius: 22px;
      backdrop-filter: blur(18px);
    }
    .top {
      display: grid;
      grid-template-columns: 310px 1fr 380px;
      gap: 12px;
      align-items: stretch;
    }
    .brand { padding: 18px; }
    .brand small { color: var(--green); font-weight: 900; letter-spacing: .15em; text-transform: uppercase; }
    h1 { margin: 9px 0 7px; font-size: 30px; letter-spacing: -0.05em; }
    .brand p, .muted { color: var(--muted); line-height: 1.65; margin: 0; }
    .controls { padding: 16px; display: grid; gap: 10px; }
    select, input, button {
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px 13px;
      color: var(--text);
      background: rgba(2, 16, 15, .76);
      font-size: 15px;
    }
    button {
      border: 0;
      cursor: pointer;
      font-weight: 900;
      background: linear-gradient(135deg, #12a66b, #095234);
      box-shadow: 0 16px 38px rgba(18,166,107,.28);
    }
    button.secondary { background: linear-gradient(135deg, #245d73, #102d3a); }
    button:disabled { opacity: .62; cursor: wait; }
    .control-row { display: grid; grid-template-columns: 1fr 100px; gap: 8px; }
    .status { color: var(--yellow); font-weight: 900; }
    .kpis { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 10px; padding: 14px; }
    .kpi { min-height: 92px; border: 1px solid var(--line); background: rgba(3, 18, 18, .62); border-radius: 18px; padding: 13px; }
    .kpi b { display: block; font-size: 30px; letter-spacing: -.04em; }
    .kpi span { color: var(--muted); font-size: 12px; font-weight: 800; }
    .workbench { display: grid; grid-template-columns: 265px minmax(0, 1fr) 330px; gap: 12px; }
    .side, .inspector, .map-panel, .bottom-panel { padding: 14px; }
    h2 { margin: 0 0 11px; font-size: 18px; letter-spacing: -.03em; }
    .scenario { display: grid; gap: 9px; }
    .scenario button {
      text-align: left;
      border: 1px solid var(--line);
      background: rgba(6, 31, 29, .78);
      box-shadow: none;
      display: grid;
      gap: 4px;
    }
    .scenario button.active { outline: 2px solid rgba(70,240,168,.42); }
    .scenario em { color: var(--muted); font-size: 12px; font-style: normal; line-height: 1.45; }
    .map-frame {
      position: relative;
      height: 560px;
      border: 1px solid var(--line);
      border-radius: 18px;
      overflow: hidden;
      background:
        radial-gradient(circle at 50% 45%, rgba(67,213,255,.18), transparent 22rem),
        linear-gradient(135deg, rgba(9,46,51,.9), rgba(3,16,23,.94));
    }
    .map-frame:before {
      content: "";
      position: absolute;
      inset: 0;
      background-image:
        linear-gradient(30deg, transparent 47%, rgba(80,255,212,.11) 49%, transparent 51%),
        linear-gradient(150deg, transparent 48%, rgba(255,255,255,.07) 50%, transparent 52%);
      background-size: 160px 95px, 140px 110px;
      opacity: .55;
    }
    svg { position: absolute; inset: 0; width: 100%; height: 100%; }
    .node { cursor: pointer; }
    .edge { fill: none; stroke-width: 2.8; stroke-dasharray: 8 8; animation: dash 2.4s linear infinite; opacity: .88; }
    .edge.accepted-dispatch { stroke: var(--green); stroke-width: 4; }
    .edge.candidate-dispatch { stroke: var(--yellow); }
    @keyframes dash { to { stroke-dashoffset: -32; } }
    .node-label { fill: var(--text); font-size: 2.2px; font-weight: 800; pointer-events: none; paint-order: stroke; stroke: rgba(0,0,0,.72); stroke-width: .55px; }
    .legend {
      position: absolute;
      left: 12px;
      top: 12px;
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
    }
    .pill { border: 1px solid var(--line); background: rgba(0,0,0,.24); border-radius: 999px; padding: 6px 8px; }
    .inspect-card { border: 1px solid var(--line); background: rgba(3,18,18,.56); border-radius: 16px; padding: 12px; margin-bottom: 10px; }
    .inspect-card b { display: block; margin-bottom: 7px; }
    .inspect-card ul { padding-left: 18px; margin: 8px 0 0; color: var(--muted); line-height: 1.55; }
    .metric-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 7px; }
    .metric { border: 1px solid var(--line); border-radius: 12px; padding: 9px; background: rgba(0,0,0,.18); }
    .metric span { display: block; color: var(--muted); font-size: 11px; }
    .bottom { display: grid; grid-template-columns: 1.1fr 1fr 1fr; gap: 12px; }
    .flow { display: flex; gap: 8px; flex-wrap: wrap; }
    .step { flex: 1; min-width: 92px; border: 1px solid var(--line); border-radius: 15px; padding: 10px; background: rgba(6,31,29,.68); }
    .step.active { border-color: var(--yellow); }
    .comparison table { width: 100%; border-collapse: collapse; color: var(--muted); }
    .comparison td { padding: 7px 0; border-bottom: 1px solid var(--line); }
    .comparison td:last-child { text-align: right; color: var(--text); font-family: var(--mono); }
    #data-boundary { font-size: 12px; color: var(--muted); line-height: 1.65; }
    @media (max-width: 1100px) {
      .top, .workbench, .bottom { grid-template-columns: 1fr; }
      .kpis { grid-template-columns: repeat(2, 1fr); }
      .map-frame { height: 480px; }
    }
  </style>
</head>
<body>
<main class="shell">
  <section class="top">
    <div class="brand card">
      <small>AutoSolver Agent</small>
      <h1>即时履约智能调度指挥舱</h1>
      <p>10 秒内生成高可靠调度方案，展示骑手无人接单风险、调度成本、策略流动与商业价值。地图坐标为演示映射，核心指标来自脱敏样例和 Agent 报告。</p>
    </div>
    <div class="card kpis" id="kpis"></div>
    <div class="controls card">
      <div class="control-row">
        <select id="case-select"></select>
        <input id="budget" value="10" inputmode="decimal">
      </div>
      <button id="run">开始推理</button>
      <button id="reload" class="secondary">刷新用例</button>
      <div class="status" id="status">等待启动</div>
    </div>
  </section>

  <section class="workbench">
    <aside class="side card">
      <h2>业务场景选择</h2>
      <div class="scenario" id="scenarios"></div>
      <div class="inspect-card" id="data-boundary">
        <b>数据边界</b>
        脱敏业务场景沙盘：任务/骑手/意愿/score/expected_cost 为真实赛题字段或派生解释指标；地图坐标为演示映射，天气/商圈/金额为答辩解释层。
      </div>
    </aside>
    <section class="map-panel card">
      <h2>调度可视化地图</h2>
      <div class="map-frame">
        <div class="legend">
          <span class="pill">橙色：商家/任务组</span>
          <span class="pill">绿色：骑手</span>
          <span class="pill">虚线：候选派单</span>
          <span class="pill">亮线：已采纳 best-so-far</span>
        </div>
        <svg id="dispatch-map" viewBox="0 0 100 100" role="img" aria-label="dispatch map"></svg>
      </div>
    </section>
    <aside class="inspector card">
      <h2>决策解释</h2>
      <div id="decision-panel" class="inspect-card">点击地图节点或先点击开始推理。</div>
      <div class="inspect-card">
        <b>当前口径</b>
        <p class="muted">多派不是“指定唯一骑手”，而是向多个候选骑手发出派单关系，用至少一人接单概率降低无人接单风险。</p>
      </div>
    </aside>
  </section>

  <section class="bottom">
    <div class="bottom-panel card">
      <h2>Agent 工作流程</h2>
      <div class="flow" id="agent-flow"></div>
    </div>
    <div class="bottom-panel card comparison">
      <h2>Baseline vs AutoSolver</h2>
      <table id="baseline-table"></table>
    </div>
    <div class="bottom-panel card">
      <h2>商业价值 ROI 模拟器</h2>
      <div id="roi-panel" class="muted">运行后展示商业金额换算。商业金额换算为演示假设，不等同官方成绩或真实财务结果。</div>
    </div>
  </section>
</main>

<script>
const $ = (id) => document.getElementById(id);
let activeStory = null;
function safe(value) {
  return String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
}
async function loadCases() {
  const payload = await fetch('/api/cases').then(r => r.json());
  $('case-select').innerHTML = payload.cases.map(c => `<option value="${safe(c.id)}">${safe(c.name)} · ${safe(c.type)}</option>`).join('');
}
function paintKpis(story) {
  $('kpis').innerHTML = story.kpis.map(k => `<div class="kpi"><span>${safe(k.label)}</span><b>${safe(k.value)}</b><span>${safe(k.hint)}</span></div>`).join('');
}
function paintScenarios(story) {
  $('scenarios').innerHTML = story.scenario_tags.map((s, i) => `<button class="${i === 0 ? 'active' : ''}"><strong>${safe(i + 1)} ${safe(s.label)}</strong><em>${safe(s.reason)}</em></button>`).join('');
}
function nodeById(story, id) {
  return story.map.nodes.find(n => n.id === id);
}
function colorFor(item) {
  if (item.type === 'merchant') return 'var(--orange)';
  if (item.type === 'scene') return 'var(--yellow)';
  if (item.tone === 'cyan') return 'var(--cyan)';
  return 'var(--green)';
}
function paintMap(story) {
  const lines = story.map.edges.map(e => {
    const a = nodeById(story, e.source);
    const b = nodeById(story, e.target);
    if (!a || !b) return '';
    return `<path class="edge ${safe(e.kind)}" d="M ${a.x} ${a.y} C ${(a.x+b.x)/2} ${Math.min(a.y,b.y)-12}, ${(a.x+b.x)/2} ${Math.max(a.y,b.y)+10}, ${b.x} ${b.y}" />`;
  }).join('');
  const nodes = story.map.nodes.map(n => `
    <g class="node" data-node="${safe(n.id)}">
      <circle cx="${n.x}" cy="${n.y}" r="${n.type === 'scene' ? 3.9 : 2.8}" fill="${colorFor(n)}" stroke="rgba(255,255,255,.75)" stroke-width=".45"></circle>
      <text class="node-label" x="${n.x + 3.6}" y="${n.y + 1.4}">${safe(n.label)}</text>
    </g>
  `).join('');
  $('dispatch-map').innerHTML = lines + nodes;
  document.querySelectorAll('.node').forEach(node => {
    node.addEventListener('click', () => paintDecision(story, node.dataset.node));
  });
}
function paintDecision(story, nodeId) {
  const decision = story.decisions[Math.abs(String(nodeId || '').split('').reduce((a, c) => a + c.charCodeAt(0), 0)) % story.decisions.length];
  $('decision-panel').innerHTML = `
    <b>${safe(decision.title)}</b>
    <p class="muted">${safe(decision.subtitle)}</p>
    <ul>${decision.bullets.map(item => `<li>${safe(item)}</li>`).join('')}</ul>
    <div class="metric-grid">
      ${Object.entries(decision.metrics).map(([k, v]) => `<div class="metric"><span>${safe(k)}</span>${safe(v)}</div>`).join('')}
    </div>
  `;
}
function paintFlow(story) {
  $('agent-flow').innerHTML = story.agent_flow.map(step => `<div class="step ${step.status === 'active' ? 'active' : ''}"><b>${safe(step.label)}</b><br><span class="muted">${safe(step.status)}</span></div>`).join('');
}
function paintBaseline(story) {
  const b = story.baseline;
  $('baseline-table').innerHTML = `
    <tr><td>贪心基线</td><td>${Number(b.cost || 0).toFixed(2)}</td></tr>
    <tr><td>AutoSolver best</td><td>${Number(b.best_cost || 0).toFixed(2)}</td></tr>
    <tr><td>相对降本</td><td>${Number(b.delta_pct || 0).toFixed(1)}%</td></tr>
    <tr><td>边界说明</td><td>解释指标</td></tr>
  `;
}
function paintRoi(story) {
  $('roi-panel').innerHTML = `<b>¥${Number(story.roi.saving_yuan).toLocaleString('zh-CN')}</b><p>${safe(story.roi.formula)}</p><p>${safe(story.roi.disclaimer)}</p>`;
}
function paintStory(story) {
  activeStory = story;
  paintKpis(story);
  paintScenarios(story);
  paintMap(story);
  paintDecision(story, 'M-01');
  paintFlow(story);
  paintBaseline(story);
  paintRoi(story);
}
async function run() {
  $('run').disabled = true;
  $('status').textContent = '推理中';
  const caseId = $('case-select').value || 'large_seed301';
  const budget = $('budget').value || '10';
  try {
    const payload = await fetch(`/api/run?case=${encodeURIComponent(caseId)}&budget=${encodeURIComponent(budget)}`).then(r => r.json());
    if (payload.status !== 'ok') throw new Error(payload.error || 'run failed');
    paintStory(payload.story);
    $('status').textContent = '运行完成';
  } catch (err) {
    $('status').textContent = '运行失败：' + err.message;
  } finally {
    $('run').disabled = false;
  }
}
$('run').addEventListener('click', run);
$('reload').addEventListener('click', loadCases);
loadCases();
</script>
</body>
</html>"""


class DispatchRequestHandler(BaseHTTPRequestHandler):
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
                self._send_html(render_dispatch_index())
                return
            if parsed.path == "/api/cases":
                self._send_json({"status": "ok", "cases": list_cases()})
                return
            if parsed.path == "/api/run":
                qs = parse_qs(parsed.query)
                case_id = qs.get("case", ["large_seed301"])[0]
                budget_s = float(qs.get("budget", ["10"])[0])
                self._send_json(build_dispatch_payload(case_id, budget_s=budget_s))
                return
            self._send_json({"status": "error", "error": "not found"}, status=404)
        except Exception as exc:
            self._send_json(
                {"status": "error", "error": str(exc), "traceback": traceback.format_exc()},
                status=500,
            )

    def log_message(self, format: str, *args: object) -> None:
        print(f"[dispatch-v1] {self.address_string()} - {format % args}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local AutoSolver dispatch command center demo.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args(argv)
    server = ThreadingHTTPServer((args.host, args.port), DispatchRequestHandler)
    print(f"AutoSolver Dispatch Command Center v1 running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
