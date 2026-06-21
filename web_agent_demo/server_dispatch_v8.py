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

from web_agent_demo.dispatch_story_v8 import build_dispatch_story_v8, build_placeholder_story_v8
from web_agent_demo.server import list_cases, run_case_agent
from web_agent_demo.server_dispatch_v7 import render_dispatch_index_v7


def build_dispatch_payload_v8(case_id: str, budget_s: float = 10.0) -> dict[str, object]:
    report = run_case_agent(case_id, budget_s=budget_s)
    return {"status": "ok", "report": report, "story": build_dispatch_story_v8(report)}


def _replace_default_story(html: str, story: dict[str, object]) -> str:
    start = html.index("const DEFAULT_STORY = ") + len("const DEFAULT_STORY = ")
    end = html.index(";\nconst $ =", start)
    return html[:start] + json.dumps(story, ensure_ascii=False) + html[end:]


V8_CSS = """
    /* v8-target-match-shell: 更贴近目标图的一屏运营指挥大屏。 */
    .v8-target-match-shell {
      --v8-frame: rgba(70, 214, 255, .34);
      --v8-frame-hot: rgba(255, 212, 59, .58);
      --v8-glow: rgba(28, 244, 210, .34);
      --v8-warn: rgba(255, 121, 56, .5);
      background:
        radial-gradient(circle at 50% 39%, rgba(255, 212, 59, .09), transparent 22rem),
        linear-gradient(180deg, rgba(14, 35, 62, .22), rgba(2, 11, 22, .04));
    }
    .v8-target-match-shell .card {
      box-shadow: inset 0 0 0 1px rgba(70, 214, 255, .08), 0 20px 64px rgba(0, 0, 0, .38);
    }
    .v8-target-match-shell .top-row {
      height: 112px;
      grid-template-columns: 560px 1fr 360px;
    }
    .v8-target-match-shell #top-kpi-strip {
      height: 118px;
      border-color: rgba(70, 214, 255, .28);
    }
    .v8-target-match-shell .main-row {
      height: 532px;
      grid-template-columns: 292px 1fr 430px;
    }
    .v8-target-match-shell #map-stage {
      height: 474px;
      background:
        radial-gradient(circle at 57% 42%, rgba(255, 211, 45, .2), transparent 9.5rem),
        radial-gradient(circle at 79% 69%, rgba(28, 244, 210, .16), transparent 10.5rem),
        linear-gradient(145deg, rgba(7, 37, 64, .99), rgba(0, 9, 20, .99));
    }
    .v8-target-match-shell .bottom-row {
      height: 236px;
      grid-template-columns: .95fr .98fr 1.06fr .9fr 1.08fr;
    }
    #v8-target-frame {
      position: absolute;
      inset: 14px;
      z-index: 9;
      pointer-events: none;
    }
    .v8-corner {
      position: absolute;
      width: 54px;
      height: 54px;
      border-color: var(--v8-frame-hot);
      filter: drop-shadow(0 0 12px rgba(255, 212, 59, .18));
    }
    .v8-corner.tl { left: 0; top: 0; border-left: 2px solid; border-top: 2px solid; }
    .v8-corner.tr { right: 0; top: 0; border-right: 2px solid; border-top: 2px solid; }
    .v8-corner.bl { left: 0; bottom: 0; border-left: 2px solid; border-bottom: 2px solid; }
    .v8-corner.br { right: 0; bottom: 0; border-right: 2px solid; border-bottom: 2px solid; }
    .v8-scanline {
      position: absolute;
      left: 250px;
      right: 250px;
      top: 126px;
      height: 1px;
      background: linear-gradient(90deg, transparent, rgba(70, 214, 255, .72), transparent);
      animation: v8Scan 4.6s ease-in-out infinite;
    }
    @keyframes v8Scan {
      50% { opacity: .35; transform: translateY(10px); }
    }
    .v8-heat-ring {
      position: absolute;
      width: 112px;
      height: 112px;
      border: 1px solid rgba(255, 212, 59, .46);
      border-radius: 50%;
      box-shadow: 0 0 36px rgba(255, 212, 59, .16), inset 0 0 26px rgba(255, 212, 59, .08);
      animation: v8Pulse 2.8s ease-in-out infinite;
    }
    .v8-heat-ring:nth-child(6) {
      border-color: rgba(28, 244, 210, .42);
      box-shadow: 0 0 36px rgba(28, 244, 210, .15), inset 0 0 26px rgba(28, 244, 210, .08);
      animation-delay: .7s;
    }
    .v8-heat-ring:nth-child(7) {
      border-color: rgba(255, 121, 56, .45);
      box-shadow: 0 0 36px rgba(255, 121, 56, .16), inset 0 0 26px rgba(255, 121, 56, .08);
      animation-delay: 1.1s;
    }
    @keyframes v8Pulse {
      50% { transform: scale(1.08); opacity: .56; }
    }
    #v8-flow-canvas {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      z-index: 2;
      pointer-events: none;
      overflow: visible;
    }
    .v8-flow-path {
      fill: none;
      stroke: rgba(28, 244, 210, .52);
      stroke-width: .62;
      stroke-dasharray: 3 3;
      animation: v8Flow 2.2s linear infinite;
      filter: drop-shadow(0 0 3px rgba(28, 244, 210, .45));
    }
    .v8-flow-path.warn {
      stroke: rgba(255, 212, 59, .62);
    }
    @keyframes v8Flow {
      to { stroke-dashoffset: -18; }
    }
    #v8-pitch-navigator {
      position: absolute;
      right: 30px;
      top: 140px;
      width: 382px;
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 6px;
      z-index: 8;
      pointer-events: none;
    }
    .v8-step {
      min-height: 46px;
      border: 1px solid rgba(70, 214, 255, .18);
      border-radius: 10px;
      background: linear-gradient(180deg, rgba(7, 28, 47, .88), rgba(1, 10, 20, .74));
      padding: 7px 8px;
      color: #9dcbd5;
      font-size: 10px;
      line-height: 1.22;
      box-shadow: inset 0 0 18px rgba(28, 244, 210, .04);
    }
    .v8-step b {
      color: #ffd43b;
      display: block;
      font-size: 11px;
      margin-bottom: 3px;
    }
    #v8-judge-matrix {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 8px;
      margin-top: 8px;
    }
    .v8-evidence-card {
      border: 1px solid rgba(70, 214, 255, .2);
      border-radius: 10px;
      padding: 8px;
      min-height: 76px;
      color: #a7cdd5;
      background: linear-gradient(180deg, rgba(9, 40, 62, .72), rgba(1, 10, 18, .52));
      font-size: 11px;
      line-height: 1.32;
    }
    .v8-evidence-card b {
      display: block;
      color: #38f29c;
      font-size: 13px;
      margin-bottom: 4px;
    }
    .v8-evidence-card em {
      display: block;
      color: #ffd43b;
      font-style: normal;
      margin-bottom: 4px;
    }
"""


