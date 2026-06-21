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

from web_agent_demo.dispatch_story_v10 import build_dispatch_story_v10, build_placeholder_story_v10
from web_agent_demo.server import list_cases, run_case_agent
from web_agent_demo.server_dispatch_v9 import render_dispatch_index_v9


def build_dispatch_payload_v10(case_id: str, budget_s: float = 10.0) -> dict[str, object]:
    report = run_case_agent(case_id, budget_s=budget_s)
    return {"status": "ok", "report": report, "story": build_dispatch_story_v10(report)}


def _replace_default_story(html: str, story: dict[str, object]) -> str:
    start = html.index("const DEFAULT_STORY = ") + len("const DEFAULT_STORY = ")
    end = html.index(";\nconst $ =", start)
    return html[:start] + json.dumps(story, ensure_ascii=False) + html[end:]


V10_CSS = """
    /* v10-exact-narrative-shell: 目标图关键讲述层。 */
    .v10-exact-narrative-shell {
      --v10-orange: #ff7938;
      --v10-green: #38f29c;
      --v10-cyan: #1cf4d2;
      --v10-gold: #ffd43b;
      --v10-panel: rgba(4, 20, 34, .82);
    }
    #v10-top-alerts {
      position: absolute;
      right: 418px;
      top: 28px;
      width: 640px;
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 10px;
      z-index: 11;
      pointer-events: none;
    }
    .v10-alert-card {
      min-height: 58px;
      display: grid;
      grid-template-columns: 38px 1fr;
      gap: 9px;
      align-items: center;
      border: 1px solid rgba(70, 214, 255, .22);
      border-radius: 13px;
      background: linear-gradient(180deg, rgba(8, 34, 53, .86), rgba(2, 12, 22, .58));
      color: #b9dfe6;
      padding: 9px;
      box-shadow: inset 0 0 18px rgba(28, 244, 210, .04), 0 0 22px rgba(0, 0, 0, .2);
    }
    .v10-alert-icon {
      width: 36px;
      height: 36px;
      display: grid;
      place-items: center;
      border-radius: 50%;
      border: 1px solid currentColor;
      color: var(--v10-gold);
      background: rgba(255, 212, 59, .08);
      font-family: var(--mono);
      font-weight: 900;
    }
    .v10-alert-card b {
      display: block;
      color: var(--v10-gold);
      font-size: 13px;
      margin-bottom: 2px;
    }
    .v10-alert-card em {
      display: block;
      color: var(--v10-green);
      font-style: normal;
      font-size: 11px;
    }
    #v10-map-callout {
      position: absolute;
      right: 150px;
      top: 137px;
      width: 254px;
      z-index: 7;
      border: 1px solid rgba(70, 214, 255, .28);
      border-radius: 12px;
      background: rgba(1, 12, 22, .82);
      color: #a9d4dc;
      padding: 11px;
      font-size: 12px;
      line-height: 1.45;
      box-shadow: 0 16px 40px rgba(0, 0, 0, .28), inset 0 0 22px rgba(28, 244, 210, .04);
    }
    #v10-map-callout b {
      display: block;
      color: white;
      font-size: 15px;
      margin-bottom: 5px;
    }
    #v10-map-callout strong {
      color: var(--v10-gold);
    }
    #v10-decision-focus {
      margin-top: 7px;
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 7px;
    }
    .v10-focus-card {
      min-height: 54px;
      border: 1px solid rgba(70, 214, 255, .18);
      border-radius: 9px;
      background: rgba(0, 0, 0, .18);
      padding: 7px;
      color: #9bbfc8;
      font-size: 11px;
      line-height: 1.32;
    }
    .v10-focus-card b {
      display: block;
      color: var(--v10-cyan);
      margin-bottom: 3px;
    }
    #v10-data-truth-rail {
      position: absolute;
      left: 20px;
      right: 20px;
      bottom: 54px;
      height: 48px;
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 10px;
      z-index: 9;
      pointer-events: none;
    }
    .v10-truth-badge {
      border: 1px solid rgba(70, 214, 255, .2);
      border-radius: 12px;
      background: rgba(1, 12, 22, .86);
      color: #a8ced6;
      padding: 8px 10px;
      font-size: 11px;
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
    }
    .v10-truth-badge b {
      color: var(--v10-gold);
      margin-right: 7px;
    }
    #v10-presenter-script {
      position: absolute;
      left: 304px;
      right: 438px;
      bottom: 107px;
      height: 30px;
      z-index: 10;
      border: 1px solid rgba(255, 212, 59, .2);
      border-radius: 999px;
      background: linear-gradient(90deg, rgba(255, 212, 59, .12), rgba(28, 244, 210, .07));
      color: #d7f7fa;
      padding: 7px 14px;
      font-size: 12px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      pointer-events: none;
    }
    #v10-presenter-script b {
      color: var(--v10-gold);
      margin-right: 8px;
    }
"""


