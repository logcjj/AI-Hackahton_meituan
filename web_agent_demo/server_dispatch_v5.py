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

from web_agent_demo.dispatch_story_v5 import build_dispatch_story_v5, build_placeholder_story_v5
from web_agent_demo.server import list_cases, run_case_agent
from web_agent_demo.server_dispatch_v4 import render_dispatch_index_v4


def build_dispatch_payload_v5(case_id: str, budget_s: float = 10.0) -> dict[str, object]:
    report = run_case_agent(case_id, budget_s=budget_s)
    return {"status": "ok", "report": report, "story": build_dispatch_story_v5(report)}


def _replace_default_story(html: str, story: dict[str, object]) -> str:
    start = html.index("const DEFAULT_STORY = ") + len("const DEFAULT_STORY = ")
    end = html.index(";\nconst $ =", start)
    return (
        html[:start]
        + json.dumps(story, ensure_ascii=False)
        + html[end:]
    )


V5_CSS = """
    /* v5 目标图风格：深色城市运营地图、霓虹路径、证据栏一屏讲清业务价值。 */
    :root {
      --map-satellite: rgba(10, 45, 73, .78);
      --meituan-gold: #ffd43b;
      --proof-blue: #36c7ff;
      --hot-orange: #ff6b2a;
    }
    .v5-target-dashboard {
      background:
        linear-gradient(180deg, rgba(255,212,59,.035), transparent 17%),
        radial-gradient(circle at 52% 42%, rgba(54,199,255,.12), transparent 30rem),
        radial-gradient(circle at 73% 67%, rgba(255,212,59,.16), transparent 22rem);
    }
    .v5-target-dashboard:after {
      content: "目标图风格 / AI 自动判断 / 商业证据闭环";
      position: absolute;
      right: 24px;
      bottom: 9px;
      color: rgba(198,251,255,.58);
      font-size: 11px;
      letter-spacing: .12em;
    }
    .v5-target-dashboard .brand {
      padding-left: 4px;
    }
    .v5-target-dashboard .logo {
      color: #42f5a9;
      box-shadow: 0 0 38px rgba(66,245,169,.28), inset 0 0 22px rgba(66,245,169,.16);
      clip-path: polygon(50% 0%, 100% 24%, 100% 76%, 50% 100%, 0 76%, 0 24%);
    }
    .v5-target-dashboard .top-row {
      grid-template-columns: 610px 1fr 345px;
    }
    .v5-target-dashboard #top-kpi-strip {
      height: 122px;
      border-color: rgba(54,199,255,.32);
    }
    .v5-target-dashboard .kpi {
      position: relative;
      isolation: isolate;
      overflow: hidden;
    }
    .v5-target-dashboard .kpi:before {
      content: "";
      position: absolute;
      inset: 0;
      background: linear-gradient(90deg, transparent, rgba(54,199,255,.08), transparent);
      transform: translateX(-70%);
      animation: v5Sweep 5s linear infinite;
      z-index: -1;
    }
    @keyframes v5Sweep { to { transform: translateX(80%); } }
    .v5-spark {
      position: absolute;
      right: 16px;
      bottom: 12px;
      width: 86px;
      height: 22px;
      opacity: .9;
    }
    .v5-spark i {
      position: absolute;
      bottom: 0;
      width: 4px;
      border-radius: 4px 4px 0 0;
      background: linear-gradient(180deg, #38f29c, rgba(56,242,156,.16));
    }
    .v5-target-dashboard .main-row {
      grid-template-columns: 292px 1fr 420px;
      height: 528px;
    }
    .v5-target-dashboard #map-stage {
      height: 470px;
      background:
        radial-gradient(circle at 58% 42%, rgba(255,211,45,.18), transparent 11rem),
        radial-gradient(circle at 78% 70%, rgba(28,244,210,.16), transparent 12rem),
        linear-gradient(145deg, var(--map-satellite), rgba(2,12,24,.99));
      box-shadow: inset 0 0 0 1px rgba(54,199,255,.28), inset 0 0 80px rgba(4,18,31,.9);
    }
    .v5-target-dashboard #map-stage:before {
      opacity: .92;
      background-image:
        linear-gradient(18deg, transparent 47%, rgba(54,199,255,.24) 49%, transparent 51%),
        linear-gradient(154deg, transparent 48%, rgba(255,255,255,.12) 50%, transparent 52%),
        linear-gradient(112deg, transparent 47%, rgba(255,211,45,.15) 49%, transparent 51%),
        linear-gradient(90deg, rgba(54,199,255,.065) 1px, transparent 1px),
        linear-gradient(rgba(54,199,255,.055) 1px, transparent 1px);
      background-size: 155px 96px, 132px 105px, 188px 112px, 42px 42px, 42px 42px;
    }
    .v5-target-dashboard .node.order-node circle {
      stroke-width: .82;
      filter: drop-shadow(0 0 9px currentColor) drop-shadow(0 0 18px rgba(255,211,45,.32));
    }
    .v5-target-dashboard .hit-target {
      fill: transparent;
      stroke: transparent;
      pointer-events: all;
      cursor: pointer;
    }
    .v5-target-dashboard .node.selected circle {
      stroke: white;
      stroke-width: 1.1;
      animation: v5Pulse 1.4s ease-in-out infinite;
    }
    @keyframes v5Pulse { 50% { filter: drop-shadow(0 0 18px currentColor); } }
    .v5-target-dashboard .edge.allocated_plan {
      stroke: #1cf4d2;
      stroke-width: 3.7;
    }
    .v5-target-dashboard .edge.candidate_plan {
      stroke: #ffd43b;
      stroke-width: 2.4;
    }
    .v5-target-dashboard #right-decision-panel {
      grid-template-rows: auto 1fr;
    }
    .v5-target-dashboard .decision-box {
      border-color: rgba(54,199,255,.28);
      background: linear-gradient(180deg, rgba(9,37,59,.7), rgba(0,0,0,.18));
    }
    .v5-target-dashboard .courier {
      position: relative;
      padding-left: 36px;
    }
    .v5-target-dashboard .courier:before {
      content: "";
      position: absolute;
      left: 8px;
      top: 10px;
      width: 20px;
      height: 20px;
      border-radius: 50%;
      background: radial-gradient(circle at 40% 35%, #fff, #38f29c 38%, #06231d 72%);
      box-shadow: 0 0 10px rgba(56,242,156,.44);
    }
    .v5-target-dashboard .bottom-row {
      grid-template-columns: 1.1fr .72fr 1.05fr .8fr 1.1fr;
      height: 238px;
    }
    .v5-target-dashboard .review-evidence-card {
      display: none;
    }
    #v5-judge-evidence {
      margin-top: 9px;
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 7px;
    }
    #v5-judge-evidence .evidence {
      border: 1px solid rgba(54,199,255,.24);
      border-radius: 9px;
      padding: 7px;
      background: rgba(54,199,255,.055);
      color: var(--muted);
      font-size: 11px;
      line-height: 1.32;
    }
    #v5-judge-evidence .evidence b {
      display: block;
      color: var(--meituan-gold);
      margin-bottom: 3px;
    }
    .v5-semantics {
      margin-top: 7px;
      color: #99f4ef;
      font-size: 12px;
      line-height: 1.45;
      border-top: 1px solid rgba(71,210,255,.13);
      padding-top: 7px;
    }
"""