V8_JS = """
const V8_FRAME_ANCHOR = '<div id="v8-target-frame" data-testid="v8-target-frame"><i class="v8-corner tl"></i><i class="v8-heat-ring"></i></div>';
const V8_PITCH_ANCHOR = '<div id="v8-pitch-navigator" data-testid="v8-pitch-navigator"></div>';
const V8_JUDGE_ANCHOR = '<div id="v8-judge-matrix" data-testid="v8-judge-matrix"><div class="v8-evidence-card"></div></div>';
const V8_FLOW_ANCHOR = '<svg id="v8-flow-canvas" data-testid="v8-flow-canvas"></svg>';
function ensureV8Element(id, html, parent) {
  let node = $(id);
  if (!node) {
    const wrap = document.createElement('div');
    wrap.innerHTML = html.trim();
    node = wrap.firstElementChild;
    parent.appendChild(node);
  }
  return node;
}
function renderV8TargetFrame(story) {
  const shell = document.querySelector('.target-dashboard');
  if (!shell) return;
  const frame = ensureV8Element('v8-target-frame', V8_FRAME_ANCHOR, shell);
  frame.innerHTML = [
    '<i class="v8-corner tl"></i>',
    '<i class="v8-corner tr"></i>',
    '<i class="v8-corner bl"></i>',
    '<i class="v8-corner br"></i>',
    '<i class="v8-scanline"></i>',
    '<i class="v8-heat-ring" style="left:940px;top:294px"></i>',
    '<i class="v8-heat-ring" style="left:1232px;top:525px"></i>',
    '<i class="v8-heat-ring" style="left:505px;top:420px"></i>'
  ].join('');
  frame.setAttribute('aria-label', story.target_screen_contract?.visual_language || 'target frame');
}
function renderV8PitchNavigator(story) {
  const shell = document.querySelector('.target-dashboard');
  if (!shell) return;
  const nav = ensureV8Element('v8-pitch-navigator', V8_PITCH_ANCHOR, shell);
  nav.innerHTML = (story.demo_runbook || []).map((item) => `<div class="v8-step"><b>${v5Html(item.step)} ${v5Html(item.title)}</b>${v5Html(item.line)}</div>`).join('');
}
function renderV8JudgeMatrix(story) {
  const review = $('review-alignment');
  if (!review) return;
  let matrix = $('v8-judge-matrix');
  if (!matrix) {
    matrix = document.createElement('div');
    matrix.id = 'v8-judge-matrix';
    matrix.setAttribute('data-testid', 'v8-judge-matrix');
    review.parentElement.appendChild(matrix);
  }
  matrix.innerHTML = (story.judge_evidence_matrix || []).map((item) => `<div class="v8-evidence-card"><b>${v5Html(item.dimension)}</b><em>${v5Html(item.metric)}</em>${v5Html(item.proof)}</div>`).join('');
}
function renderV8FlowCanvas(story) {
  const stage = $('map-stage');
  if (!stage) return;
  let canvas = $('v8-flow-canvas');
  if (!canvas) {
    canvas = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    canvas.setAttribute('id', 'v8-flow-canvas');
    canvas.setAttribute('data-testid', 'v8-flow-canvas');
    canvas.setAttribute('viewBox', '0 0 100 100');
    stage.appendChild(canvas);
  }
  const edges = (story.operation_map?.edges || []).slice(0, 12);
  canvas.innerHTML = edges.map((edge, index) => {
    const source = nodeById(story, edge.source);
    const target = nodeById(story, edge.target);
    if (!source || !target) return '';
    const bend = index % 2 === 0 ? 8 : -8;
    const klass = edge.type === 'allocated_plan' ? 'v8-flow-path' : 'v8-flow-path warn';
    const path = `M ${source.x} ${source.y} Q ${(source.x + target.x) / 2 + bend} ${(source.y + target.y) / 2 - 7} ${target.x} ${target.y}`;
    return `<path class="${klass}" d="${path}"></path>`;
  }).join('');
}
function enhanceV8TargetMatch(story) {
  document.querySelector('.target-dashboard')?.classList.add('v8-target-match-shell');
  renderV8TargetFrame(story);
  renderV8PitchNavigator(story);
  renderV8JudgeMatrix(story);
  renderV8FlowCanvas(story);
}
const renderStoryV7ForV8 = renderStory;
renderStory = function renderStoryV8(story) {
  renderStoryV7ForV8(story);
  enhanceV8TargetMatch(story);
};
"""


