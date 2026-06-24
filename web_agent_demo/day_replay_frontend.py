from __future__ import annotations

import json
from functools import lru_cache

from web_agent_demo.day_simulation import (
    DAY_SIMULATION_ENDPOINTS,
    DaySimulationControls,
    day_comparison_to_dict,
    run_full_day_comparison,
)


@lru_cache(maxsize=1)
def _bootstrap_payload() -> dict[str, object]:
    controls = DaySimulationControls(courier_count=18, order_scale=0.38, weather="mixed", congestion_profile="weekday")
    contract = run_full_day_comparison(seed="frontend-shell", controls=controls)
    return {
        "contract": day_comparison_to_dict(contract),
        "endpoints": dict(DAY_SIMULATION_ENDPOINTS),
        "mode": "full-day-replay-shell",
    }


def render_day_replay_index() -> str:
    boot_json = json.dumps(_bootstrap_payload(), ensure_ascii=False, sort_keys=True).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AutoSolver Agent - 全日配送模拟推演</title>
  <style>
    :root {{
      --bg: #10100c;
      --bg-2: #23190f;
      --paper: #f2dec0;
      --paper-strong: #fff3d6;
      --ink: #251a10;
      --muted: #7d6954;
      --line: rgba(77, 52, 28, .24);
      --gold: #d89a37;
      --green: #2f7054;
      --green-deep: #173b31;
      --red: #b54435;
      --blue: #39677e;
      --route-greedy: #b54435;
      --route-agent: #2f7054;
      --shadow: 0 24px 80px rgba(15, 10, 5, .32);
      --serif: "Noto Serif SC", "Songti SC", "STSong", serif;
      --ui: "Avenir Next Condensed", "DIN Condensed", "PingFang SC", sans-serif;
      --mono: "IBM Plex Mono", "Cascadia Mono", "Menlo", monospace;
    }}
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; min-height: 100%; }}
    body {{
      color: var(--ink);
      background:
        radial-gradient(circle at 12% 8%, rgba(216, 154, 55, .28), transparent 32%),
        radial-gradient(circle at 80% 18%, rgba(47, 112, 84, .25), transparent 34%),
        linear-gradient(135deg, #090b08 0%, var(--bg) 42%, var(--bg-2) 100%);
      font-family: var(--ui);
      overflow: auto;
    }}
    button, select, input {{ font: inherit; }}
    button {{ cursor: pointer; }}
    .day-replay-shell {{
      width: 100vw;
      min-height: 100vh;
      padding: 16px;
      display: grid;
      grid-template-rows: auto auto auto minmax(540px, auto) auto;
      gap: 14px;
    }}
    .hero, .kpi-strip, .control-strip, .replay-grid, .bottom-grid {{
      width: min(1720px, 100%);
      margin: 0 auto;
    }}
    .hero {{
      min-height: 86px;
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 18px;
      align-items: center;
      padding: 18px 20px;
      border: 1px solid rgba(255, 243, 214, .16);
      border-radius: 28px;
      color: #fff1cf;
      background:
        linear-gradient(100deg, rgba(23, 59, 49, .92), rgba(64, 38, 17, .82)),
        repeating-linear-gradient(90deg, rgba(255, 255, 255, .04) 0 1px, transparent 1px 12px);
      box-shadow: var(--shadow);
    }}
    .eyebrow {{
      color: #efc26a;
      letter-spacing: .18em;
      text-transform: uppercase;
      font: 700 12px var(--mono);
    }}
    h1, h2, h3, p {{ margin-top: 0; }}
    h1 {{
      margin-bottom: 6px;
      font-family: var(--serif);
      font-size: clamp(28px, 4vw, 54px);
      letter-spacing: -.05em;
      line-height: .95;
    }}
    .hero p {{
      margin-bottom: 0;
      max-width: 900px;
      color: rgba(255, 241, 207, .76);
      line-height: 1.55;
    }}
    .hero-badge {{
      min-width: 250px;
      padding: 14px;
      border: 1px solid rgba(255, 243, 214, .18);
      border-radius: 22px;
      background: rgba(255, 255, 255, .08);
    }}
    .hero-badge b {{
      display: block;
      margin-bottom: 5px;
      font-family: var(--serif);
      font-size: 20px;
    }}
    .hero-badge span {{
      color: rgba(255, 241, 207, .72);
      font-size: 13px;
      line-height: 1.45;
    }}
    .kpi-strip {{
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 10px;
    }}
    .kpi-card {{
      min-height: 86px;
      padding: 14px;
      border: 1px solid rgba(255, 243, 214, .16);
      border-radius: 22px;
      color: var(--paper-strong);
      background: linear-gradient(150deg, rgba(255, 255, 255, .1), rgba(255, 255, 255, .03));
      box-shadow: 0 16px 40px rgba(0, 0, 0, .18);
    }}
    .kpi-card small {{
      display: block;
      margin-bottom: 10px;
      color: rgba(255, 243, 214, .62);
      letter-spacing: .08em;
      text-transform: uppercase;
      font: 700 11px var(--mono);
    }}
    .kpi-card strong {{
      display: block;
      font: 800 clamp(22px, 2.4vw, 36px) var(--serif);
      letter-spacing: -.05em;
    }}
    .kpi-card span {{ color: rgba(255, 243, 214, .68); font-size: 12px; }}
    .kpi-card em {{
      display: block;
      margin-top: 8px;
      color: rgba(255, 243, 214, .86);
      font: 800 11px var(--mono);
      font-style: normal;
    }}
    .kpi-card[data-trend="good"] {{
      border-color: rgba(93, 186, 119, .38);
      background: linear-gradient(150deg, rgba(47, 112, 84, .32), rgba(255, 255, 255, .04));
    }}
    .kpi-card[data-trend="warn"] {{
      border-color: rgba(181, 68, 53, .42);
      background: linear-gradient(150deg, rgba(181, 68, 53, .28), rgba(255, 255, 255, .04));
    }}
    .control-strip {{
      display: grid;
      grid-template-columns: minmax(210px, .8fr) repeat(5, minmax(120px, .45fr)) auto;
      gap: 10px;
      padding: 12px;
      border: 1px solid rgba(255, 243, 214, .14);
      border-radius: 24px;
      background: rgba(255, 243, 214, .08);
      backdrop-filter: blur(18px);
    }}
    .control-box {{
      min-height: 60px;
      padding: 10px 12px;
      border-radius: 18px;
      background: rgba(255, 243, 214, .9);
      border: 1px solid var(--line);
    }}
    .control-box label {{
      display: flex;
      justify-content: space-between;
      margin-bottom: 6px;
      color: var(--muted);
      font: 700 11px var(--mono);
      text-transform: uppercase;
    }}
    .control-box select, .control-box input {{ width: 100%; }}
    .control-box select {{
      height: 30px;
      border: 0;
      border-radius: 10px;
      color: var(--ink);
      background: rgba(255, 255, 255, .66);
      padding: 0 8px;
    }}
    .control-box input[type="range"] {{ accent-color: var(--green); }}
    .control-actions {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
      min-width: 260px;
    }}
    .control-actions button {{
      border: 0;
      border-radius: 18px;
      padding: 0 14px;
      color: #fff4d8;
      background: linear-gradient(135deg, var(--green-deep), var(--gold));
      box-shadow: 0 12px 24px rgba(0, 0, 0, .18);
    }}
    .control-actions button.secondary {{
      color: var(--paper-strong);
      background: rgba(255, 243, 214, .14);
      border: 1px solid rgba(255, 243, 214, .16);
      box-shadow: none;
    }}
    .replay-grid {{
      min-height: 540px;
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 14px;
    }}
    .algorithm-theater {{
      min-height: 540px;
      display: grid;
      grid-template-rows: auto minmax(0, 1fr) auto;
      overflow: hidden;
      border: 1px solid rgba(255, 243, 214, .18);
      border-radius: 30px;
      background: var(--paper);
      box-shadow: var(--shadow);
    }}
    .theater-head {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 12px;
      align-items: start;
      padding: 16px 18px 10px;
      border-bottom: 1px solid var(--line);
    }}
    .theater-head h2 {{
      margin-bottom: 4px;
      font: 900 24px var(--serif);
      letter-spacing: -.04em;
    }}
    .theater-head p {{
      margin-bottom: 0;
      color: var(--muted);
      line-height: 1.45;
      font-size: 13px;
    }}
    .map-legend-copy {{
      margin-top: 8px;
      color: #5d4b37;
      font: 800 11px var(--mono);
      letter-spacing: .04em;
      text-transform: uppercase;
    }}
    .algorithm-pill {{
      padding: 9px 11px;
      border-radius: 999px;
      color: var(--paper-strong);
      background: var(--red);
      font: 800 12px var(--mono);
      white-space: nowrap;
    }}
    .agent .algorithm-pill {{ background: var(--green); }}
    .map-stage {{
      position: relative;
      min-height: 280px;
      margin: 12px 14px;
      overflow: hidden;
      border-radius: 24px;
      background:
        linear-gradient(90deg, rgba(72, 49, 28, .16) 1px, transparent 1px),
        linear-gradient(0deg, rgba(72, 49, 28, .16) 1px, transparent 1px),
        radial-gradient(circle at 30% 36%, rgba(216, 154, 55, .18), transparent 20%),
        radial-gradient(circle at 70% 62%, rgba(47, 112, 84, .2), transparent 24%),
        #e6d0aa;
      background-size: 56px 56px, 56px 56px, auto, auto, auto;
    }}
    .district {{
      position: absolute;
      border: 1px solid rgba(77, 52, 28, .12);
      background: rgba(255, 255, 255, .22);
      transform: rotate(-6deg);
    }}
    .district.one {{ left: 8%; top: 12%; width: 28%; height: 32%; }}
    .district.two {{ right: 10%; top: 18%; width: 32%; height: 26%; transform: rotate(8deg); }}
    .district.three {{ left: 24%; bottom: 12%; width: 46%; height: 27%; transform: rotate(3deg); }}
    .road {{
      position: absolute;
      height: 4px;
      border-radius: 999px;
      background: rgba(74, 59, 38, .24);
      transform-origin: left center;
    }}
    .road.r1 {{ left: 6%; top: 50%; width: 88%; transform: rotate(4deg); }}
    .road.r2 {{ left: 16%; top: 16%; width: 72%; transform: rotate(36deg); }}
    .road.r3 {{ left: 30%; top: 8%; width: 70%; transform: rotate(102deg); }}
    .shock-band {{
      position: absolute;
      left: 20%;
      top: 39%;
      width: 58%;
      height: 17%;
      border: 1px dashed rgba(181, 68, 53, .4);
      border-radius: 999px;
      background: rgba(181, 68, 53, .11);
      transform: rotate(-10deg);
    }}
    .map-hud {{
      position: absolute;
      left: 12px;
      top: 12px;
      z-index: 8;
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
      max-width: calc(100% - 24px);
    }}
    .map-hud span, .burst-marker {{
      padding: 6px 8px;
      border-radius: 999px;
      color: #fff7df;
      background: rgba(23, 59, 49, .78);
      font: 800 10px var(--mono);
      box-shadow: 0 8px 18px rgba(0, 0, 0, .16);
    }}
    .burst-marker {{
      position: absolute;
      right: 14px;
      top: 14px;
      z-index: 9;
      background: rgba(181, 68, 53, .86);
      animation: burstPulse 1.4s ease-in-out infinite;
    }}
    @keyframes burstPulse {{
      0%, 100% {{ transform: scale(1); }}
      50% {{ transform: scale(1.06); }}
    }}
    .route-svg {{ position: absolute; inset: 0; width: 100%; height: 100%; }}
    .route-svg path {{
      fill: none;
      stroke-width: 2.8;
      stroke-linecap: round;
      stroke-dasharray: 9 7;
      opacity: .86;
    }}
    .greedy .route-svg path {{ stroke: var(--route-greedy); }}
    .agent .route-svg path {{ stroke: var(--route-agent); }}
    .pin {{
      position: absolute;
      width: 30px;
      height: 30px;
      display: grid;
      place-items: center;
      border-radius: 999px;
      color: white;
      font-weight: 900;
      font-size: 12px;
      border: 2px solid rgba(255, 255, 255, .82);
      transform: translate(-50%, -50%);
      box-shadow: 0 10px 22px rgba(0, 0, 0, .24);
    }}
    .pin::after {{
      content: attr(data-label);
      position: absolute;
      left: 50%;
      top: 31px;
      transform: translateX(-50%);
      min-width: max-content;
      padding: 3px 7px;
      border-radius: 9px;
      color: var(--ink);
      background: rgba(255, 246, 223, .9);
      border: 1px solid rgba(77, 52, 28, .16);
      font-size: 11px;
      font-weight: 800;
    }}
    .pin.merchant {{ background: var(--gold); }}
    .pin.courier {{ background: var(--blue); }}
    .pin.order {{ background: var(--red); width: 24px; height: 24px; font-size: 10px; }}
    .agent .pin.courier {{ background: var(--green); }}
    .pin.highlight {{
      outline: 4px solid rgba(255, 243, 214, .92);
      animation: decisionPulse 1.1s ease-in-out infinite;
      z-index: 12;
    }}
    .route-svg path.highlight-route {{
      stroke-width: 5.2;
      stroke-dasharray: 1 0;
      opacity: 1;
      filter: drop-shadow(0 0 8px rgba(255, 243, 214, .86));
    }}
    @keyframes decisionPulse {{
      0%, 100% {{ transform: translate(-50%, -50%) scale(1); }}
      50% {{ transform: translate(-50%, -50%) scale(1.14); }}
    }}
    .theater-foot {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 8px;
      padding: 0 14px 14px;
    }}
    .mini-metric {{
      padding: 10px;
      border-radius: 16px;
      background: rgba(255, 255, 255, .46);
      border: 1px solid var(--line);
    }}
    .mini-metric small {{
      display: block;
      color: var(--muted);
      font: 700 10px var(--mono);
      text-transform: uppercase;
    }}
    .mini-metric strong {{
      display: block;
      margin-top: 4px;
      font: 900 18px var(--serif);
    }}
    .bottom-grid {{
      display: grid;
      grid-template-columns: minmax(0, 1.1fr) minmax(340px, .75fr);
      gap: 14px;
      min-height: 172px;
    }}
    .reasoning-panel, .memory-panel {{
      overflow: hidden;
      border: 1px solid rgba(255, 243, 214, .16);
      border-radius: 26px;
      background: rgba(255, 243, 214, .92);
      box-shadow: var(--shadow);
    }}
    .panel-head {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      padding: 14px 16px 10px;
      border-bottom: 1px solid var(--line);
    }}
    .panel-head h2 {{
      margin-bottom: 2px;
      font: 900 19px var(--serif);
    }}
    .panel-head p {{
      margin-bottom: 0;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
    }}
    .timeline-track {{
      display: grid;
      grid-template-columns: repeat(4, minmax(160px, 1fr));
      gap: 10px;
      padding: 12px 14px 14px;
      overflow-x: auto;
    }}
    .decision-highlight-strip {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      padding: 12px 14px 0;
    }}
    .decision-chip {{
      padding: 8px 10px;
      border-radius: 999px;
      color: var(--green-deep);
      background: rgba(47, 112, 84, .1);
      border: 1px solid rgba(47, 112, 84, .22);
      font: 800 11px var(--mono);
    }}
    .event-card, .memory-card {{
      padding: 12px;
      border-radius: 18px;
      background: rgba(255, 255, 255, .52);
      border: 1px solid var(--line);
      line-height: 1.45;
      font-size: 12px;
    }}
    .event-card[data-highlight-card="true"] {{
      cursor: pointer;
      transition: transform .18s ease, border-color .18s ease, background .18s ease;
    }}
    .event-card[data-highlight-card="true"]:hover,
    .event-card[data-active-highlight="true"] {{
      transform: translateY(-2px);
      border-color: rgba(47, 112, 84, .42);
      background: rgba(47, 112, 84, .12);
    }}
    .event-card time, .memory-card code {{
      display: block;
      margin-bottom: 6px;
      color: var(--green-deep);
      font: 800 11px var(--mono);
    }}
    .event-card b, .memory-card b {{ display: block; margin-bottom: 5px; }}
    .memory-stack {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      padding: 12px 14px 14px;
    }}
    .memory-card[data-event-type="memory_writeback"] {{
      background: rgba(216, 154, 55, .18);
    }}
    .memory-card[data-event-type="future_policy_shift"] {{
      background: rgba(47, 112, 84, .14);
    }}
    .api-tags {{
      display: flex;
      flex-wrap: wrap;
      gap: 7px;
      align-content: start;
      justify-content: flex-end;
    }}
    .api-tags span {{
      padding: 6px 8px;
      border-radius: 999px;
      color: var(--paper-strong);
      background: rgba(23, 59, 49, .78);
      font: 700 10px var(--mono);
    }}
    @media (max-width: 1180px) {{
      body {{ overflow: auto; }}
      .day-replay-shell {{ height: auto; min-height: 100vh; }}
      .hero, .control-strip, .replay-grid, .bottom-grid {{ grid-template-columns: 1fr; }}
      .kpi-strip {{ grid-template-columns: repeat(3, 1fr); }}
      .control-actions {{ min-height: 58px; }}
      .algorithm-theater {{ min-height: 560px; }}
      .memory-stack {{ grid-template-columns: 1fr; }}
    }}
    @media (max-width: 720px) {{
      .day-replay-shell {{ padding: 10px; gap: 10px; }}
      .hero {{ grid-template-columns: 1fr; border-radius: 22px; }}
      .hero-badge {{ min-width: 0; }}
      .kpi-strip {{ grid-template-columns: 1fr 1fr; }}
      .control-strip {{ padding: 8px; }}
      .control-actions {{ grid-template-columns: 1fr; }}
      .theater-head, .theater-foot {{ grid-template-columns: 1fr; }}
      .timeline-track {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main class="day-replay-shell" id="day-replay-shell" data-product-mode="full-day-simulation-replay" data-map-style="existing-project-operational-map">
    <header class="hero">
      <div>
        <div class="eyebrow">AutoSolver Agent Full-Day Replay</div>
        <h1>全日配送模拟推演对比台</h1>
        <p>重新抛弃旧前端小沙盘，把核心放在一天订单流、跨时间片推演、纯贪心和 AutoSolver 并排对比、指标节省、推理流程与 Memory 自进化。</p>
      </div>
      <aside class="hero-badge" id="engine-status">
        <b>本地确定性仿真引擎</b>
        <span>先使用 native discrete-event engine，后续可接 UXsim / SUMO adapter seam。所有 LLM 配置只走 env-only-redacted。</span>
      </aside>
    </header>

    <section class="kpi-strip" id="kpi-strip" aria-label="全日对比指标">
      <article class="kpi-card" id="kpi-card-time" data-kpi="time_saved"><small>Time Saved</small><strong id="kpi-time-saved">--</strong><span id="kpi-time-context">当前帧 vs nearest greedy</span><em id="kpi-time-total">全日累计 --</em></article>
      <article class="kpi-card" id="kpi-card-cost" data-kpi="cost_saved"><small>Cost Saved</small><strong id="kpi-cost-saved">--</strong><span id="kpi-cost-context">当前帧履约成本节省</span><em id="kpi-cost-total">全日累计 --</em></article>
      <article class="kpi-card" id="kpi-card-delivered" data-kpi="delivered"><small>Delivered</small><strong id="kpi-delivered">--</strong><span id="kpi-delivered-context">当前帧同一批订单</span><em id="kpi-delivered-total">全日累计 --</em></article>
      <article class="kpi-card" id="kpi-card-risk" data-kpi="timeout_risk"><small>Timeout Risk</small><strong id="kpi-risk">--</strong><span id="kpi-risk-context">当前帧风险变化</span><em id="kpi-risk-total">全日累计 --</em></article>
      <article class="kpi-card" id="kpi-card-eta" data-kpi="average_eta"><small>Average ETA</small><strong id="kpi-eta">--</strong><span id="kpi-eta-context">当前帧 AutoSolver</span><em id="kpi-eta-total">全日累计 --</em></article>
      <article class="kpi-card" id="kpi-card-utilization" data-kpi="utilization"><small>Utilization</small><strong id="kpi-utilization">--</strong><span id="kpi-utilization-context">当前帧骑手利用率</span><em id="kpi-utilization-total">全日累计 --</em></article>
    </section>

    <section class="control-strip" id="replay-controls" aria-label="全日推演控制">
      <div class="control-box">
        <label for="scenario-select"><span>Scenario</span><output id="scenario-label">weekday_full_day</output></label>
        <select id="scenario-select">
          <option value="weekday_full_day">weekday_full_day</option>
        </select>
      </div>
      <div class="control-box">
        <label for="courier-count"><span>Couriers</span><output id="courier-count-value">18</output></label>
        <input id="courier-count" type="range" min="8" max="120" value="18">
      </div>
      <div class="control-box">
        <label for="order-scale"><span>Order Scale</span><output id="order-scale-value">0.38</output></label>
        <input id="order-scale" type="range" min="0.10" max="2.00" step="0.05" value="0.38">
      </div>
      <div class="control-box">
        <label for="weather-mode"><span>Weather</span><output id="weather-label">mixed</output></label>
        <select id="weather-mode">
          <option value="mixed">mixed</option>
          <option value="clear">clear</option>
          <option value="rain">rain</option>
          <option value="storm">storm</option>
          <option value="event">event</option>
        </select>
      </div>
      <div class="control-box">
        <label for="playback-speed"><span>Speed</span><output id="playback-speed-label">1.2s/frame</output></label>
        <select id="playback-speed">
          <option value="1800">慢速 1.8s</option>
          <option value="1200" selected>标准 1.2s</option>
          <option value="700">快速 0.7s</option>
          <option value="350">战报 0.35s</option>
        </select>
      </div>
      <div class="control-box">
        <label for="timeline-scrubber"><span>Timeline</span><output id="timeline-label">12:00</output></label>
        <input id="timeline-scrubber" type="range" min="0" max="0" value="0">
      </div>
      <div class="control-actions">
        <button id="play-replay">播放</button>
        <button id="pause-replay" class="secondary">暂停</button>
        <button id="compare-algorithms">生成对比</button>
      </div>
    </section>

    <section class="replay-grid" id="side-by-side-replay" aria-label="左右同步算法仿真">
      <article class="algorithm-theater greedy" id="greedy-map-panel" data-algorithm="nearest_greedy">
        <div class="theater-head">
          <div>
            <h2>Pure Greedy Replay</h2>
            <p>最近距离优先，只看当前可行，容易在雨天、拥堵、午晚峰把风险累积到后续时间片。</p>
            <div class="map-legend-copy">图层: 商家 / 骑手 / 订单 / 拥堵带 / 路线</div>
          </div>
          <span class="algorithm-pill">nearest_greedy</span>
        </div>
        <div class="map-stage" id="greedy-map-stage" aria-label="贪心算法地图推演"></div>
        <div class="theater-foot" id="greedy-metrics"></div>
      </article>

      <article class="algorithm-theater agent" id="autosolver-map-panel" data-algorithm="autosolver_agent">
        <div class="theater-head">
          <div>
            <h2>AutoSolver Agent Replay</h2>
            <p>同一批订单上综合供给、拥堵、deadline、成本和历史 Memory，展示为什么能省时间和钱。</p>
            <div class="map-legend-copy">图层: 商家 / 骑手 / 订单 / Memory 决策路线</div>
          </div>
          <span class="algorithm-pill">autosolver_agent</span>
        </div>
        <div class="map-stage" id="autosolver-map-stage" aria-label="AutoSolver 地图推演"></div>
        <div class="theater-foot" id="autosolver-metrics"></div>
      </article>
    </section>

    <section class="bottom-grid">
      <article class="reasoning-panel" id="reasoning-flow-panel">
        <div class="panel-head">
          <div>
            <h2>算法推理流程</h2>
            <p>不用复杂线框图，直接按时间片展示候选算法评分、选择理由和关键影响。</p>
          </div>
          <div class="api-tags" id="day-api-tags"></div>
        </div>
        <div class="decision-highlight-strip" id="decision-highlight-summary" aria-label="当前决策高亮"></div>
        <div class="timeline-track" id="reasoning-timeline"></div>
      </article>
      <article class="memory-panel" id="memory-evolution-panel">
        <div class="panel-head">
          <div>
            <h2>Memory 自进化</h2>
            <p>演示 recall、writeback、future policy shift。外部 predictor 只显示 env 占位，不泄露配置。</p>
            <p class="memory-event-types">memory_recall / memory_writeback / future_policy_shift</p>
          </div>
        </div>
        <div class="memory-stack" id="memory-evolution-stack"></div>
      </article>
    </section>
  </main>

  <script id="day-replay-bootstrap" type="application/json">{boot_json}</script>
  <script>
    const replayBoot = JSON.parse(document.getElementById("day-replay-bootstrap").textContent);
    const replayState = {{
      contract: replayBoot.contract,
      endpoints: replayBoot.endpoints,
      frameIndex: 0,
      playing: false,
      timer: null,
      pendingRunToken: "",
      controlRunTimer: null,
      highlight: {{orderIds: [], courierIds: [], sourceLabel: "current frame"}}
    }};
    const $ = (id) => document.getElementById(id);

    function escapeText(value, fallback = "--") {{
      if (value === null || value === undefined || value === "") return fallback;
      const escapes = {{"&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;"}};
      escapes[String.fromCharCode(34)] = "&quot;";
      return String(value).replace(/[&<>"']/g, (ch) => escapes[ch]);
    }}

    function minutes(value) {{
      const num = Number(value) || 0;
      return `${{(num / 60).toFixed(1)}}m`;
    }}

    function yuan(value) {{
      const num = Number(value) || 0;
      return `${{num.toFixed(1)}}元`;
    }}

    function percent(value) {{
      const num = Number(value) || 0;
      return `${{(num * 100).toFixed(1)}}%`;
    }}

    function signedPercent(value) {{
      const num = Number(value) || 0;
      return `${{num >= 0 ? "+" : ""}}${{(num * 100).toFixed(1)}}%`;
    }}

    function signedMinutes(value) {{
      const num = Number(value) || 0;
      return `${{num >= 0 ? "+" : ""}}${{(num / 60).toFixed(1)}}m`;
    }}

    function signedYuan(value) {{
      const num = Number(value) || 0;
      return `${{num >= 0 ? "+" : ""}}${{num.toFixed(1)}}元`;
    }}

    function clock(seconds) {{
      const total = Math.max(0, Math.round(Number(seconds) || 0));
      const hh = String(Math.floor(total / 3600)).padStart(2, "0");
      const mm = String(Math.floor((total % 3600) / 60)).padStart(2, "0");
      return `${{hh}}:${{mm}}`;
    }}

    function currentFrame() {{
      return replayState.contract.frames[Math.min(replayState.frameIndex, replayState.contract.frames.length - 1)];
    }}

    function traceForFrame(frame) {{
      const tracesById = new Map(replayState.contract.reasoning_traces.map((trace) => [trace.id, trace]));
      return tracesById.get((frame.reasoning_trace_ids || [])[0]);
    }}

    function finalDelta() {{
      const baseline = replayState.contract.baseline_run.metrics;
      const challenger = replayState.contract.challenger_run.metrics;
      return {{
        time_saved_s: baseline.total_time_cost_s - challenger.total_time_cost_s,
        cost_saved_yuan: baseline.total_cost_yuan - challenger.total_cost_yuan,
        delivered_delta: challenger.delivered_orders - baseline.delivered_orders,
        timeout_risk_delta: challenger.timeout_risk - baseline.timeout_risk,
        utilization_delta: challenger.courier_utilization - baseline.courier_utilization
      }};
    }}

    function setKpiCard(cardId, valueId, contextId, totalId, value, context, total, trend) {{
      $(valueId).textContent = value;
      $(contextId).textContent = context;
      $(totalId).textContent = total;
      $(cardId).dataset.trend = trend;
    }}

    function idCsv(ids) {{
      return (ids || []).filter(Boolean).join(",");
    }}

    function setEngineStatus(title, detail) {{
      const box = $("engine-status");
      if (!box) return;
      const titleNode = box.querySelector("b");
      const detailNode = box.querySelector("span");
      if (titleNode) titleNode.textContent = title;
      if (detailNode) detailNode.textContent = detail;
    }}

    async function apiJson(path, body) {{
      const response = await fetch(path, {{
        method: "POST",
        headers: {{"Content-Type": "application/json"}},
        body: JSON.stringify(body)
      }});
      const payload = await response.json();
      if (!response.ok || payload.status === "error") throw new Error(payload.error || `request failed: ${{path}}`);
      return payload;
    }}

    function dayRunRequest() {{
      const scenarioId = $("scenario-select").value || "weekday_full_day";
      const controls = {{
        courier_count: Number($("courier-count").value),
        order_scale: Number($("order-scale").value),
        weather: $("weather-mode").value,
        congestion_profile: "weekday",
        memory_mode: "read-write",
        predictor_mode: "auto"
      }};
      const seed = `ui-${{scenarioId}}-${{controls.courier_count}}-${{controls.order_scale.toFixed(2)}}-${{controls.weather}}`;
      return {{scenario_id: scenarioId, seed, controls}};
    }}

    function applyContractPayload(payload, reason) {{
      const contract = payload.contract || payload;
      replayState.contract = contract;
      replayState.endpoints = payload.endpoints || replayState.endpoints;
      replayState.frameIndex = 0;
      renderApiTags();
      setFrameIndex(0);
      setEngineStatus("全日推演已更新", `${{reason}} · ${{contract.orders.length}} orders · ${{contract.frames.length}} frames`);
      return contract;
    }}

    async function runDaySimulation(reason = "control update") {{
      const request = dayRunRequest();
      const token = `${{Date.now()}}-${{Math.random()}}`;
      replayState.pendingRunToken = token;
      setEngineStatus("重新构建全日推演", `${{reason}} · couriers=${{request.controls.courier_count}} · scale=${{request.controls.order_scale.toFixed(2)}}`);
      const payload = await apiJson(replayState.endpoints.run, request);
      if (replayState.pendingRunToken !== token) return null;
      return applyContractPayload(payload, reason);
    }}

    function scheduleReplayRun(reason) {{
      if (replayState.controlRunTimer) window.clearTimeout(replayState.controlRunTimer);
      replayState.controlRunTimer = window.setTimeout(() => {{
        runDaySimulation(reason).catch((error) => setEngineStatus("推演更新失败", error.message || String(error)));
      }}, 520);
    }}

    function positionStyle(position) {{
      const x = Math.max(4, Math.min(96, Number(position && position.screen_x) || 50));
      const y = Math.max(4, Math.min(96, Number(position && position.screen_y) || 50));
      return `left:${{x}}%;top:${{y}}%;`;
    }}

    function routePath(route) {{
      const points = route.polyline || route.points || [];
      if (points.length < 2) return "";
      return points.map((point, index) => `${{index ? "L" : "M"}}${{Number(point.screen_x || 50).toFixed(2)}} ${{Number(point.screen_y || 50).toFixed(2)}}`).join(" ");
    }}

    function stageBaseHtml(frame, algorithmFrame) {{
      const orderIds = new Set(algorithmFrame.active_order_ids || []);
      const highlightedOrders = new Set(replayState.highlight.orderIds || frame.highlighted_order_ids || []);
      const highlightedCouriers = new Set(replayState.highlight.courierIds || frame.highlighted_courier_ids || []);
      const timeSlice = replayState.contract.time_slices.find((item) => item.id === frame.time_slice_id) || {{}};
      const shockIds = timeSlice.shock_ids || [];
      const hasBurst = shockIds.some((id) => id.includes("merchant-burst"));
      const congestionOpacity = Math.max(.2, Math.min(.92, Number(timeSlice.congestion_level || 0.4) * .95)).toFixed(2);
      const merchants = replayState.contract.merchants.slice(0, 8).map((merchant) =>
        `<span class="pin merchant" data-label="${{escapeText(merchant.id)}}" style="${{positionStyle(merchant.position)}}">商</span>`
      ).join("");
      const couriers = (algorithmFrame.courier_positions || []).slice(0, 10).map((courier) => {{
        const isHot = highlightedCouriers.has(courier.courier_id);
        return `<span class="pin courier${{isHot ? " highlight" : ""}}" data-courier-id="${{escapeText(courier.courier_id, "")}}" data-label="${{escapeText(courier.courier_id)}}" style="${{positionStyle(courier.position)}}">骑</span>`;
      }}).join("");
      const orders = replayState.contract.orders.filter((order) => orderIds.has(order.id)).slice(0, 10).map((order) => {{
        const isHot = highlightedOrders.has(order.id);
        return `<span class="pin order${{isHot ? " highlight" : ""}}" data-order-id="${{escapeText(order.id, "")}}" data-label="${{escapeText(order.id)}}" style="${{positionStyle(order.destination)}}">单</span>`;
      }}).join("");
      const routes = (algorithmFrame.route_overlays || []).slice(0, 8).map((route) => {{
        const isHot = highlightedOrders.has(route.order_id) || highlightedCouriers.has(route.courier_id);
        return `<path class="${{isHot ? "highlight-route" : ""}}" data-order-id="${{escapeText(route.order_id, "")}}" data-courier-id="${{escapeText(route.courier_id, "")}}" d="${{routePath(route)}}"></path>`;
      }}).join("");
      return `
        <div class="map-hud">
          <span>${{escapeText(timeSlice.label || frame.time_slice_id)}}</span>
          <span>weather ${{escapeText(timeSlice.weather)}}</span>
          <span>congestion ${{Number(timeSlice.congestion_level || 0).toFixed(2)}}</span>
          <span>supply ${{escapeText(timeSlice.courier_supply)}}</span>
        </div>
        <div class="district one"></div><div class="district two"></div><div class="district three"></div>
        <div class="road r1"></div><div class="road r2"></div><div class="road r3"></div>
        <div class="shock-band" data-shock-ids="${{escapeText(shockIds.join(","))}}" title="${{escapeText(shockIds.join(",") || frame.time_slice_id)}}" style="opacity:${{congestionOpacity}}"></div>
        ${{hasBurst ? `<div class="burst-marker">merchant_burst</div>` : ""}}
        <svg class="route-svg" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">${{routes}}</svg>
        ${{merchants}}${{couriers}}${{orders}}
      `;
    }}

    function metricCards(metrics) {{
      return [
        ["assigned", `${{metrics.assigned_orders}}/${{metrics.total_orders}}`],
        ["avg eta", minutes(metrics.avg_eta_s)],
        ["cost", yuan(metrics.total_cost_yuan)],
        ["risk", percent(metrics.timeout_risk)]
      ].map(([label, value]) => `<div class="mini-metric"><small>${{label}}</small><strong>${{value}}</strong></div>`).join("");
    }}

    function renderMaps(frame) {{
      $("greedy-map-stage").innerHTML = stageBaseHtml(frame, frame.baseline);
      $("autosolver-map-stage").innerHTML = stageBaseHtml(frame, frame.challenger);
      $("greedy-metrics").innerHTML = metricCards(frame.baseline.metrics);
      $("autosolver-metrics").innerHTML = metricCards(frame.challenger.metrics);
    }}

    function renderKpis(frame) {{
      const baseline = replayState.contract.baseline_run.metrics;
      const challenger = replayState.contract.challenger_run.metrics;
      const final = finalDelta();
      const frameBaseline = frame.baseline.metrics;
      const frameChallenger = frame.challenger.metrics;
      setKpiCard(
        "kpi-card-time",
        "kpi-time-saved",
        "kpi-time-context",
        "kpi-time-total",
        signedMinutes(frame.delta.time_saved_s),
        `当前帧 ${{clock(frame.sim_time_s)}} 累计节省`,
        `全日累计 ${{signedMinutes(final.time_saved_s)}}`,
        frame.delta.time_saved_s >= 0 ? "good" : "warn"
      );
      setKpiCard(
        "kpi-card-cost",
        "kpi-cost-saved",
        "kpi-cost-context",
        "kpi-cost-total",
        signedYuan(frame.delta.cost_saved_yuan),
        "当前帧履约成本差值",
        `全日累计 ${{signedYuan(final.cost_saved_yuan)}}`,
        frame.delta.cost_saved_yuan >= 0 ? "good" : "warn"
      );
      setKpiCard(
        "kpi-card-delivered",
        "kpi-delivered",
        "kpi-delivered-context",
        "kpi-delivered-total",
        `${{frameChallenger.delivered_orders}}/${{frameChallenger.total_orders}}`,
        `当前帧 vs greedy ${{frame.delta.extra_delivered_orders >= 0 ? "+" : ""}}${{frame.delta.extra_delivered_orders}} 单`,
        `全日累计 ${{challenger.delivered_orders}}/${{challenger.total_orders}}`,
        frame.delta.extra_delivered_orders >= 0 ? "good" : "warn"
      );
      setKpiCard(
        "kpi-card-risk",
        "kpi-risk",
        "kpi-risk-context",
        "kpi-risk-total",
        signedPercent(frame.delta.timeout_risk_delta),
        `Greedy ${{percent(frameBaseline.timeout_risk)}} / AutoSolver ${{percent(frameChallenger.timeout_risk)}}`,
        `全日累计 ${{signedPercent(final.timeout_risk_delta)}}`,
        frame.delta.timeout_risk_delta <= 0 ? "good" : "warn"
      );
      setKpiCard(
        "kpi-card-eta",
        "kpi-eta",
        "kpi-eta-context",
        "kpi-eta-total",
        minutes(frameChallenger.avg_eta_s),
        `当前帧 Greedy ${{minutes(frameBaseline.avg_eta_s)}}`,
        `全日 AutoSolver ${{minutes(challenger.avg_eta_s)}}`,
        frameChallenger.avg_eta_s <= frameBaseline.avg_eta_s ? "good" : "warn"
      );
      setKpiCard(
        "kpi-card-utilization",
        "kpi-utilization",
        "kpi-utilization-context",
        "kpi-utilization-total",
        percent(frameChallenger.courier_utilization),
        `vs greedy ${{signedPercent(frame.delta.utilization_delta)}}`,
        `全日 AutoSolver ${{percent(challenger.courier_utilization)}}`,
        frame.delta.utilization_delta >= -0.03 ? "good" : "warn"
      );
      $("timeline-label").textContent = clock(frame.sim_time_s);
    }}

    function businessCandidateReason(score, trace) {{
      const evidence = (trace && trace.evidence) || {{}};
      const phase = escapeText(evidence.demand_phase || "unknown");
      const orders = Number(evidence.order_count || 0);
      const congestion = Number(evidence.congestion_level || 0).toFixed(2);
      if (score.algorithm_id === "nearest_greedy") {{
        return `只看最近取餐距离，${{phase}} 的 ${{orders}} 单在拥堵 ${{congestion}} 下容易把超时风险推到后续时间片。`;
      }}
      if (score.algorithm_id === "autosolver_agent") {{
        return `综合供给、拥堵、deadline、成本和 Memory，在 ${{phase}} 中优先压低 ETA 与风险。`;
      }}
      return escapeText(score.reason);
    }}

    function impactLine(delta) {{
      return `预计影响: 时间 ${{signedMinutes(delta.time_saved_s)}} / 成本 ${{signedYuan(delta.cost_saved_yuan)}} / 风险 ${{signedPercent(delta.timeout_risk_delta)}}`;
    }}

    function renderDecisionHighlights(frame, trace, sourceLabel = "关键决策点") {{
      const orderIds = replayState.highlight.orderIds || frame.highlighted_order_ids || [];
      const courierIds = replayState.highlight.courierIds || frame.highlighted_courier_ids || [];
      const evidence = (trace && trace.evidence) || {{}};
      const chips = [
        ["source", sourceLabel],
        ["time-slice", `${{clock(frame.sim_time_s)}} · ${{frame.time_slice_id}}`],
        ["orders", orderIds.length ? orderIds.slice(0, 4).join(", ") : "no highlighted order"],
        ["couriers", courierIds.length ? courierIds.slice(0, 4).join(", ") : "no courier switch"],
        ["phase", `${{escapeText(evidence.demand_phase)}} · congestion ${{Number(evidence.congestion_level || 0).toFixed(2)}}`],
        ["impact", `${{signedMinutes(frame.delta.time_saved_s)}} / ${{signedYuan(frame.delta.cost_saved_yuan)}}`]
      ];
      $("decision-highlight-summary").innerHTML = chips.map(([label, value]) => `<span class="decision-chip" data-chip="${{escapeText(label, "")}}">${{escapeText(label)}}: ${{escapeText(value)}}</span>`).join("");
    }}

    function applyDecisionHighlight(frame, orderIds, courierIds, sourceLabel) {{
      replayState.highlight = {{
        orderIds: orderIds && orderIds.length ? orderIds : (frame.highlighted_order_ids || []),
        courierIds: courierIds && courierIds.length ? courierIds : (frame.highlighted_courier_ids || []),
        sourceLabel: sourceLabel || "关键决策点"
      }};
      renderMaps(frame);
      renderDecisionHighlights(frame, traceForFrame(frame), replayState.highlight.sourceLabel);
      document.querySelectorAll("#reasoning-timeline [data-highlight-card='true']").forEach((card) => {{
        card.dataset.activeHighlight = card.dataset.highlightSource === replayState.highlight.sourceLabel ? "true" : "false";
      }});
    }}

    function bindDecisionCards(frame) {{
      document.querySelectorAll("#reasoning-timeline [data-highlight-card='true']").forEach((card) => {{
        const orderIds = (card.dataset.orderIds || "").split(",").filter(Boolean);
        const courierIds = (card.dataset.courierIds || "").split(",").filter(Boolean);
        const label = card.dataset.highlightSource || "关键决策点";
        const activate = () => applyDecisionHighlight(frame, orderIds, courierIds, label);
        card.addEventListener("mouseenter", activate);
        card.addEventListener("focus", activate);
        card.addEventListener("click", activate);
      }});
    }}

    function renderReasoning(frame) {{
      const trace = traceForFrame(frame);
      const orderCsv = idCsv(frame.highlighted_order_ids);
      const courierCsv = idCsv(frame.highlighted_courier_ids);
      const cards = [];
      cards.push(`<article class="event-card" tabindex="0" data-highlight-card="true" data-active-highlight="true" data-highlight-source="关键决策点" data-time-slice-id="${{escapeText(frame.time_slice_id, "")}}" data-order-ids="${{escapeText(orderCsv, "")}}" data-courier-ids="${{escapeText(courierCsv, "")}}"><time>${{clock(frame.sim_time_s)}} · ${{escapeText(frame.time_slice_id)}}</time><b>关键决策点</b><span>${{escapeText(frame.delta.headline)}} ${{impactLine(frame.delta)}}</span></article>`);
      if (trace) {{
        (trace.candidate_scores || []).forEach((score) => {{
          cards.push(`<article class="event-card" tabindex="0" data-highlight-card="true" data-highlight-source="${{escapeText(score.algorithm_id, "")}}" data-algorithm="${{escapeText(score.algorithm_id, "")}}" data-time-slice-id="${{escapeText(frame.time_slice_id, "")}}" data-order-ids="${{escapeText(orderCsv, "")}}" data-courier-ids="${{escapeText(courierCsv, "")}}"><time>score ${{Number(score.score).toFixed(2)}} · ${{Number(score.estimated_runtime_ms).toFixed(0)}}ms</time><b>${{escapeText(score.algorithm_id)}}</b><span>${{businessCandidateReason(score, trace)}} ${{impactLine(trace.expected_impact)}}</span></article>`);
        }});
        cards.push(`<article class="event-card" tabindex="0" data-highlight-card="true" data-highlight-source="${{escapeText(trace.selected_strategy, "")}}" data-time-slice-id="${{escapeText(frame.time_slice_id, "")}}" data-order-ids="${{escapeText(orderCsv, "")}}" data-courier-ids="${{escapeText(courierCsv, "")}}"><time>10s budget · ${{Number(trace.time_budget_ms || 0)}}ms</time><b>${{escapeText(trace.selected_strategy)}}</b><span>${{escapeText(trace.rationale)}} 命中订单 ${{escapeText(orderCsv || "none")}}，涉及骑手 ${{escapeText(courierCsv || "none")}}。</span></article>`);
      }}
      $("reasoning-timeline").innerHTML = cards.join("");
      renderDecisionHighlights(frame, trace, replayState.highlight.sourceLabel || "关键决策点");
      bindDecisionCards(frame);
    }}

    function renderMemory(frame) {{
      const eventsById = new Map(replayState.contract.evolution_events.map((event) => [event.id, event]));
      const cards = frame.memory_event_ids.map((eventId) => eventsById.get(eventId)).filter(Boolean).map((event) => `
        <article class="memory-card" data-event-type="${{escapeText(event.event_type)}}" data-secret-handling="${{escapeText(event.secret_handling)}}">
          <code>${{escapeText(event.event_type)}} · ${{escapeText(event.secret_handling)}}</code>
          <b>${{escapeText(event.context_signature)}}</b>
          <span>${{escapeText(event.learned_rule)}}</span>
        </article>
      `);
      $("memory-evolution-stack").innerHTML = cards.join("");
    }}

    function renderApiTags() {{
      $("day-api-tags").innerHTML = Object.values(replayState.endpoints).map((endpoint) => `<span>${{escapeText(endpoint)}}</span>`).join("");
    }}

    function setFrameIndex(index) {{
      const frames = replayState.contract.frames;
      replayState.frameIndex = Math.max(0, Math.min(frames.length - 1, Number(index) || 0));
      const frame = currentFrame();
      $("timeline-scrubber").max = String(Math.max(0, frames.length - 1));
      $("timeline-scrubber").value = String(replayState.frameIndex);
      replayState.highlight = {{
        orderIds: frame.highlighted_order_ids || [],
        courierIds: frame.highlighted_courier_ids || [],
        sourceLabel: "关键决策点"
      }};
      renderKpis(frame);
      renderMaps(frame);
      renderReasoning(frame);
      renderMemory(frame);
      return frame;
    }}

    async function compareAlgorithms() {{
      const contract = await runDaySimulation("manual compare");
      if (contract) setEngineStatus("对比完成", `${{contract.orders.length}} orders · ${{contract.frames.length}} frames`);
      return contract;
    }}

    function playbackDelayMs() {{
      return Number($("playback-speed").value) || 1200;
    }}

    function schedulePlaybackTick(delay = playbackDelayMs()) {{
      if (replayState.timer) window.clearTimeout(replayState.timer);
      if (!replayState.playing) return;
      replayState.timer = window.setTimeout(() => {{
        const next = replayState.frameIndex + 1 >= replayState.contract.frames.length ? 0 : replayState.frameIndex + 1;
        setFrameIndex(next);
        schedulePlaybackTick();
      }}, delay);
    }}

    function playReplay() {{
      if (replayState.playing) return;
      replayState.playing = true;
      setEngineStatus("播放全日推演", `${{replayState.contract.frames.length}} frames · speed=${{playbackDelayMs()}}ms`);
      schedulePlaybackTick(40);
    }}

    function pauseReplay() {{
      replayState.playing = false;
      if (replayState.timer) window.clearTimeout(replayState.timer);
      replayState.timer = null;
      setEngineStatus("推演已暂停", `frame ${{replayState.frameIndex + 1}}/${{replayState.contract.frames.length}}`);
    }}

    function bindControls() {{
      $("timeline-scrubber").max = String(Math.max(0, replayState.contract.frames.length - 1));
      $("courier-count").addEventListener("input", () => {{ $("courier-count-value").textContent = $("courier-count").value; scheduleReplayRun("courier control"); }});
      $("order-scale").addEventListener("input", () => {{ $("order-scale-value").textContent = Number($("order-scale").value).toFixed(2); scheduleReplayRun("order scale control"); }});
      $("weather-mode").addEventListener("change", () => {{ $("weather-label").textContent = $("weather-mode").value; scheduleReplayRun("weather control"); }});
      $("scenario-select").addEventListener("change", () => {{ $("scenario-label").textContent = $("scenario-select").value; scheduleReplayRun("scenario control"); }});
      $("playback-speed").addEventListener("change", () => {{
        $("playback-speed-label").textContent = `${{(playbackDelayMs() / 1000).toFixed(2)}}s/frame`;
        if (replayState.playing) schedulePlaybackTick(40);
      }});
      $("timeline-scrubber").addEventListener("input", (event) => setFrameIndex(event.target.value));
      $("play-replay").addEventListener("click", playReplay);
      $("pause-replay").addEventListener("click", pauseReplay);
      $("compare-algorithms").addEventListener("click", () => compareAlgorithms().catch((error) => setEngineStatus("对比生成失败", error.message || String(error))));
    }}

    function bootstrapDayReplayShell() {{
      renderApiTags();
      bindControls();
      setFrameIndex(0);
      window.__AUTO_SOLVER_DAY_REPLAY_READY__ = true;
    }}

    document.addEventListener("DOMContentLoaded", bootstrapDayReplayShell);
    window.__AUTO_SOLVER_DAY_REPLAY__ = {{
      replayState,
      bootstrapDayReplayShell,
      setFrameIndex,
      setKpiCard,
      applyDecisionHighlight,
      renderDecisionHighlights,
      playReplay,
      pauseReplay,
      compareAlgorithms
    }};
  </script>
</body>
</html>"""
