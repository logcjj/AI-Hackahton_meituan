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

from web_agent_demo.dispatch_story_v7 import build_dispatch_story_v7, build_placeholder_story_v7
from web_agent_demo.server import list_cases, run_case_agent
from web_agent_demo.server_dispatch_v6 import render_dispatch_index_v6


def build_dispatch_payload_v7(case_id: str, budget_s: float = 10.0) -> dict[str, object]:
    report = run_case_agent(case_id, budget_s=budget_s)
    return {"status": "ok", "report": report, "story": build_dispatch_story_v7(report)}


def _replace_default_story(html: str, story: dict[str, object]) -> str:
    start = html.index("const DEFAULT_STORY = ") + len("const DEFAULT_STORY = ")
    end = html.index(";\nconst $ =", start)
    return html[:start] + json.dumps(story, ensure_ascii=False) + html[end:]


V7_CSS = """
    /* v7-polish-shell: 目标图质感增强层。 */
    .v7-polish-shell {
      --v7-road: rgba(61, 151, 210, .34);
      --v7-road-soft: rgba(61, 151, 210, .16);
      --v7-river: rgba(32, 102, 159, .46);
      --v7-judge: rgba(255, 212, 59, .18);
    }
    .v7-polish-shell #map-stage {
      background:
        radial-gradient(circle at 58% 39%, rgba(255, 212, 59, .22), transparent 10.5rem),
        radial-gradient(circle at 77% 70%, rgba(28, 244, 210, .2), transparent 11rem),
        linear-gradient(145deg, rgba(6, 36, 61, .98), rgba(1, 8, 18, .99));
    }
    #v7-road-layer {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      z-index: 0;
      pointer-events: none;
      opacity: .95;
    }
    .v7-road {
      fill: none;
      vector-effect: non-scaling-stroke;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    .v7-road.major {
      stroke: var(--v7-road);
      filter: drop-shadow(0 0 3px rgba(54, 199, 255, .18));
    }
    .v7-road.minor {
      stroke: var(--v7-road-soft);
    }
    .v7-road.river {
      stroke: var(--v7-river);
      filter: drop-shadow(0 0 8px rgba(32, 102, 159, .34));
    }
    .v7-polish-shell #operation-map {
      z-index: 1;
    }
    .v7-kpi-micro {
      position: absolute;
      right: 14px;
      bottom: 10px;
      width: 92px;
      height: 26px;
      overflow: visible;
    }
    .v7-kpi-micro path {
      fill: none;
      stroke: #38f29c;
      stroke-width: 2.4;
      stroke-linecap: round;
      filter: drop-shadow(0 0 4px rgba(56, 242, 156, .35));
    }
    .v7-kpi-micro rect {
      fill: rgba(56, 242, 156, .22);
    }
    #v7-judge-ribbon {
      position: absolute;
      left: 305px;
      right: 432px;
      top: 103px;
      height: 28px;
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 8px;
      z-index: 3;
      pointer-events: none;
    }
    .v7-judge-pill {
      border: 1px solid rgba(255, 212, 59, .24);
      border-radius: 999px;
      background: linear-gradient(90deg, rgba(255, 212, 59, .11), rgba(28, 244, 210, .06));
      color: #bcecf4;
      font-size: 11px;
      padding: 5px 9px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      box-shadow: inset 0 0 12px rgba(255, 212, 59, .05);
    }
    .v7-judge-pill b {
      color: #ffd43b;
      margin-right: 5px;
    }
    #v7-decision-ticker {
      margin-top: 6px;
      border: 1px solid rgba(74, 211, 255, .18);
      border-radius: 9px;
      padding: 7px;
      background: rgba(0, 0, 0, .16);
      color: #93cbd5;
      font-size: 11px;
      line-height: 1.42;
    }
    #v7-decision-ticker b {
      color: #38f29c;
    }
    .v7-eliminate {
      animation: v7Eliminate .9s ease both;
    }
    @keyframes v7Eliminate {
      0% { opacity: 1; transform: translateY(0) scale(1); }
      60% { opacity: .45; transform: translateY(3px) scale(.98); }
      100% { opacity: .28; filter: grayscale(.65); }
    }
"""