def render_dispatch_index_v8() -> str:
    html = render_dispatch_index_v7()
    html = _replace_default_story(html, build_placeholder_story_v8())
    html = html.replace(
        '<main class="target-dashboard v5-target-dashboard v6-exact-target-shell v7-polish-shell" data-stage="v7-target-dashboard">',
        '<main class="target-dashboard v5-target-dashboard v6-exact-target-shell v7-polish-shell v8-target-match-shell" data-stage="v8-target-dashboard">',
    )
    html = html.replace("AutoSolver Agent 即时履约智能调度指挥舱 v7", "AutoSolver Agent 即时履约智能调度指挥舱 v8", 1)
    html = html.replace("</style>", V8_CSS + "\n  </style>", 1)
    html = html.replace("window.addEventListener('resize', updateScale);", V8_JS + "\nwindow.addEventListener('resize', updateScale);", 1)
    return html


class DispatchV8RequestHandler(BaseHTTPRequestHandler):
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
                self._send_html(render_dispatch_index_v8())
                return
            if parsed.path == "/api/cases":
                self._send_json({"status": "ok", "cases": list_cases()})
                return
            if parsed.path == "/api/run":
                qs = parse_qs(parsed.query)
                case_id = qs.get("case", ["large_seed301"])[0]
                budget_s = float(qs.get("budget", ["10"])[0])
                self._send_json(build_dispatch_payload_v8(case_id, budget_s=budget_s))
                return
            self._send_json({"status": "error", "error": "not found"}, status=404)
        except Exception as exc:
            self._send_json(
                {"status": "error", "error": str(exc), "traceback": traceback.format_exc()},
                status=500,
            )

    def log_message(self, format: str, *args: object) -> None:
        print(f"[dispatch-v8] {self.address_string()} - {format % args}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local AutoSolver dispatch command center v8 demo.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8773)
    args = parser.parse_args(argv)
    server = ThreadingHTTPServer((args.host, args.port), DispatchV8RequestHandler)
    print(f"AutoSolver Dispatch Command Center v8 running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
