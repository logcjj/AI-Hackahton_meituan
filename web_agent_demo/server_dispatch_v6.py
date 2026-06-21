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

from web_agent_demo.dispatch_story_v6 import build_dispatch_story_v6, build_placeholder_story_v6
from web_agent_demo.server import list_cases, run_case_agent
from web_agent_demo.server_dispatch_v5 import render_dispatch_index_v5


def build_dispatch_payload_v6(case_id: str, budget_s: float = 10.0) -> dict[str, object]:
    report = run_case_agent(case_id, budget_s=budget_s)
    return {"status": "ok", "report": report, "story": build_dispatch_story_v6(report)}


def _replace_default_story(html: str, story: dict[str, object]) -> str:
    start = html.index("const DEFAULT_STORY = ") + len("const DEFAULT_STORY = ")
    end = html.index(";\nconst $ =", start)
    return html[:start] + json.dumps(story, ensure_ascii=False) + html[end:]


V6_CSS = """
    /* v6-exact-target-shell: 进一步贴近目标图的一屏答辩大屏。 */
    .v6-exact-target-shell {
      --target-panel: rgba(4, 20, 33, .88);
      --target-line: rgba(74, 211, 255, .28);
      --target-gold: #ffd43b;
      --target-mint: #1cf4d2;
    }
    .v6-exact-target-shell .top-row {
      height: 114px;
      grid-template-columns: 625px 1fr 338px;
      margin-bottom: 12px;
    }
    .v6-exact-target-shell h1 {
      font-size: 34px;
      letter-spacing: -.05em;
    }
    .v6-exact-target-shell #top-kpi-strip {
      height: 116px;
      margin-bottom: 12px;
    }
    .v6-exact-target-shell .kpi {
      padding: 15px 20px;
    }
    .v6-exact-target-shell .kpi b {
      font-size: 36px;
    }
    .v6-exact-target-shell .main-row {
      height: 552px;
      grid-template-columns: 292px 1fr 420px;
      margin-bottom: 12px;
    }
    .v6-exact-target-shell aside.panel-pad {
      padding: 12px;
    }
    .v6-exact-target-shell #left-scene-rail {
      gap: 8px;
      margin-bottom: 10px;
    }
    .v6-scene-card {
      min-height: 60px;
      border: 1px solid rgba(74, 211, 255, .22);
      border-radius: 11px;
      background: linear-gradient(90deg, rgba(4, 28, 46, .92), rgba(4, 16, 28, .62));
      display: grid;
      grid-template-columns: 42px 1fr;
      align-items: center;
      gap: 9px;
      padding: 8px;
      cursor: pointer;
      position: relative;
      overflow: hidden;
    }
    .v6-scene-card:before {
      content: "";
      position: absolute;
      inset: 0;
      background: linear-gradient(90deg, rgba(255, 212, 59, .16), transparent 52%);
      opacity: 0;
      transition: opacity .2s ease;
    }
    .v6-scene-card.active {
      border-color: rgba(255, 212, 59, .84);
      box-shadow: inset 0 0 0 1px rgba(255, 212, 59, .25), 0 0 18px rgba(255, 212, 59, .12);
    }
    .v6-scene-card.active:before {
      opacity: 1;
    }
    .v6-scene-card .v6-icon {
      width: 34px;
      height: 34px;
      border-radius: 9px;
      display: grid;
      place-items: center;
      color: #06131b;
      background: linear-gradient(135deg, #ffd43b, #ff8f2a);
      font-weight: 1000;
      position: relative;
      z-index: 1;
    }
    .v6-scene-card b, .v6-scene-card small {
      position: relative;
      z-index: 1;
    }
    .v6-scene-card b {
      display: block;
      color: #f2fcff;
      font-size: 14px;
    }
    .v6-scene-card small {
      display: block;
      color: #8fb1bf;
      line-height: 1.24;
    }
    .v6-exact-target-shell #map-stage {
      height: 494px;
      border-color: rgba(74, 211, 255, .34);
      background:
        radial-gradient(circle at 58% 39%, rgba(255, 212, 59, .18), transparent 10.5rem),
        radial-gradient(circle at 77% 70%, rgba(28, 244, 210, .17), transparent 11rem),
        linear-gradient(145deg, rgba(7, 38, 64, .96), rgba(1, 9, 19, .99));
    }
    .v6-exact-target-shell #map-stage[data-focus="G-023"] {
      box-shadow: inset 0 0 0 1px rgba(255, 212, 59, .46), inset 0 0 95px rgba(255, 212, 59, .09);
    }
    .v6-exact-target-shell #map-stage[data-focus="G-030"] {
      box-shadow: inset 0 0 0 1px rgba(255, 107, 42, .46), inset 0 0 95px rgba(255, 107, 42, .09);
    }
    .v6-exact-target-shell #map-stage:after {
      content: "地图聚焦模式";
      position: absolute;
      left: 54px;
      bottom: 16px;
      color: rgba(198, 251, 255, .68);
      font-size: 12px;
      letter-spacing: .12em;
      z-index: 2;
    }
    .v6-exact-target-shell #right-decision-panel {
      padding: 12px;
      gap: 8px;
    }
    .v6-exact-target-shell .decision-box {
      padding: 9px;
      font-size: 12px;
    }
    .v6-exact-target-shell .bottom-row {
      height: 236px;
      grid-template-columns: 1.1fr .7fr 1.03fr .82fr 1.16fr;
      gap: 12px;
    }
    .v6-exact-target-shell .bottom-card {
      padding: 11px;
    }
    .v6-goal-box {
      border: 1px solid rgba(74, 211, 255, .2);
      border-radius: 10px;
      padding: 8px;
      margin-top: 8px;
      background: rgba(54, 199, 255, .05);
      color: #9ddae5;
      font-size: 12px;
      line-height: 1.42;
    }
    .v6-goal-box b {
      color: #ffd43b;
      display: block;
      margin-bottom: 4px;
    }
    .v6-solver-card {
      margin-top: 8px;
      border: 1px solid rgba(28, 244, 210, .42);
      border-radius: 12px;
      padding: 10px;
      background: radial-gradient(circle at 84% 50%, rgba(56, 242, 156, .18), transparent 4rem), rgba(28, 244, 210, .055);
      color: #9fd6df;
      font-size: 12px;
      line-height: 1.42;
    }
    .v6-solver-card b {
      display: block;
      color: #38f29c;
      font-size: 18px;
      margin-bottom: 4px;
    }
    .v6-solver-card em {
      color: #ffd43b;
      font-style: normal;
    }
    .v6-operator-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 7px;
      margin-top: 7px;
    }
    .v6-operator-grid .op {
      border: 1px solid rgba(74, 211, 255, .18);
      border-radius: 9px;
      padding: 7px;
      background: rgba(0, 0, 0, .16);
      color: #91aeba;
      font-size: 11px;
    }
    .v6-operator-grid .op b {
      display: block;
      color: #38f29c;
      font-size: 16px;
      margin-top: 2px;
    }
    .v6-exact-target-shell .review-evidence-card {
      display: none !important;
    }
"""