V7_JS = """
const V7_ROAD_ANCHOR = '<svg id="v7-road-layer" data-testid="v7-road-layer"><path class="v7-road major"></path><path class="v7-road river"></path></svg>';
const V7_RIBBON_ANCHOR = '<div id="v7-judge-ribbon" data-testid="v7-judge-ribbon"></div>';
const V7_TICKER_ANCHOR = '<div id="v7-decision-ticker" data-testid="v7-decision-ticker"></div>';
const V7_KPI_MICRO_ANCHOR = '<svg class="v7-kpi-micro"></svg>';
function renderV7RoadNetwork(story) {
  const stage = $('map-stage');
  if (!stage) return;
  let layer = $('v7-road-layer');
  if (!layer) {
    layer = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    layer.setAttribute('id', 'v7-road-layer');
    layer.setAttribute('data-testid', 'v7-road-layer');
    layer.setAttribute('viewBox', '0 0 100 100');
    stage.insertBefore(layer, stage.firstChild);
  }
  layer.innerHTML = (story.map_road_layers || []).map((item) => `<path class="v7-road ${v5Html(item.kind)}" d="${v5Html(item.path)}" stroke-width="${v5Html(item.width)}"></path>`).join('');
}
function renderV7KpiMicroCharts() {
  document.querySelectorAll('#top-kpi-strip .kpi').forEach((card, index) => {
    card.querySelectorAll('.v7-kpi-micro').forEach((node) => node.remove());
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('class', 'v7-kpi-micro');
    svg.setAttribute('viewBox', '0 0 92 26');
    const bars = [6, 9, 5, 12, 10, 14, 8, 17, 13, 20].map((height, i) => `<rect x="${i * 8}" y="${26 - height}" width="4" height="${height}"></rect>`).join('');
    const lift = index % 2 === 0 ? 'M2 20 C15 18 19 13 31 14 S49 9 62 10 S75 5 90 4' : 'M2 8 C16 9 20 13 32 12 S50 16 63 15 S76 18 90 14';
    svg.innerHTML = `${bars}<path d="${lift}"></path>`;
    card.appendChild(svg);
  });
}
function renderV7JudgeRibbon(story) {
  let ribbon = $('v7-judge-ribbon');
  if (!ribbon) {
    ribbon = document.createElement('div');
    ribbon.id = 'v7-judge-ribbon';
    ribbon.setAttribute('data-testid', 'v7-judge-ribbon');
    document.querySelector('.target-dashboard')?.appendChild(ribbon);
  }
  ribbon.innerHTML = (story.judge_ribbon || []).map((item) => `<div class="v7-judge-pill"><b>${v5Html(item.dimension)}</b>${v5Html(item.hook)}</div>`).join('');
}
function renderV7DecisionTicker(story) {
  const panel = $('decision-panel');
  if (!panel) return;
  let ticker = $('v7-decision-ticker');
  if (!ticker) {
    ticker = document.createElement('div');
    ticker.id = 'v7-decision-ticker';
    ticker.setAttribute('data-testid', 'v7-decision-ticker');
    panel.appendChild(ticker);
  }
  const beats = (story.pitch_storyboard || []).slice(0, 3).map((item) => `${item.beat}: ${item.line}`).join(' / ');
  ticker.innerHTML = `<b>答辩故事线</b><br>${v5Html(beats)}`;
}
function triggerV7PlanElimination() {
  document.querySelectorAll('#plan-evaluation .eval').forEach((node) => {
    if (!node.textContent.includes('已命中')) node.classList.add('v7-eliminate');
  });
}
function enhanceV7Polish(story) {
  document.querySelector('.target-dashboard')?.classList.add('v7-polish-shell');
  renderV7RoadNetwork(story);
  renderV7KpiMicroCharts();
  renderV7JudgeRibbon(story);
  renderV7DecisionTicker(story);
  triggerV7PlanElimination();
}
const renderStoryV6ForV7 = renderStory;
renderStory = function renderStoryV7(story) {
  renderStoryV6ForV7(story);
  enhanceV7Polish(story);
};
"""


def render_dispatch_index_v7() -> str:
    html = render_dispatch_index_v6()
    html = _replace_default_story(html, build_placeholder_story_v7())
    html = html.replace(
        '<main class="target-dashboard v5-target-dashboard v6-exact-target-shell" data-stage="v6-target-dashboard">',
        '<main class="target-dashboard v5-target-dashboard v6-exact-target-shell v7-polish-shell" data-stage="v7-target-dashboard">',
    )
    html = html.replace("AutoSolver Agent 即时履约智能调度指挥舱 v6", "AutoSolver Agent 即时履约智能调度指挥舱 v7", 1)
    html = html.replace("</style>", V7_CSS + "\n  </style>", 1)
    html = html.replace("window.addEventListener('resize', updateScale);", V7_JS + "\nwindow.addEventListener('resize', updateScale);", 1)
    return html


class DispatchV7RequestHandler(BaseHTTPRequestHandler):
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
                self._send_html(render_dispatch_index_v7())
                return
            if parsed.path == "/api/cases":
                self._send_json({"status": "ok", "cases": list_cases()})
                return
            if parsed.path == "/api/run":
                qs = parse_qs(parsed.query)
                case_id = qs.get("case", ["large_seed301"])[0]
                budget_s = float(qs.get("budget", ["10"])[0])
                self._send_json(build_dispatch_payload_v7(case_id, budget_s=budget_s))
                return
            self._send_json({"status": "error", "error": "not found"}, status=404)
        except Exception as exc:
            self._send_json(
                {"status": "error", "error": str(exc), "traceback": traceback.format_exc()},
                status=500,
            )

    def log_message(self, format: str, *args: object) -> None:
        print(f"[dispatch-v7] {self.address_string()} - {format % args}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local AutoSolver dispatch command center v7 demo.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8772)
    args = parser.parse_args(argv)
    server = ThreadingHTTPServer((args.host, args.port), DispatchV7RequestHandler)
    print(f"AutoSolver Dispatch Command Center v7 running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
