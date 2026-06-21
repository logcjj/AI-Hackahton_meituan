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

from web_agent_demo.dispatch_story_v9 import build_dispatch_story_v9, build_placeholder_story_v9
from web_agent_demo.server import list_cases, run_case_agent
from web_agent_demo.server_dispatch_v8 import render_dispatch_index_v8


def build_dispatch_payload_v9(case_id: str, budget_s: float = 10.0) -> dict[str, object]:
    report = run_case_agent(case_id, budget_s=budget_s)
    return {"status": "ok", "report": report, "story": build_dispatch_story_v9(report)}


def _replace_default_story(html: str, story: dict[str, object]) -> str:
    start = html.index("const DEFAULT_STORY = ") + len("const DEFAULT_STORY = ")
    end = html.index(";\nconst $ =", start)
    return html[:start] + json.dumps(story, ensure_ascii=False) + html[end:]


V9_CSS = """
    /* v9-density-shell: 目标图组件密度和答辩交互增强。 */
    .v9-density-shell {
      --v9-gold: #ffd43b;
      --v9-cyan: #1cf4d2;
      --v9-blue: #2cb7ff;
      --v9-panel: rgba(4, 20, 34, .74);
    }
    .v9-density-shell .scene-card,
    .v9-density-shell .v6-scene-card {
      position: relative;
      overflow: hidden;
      min-height: 74px;
      border-color: rgba(70, 214, 255, .22);
      background: linear-gradient(90deg, rgba(5, 28, 45, .86), rgba(2, 12, 22, .52));
    }
    .v9-density-shell .scene-card.active,
    .v9-density-shell .v6-scene-card.active {
      border-color: rgba(255, 212, 59, .76);
      box-shadow: inset 0 0 24px rgba(255, 212, 59, .08), 0 0 18px rgba(255, 212, 59, .08);
    }
    .v9-left-card-meter {
      position: absolute;
      left: 50px;
      right: 11px;
      bottom: 8px;
      height: 4px;
      border-radius: 999px;
      overflow: hidden;
      background: rgba(255, 255, 255, .08);
    }
    .v9-meter-bar {
      display: block;
      height: 100%;
      width: var(--v9-meter, 58%);
      border-radius: inherit;
      background: linear-gradient(90deg, var(--v9-gold), var(--v9-cyan));
      box-shadow: 0 0 10px rgba(28, 244, 210, .36);
    }
    #v9-mode-tabs {
      position: absolute;
      left: 610px;
      top: 20px;
      width: 610px;
      height: 34px;
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 8px;
      z-index: 10;
      pointer-events: none;
    }
    .v9-mode-tab {
      border: 1px solid rgba(70, 214, 255, .2);
      border-radius: 999px;
      background: linear-gradient(90deg, rgba(28, 244, 210, .1), rgba(255, 212, 59, .06));
      color: #aeeef5;
      font-size: 11px;
      padding: 8px 10px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .v9-mode-tab b {
      color: var(--v9-gold);
      margin-right: 5px;
    }
    #v9-map-toolbar {
      position: absolute;
      left: 14px;
      top: 14px;
      z-index: 6;
      display: grid;
      gap: 7px;
      pointer-events: none;
    }
    .v9-map-tool {
      width: 34px;
      height: 34px;
      display: grid;
      place-items: center;
      border: 1px solid rgba(70, 214, 255, .28);
      border-radius: 9px;
      background: rgba(0, 0, 0, .34);
      color: #9cecf2;
      font-family: var(--mono);
      font-size: 13px;
      box-shadow: inset 0 0 16px rgba(28, 244, 210, .05);
    }
    #v9-decision-lens {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 6px;
      margin-top: 6px;
    }
    .v9-lens {
      min-height: 52px;
      border: 1px solid rgba(70, 214, 255, .18);
      border-radius: 9px;
      padding: 7px;
      color: #91b9c3;
      background: linear-gradient(180deg, rgba(8, 36, 56, .72), rgba(0, 0, 0, .18));
      font-size: 10px;
      line-height: 1.25;
    }
    .v9-lens b {
      display: block;
      color: var(--v9-cyan);
      font-size: 11px;
      margin-bottom: 4px;
    }
    #v9-proof-dock {
      position: absolute;
      left: 278px;
      right: 20px;
      bottom: 13px;
      height: 38px;
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 8px;
      z-index: 8;
      pointer-events: none;
    }
    .v9-proof-chip {
      border: 1px solid rgba(70, 214, 255, .24);
      border-radius: 11px;
      background: rgba(1, 12, 22, .84);
      color: #a7d5dd;
      padding: 7px 9px;
      font-size: 11px;
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
      box-shadow: inset 0 0 18px rgba(28, 244, 210, .04);
    }
    .v9-proof-chip b {
      color: var(--v9-gold);
      margin-right: 6px;
    }
"""