V6_JS = """
const V6_SOLVER_ANCHOR = '<div data-testid="v6-solver-card"></div>';
function updateScaleV6() {
  const fitScale = Math.min((window.innerWidth - 20) / 1920, (window.innerHeight - 16) / 1080);
  const scale = Math.min(1, Math.max(0.34, fitScale));
  document.documentElement.style.setProperty('--stage-scale', scale.toFixed(4));
}
updateScale = updateScaleV6;
function v6Icon(label) {
  const icons = { bars: '▥', rider: '●', building: '▦', layers: '▰', shop: '✦' };
  return icons[label] || '●';
}
function renderV6ScenarioRail(story) {
  const rail = $('left-scene-rail');
  if (!rail) return;
  rail.innerHTML = (story.scenario_focus_cards || []).map((item, index) => `
    <div class="v6-scene-card ${index === 0 ? 'active' : ''}" role="button" tabindex="0" data-focus-order="${v5Html(item.focus_order)}">
      <div class="v6-icon">${v6Icon(item.icon)}</div>
      <div><b>${v5Html(item.rank)} ${v5Html(item.label)}</b><small>${v5Html(item.signal)} · ${v5Html(item.risk)}</small></div>
    </div>
  `).join('');
  rail.querySelectorAll('.v6-scene-card').forEach((card) => {
    const orderId = card.dataset.focusOrder;
    const choose = () => focusScenarioArea(orderId, story);
    card.addEventListener('click', choose);
    card.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') choose();
    });
  });
}
function focusScenarioArea(orderGroupId, story) {
  if (!orderGroupId) return;
  document.querySelectorAll('.v6-scene-card').forEach((card) => {
    card.classList.toggle('active', card.dataset.focusOrder === orderGroupId);
  });
  $('map-stage')?.setAttribute('data-focus', orderGroupId);
  if (typeof selectOrderGroup === 'function') selectOrderGroup(orderGroupId, story);
}
function renderV6SolverEvidence(story) {
  const memory = $('strategy-memory');
  if (!memory || !memory.parentElement) return;
  const solver = story.solver_evidence || {};
  let target = document.querySelector('[data-testid="v6-solver-card"]');
  if (!target) {
    target = document.createElement('div');
    target.className = 'v6-solver-card';
    target.setAttribute('data-testid', 'v6-solver-card');
    memory.parentElement.appendChild(target);
  }
  target.innerHTML = `<b>${v5Html(solver.solver || 'AutoSolver')}</b><em>${v5Html(solver.status || '')}</em><br>${v5Html(solver.quality || '')}<br>${v5Html(solver.guardrail || '')}`;
}
function renderV6OperatorMatrix(story) {
  const roi = $('commercial-roi');
  if (!roi) return;
  const matrix = story.operator_matrix || [];
  roi.innerHTML = `<div class="v6-operator-grid">${matrix.map((item) => `<div class="op">${v5Html(item.label)}<b>${v5Html(item.value)}</b></div>`).join('')}</div>`;
}
function playDecisionTimeline(story) {
  const policy = $('policy-box');
  if (!policy) return;
  const brief = story.meeting_brief || {};
  policy.innerHTML = `<h2 style="margin-top:0">调度目标</h2><div class="v6-goal-box"><b>${v5Html(brief.agreed_direction || 'AI 自动判断')}</b>${v5Html(brief.pitch_priority || '')}</div><div class="v6-goal-box"><b>推荐 Agent 策略</b>${v5Html(story.ai_scene_judgement.recommended_policy)} · ${v5Html(brief.dispatch_semantics || '')}</div>`;
}
function enhanceV6TargetFidelity(story) {
  document.querySelector('.target-dashboard')?.classList.add('v6-exact-target-shell');
  renderV6ScenarioRail(story);
  playDecisionTimeline(story);
  renderV6OperatorMatrix(story);
  renderV6SolverEvidence(story);
  focusScenarioArea(((story.scenario_focus_cards || [])[0] || {}).focus_order, story);
}
const renderStoryV5ForV6 = renderStory;
renderStory = function renderStoryV6(story) {
  renderStoryV5ForV6(story);
  enhanceV6TargetFidelity(story);
};
"""