V5_JS = """
const V5_DISPATCH_SEMANTICS = '多派候选不是指定唯一骑手';
const V5_EVIDENCE_ANCHOR = '<div id="v5-judge-evidence"></div>';
const V5_HIT_TARGET_ANCHOR = '<circle class="hit-target"></circle>';
function v5Html(value) {
  return safe(value);
}
function addV5SparkLines() {
  document.querySelectorAll('.kpi').forEach((card, cardIndex) => {
    if (card.querySelector('.v5-spark')) return;
    const spark = document.createElement('div');
    spark.className = 'v5-spark';
    [7, 10, 8, 12, 15, 11, 17, 13, 18, 22].forEach((height, index) => {
      const bar = document.createElement('i');
      bar.style.left = `${index * 8}px`;
      bar.style.height = `${Math.max(4, height - cardIndex)}px`;
      spark.appendChild(bar);
    });
    card.appendChild(spark);
  });
}
function selectOrderGroup(orderGroupId, story) {
  const hotspot = (story.interactive_hotspots || []).find((item) => item.order_group === orderGroupId) || (story.interactive_hotspots || [])[0];
  if (!hotspot) return;
  document.querySelectorAll('#operation-map .node').forEach((node) => {
    node.classList.toggle('selected', node.dataset.nodeId === hotspot.order_group);
  });
  $('map-callout').innerHTML = `<b>订单组 ${v5Html(hotspot.order_group)}</b><br>风险：${v5Html(hotspot.risk)}<br>预计送达：${v5Html(hotspot.eta)}<br>候选方案：${v5Html(hotspot.candidate_count)} 个`;
  $('decision-panel').innerHTML = `
    <div class="decision-box"><h3>任务组 ${v5Html(hotspot.order_group)} <span style="color:var(--red);font-size:12px">${v5Html(hotspot.risk)}</span></h3><div class="kv-grid"><div class="kv">候选方案<b>${v5Html(hotspot.candidate_count)} 个</b></div><div class="kv">预计送达<b>${v5Html(hotspot.eta)}</b></div><div class="kv" style="grid-column:1 / -1">调度判断<b>${v5Html(hotspot.summary)}</b></div></div><div class="v5-semantics">${V5_DISPATCH_SEMANTICS}，而是提高至少一名骑手接单的概率。</div></div>
    <div class="decision-box"><h3>选择的骑手</h3><div class="couriers">${hotspot.couriers.map((item) => `<div class="courier"><b>${v5Html(item.id)}</b>接单意愿 ${v5Html(item.willingness)}<br>距离 ${v5Html(item.distance)}<br>score ${v5Html(item.score)}</div>`).join('')}</div></div>
    <div class="decision-box"><h3>决策原因</h3><ul class="reasons">${hotspot.reasons.map((item) => `<li>${v5Html(item)}</li>`).join('')}</ul></div>
    <div class="decision-box"><h3>商业解释</h3>优先讲无人接单风险下降、相对贪心基线改善和履约成本节约，避免把演示讲成单纯地图可视化。</div>`;
}
function wireV5MapInteractions(story) {
  const nodes = Array.from(document.querySelectorAll('#operation-map .node'));
  nodes.forEach((node, index) => {
    const datum = story.operation_map.nodes[index];
    if (!datum) return;
    node.dataset.nodeId = datum.id;
    node.setAttribute('role', datum.type === 'courier' ? 'img' : 'button');
    node.classList.toggle('order-node', datum.type !== 'courier');
    if (datum.type !== 'courier') {
      node.setAttribute('tabindex', '0');
      node.setAttribute('aria-label', `${datum.id} ${datum.orders}单`);
      const hit = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      hit.setAttribute('class', 'hit-target');
      hit.setAttribute('cx', datum.x);
      hit.setAttribute('cy', datum.y);
      hit.setAttribute('r', '6.2');
      node.insertBefore(hit, node.firstChild);
      const choose = (event) => {
        event.stopPropagation();
        selectOrderGroup(datum.id, story);
      };
      hit.addEventListener('click', choose);
      node.addEventListener('click', choose);
      node.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') selectOrderGroup(datum.id, story);
      });
    }
  });
  selectOrderGroup(((story.interactive_hotspots || [])[0] || {}).order_group, story);
}
function renderV5JudgeEvidence(story) {
  const oldReview = $('review-alignment');
  if (oldReview && oldReview.parentElement) oldReview.parentElement.classList.add('review-evidence-card');
  const roi = $('commercial-roi');
  if (!roi) return;
  let target = $('v5-judge-evidence');
  if (!target) {
    const title = document.createElement('h2');
    title.textContent = '评审证据栏';
    title.style.marginTop = '10px';
    target = document.createElement('div');
    target.id = 'v5-judge-evidence';
    roi.parentElement.appendChild(title);
    roi.parentElement.appendChild(target);
  }
  target.innerHTML = (story.judge_evidence_bar || []).map((item) => `<div class="evidence"><b>${v5Html(item.dimension)}</b>${v5Html(item.headline)}</div>`).join('');
}
function enhanceV5Interactions(story) {
  document.querySelector('.target-dashboard')?.classList.add('v5-target-dashboard');
  addV5SparkLines();
  wireV5MapInteractions(story);
  renderV5JudgeEvidence(story);
}
const renderStoryV4 = renderStory;
renderStory = function renderStoryV5(story) {
  renderStoryV4(story);
  enhanceV5Interactions(story);
};
"""