V9_JS = """
const V9_LEFT_METER_ANCHOR = '<div data-testid="v9-left-card-meter" class="v9-left-card-meter"><i class="v9-meter-bar"></i></div>';
const V9_DECISION_LENS_ANCHOR = '<div id="v9-decision-lens" data-testid="v9-decision-lens"></div>';
const V9_PROOF_DOCK_ANCHOR = '<div id="v9-proof-dock" data-testid="v9-proof-dock"><span class="v9-proof-chip"></span></div>';
const V9_MODE_TABS_ANCHOR = '<div id="v9-mode-tabs" data-testid="v9-mode-tabs"></div>';
const V9_MAP_TOOLBAR_ANCHOR = '<div id="v9-map-toolbar" data-testid="v9-map-toolbar"></div>';
function renderV9SceneMeters(story) {
  const cards = document.querySelectorAll('#left-scene-rail .scene-card, #left-scene-rail .v6-scene-card');
  cards.forEach((card, index) => {
    let meter = card.querySelector('[data-testid="v9-left-card-meter"]');
    if (!meter) {
      const wrap = document.createElement('div');
      wrap.innerHTML = V9_LEFT_METER_ANCHOR;
      meter = wrap.firstElementChild;
      card.appendChild(meter);
    }
    const value = [92, 78, 64, 58, 46][index] || 52;
    meter.style.setProperty('--v9-meter', `${value}%`);
  });
}
function renderV9ModeTabs(story) {
  const shell = document.querySelector('.target-dashboard');
  if (!shell) return;
  let tabs = $('v9-mode-tabs');
  if (!tabs) {
    tabs = document.createElement('div');
    tabs.id = 'v9-mode-tabs';
    tabs.setAttribute('data-testid', 'v9-mode-tabs');
    shell.appendChild(tabs);
  }
  tabs.innerHTML = (story.pitch_mode_tabs || []).map((item) => `<div class="v9-mode-tab"><b>${v5Html(item.label)}</b>${v5Html(item.line)}</div>`).join('');
}
function renderV9MapToolbar() {
  const stage = $('map-stage');
  if (!stage) return;
  let toolbar = $('v9-map-toolbar');
  if (!toolbar) {
    toolbar = document.createElement('div');
    toolbar.id = 'v9-map-toolbar';
    toolbar.setAttribute('data-testid', 'v9-map-toolbar');
    stage.appendChild(toolbar);
  }
  toolbar.innerHTML = ['AI', '热', '线', '证'].map((item) => `<div class="v9-map-tool">${item}</div>`).join('');
}
function renderV9DecisionLens(story) {
  const panel = $('decision-panel');
  if (!panel) return;
  let lens = $('v9-decision-lens');
  if (!lens) {
    lens = document.createElement('div');
    lens.id = 'v9-decision-lens';
    lens.setAttribute('data-testid', 'v9-decision-lens');
    panel.appendChild(lens);
  }
  lens.innerHTML = (story.decision_lens || []).map((item) => `<div class="v9-lens"><b>${v5Html(item.label)}</b>${v5Html(item.value)}</div>`).join('');
}
function renderV9ProofDock(story) {
  const shell = document.querySelector('.target-dashboard');
  if (!shell) return;
  let dock = $('v9-proof-dock');
  if (!dock) {
    dock = document.createElement('div');
    dock.id = 'v9-proof-dock';
    dock.setAttribute('data-testid', 'v9-proof-dock');
    shell.appendChild(dock);
  }
  dock.innerHTML = (story.judge_zone_map || []).map((item) => `<div class="v9-proof-chip"><b>${v5Html(item.dimension)}</b>${v5Html(item.zone)}</div>`).join('');
}
function enhanceV9Density(story) {
  document.querySelector('.target-dashboard')?.classList.add('v9-density-shell');
  renderV9SceneMeters(story);
  renderV9ModeTabs(story);
  renderV9MapToolbar();
  renderV9DecisionLens(story);
  renderV9ProofDock(story);
}
const renderStoryV8ForV9 = renderStory;
renderStory = function renderStoryV9(story) {
  renderStoryV8ForV9(story);
  enhanceV9Density(story);
};
"""


def render_dispatch_index_v9() -> str:
    html = render_dispatch_index_v8()
    html = _replace_default_story(html, build_placeholder_story_v9())
    html = html.replace(
        '<main class="target-dashboard v5-target-dashboard v6-exact-target-shell v7-polish-shell v8-target-match-shell" data-stage="v8-target-dashboard">',
        '<main class="target-dashboard v5-target-dashboard v6-exact-target-shell v7-polish-shell v8-target-match-shell v9-density-shell" data-stage="v9-target-dashboard">',
    )
    html = html.replace("AutoSolver Agent 即时履约智能调度指挥舱 v8", "AutoSolver Agent 即时履约智能调度指挥舱 v9", 1)
    html = html.replace("</style>", V9_CSS + "\n  </style>", 1)
    html = html.replace("window.addEventListener('resize', updateScale);", V9_JS + "\nwindow.addEventListener('resize', updateScale);", 1)
    return html


class DispatchV9RequestHandler(BaseHTTPRequestHandler):
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
                self._send_html(render_dispatch_index_v9())
                return
            if parsed.path == "/api/cases":
                self._send_json({"status": "ok", "cases": list_cases()})
                return
            if parsed.path == "/api/run":
                qs = parse_qs(parsed.query)
                case_id = qs.get("case", ["large_seed301"])[0]
                budget_s = float(qs.get("budget", ["10"])[0])
                self._send_json(build_dispatch_payload_v9(case_id, budget_s=budget_s))
                return
            self._send_json({"status": "error", "error": "not found"}, status=404)
        except Exception as exc:
            self._send_json(
                {"status": "error", "error": str(exc), "traceback": traceback.format_exc()},
                status=500,
            )

    def log_message(self, format: str, *args: object) -> None:
        print(f"[dispatch-v9] {self.address_string()} - {format % args}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local AutoSolver dispatch command center v9 demo.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8774)
    args = parser.parse_args(argv)
    server = ThreadingHTTPServer((args.host, args.port), DispatchV9RequestHandler)
    print(f"AutoSolver Dispatch Command Center v9 running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