def render_dispatch_index_v6() -> str:
    html = render_dispatch_index_v5()
    html = _replace_default_story(html, build_placeholder_story_v6())
    html = html.replace(
        '<main class="target-dashboard v5-target-dashboard" data-stage="v5-target-dashboard">',
        '<main class="target-dashboard v5-target-dashboard v6-exact-target-shell" data-stage="v6-target-dashboard">',
    )
    html = html.replace('<h2>AI 场景识别</h2>', '<h2>业务场景选择</h2>', 1)
    html = html.replace('<div id="map-stage">', '<div id="map-stage" data-testid="v6-main-map">', 1)
    html = html.replace("AutoSolver Agent 即时履约智能调度指挥舱 v5", "AutoSolver Agent 即时履约智能调度指挥舱 v6", 1)
    html = html.replace("</style>", V6_CSS + "\n  </style>", 1)
    html = html.replace("window.addEventListener('resize', updateScale);", V6_JS + "\nwindow.addEventListener('resize', updateScale);", 1)
    return html


class DispatchV6RequestHandler(BaseHTTPRequestHandler):
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
                self._send_html(render_dispatch_index_v6())
                return
            if parsed.path == "/api/cases":
                self._send_json({"status": "ok", "cases": list_cases()})
                return
            if parsed.path == "/api/run":
                qs = parse_qs(parsed.query)
                case_id = qs.get("case", ["large_seed301"])[0]
                budget_s = float(qs.get("budget", ["10"])[0])
                self._send_json(build_dispatch_payload_v6(case_id, budget_s=budget_s))
                return
            self._send_json({"status": "error", "error": "not found"}, status=404)
        except Exception as exc:
            self._send_json(
                {"status": "error", "error": str(exc), "traceback": traceback.format_exc()},
                status=500,
            )

    def log_message(self, format: str, *args: object) -> None:
        print(f"[dispatch-v6] {self.address_string()} - {format % args}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local AutoSolver dispatch command center v6 demo.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8771)
    args = parser.parse_args(argv)
    server = ThreadingHTTPServer((args.host, args.port), DispatchV6RequestHandler)
    print(f"AutoSolver Dispatch Command Center v6 running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