def render_dispatch_index_v5() -> str:
    html = render_dispatch_index_v4()
    html = _replace_default_story(html, build_placeholder_story_v5())
    html = html.replace(
        '<main class="target-dashboard">',
        '<main class="target-dashboard v5-target-dashboard" data-stage="v5-target-dashboard">',
    )
    html = html.replace("AutoSolver Agent 即时履约智能调度指挥舱", "AutoSolver Agent 即时履约智能调度指挥舱 v5", 1)
    html = html.replace("</style>", V5_CSS + "\n  </style>", 1)
    html = html.replace("window.addEventListener('resize', updateScale);", V5_JS + "\nwindow.addEventListener('resize', updateScale);", 1)
    return html


class DispatchV5RequestHandler(BaseHTTPRequestHandler):
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
                self._send_html(render_dispatch_index_v5())
                return
            if parsed.path == "/api/cases":
                self._send_json({"status": "ok", "cases": list_cases()})
                return
            if parsed.path == "/api/run":
                qs = parse_qs(parsed.query)
                case_id = qs.get("case", ["large_seed301"])[0]
                budget_s = float(qs.get("budget", ["10"])[0])
                self._send_json(build_dispatch_payload_v5(case_id, budget_s=budget_s))
                return
            self._send_json({"status": "error", "error": "not found"}, status=404)
        except Exception as exc:
            self._send_json(
                {"status": "error", "error": str(exc), "traceback": traceback.format_exc()},
                status=500,
            )

    def log_message(self, format: str, *args: object) -> None:
        print(f"[dispatch-v5] {self.address_string()} - {format % args}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local AutoSolver dispatch command center v5 demo.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8770)
    args = parser.parse_args(argv)
    server = ThreadingHTTPServer((args.host, args.port), DispatchV5RequestHandler)
    print(f"AutoSolver Dispatch Command Center v5 running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