V10_JS = """
const V10_TOP_ALERTS_ANCHOR = '<div id="v10-top-alerts" data-testid="v10-top-alerts"><div class="v10-alert-card"></div></div>';
const V10_MAP_CALLOUT_ANCHOR = '<div id="v10-map-callout" data-testid="v10-map-callout"></div>';
const V10_DATA_TRUTH_ANCHOR = '<div id="v10-data-truth-rail" data-testid="v10-data-truth-rail"><div class="v10-truth-badge"></div></div>';
const V10_PRESENTER_ANCHOR = '<div id="v10-presenter-script" data-testid="v10-presenter-script"></div>';
const V10_DECISION_FOCUS_ANCHOR = '<div id="v10-decision-focus" data-testid="v10-decision-focus"></div>';
function v10ToneIcon(index) {
  return ['峰', '骑', '合'][index] || 'AI';
}
function renderV10TopAlerts(story) {
  const shell = document.querySelector('.target-dashboard');
  if (!shell) return;
  let target = $('v10-top-alerts');
  if (!target) {
    target = document.createElement('div');
    target.id = 'v10-top-alerts';
    target.setAttribute('data-testid', 'v10-top-alerts');
    shell.appendChild(target);
  }
  target.innerHTML = (story.top_alert_cards || []).map((item, index) => `<div class="v10-alert-card"><i class="v10-alert-icon">${v10ToneIcon(index)}</i><span><b>${v5Html(item.label)}</b><em>${v5Html(item.metric)}</em></span></div>`).join('');
}
function renderV10MapCallout(story) {
  const stage = $('map-stage');
  if (!stage) return;
  let callout = $('v10-map-callout');
  if (!callout) {
    callout = document.createElement('div');
    callout.id = 'v10-map-callout';
    callout.setAttribute('data-testid', 'v10-map-callout');
    stage.appendChild(callout);
  }
  const info = story.target_map_callout || {};
  callout.innerHTML = `<b>${v5Html(info.title || '')}</b>风险：<strong>${v5Html(info.risk || '')}</strong><br>商圈：${v5Html(info.merchant || '')}<br>预计送达：${v5Html(info.eta || '')}<br>${v5Html(info.adopted_plan || '')}<br>${v5Html(info.dispatch_semantics || '')}`;
}
function renderV10DataTruthRail(story) {
  const shell = document.querySelector('.target-dashboard');
  if (!shell) return;
  let rail = $('v10-data-truth-rail');
  if (!rail) {
    rail = document.createElement('div');
    rail.id = 'v10-data-truth-rail';
    rail.setAttribute('data-testid', 'v10-data-truth-rail');
    shell.appendChild(rail);
  }
  rail.innerHTML = (story.data_truth_rail || []).map((item) => `<div class="v10-truth-badge"><b>${v5Html(item.label)}</b>${v5Html(item.items)} · ${v5Html(item.note)}</div>`).join('');
}
function renderV10PresenterScript(story) {
  const shell = document.querySelector('.target-dashboard');
  if (!shell) return;
  let script = $('v10-presenter-script');
  if (!script) {
    script = document.createElement('div');
    script.id = 'v10-presenter-script';
    script.setAttribute('data-testid', 'v10-presenter-script');
    shell.appendChild(script);
  }
  const first = (story.presenter_script || [])[0] || {};
  script.innerHTML = `<b>答辩提示 ${v5Html(first.judge || '')}</b>${v5Html(first.line || '')}`;
}
function renderV10DecisionFocus(story) {
  const panel = $('decision-panel');
  if (!panel) return;
  let focus = $('v10-decision-focus');
  if (!focus) {
    focus = document.createElement('div');
    focus.id = 'v10-decision-focus';
    focus.setAttribute('data-testid', 'v10-decision-focus');
    panel.appendChild(focus);
  }
  const items = (story.presenter_script || []).slice(1, 5);
  focus.innerHTML = items.map((item) => `<div class="v10-focus-card"><b>${v5Html(item.judge)}</b>${v5Html(item.line)}</div>`).join('');
}
function enhanceV10Narrative(story) {
  document.querySelector('.target-dashboard')?.classList.add('v10-exact-narrative-shell');
  renderV10TopAlerts(story);
  renderV10MapCallout(story);
  renderV10DataTruthRail(story);
  renderV10PresenterScript(story);
  renderV10DecisionFocus(story);
}
const renderStoryV9ForV10 = renderStory;
renderStory = function renderStoryV10(story) {
  renderStoryV9ForV10(story);
  enhanceV10Narrative(story);
};
"""


def render_dispatch_index_v10() -> str:
    html = render_dispatch_index_v9()
    html = _replace_default_story(html, build_placeholder_story_v10())
    html = html.replace(
        '<main class="target-dashboard v5-target-dashboard v6-exact-target-shell v7-polish-shell v8-target-match-shell v9-density-shell" data-stage="v9-target-dashboard">',
        '<main class="target-dashboard v5-target-dashboard v6-exact-target-shell v7-polish-shell v8-target-match-shell v9-density-shell v10-exact-narrative-shell" data-stage="v10-target-dashboard">',
    )
    html = html.replace("AutoSolver Agent 即时履约智能调度指挥舱 v9", "AutoSolver Agent 即时履约智能调度指挥舱 v10", 1)
    html = html.replace("</style>", V10_CSS + "\n  </style>", 1)
    html = html.replace("window.addEventListener('resize', updateScale);", V10_JS + "\nwindow.addEventListener('resize', updateScale);", 1)
    return html


class DispatchV10RequestHandler(BaseHTTPRequestHandler):
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
                self._send_html(render_dispatch_index_v10())
                return
            if parsed.path == "/api/cases":
                self._send_json({"status": "ok", "cases": list_cases()})
                return
            if parsed.path == "/api/run":
                qs = parse_qs(parsed.query)
                case_id = qs.get("case", ["large_seed301"])[0]
                budget_s = float(qs.get("budget", ["10"])[0])
                self._send_json(build_dispatch_payload_v10(case_id, budget_s=budget_s))
                return
            self._send_json({"status": "error", "error": "not found"}, status=404)
        except Exception as exc:
            self._send_json(
                {"status": "error", "error": str(exc), "traceback": traceback.format_exc()},
                status=500,
            )

    def log_message(self, format: str, *args: object) -> None:
        print(f"[dispatch-v10] {self.address_string()} - {format % args}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local AutoSolver dispatch command center v10 demo.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8775)
    args = parser.parse_args(argv)
    server = ThreadingHTTPServer((args.host, args.port), DispatchV10RequestHandler)
    print(f"AutoSolver Dispatch Command Center v10 running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
