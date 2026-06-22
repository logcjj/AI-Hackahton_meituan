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

from autosolver_agent.system import get_agent_blueprint, run_case_agent as _run_case_agent

try:
    from web_agent_demo.sample_cases import SAMPLE_CASES, ensure_sample_cases
except ImportError:  # The demo can still run before optional synthetic cases are generated.
    SAMPLE_CASES = {}
    ensure_sample_cases = None


DATA_DIR = ROOT / "data" / "official_cases"
GENERATED_CASE_DIR = ROOT / "web_agent_demo" / "generated_cases"
CASE_FILES = {
    "large_seed301": DATA_DIR / "large_seed301.txt",
}


def _case_files() -> dict[str, Path]:
    files = dict(CASE_FILES)
    if ensure_sample_cases is not None:
        files.update(ensure_sample_cases(ROOT))
    return files


def list_cases() -> list[dict[str, object]]:
    cases = []
    for case_id, path in _case_files().items():
        if not path.exists():
            continue
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        row_count = max(0, len(lines) - (1 if lines and lines[0].startswith("task_id_list") else 0))
        sample = SAMPLE_CASES.get(case_id)
        case_type = "real provided case" if case_id == "large_seed301" else "synthetic demo case"
        scenario_name = sample.name if sample is not None else case_id
        scenario_type = sample.scenario_type if sample is not None else "generic"
        risk_tags = list(sample.risk_tags) if sample is not None else []
        operator_note = sample.description if sample is not None else "Case metadata is unavailable; using technical case id."
        source_type = "official_case" if case_id == "large_seed301" else "synthetic_demo_case"
        cases.append(
            {
                "id": case_id,
                "name": scenario_name,
                "scenario_name": scenario_name,
                "scenario_type": scenario_type,
                "risk_tags": risk_tags,
                "operator_note": operator_note,
                "source_type": source_type,
                "rows": row_count,
                "type": case_type,
            }
        )
    return cases


def run_case_agent(case_id: str, budget_s: float = 10.0, observer=None) -> dict[str, object]:
    path = _case_files().get(case_id)
    if path is None or not path.exists():
        raise ValueError(f"unknown case: {case_id}")
    return _run_case_agent(path, case_id=case_id, budget_s=budget_s, observer=observer)


def build_agent_payload(case_id: str, budget_s: float = 10.0) -> dict[str, object]:
    return {"status": "ok", "report": run_case_agent(case_id, budget_s=budget_s)}


def _sse(event: str, data: dict[str, object]) -> bytes:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n".encode("utf-8")


def render_index() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AutoSolver Agent System</title>
  <style>
    :root {
      --ink: #16211e;
      --muted: #66736e;
      --leaf: #236a43;
      --leaf-2: #123f2a;
      --gold: #d8b14a;
      --sand: #f4ead6;
      --clay: #c9714a;
      --blue: #2e5f73;
      --paper: rgba(255, 253, 246, .82);
      --card: rgba(255, 255, 255, .72);
      --line: rgba(22, 33, 30, .14);
      --shadow: 0 24px 80px rgba(31, 46, 38, .16);
      --mono: "SFMono-Regular", "Cascadia Code", Consolas, monospace;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--ink);
      font-family: "Avenir Next", "PingFang SC", "Hiragino Sans GB", sans-serif;
      background:
        linear-gradient(90deg, rgba(22,33,30,.055) 1px, transparent 1px),
        linear-gradient(180deg, rgba(22,33,30,.045) 1px, transparent 1px),
        radial-gradient(circle at 8% 12%, rgba(216,177,74,.34), transparent 22rem),
        radial-gradient(circle at 88% 4%, rgba(46,95,115,.25), transparent 28rem),
        radial-gradient(circle at 80% 92%, rgba(35,106,67,.22), transparent 24rem),
        linear-gradient(135deg, #f8efd9 0%, #eef0df 44%, #d9e8df 100%);
      background-size: 42px 42px, 42px 42px, auto, auto, auto, auto;
      min-height: 100vh;
    }
    main { width: min(1440px, calc(100vw - 32px)); margin: 0 auto; padding: 26px 0 46px; }
    .panel {
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 26px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(18px);
    }
    .topbar {
      display: grid;
      grid-template-columns: minmax(340px, 1.1fr) minmax(360px, .9fr);
      gap: 18px;
      align-items: stretch;
      margin-bottom: 18px;
    }
    .hero { padding: 28px; position: relative; overflow: hidden; }
    .eyebrow { color: var(--leaf); font-weight: 900; letter-spacing: .16em; text-transform: uppercase; font-size: 12px; }
    h1 { font-size: clamp(32px, 4.3vw, 58px); line-height: .96; margin: 12px 0 14px; letter-spacing: -0.06em; max-width: 880px; }
    h2 { margin: 0; font-size: 22px; letter-spacing: -0.035em; }
    .lead { color: var(--muted); font-size: 17px; line-height: 1.75; max-width: 790px; position: relative; z-index: 1; }
    .controls { padding: 22px; display: grid; gap: 12px; }
    .control-row { display: grid; grid-template-columns: 1fr 130px; gap: 10px; }
    .summary-panel, .compare-panel { padding: 20px; margin-bottom: 18px; }
    .summary-head {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 16px;
      align-items: start;
      margin-bottom: 14px;
    }
    .summary-grid, .result-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-top: 14px;
    }
    .summary-item, .result-item {
      padding: 13px;
      border-radius: 16px;
      background: rgba(255,255,255,.68);
      border: 1px solid var(--line);
      min-height: 88px;
    }
    .summary-item span, .result-item span {
      display: block;
      color: var(--muted);
      font-size: 11px;
      font-weight: 900;
      letter-spacing: .05em;
      text-transform: uppercase;
      margin-bottom: 7px;
    }
    .summary-item strong, .result-item strong {
      display: block;
      font-size: 18px;
      line-height: 1.3;
      letter-spacing: -.03em;
    }
    .summary-item code, .result-item code {
      display: block;
      margin-top: 6px;
      color: var(--muted);
      font-family: var(--mono);
      font-size: 12px;
      word-break: break-all;
    }
    .tag-list { display: flex; gap: 6px; flex-wrap: wrap; }
    .tag {
      border-radius: 999px;
      padding: 5px 8px;
      background: rgba(46,95,115,.12);
      color: var(--blue);
      font-size: 12px;
      font-weight: 900;
    }
    .result-caption { margin: 8px 0 0; color: var(--muted); line-height: 1.6; font-size: 14px; }
    label { color: var(--muted); font-size: 13px; font-weight: 800; display: grid; gap: 7px; }
    select, input, button {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 13px 14px;
      font-size: 16px;
      background: rgba(255,255,255,.88);
      color: var(--ink);
    }
    button {
      cursor: pointer;
      border: none;
      color: white;
      font-weight: 900;
      background: linear-gradient(135deg, var(--leaf), var(--leaf-2));
      box-shadow: 0 14px 34px rgba(35,106,67,.26);
    }
    button.secondary { background: linear-gradient(135deg, var(--blue), #183247); }
    button:disabled { cursor: wait; opacity: .6; }
    .status-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      width: fit-content;
      border-radius: 999px;
      padding: 8px 11px;
      background: rgba(255,255,255,.62);
      color: var(--muted);
      font-weight: 800;
      font-size: 12px;
    }
    .status-pill:before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: var(--gold); box-shadow: 0 0 0 4px rgba(216,177,74,.18); }
    .status-pill.running:before { background: var(--leaf); animation: pulse 1.1s infinite; }
    @keyframes pulse { 50% { transform: scale(1.4); opacity: .55; } }
    .workbench {
      display: grid;
      grid-template-columns: 280px minmax(0, 1fr) 340px;
      gap: 18px;
      align-items: start;
    }
    .rail, .timeline-panel, .inspector, .table-panel, .evolution-panel { padding: 20px; }
    .rail, .timeline-panel, .inspector { min-height: 877px; }
    .rail { position: sticky; top: 18px; display: flex; flex-direction: column; }
    .objective {
      margin: 14px 0 18px;
      color: var(--muted);
      line-height: 1.65;
      font-size: 14px;
    }
    .stage-list { display: flex; flex-direction: column; gap: 10px; flex: 1; min-height: 0; }
    .stage {
      display: grid;
      grid-template-columns: 36px 1fr;
      gap: 10px;
      align-items: center;
      flex: 1 0 auto;
      padding: 12px;
      border-radius: 18px;
      background: var(--card);
      border: 1px solid var(--line);
      transition: border-color .2s ease, transform .2s ease, background .2s ease;
    }
    .stage.active { border-color: rgba(35,106,67,.62); background: rgba(239, 248, 228, .86); transform: translateX(4px); }
    .stage.done { border-color: rgba(216,177,74,.45); }
    .stage-index {
      width: 34px;
      height: 34px;
      display: grid;
      place-items: center;
      border-radius: 12px;
      background: rgba(22,33,30,.08);
      font-weight: 900;
      color: var(--leaf-2);
    }
    .stage b { display: block; margin-bottom: 4px; }
    .stage span { display: block; color: var(--muted); font-size: 12px; line-height: 1.45; }
    .timeline-toolbar {
      display: grid;
      grid-template-columns: 1fr auto auto;
      gap: 10px;
      align-items: center;
      margin: 14px 0;
    }
    .filters { display: flex; flex-wrap: wrap; gap: 7px; }
    .filter {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 8px 10px;
      background: rgba(255,255,255,.66);
      color: var(--muted);
      font-size: 12px;
      font-weight: 900;
      cursor: pointer;
      user-select: none;
    }
    .filter.active { color: white; background: var(--leaf); border-color: transparent; }
    .toggle {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 8px 11px;
      background: rgba(255,255,255,.66);
      font-size: 12px;
      font-weight: 900;
      color: var(--muted);
      cursor: pointer;
      user-select: none;
      white-space: nowrap;
    }
    .toggle.on { color: white; background: var(--blue); border-color: transparent; }
    .timeline {
      height: 620px;
      overflow: auto;
      padding-right: 6px;
      display: grid;
      align-content: start;
      gap: 10px;
    }
    .event {
      position: relative;
      display: grid;
      grid-template-columns: 90px 1fr;
      gap: 12px;
      min-height: 156px;
      padding: 14px;
      border-radius: 18px;
      background: rgba(255,255,255,.70);
      border: 1px solid var(--line);
    }
    .event.accepted { border-color: rgba(35,106,67,.55); background: rgba(239,248,228,.82); }
    .event.rejected { border-color: rgba(201,113,74,.42); }
    .time {
      font-family: var(--mono);
      font-size: 12px;
      color: var(--muted);
      white-space: nowrap;
    }
    .event-type {
      display: inline-block;
      border-radius: 999px;
      padding: 4px 8px;
      margin-bottom: 7px;
      background: rgba(46,95,115,.12);
      color: var(--blue);
      font-size: 11px;
      font-weight: 900;
      letter-spacing: .06em;
      text-transform: uppercase;
    }
    .event.accepted .event-type { background: rgba(35,106,67,.14); color: var(--leaf); }
    .event.rejected .event-type { background: rgba(201,113,74,.14); color: var(--clay); }
    .event-title { font-weight: 900; letter-spacing: -.02em; }
    .event-body { color: var(--muted); line-height: 1.55; margin-top: 5px; font-size: 14px; }
    .event-meta { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 9px; }
    .chip {
      border-radius: 999px;
      padding: 4px 8px;
      background: rgba(22,33,30,.07);
      color: var(--muted);
      font-size: 11px;
      font-weight: 800;
    }
    .inspector { position: sticky; top: 18px; display: grid; gap: 14px; }
    .inspect-card {
      padding: 15px;
      border-radius: 18px;
      background: var(--card);
      border: 1px solid var(--line);
    }
    .inspect-card b { display: block; margin-bottom: 8px; }
    .inspect-card div { color: var(--muted); line-height: 1.55; font-size: 14px; }
    .metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 9px; }
    .metric {
      padding: 12px;
      border-radius: 16px;
      background: rgba(255,255,255,.68);
      border: 1px solid var(--line);
    }
    .metric strong { display: block; font-size: 21px; letter-spacing: -.04em; }
    .metric span { color: var(--muted); font-size: 11px; font-weight: 900; text-transform: uppercase; }
    .evolution-panel { margin-top: 18px; overflow: hidden; }
    .evolution-head {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 18px;
      align-items: center;
      margin-bottom: 16px;
    }
    .evolution-head p {
      margin: 7px 0 0;
      color: var(--muted);
      line-height: 1.6;
      max-width: 840px;
    }
    .loop-badge {
      border-radius: 999px;
      padding: 9px 12px;
      background: rgba(35,106,67,.12);
      color: var(--leaf);
      font-weight: 900;
      font-size: 12px;
      white-space: nowrap;
    }
    .code-loop {
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 10px;
      align-items: stretch;
    }
    .loop-step {
      position: relative;
      min-height: 128px;
      padding: 14px;
      border-radius: 19px;
      border: 1px solid var(--line);
      background:
        radial-gradient(circle at 12% 14%, rgba(216,177,74,.18), transparent 5.2rem),
        rgba(255,255,255,.66);
      transition: border-color .2s ease, background .2s ease, transform .2s ease;
    }
    .loop-step.running { border-color: rgba(46,95,115,.58); background: rgba(232,244,248,.82); transform: translateY(-2px); }
    .loop-step.pass { border-color: rgba(35,106,67,.58); background: rgba(239,248,228,.84); }
    .loop-step.fail { border-color: rgba(201,113,74,.52); background: rgba(255,242,233,.82); }
    .loop-step.muted { border-color: rgba(22,33,30,.12); background: rgba(255,255,255,.50); }
    .loop-step.pending { border-color: var(--line); }
    .loop-step:after {
      content: ">";
      position: absolute;
      right: -10px;
      top: 45%;
      color: rgba(22,33,30,.28);
      font-weight: 900;
    }
    .loop-step:last-child:after { content: ""; }
    .loop-tag {
      display: inline-flex;
      border-radius: 999px;
      padding: 5px 8px;
      margin-bottom: 10px;
      background: rgba(46,95,115,.12);
      color: var(--blue);
      font-weight: 900;
      font-size: 11px;
      letter-spacing: .04em;
      text-transform: uppercase;
    }
    .loop-step b { display: block; margin-bottom: 7px; }
    .loop-status {
      display: block;
      color: var(--ink);
      font-weight: 900;
      line-height: 1.4;
      font-size: 13px;
    }
    .loop-detail {
      margin-top: 7px;
      color: var(--muted);
      line-height: 1.45;
      font-size: 13px;
    }
    .loop-step.pass .loop-status { color: var(--leaf); }
    .loop-step.fail .loop-status { color: var(--clay); }
    .loop-step.running .loop-status { color: var(--blue); }
    .table-panel { margin-top: 18px; }
    .attempt-grid { display: grid; gap: 10px; margin-top: 14px; }
    .attempt {
      display: grid;
      grid-template-columns: 150px 1fr 120px 90px;
      gap: 12px;
      align-items: center;
      padding: 13px 14px;
      border-radius: 17px;
      background: rgba(255,255,255,.70);
      border: 1px solid var(--line);
    }
    .attempt.accepted { border-color: rgba(35,106,67,.55); background: rgba(239,248,228,.82); }
    .attempt.rejected { border-color: rgba(201,113,74,.38); }
    .attempt .name { font-weight: 900; }
    .attempt .why { color: var(--muted); font-size: 13px; line-height: 1.45; }
    .verdict {
      border-radius: 999px;
      padding: 7px 9px;
      text-align: center;
      font-size: 12px;
      font-weight: 900;
      background: rgba(22,33,30,.08);
      color: var(--muted);
    }
    .attempt.accepted .verdict { color: white; background: var(--leaf); }
    .attempt.rejected .verdict { color: white; background: var(--clay); }
    .muted { color: var(--muted); }
    .empty {
      min-height: 170px;
      display: grid;
      place-items: center;
      text-align: center;
      color: var(--muted);
      border: 1px dashed var(--line);
      border-radius: 18px;
      background: rgba(255,255,255,.42);
      line-height: 1.7;
    }
    @media (max-width: 1100px) {
      .workbench, .topbar { grid-template-columns: 1fr; }
      .summary-grid, .result-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .code-loop { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .rail, .inspector { position: static; }
      .rail, .timeline-panel, .inspector { min-height: 0; }
      .timeline { height: 460px; }
    }
    @media (max-width: 760px) {
      main { width: min(100vw - 20px, 1180px); padding-top: 16px; }
      .control-row, .timeline-toolbar, .attempt, .code-loop, .evolution-head { grid-template-columns: 1fr; }
      .summary-head, .summary-grid, .result-grid { grid-template-columns: 1fr; }
      .event { grid-template-columns: 1fr; }
      .metrics { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
<main>
  <div class="topbar">
    <section class="hero panel">
      <div class="eyebrow">Developer Workbench</div>
      <h1>AutoSolver Agent Workbench</h1>
      <p class="lead">用于复核同一套 Agent 控制器如何处理当前调度场景。页面按输入摘要、运行轨迹、候选策略、结果对比和实验轨道组织信息，保留技术 ID，避免把内部估算包装成正式评测结论。</p>
    </section>
    <section class="controls panel">
      <div class="control-row">
        <label>调度场景<select id="case-select"></select></label>
        <label>预算秒数<input id="budget" type="number" min="1" max="10" step="0.5" value="10"></label>
      </div>
      <button id="run-agent">运行调度分析</button>
      <button id="reload-cases" class="secondary">刷新场景与能力</button>
      <div id="status" class="status-pill">等待启动</div>
    </section>
  </div>

  <section class="summary-panel panel" aria-label="场景摘要">
    <div class="summary-head">
      <div>
        <h2>场景摘要</h2>
        <p class="result-caption">运行前确认 case ID、数据来源、风险标签和候选规模；运行后补充 Agent 识别出的 regime 与输入画像。</p>
      </div>
      <div class="loop-badge">Input Summary</div>
    </div>
    <div class="summary-grid">
      <div class="summary-item"><span>Scenario</span><strong id="scenario-name">等待加载</strong><code id="scenario-id">case_id pending</code></div>
      <div class="summary-item"><span>Type</span><strong id="scenario-type">unknown</strong><code id="scenario-source">source pending</code></div>
      <div class="summary-item"><span>Rows</span><strong id="scenario-rows">0</strong><code id="scenario-profile">profile pending</code></div>
      <div class="summary-item"><span>Risk Tags</span><div id="scenario-risk-tags" class="tag-list"><span class="tag">pending</span></div></div>
    </div>
    <p id="scenario-note" class="result-caption">选择场景后会显示 operator note。</p>
  </section>

  <section class="compare-panel panel" aria-label="结果对比">
    <div class="summary-head">
      <div>
        <h2>Baseline vs AutoSolver</h2>
        <p class="result-caption">运行完成后展示最快稳定基线与最终 best-so-far 的本地对比参考；这里只展示可复核字段，不展示内部排序数值。</p>
      </div>
      <div class="loop-badge">Result Comparison</div>
    </div>
    <div id="result-comparison" class="result-grid"><div class="empty">运行调度分析后，这里会展示覆盖、候选组、骑手占用、耗时和接受策略数。</div></div>
  </section>

  <section class="workbench">
    <aside class="rail panel">
      <h2>Agent 阶段</h2>
      <div id="objective" class="objective">加载 Agent 目标中。</div>
      <div class="stage-list" id="stages"></div>
    </aside>

    <section class="timeline-panel panel">
      <h2>实时事件流</h2>
      <div class="timeline-toolbar">
        <div class="filters" id="filters"></div>
        <div class="toggle on" id="autoscroll">自动滚动</div>
        <div class="toggle" id="compact">紧凑视图</div>
      </div>
      <div class="timeline" id="events"><div class="empty">启动后这里会按时间顺序显示每个 Agent 动作。<br>可以筛选 Planner、Executor、Critic、Controller、Memory、Evolution。</div></div>
    </section>

    <aside class="inspector panel">
      <h2>当前检查器</h2>
      <div class="metrics">
        <div class="metric"><strong id="metric-events">0</strong><span>Events</span></div>
        <div class="metric"><strong id="metric-accepted">0</strong><span>Accepted</span></div>
        <div class="metric"><strong id="metric-round">0</strong><span>Round</span></div>
      </div>
      <div class="inspect-card"><b>当前阶段</b><div id="current-stage">等待启动。</div></div>
      <div class="inspect-card"><b>当前动作</b><div id="current-action">还没有工具调用。</div></div>
      <div class="inspect-card"><b>Controller 解释</b><div id="controller-note">等待第一轮规划。</div></div>
        <div class="inspect-card"><b>Self-Evolving Code Loop</b><div id="evolution-note">等待生成策略变体。</div></div>
      <div class="inspect-card"><b>Case Profile</b><div id="case-profile">选择用例后会展示任务数、骑手数、候选行和 regime。</div></div>
    </aside>
  </section>

  <section class="evolution-panel panel">
    <div class="evolution-head">
      <div>
        <h2>Self-Evolving Code Loop</h2>
        <p>这个区域展示 Agent 的实验轨道：生成策略变体，记录 case 画像，按相似样例检索，再经过验证、试跑、回退或晋升。正式 `solver.py` 始终作为 stable baseline，不被网页实验直接改写。</p>
      </div>
      <div class="loop-badge">Experimental Track</div>
    </div>
    <div class="code-loop">
      <div class="loop-step pending" id="evolution-step-generate" data-evolution-step="generate"><span class="loop-tag">Generate</span><b>生成策略变体</b><span class="loop-status" id="evolution-generate-status">等待本轮开始</span><div class="loop-detail" id="evolution-generate-detail">启动后显示本次生成的策略变体 ID 和 case 画像。</div></div>
      <div class="loop-step pending" id="evolution-step-recall" data-evolution-step="recall"><span class="loop-tag">Recall</span><b>相似历史检索</b><span class="loop-status" id="evolution-recall-status">等待检索</span><div class="loop-detail" id="evolution-recall-detail">如果没有历史候选，会显示：未命中相似候选，本轮仅生成新策略变体。</div></div>
      <div class="loop-step pending" id="evolution-step-safety" data-evolution-step="safety"><span class="loop-tag">Safety Gate</span><b>代码门禁</b><span class="loop-status" id="evolution-safety-status">等待策略生成</span><div class="loop-detail" id="evolution-safety-detail">AST 检查导入、危险调用和 propose 接口。</div></div>
      <div class="loop-step pending" id="evolution-step-sandbox" data-evolution-step="sandbox"><span class="loop-tag">Sandbox Execute</span><b>限时试跑</b><span class="loop-status" id="evolution-sandbox-status">等待门禁结果</span><div class="loop-detail" id="evolution-sandbox-detail">通过门禁后才会进入短时间片试跑。</div></div>
      <div class="loop-step pending" id="evolution-step-decision" data-evolution-step="decision"><span class="loop-tag">Decision</span><b>回退/晋升决策</b><span class="loop-status" id="evolution-decision-status">等待试跑结果</span><div class="loop-detail" id="evolution-decision-detail">Critic 对比 stable baseline，决定 rollback 或 promote。</div></div>
      <div class="loop-step pending" id="evolution-step-memory" data-evolution-step="memory"><span class="loop-tag">Evolution Memory</span><b>审计与候选池</b><span class="loop-status" id="evolution-memory-status">等待沉淀</span><div class="loop-detail" id="evolution-memory-detail">所有生成、验证、试跑都会写入审计记忆；只有 accepted/candidate/trusted/promoted 策略才会被后续相似样例 replay。</div></div>
    </div>
  </section>

  <section class="table-panel panel">
    <h2>策略候选表</h2>
    <div id="rounds" class="attempt-grid"><div class="empty">候选表会在每轮运行后更新：展示每个策略的用途、耗时、以及是否更新 best-so-far。</div></div>
  </section>
</main>
<script>
const $ = (id) => document.getElementById(id);
let currentRun = null;
let events = [];
let attempts = [];
let activeFilter = 'all';
let autoScroll = true;
let compactView = false;
let acceptedCount = 0;
let evolutionState = initialEvolutionState();
let casesById = {};
const stages = [
  ['perception', 'Perception', '读取 case，识别任务、骑手、bundle 和意愿分布。'],
  ['planner', 'Planner', '提出本轮策略批次，并说明尝试原因。'],
  ['executor', 'Executor', '实际调用候选生成或生产级 solver。'],
  ['critic', 'Critic', '判断候选是否有效，是否更新 best-so-far。'],
  ['controller', 'Controller', '根据结果决定下一轮方向和预算处理。'],
  ['memory', 'Memory', '保留 best-so-far，最终输出方案。'],
  ['evolution', 'Evolution', 'Self-Evolving Code Loop：生成策略变体，记录 case 画像和验证结果，只复用已接受的相似历史候选。'],
];
const filterItems = [
  ['all', '全部'],
  ['planner', 'Planner'],
  ['executor', 'Executor'],
  ['critic', 'Critic'],
  ['controller', 'Controller'],
  ['memory', 'Memory'],
  ['evolution', 'Evolution'],
];
function safe(text) {
  return String(text ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
}
function selectedCase() {
  return casesById[$('case-select')?.value] || null;
}
function renderTags(tags) {
  const items = Array.isArray(tags) && tags.length ? tags : ['未标注'];
  return items.map(item => `<span class="tag">${safe(item)}</span>`).join('');
}
function renderScenarioSummary(caseData, profile) {
  const data = caseData || {};
  const scenarioName = data.scenario_name || data.name || data.id || '等待加载';
  $('scenario-name').textContent = scenarioName;
  $('scenario-id').textContent = data.id ? `case_id: ${data.id}` : 'case_id pending';
  $('scenario-type').textContent = data.scenario_type || 'unknown';
  $('scenario-source').textContent = data.source_type || data.type || 'source pending';
  $('scenario-rows').textContent = String(profile?.rows ?? data.rows ?? 0);
  const profileText = profile
    ? `regime ${profile.regime ?? 'unknown'} · tasks ${profile.tasks ?? '?'} · couriers ${profile.couriers ?? '?'}`
    : 'profile pending';
  $('scenario-profile').textContent = profileText;
  $('scenario-risk-tags').innerHTML = renderTags(data.risk_tags);
  $('scenario-note').textContent = data.operator_note || '选择场景后会显示 operator note。';
}
function coverageText(record) {
  if (!record) return 'n/a';
  const covered = record.covered_tasks ?? '?';
  const total = record.total_tasks ?? '?';
  return `${covered}/${total}`;
}
function strategyName(record) {
  return record?.label || record?.name || record?.strategy || 'n/a';
}
function strategyId(record) {
  return record?.name || record?.strategy || 'n/a';
}
function attemptDecisionText(record) {
  if (!record) return '等待运行';
  if (record.error) return `拒绝：${record.error}`;
  if (record.accepted) return '接受：更新 best-so-far';
  if (record.valid === false) return '拒绝：候选无效';
  return '参考：未优于当前 best-so-far';
}
function renderResultComparison(report) {
  const baseline = attempts.find(item => item.name === 'greedy_baseline') || attempts[0] || null;
  const best = report?.best || null;
  const accepted = attempts.filter(item => item.accepted).length;
  const bestUncovered = Array.isArray(best?.uncovered_tasks) ? best.uncovered_tasks.length : 'n/a';
  const wallMs = Number.isFinite(Number(report?.wall_time_s)) ? `${Math.round(Number(report.wall_time_s) * 1000)} ms` : 'n/a';
  $('result-comparison').innerHTML = `
    <div class="result-item"><span>Baseline Source</span><strong>${safe(strategyName(baseline))}</strong><code>strategy_id: ${safe(strategyId(baseline))}</code></div>
    <div class="result-item"><span>Baseline Coverage</span><strong>${safe(coverageText(baseline))}</strong><code>${safe(attemptDecisionText(baseline))}</code></div>
    <div class="result-item"><span>AutoSolver Source</span><strong>${safe(best?.strategy || 'n/a')}</strong><code>final best-so-far</code></div>
    <div class="result-item"><span>AutoSolver Coverage</span><strong>${safe(coverageText(best))}</strong><code>uncovered tasks: ${safe(bestUncovered)}</code></div>
    <div class="result-item"><span>Resource Use</span><strong>${safe(best?.used_couriers ?? 'n/a')}</strong><code>couriers · groups ${safe(best?.groups ?? 'n/a')}</code></div>
    <div class="result-item"><span>Run Evidence</span><strong>${safe(wallMs)}</strong><code>${safe(accepted)} accepted / ${safe(attempts.length)} attempts</code></div>
  `;
}
function initialEvolutionState() {
  return {
    generatedStrategy: null,
    trustedDetails: [],
    caseProfile: null,
    steps: {
      generate: {
        className: 'pending',
        status: '等待本轮开始',
        detail: '启动后显示本次生成的策略变体 ID 和 case 画像。',
      },
      recall: {
        className: 'pending',
        status: '等待检索',
        detail: '如果没有历史候选，会显示：未命中相似候选，本轮仅生成新策略变体。',
      },
      safety: {
        className: 'pending',
        status: '等待策略生成',
        detail: 'AST 检查导入、危险调用和 propose 接口。',
      },
      sandbox: {
        className: 'pending',
        status: '等待门禁结果',
        detail: '通过门禁后才会进入短时间片试跑。',
      },
      decision: {
        className: 'pending',
        status: '等待试跑结果',
        detail: 'Critic 对比 stable baseline，决定 rollback 或 promote。',
      },
      memory: {
        className: 'pending',
        status: '等待沉淀',
        detail: '所有生成、验证、试跑都会写入审计记忆；只有 accepted/candidate/trusted/promoted 策略才会被后续相似样例 replay。',
      },
    },
  };
}
function setEvolutionStep(step, className, status, detail) {
  if (!evolutionState || !evolutionState.steps[step]) return;
  evolutionState.steps[step] = {className, status, detail};
}
function formatSimilarity(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric.toFixed(2) : '0.00';
}
function bestSimilarityFrom(values) {
  const numbers = (values || []).map(item => Number(item)).filter(Number.isFinite);
  return numbers.length ? Math.max(...numbers) : 0;
}
function summarizeCaseProfile(profile) {
  if (!profile) return 'case profile 等待最终 report 补全。';
  const willingness = Number(profile.avg_willingness);
  const willingnessText = Number.isFinite(willingness) ? willingness.toFixed(3) : 'unknown';
  return `regime ${profile.regime ?? 'unknown'} · tasks ${profile.tasks ?? '?'} · couriers ${profile.couriers ?? '?'} · rows ${profile.rows ?? '?'} · avg willingness ${willingnessText} · bundles ${profile.has_bundles ? 'yes' : 'no'}`;
}
function summarizeTrusted(details) {
  if (!details || !details.length) return '未命中相似候选，本轮仅生成新策略变体。';
  const best = Math.max(...details.map(item => Number(item.similarity || 0)).filter(Number.isFinite));
  const ids = details.slice(0, 3).map(item => item.strategy_id).filter(Boolean).join(', ');
  return `命中 ${details.length} 个相似候选，最高相似度 ${formatSimilarity(best)}${ids ? `：${ids}` : ''}。`;
}
function fallbackEvolutionReason(reason, accepted) {
  if (accepted) {
    return {
      reasonLabel: '试跑通过',
      reasonDetail: '试跑通过：实验策略没有造成质量回退，可进入候选池。',
      decisionAction: '系统动作：进入候选池，可供后续相似样例 replay。',
    };
  }
  const value = String(reason || '').trim();
  if (value === 'timeout') {
    return {
      reasonLabel: '试跑超时',
      reasonDetail: '试跑超时：实验策略未在短时间沙箱窗口内返回，本轮终止试跑。',
      decisionAction: '系统动作：回退到 stable baseline，solver.py 未修改。',
    };
  }
  if (value === 'quality regression') {
    return {
      reasonLabel: '质量门未通过',
      reasonDetail: '质量门未通过：实验策略按时返回，但没有优于当前 stable baseline，因此拒绝采用。',
      decisionAction: '系统动作：回退到 stable baseline，solver.py 未修改。',
    };
  }
  if (value === 'invalid output format') {
    return {
      reasonLabel: '输出格式无效',
      reasonDetail: '输出格式无效：策略返回内容不符合 propose 接口要求。',
      decisionAction: '系统动作：回退到 stable baseline，solver.py 未修改。',
    };
  }
  if (value.includes('unsafe') || value.includes('propose') || value.includes('syntax error') || value.includes('load error')) {
    return {
      reasonLabel: '安全门拒绝',
      reasonDetail: '安全门拒绝：代码未通过 AST/import/interface 检查。',
      decisionAction: '系统动作：回退到 stable baseline，solver.py 未修改。',
    };
  }
  return {
    reasonLabel: '试跑拒绝',
    reasonDetail: `试跑拒绝：${value || 'unknown reason'}。`,
    decisionAction: '系统动作：回退到 stable baseline，solver.py 未修改。',
  };
}
function describeEvolutionTrial(payload) {
  const fallback = fallbackEvolutionReason(payload?.reason, Boolean(payload?.accepted));
  return {
    reasonLabel: payload?.reason_label || fallback.reasonLabel,
    reasonDetail: payload?.reason_detail || fallback.reasonDetail,
    decisionAction: payload?.decision_action || fallback.decisionAction,
  };
}
function paintEvolutionPanel() {
  if (!evolutionState) evolutionState = initialEvolutionState();
  Object.entries(evolutionState.steps).forEach(([step, data]) => {
    const node = $(`evolution-step-${step}`);
    const status = $(`evolution-${step}-status`);
    const detail = $(`evolution-${step}-detail`);
    if (!node || !status || !detail) return;
    node.classList.remove('pending', 'running', 'pass', 'fail', 'muted');
    node.classList.add(data.className || 'pending');
    status.textContent = data.status;
    detail.textContent = data.detail;
  });
}
function updateEvolutionFromEvent(payload) {
  if (!payload.type || !payload.type.startsWith('evolution_')) return;
  if (!evolutionState) evolutionState = initialEvolutionState();
  const strategyId = payload.strategy_id || evolutionState.generatedStrategy || 'unknown strategy';
  if (payload.type === 'evolution_recall') {
    const strategies = payload.strategies || [];
    const similarities = payload.similarity || [];
    evolutionState.trustedDetails = strategies.map((strategy, index) => ({
      strategy_id: strategy,
      similarity: similarities[index] || 0,
    }));
    setEvolutionStep(
      'recall',
      strategies.length ? 'pass' : 'muted',
      strategies.length ? `命中 ${strategies.length} 个历史候选` : '未命中相似候选',
      strategies.length ? `最高相似度 ${formatSimilarity(bestSimilarityFrom(similarities))}；候选 ${strategies.slice(0, 3).join(', ')}。` : '未命中相似候选，本轮仅生成新策略变体。'
    );
  }
  if (payload.type === 'evolution_generate') {
    evolutionState.generatedStrategy = payload.strategy_id || strategyId;
    setEvolutionStep('generate', 'pass', `生成 ${evolutionState.generatedStrategy}`, payload.message || '生成策略变体已进入实验轨道。');
    if (evolutionState.steps.recall.className === 'pending') {
      setEvolutionStep('recall', 'muted', '未命中相似候选', '未命中相似候选，本轮仅生成新策略变体。');
    }
    setEvolutionStep('safety', 'running', '正在检查代码门禁', `等待 ${evolutionState.generatedStrategy} 的 AST 和接口检查结果。`);
  }
  if (payload.type === 'evolution_validate') {
    const passed = Boolean(payload.passed);
    setEvolutionStep('safety', passed ? 'pass' : 'fail', passed ? '安全门通过' : '安全门拒绝', payload.message || `${strategyId} 门禁完成。`);
    const safetyFailure = fallbackEvolutionReason(payload.reason || payload.message || 'unsafe', false);
    setEvolutionStep(
      'sandbox',
      passed ? 'running' : 'muted',
      passed ? '等待限时试跑' : '跳过试跑',
      passed ? `${strategyId} 可以进入短时间片试跑。` : `失败原因：${safetyFailure.reasonDetail}`
    );
    if (!passed) {
      setEvolutionStep('decision', 'fail', '拒绝并回退', safetyFailure.decisionAction);
      setEvolutionStep('memory', 'fail', '只写入审计', '仅写入审计日志，不进入候选池。');
    }
  }
  if (payload.type === 'evolution_trial') {
    const accepted = Boolean(payload.accepted);
    const trial = describeEvolutionTrial(payload);
    setEvolutionStep('sandbox', accepted ? 'pass' : 'fail', trial.reasonLabel, `失败原因：${trial.reasonDetail}`);
    setEvolutionStep(
      'decision',
      accepted ? 'pass' : 'fail',
      accepted ? '准备晋升' : '准备回退',
      trial.decisionAction
    );
  }
  if (payload.type === 'evolution_replay') {
    const accepted = Boolean(payload.accepted);
    const similarityText = payload.similarity !== undefined ? `；相似度 ${formatSimilarity(payload.similarity)}` : '';
    setEvolutionStep(
      'recall',
      accepted ? 'pass' : 'muted',
      accepted ? '历史候选 replay 通过' : '历史候选 replay 未采纳',
      `${strategyId} replay ${payload.decision || 'done'}${similarityText}。`
    );
  }
  if (payload.type === 'evolution_rollback') {
    setEvolutionStep('decision', 'fail', '回退到 stable baseline', '系统动作：回退到 stable baseline，solver.py 未修改。');
    setEvolutionStep('memory', 'fail', '只写入审计', '仅写入审计日志，不进入候选池。');
  }
  if (payload.type === 'evolution_promote') {
    setEvolutionStep('decision', 'pass', '晋升为可复用候选', '系统动作：进入候选池，可供后续相似样例 replay。');
    setEvolutionStep('memory', 'pass', '进入候选池', '进入候选池，可供后续相似样例 replay。');
  }
  paintEvolutionPanel();
}
function paintBlueprint(data) {
  $('objective').textContent = data.objective;
  $('stages').innerHTML = stages.map(([id, title, desc], index) => `
    <div class="stage" data-stage="${id}">
      <div class="stage-index">${index + 1}</div>
      <div><b>${title}</b><span>${desc}</span></div>
    </div>`).join('');
  $('filters').innerHTML = filterItems.map(([id, label]) => `<div class="filter ${id === 'all' ? 'active' : ''}" data-filter="${id}">${label}</div>`).join('');
  document.querySelectorAll('.filter').forEach(node => node.addEventListener('click', () => {
    activeFilter = node.dataset.filter;
    document.querySelectorAll('.filter').forEach(item => item.classList.toggle('active', item.dataset.filter === activeFilter));
    paintEvents();
  }));
}
async function loadCases() {
  const [casesRes, blueprintRes] = await Promise.all([fetch('/api/cases'), fetch('/api/blueprint')]);
  const payload = await casesRes.json();
  const blueprint = await blueprintRes.json();
  paintBlueprint(blueprint.blueprint);
  casesById = Object.fromEntries(payload.cases.map(c => [c.id, c]));
  $('case-select').innerHTML = payload.cases.map(c => `<option value="${safe(c.id)}">${safe(c.scenario_name || c.name)} · ${safe(c.scenario_type || c.type)}</option>`).join('');
  renderScenarioSummary(selectedCase());
  $('case-profile').textContent = '已加载场景列表。启动后会展示本次 case 的结构画像。';
}
function stageForType(type) {
  if (type === 'perception' || type === 'critic_policy') return 'perception';
  if (type === 'round_start') return 'planner';
  if (type === 'attempt_start') return 'executor';
  if (type === 'attempt_result') return 'critic';
  if (type === 'adapt' || type === 'budget' || type === 'fallback') return 'controller';
  if (type === 'best_update' || type === 'final' || type === 'result') return 'memory';
  if (type.startsWith('evolution_')) return 'evolution';
  return 'controller';
}
function readableType(type) {
  return ({
    perception: 'Perception',
    critic_policy: 'Policy',
    round_start: 'Planner',
    attempt_start: 'Executor',
    attempt_result: 'Critic',
    best_update: 'Memory',
    adapt: 'Controller',
    budget: 'Budget',
    fallback: 'Fallback',
    evolution_recall: 'Recall',
    evolution_replay: 'Replay',
    evolution_generate: 'Generate',
    evolution_validate: 'Safety Gate',
    evolution_trial: 'Sandbox Execute',
    evolution_rollback: 'Rollback',
    evolution_promote: 'Promote',
    final: 'Final',
  })[type] || type;
}
function titleFor(e) {
  if (e.type === 'attempt_start') return `调用 ${e.label || e.strategy}`;
  if (e.type === 'attempt_result') return `${e.label || e.strategy}：${e.accepted ? '更新 best-so-far' : '暂不采用'}`;
  if (e.type === 'best_update') return 'Memory 更新 best-so-far';
  if (e.type === 'round_start') return `第 ${e.round} 轮策略规划`;
  if (e.type === 'adapt') return 'Controller 调整下一轮';
  if (e.type === 'evolution_recall') return '检索相似历史策略';
  if (e.type === 'evolution_replay') return '复用相似历史策略';
  if (e.type === 'evolution_generate') return '生成策略变体';
  if (e.type === 'evolution_validate') return `安全门禁：${e.passed ? '通过' : '拒绝'}`;
  if (e.type === 'evolution_trial') return `实验策略：${e.accepted ? '接受/晋升' : '回退/拒绝'}`;
  if (e.type === 'evolution_rollback') return '生成策略回退到 stable baseline';
  if (e.type === 'evolution_promote') return '生成策略进入候选记忆';
  if (e.type === 'final') return '输出最终 best-so-far';
  return e.message || readableType(e.type);
}
function bodyFor(e) {
  if (e.type === 'attempt_result') {
    return e.accepted ? 'Critic 判断这个候选优于当前 best-so-far，已保留为新的上下文。' : 'Critic 没有把这个候选作为当前最优，但它仍保留在候选表里便于对比。';
  }
  return e.message || '';
}
function metaFor(e) {
  const meta = [];
  if (e.round) meta.push(`round ${e.round}`);
  if (e.strategy) meta.push(e.strategy);
  if (e.elapsed_ms !== undefined) meta.push(`${Math.round(e.elapsed_ms)} ms`);
  if (e.valid !== undefined) meta.push(e.valid ? 'valid candidate' : 'invalid candidate');
  if (e.time_slice_s !== undefined) meta.push(`slice ${e.time_slice_s}s`);
  if (e.strategy_id) meta.push(e.strategy_id);
  if (e.decision) meta.push(e.decision);
  return meta;
}
function setStage(id, text) {
  document.querySelectorAll('.stage').forEach(node => {
    const isActive = node.dataset.stage === id;
    node.classList.toggle('active', isActive);
    if (isActive) node.classList.add('done');
  });
  $('current-stage').textContent = text;
}
function addEvent(payload) {
  const stage = stageForType(payload.type);
  events.push({...payload, stage});
  $('metric-events').textContent = events.length;
  if (payload.round) $('metric-round').textContent = payload.round;
  if (payload.type === 'attempt_result' && payload.accepted) {
    acceptedCount += 1;
    $('metric-accepted').textContent = acceptedCount;
  }
  updateEvolutionFromEvent(payload);
  paintEvents();
}
function paintEvents() {
  const visible = events.filter(e => activeFilter === 'all' || e.stage === activeFilter);
  if (!visible.length) {
    $('events').innerHTML = '<div class="empty">当前筛选条件下还没有事件。</div>';
    return;
  }
  $('events').innerHTML = visible.map(e => {
    const klass = e.type === 'attempt_result' ? (e.accepted ? 'accepted' : 'rejected') : '';
    const meta = metaFor(e).map(item => `<span class="chip">${safe(item)}</span>`).join('');
    return `<div class="event ${klass}">
      <div class="time">+${safe(e.time_s ?? '0.000')}s</div>
      <div>
        <span class="event-type">${safe(readableType(e.type))}</span>
        <div class="event-title">${safe(titleFor(e))}</div>
        ${compactView ? '' : `<div class="event-body">${safe(bodyFor(e))}</div>`}
        ${meta ? `<div class="event-meta">${meta}</div>` : ''}
      </div>
    </div>`;
  }).join('');
  if (autoScroll) $('events').scrollTop = $('events').scrollHeight;
}
function paintAttempts(report) {
  attempts = report.rounds.flatMap(round => round.strategies.map(s => ({...s, round: round.round})));
  if (!attempts.length) {
    $('rounds').innerHTML = '<div class="empty">这次运行没有记录到候选策略。</div>';
    return;
  }
  $('rounds').innerHTML = attempts.map(s => `
    <div class="attempt ${s.accepted ? 'accepted' : 'rejected'}">
      <div class="name">${safe(s.label || s.name)}<code>strategy_id: ${safe(s.name)}</code></div>
      <div class="why">${safe(s.reason || '策略执行记录')} · ${safe(attemptDecisionText(s))}</div>
      <div class="muted">${Math.round(s.elapsed_ms || 0)} ms · round ${safe(s.round)}</div>
      <div class="verdict">${s.accepted ? 'Best-so-far' : 'Reference'}</div>
    </div>`).join('');
}
function render(report) {
  $('case-profile').textContent = `${report.case_id} · regime ${report.regime} · tasks ${report.features.tasks} · couriers ${report.features.couriers} · rows ${report.features.rows}`;
  renderScenarioSummary(selectedCase(), {...(report.features || {}), regime: report.regime});
  $('current-action').textContent = '运行结束，Memory 已输出 best-so-far。';
  setStage('memory', `Agent session finished for ${report.case_id}.`);
  if (report.evolution) {
    const recalled = report.evolution.trusted_details || [];
    const recallText = recalled.length ? `；已检索 ${recalled.length} 个相似历史候选` : '';
    const trial = (report.events || []).find(e => e.type === 'evolution_trial' && e.strategy_id === report.evolution.generated_strategy);
    const validation = (report.events || []).find(e => e.type === 'evolution_validate' && e.strategy_id === report.evolution.generated_strategy);
    const trialDescription = trial ? describeEvolutionTrial(trial) : null;
    const trialText = trialDescription ? `；失败原因 ${trialDescription.reasonLabel}；${trialDescription.decisionAction.replace('系统动作：', '')}` : '；等待试跑结果';
    $('evolution-note').textContent = `策略变体 ${report.evolution.generated_strategy} 已写入 Evolution Memory 审计日志${trialText}${recallText}；模式 ${report.evolution.mode}。`;
    evolutionState.generatedStrategy = report.evolution.generated_strategy;
    evolutionState.caseProfile = report.evolution.case_profile || null;
    evolutionState.trustedDetails = recalled;
    setEvolutionStep('generate', 'pass', `生成 ${report.evolution.generated_strategy}`, summarizeCaseProfile(report.evolution.case_profile));
    setEvolutionStep('recall', recalled.length ? 'pass' : 'muted', recalled.length ? `命中 ${recalled.length} 个历史候选` : '未命中相似候选', summarizeTrusted(recalled));
    if (validation) {
      setEvolutionStep('safety', validation.passed ? 'pass' : 'fail', validation.passed ? '安全门通过' : '安全门拒绝', validation.message || '门禁结果已返回。');
    }
    if (trial && trialDescription) {
      setEvolutionStep('sandbox', trial.accepted ? 'pass' : 'fail', trialDescription.reasonLabel, `失败原因：${trialDescription.reasonDetail}`);
      setEvolutionStep('decision', trial.accepted ? 'pass' : 'fail', trial.accepted ? '晋升为可复用候选' : '回退到 stable baseline', trialDescription.decisionAction);
      setEvolutionStep('memory', trial.accepted ? 'pass' : 'fail', trial.accepted ? '进入候选池' : '只写入审计', trial.accepted ? `进入候选池，可供后续相似样例 replay；模式 ${report.evolution.mode}。` : `仅写入审计日志，不进入候选池；模式 ${report.evolution.mode}。`);
    } else if (validation && !validation.passed) {
      const safetyFailure = fallbackEvolutionReason(validation.reason || validation.message || 'unsafe', false);
      setEvolutionStep('sandbox', 'muted', '跳过试跑', `失败原因：${safetyFailure.reasonDetail}`);
      setEvolutionStep('decision', 'fail', '拒绝并回退', safetyFailure.decisionAction);
      setEvolutionStep('memory', 'fail', '只写入审计', `仅写入审计日志，不进入候选池；模式 ${report.evolution.mode}。`);
    }
    paintEvolutionPanel();
  }
  paintAttempts(report);
  renderResultComparison(report);
}
function resetRun() {
  events = [];
  attempts = [];
  acceptedCount = 0;
  evolutionState = initialEvolutionState();
  $('metric-events').textContent = '0';
  $('metric-accepted').textContent = '0';
  $('metric-round').textContent = '0';
  $('rounds').innerHTML = '<div class="empty">候选表会在每轮运行后更新：展示每个策略的用途、耗时、以及是否更新 best-so-far。</div>';
  $('result-comparison').innerHTML = '<div class="empty">运行调度分析后，这里会展示覆盖、候选组、骑手占用、耗时和接受策略数。</div>';
  $('events').innerHTML = '<div class="empty">启动后这里会按时间顺序显示每个 Agent 动作。</div>';
  $('current-stage').textContent = '等待启动。';
  $('current-action').textContent = '还没有工具调用。';
  $('controller-note').textContent = '等待第一轮规划。';
  $('evolution-note').textContent = '等待生成策略变体。';
  paintEvolutionPanel();
  document.querySelectorAll('.stage').forEach(node => node.classList.remove('active', 'done'));
}
async function streamRun() {
  if (currentRun) currentRun.close();
  resetRun();
  const button = $('run-agent');
  button.disabled = true;
  $('status').textContent = '运行中';
  $('status').classList.add('running');
  const qs = new URLSearchParams({ case: $('case-select').value, budget: $('budget').value });
  currentRun = new EventSource('/api/stream?' + qs.toString());
  currentRun.addEventListener('start', (ev) => {
    const payload = JSON.parse(ev.data);
    setStage('controller', 'Controller 打开新的 Agent session。');
    $('current-action').textContent = payload.message;
  });
  currentRun.addEventListener('perception', (ev) => {
    const payload = JSON.parse(ev.data);
    addEvent(payload);
    setStage('perception', payload.message);
    const f = payload.features || {};
    $('case-profile').textContent = `tasks ${f.tasks} · couriers ${f.couriers} · rows ${f.rows} · avg willingness ${f.avg_willingness} · bundles ${f.has_bundles ? 'yes' : 'no'}`;
    renderScenarioSummary(selectedCase(), {...f, regime: payload.regime});
    $('current-action').textContent = '已完成 case 画像，准备规划策略。';
  });
  currentRun.addEventListener('critic_policy', (ev) => {
    const payload = JSON.parse(ev.data);
    addEvent(payload);
    $('current-action').textContent = payload.message;
  });
  currentRun.addEventListener('round_start', (ev) => {
    const payload = JSON.parse(ev.data);
    addEvent(payload);
    setStage('planner', payload.message);
    $('current-action').textContent = `本轮将尝试 ${payload.strategies.length} 个策略。`;
  });
  ['evolution_recall', 'evolution_replay', 'evolution_generate', 'evolution_validate', 'evolution_trial', 'evolution_rollback', 'evolution_promote'].forEach(type => {
    currentRun.addEventListener(type, (ev) => {
      const payload = JSON.parse(ev.data);
      addEvent(payload);
      setStage('evolution', payload.message);
      $('evolution-note').textContent = payload.message;
      $('current-action').textContent = payload.message;
    });
  });
  currentRun.addEventListener('attempt_start', (ev) => {
    const payload = JSON.parse(ev.data);
    addEvent(payload);
    setStage('executor', `${payload.label}: ${payload.message}`);
    $('current-action').textContent = `Executor 正在调用 ${payload.strategy}。`;
  });
  currentRun.addEventListener('attempt_result', (ev) => {
    const payload = JSON.parse(ev.data);
    addEvent(payload);
    setStage('critic', `${payload.label || payload.strategy}: ${payload.accepted ? '更新 best-so-far' : '暂不采用'}`);
    $('current-action').textContent = payload.accepted ? 'Critic 接受候选，best-so-far 将更新。' : 'Critic 保留候选作为参考，继续搜索。';
  });
  currentRun.addEventListener('best_update', (ev) => {
    const payload = JSON.parse(ev.data);
    addEvent(payload);
    setStage('memory', payload.message);
    $('current-action').textContent = 'Memory 已保存新的 best-so-far。';
  });
  currentRun.addEventListener('adapt', (ev) => {
    const payload = JSON.parse(ev.data);
    addEvent(payload);
    setStage('controller', payload.message);
    $('controller-note').textContent = payload.message;
  });
  currentRun.addEventListener('budget', (ev) => {
    const payload = JSON.parse(ev.data);
    addEvent(payload);
    setStage('controller', payload.message);
    $('controller-note').textContent = payload.message;
  });
  currentRun.addEventListener('final', (ev) => {
    const payload = JSON.parse(ev.data);
    addEvent(payload);
    setStage('memory', payload.message);
    $('current-action').textContent = payload.message;
  });
  currentRun.addEventListener('result', (ev) => {
    const payload = JSON.parse(ev.data);
    render(payload.report);
    $('status').textContent = '运行完成';
    $('status').classList.remove('running');
    button.disabled = false;
    currentRun.close();
  });
  currentRun.addEventListener('error', () => {
    $('status').textContent = '实时流中断';
    $('status').classList.remove('running');
    button.disabled = false;
  });
}
$('autoscroll').addEventListener('click', () => {
  autoScroll = !autoScroll;
  $('autoscroll').classList.toggle('on', autoScroll);
});
$('compact').addEventListener('click', () => {
  compactView = !compactView;
  $('compact').classList.toggle('on', compactView);
  paintEvents();
});
$('run-agent').addEventListener('click', streamRun);
$('reload-cases').addEventListener('click', loadCases);
$('case-select').addEventListener('change', () => renderScenarioSummary(selectedCase()));
paintEvolutionPanel();
loadCases();
</script>
</body>
</html>"""


class AgentRequestHandler(BaseHTTPRequestHandler):
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
                self._send_html(render_index())
                return
            if parsed.path == "/api/blueprint":
                self._send_json({"status": "ok", "blueprint": get_agent_blueprint()})
                return
            if parsed.path == "/api/cases":
                self._send_json({"status": "ok", "cases": list_cases()})
                return
            if parsed.path == "/api/run":
                qs = parse_qs(parsed.query)
                case_id = qs.get("case", ["large_seed301"])[0]
                budget_s = float(qs.get("budget", ["10"])[0])
                self._send_json(build_agent_payload(case_id, budget_s=budget_s))
                return
            if parsed.path == "/api/stream":
                qs = parse_qs(parsed.query)
                case_id = qs.get("case", ["large_seed301"])[0]
                budget_s = float(qs.get("budget", ["10"])[0])
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(_sse("start", {"message": f"starting agent session for {case_id}"}))
                self.wfile.flush()

                def observer(event: dict[str, object]) -> None:
                    self.wfile.write(_sse(event["type"], event))
                    self.wfile.flush()

                report = run_case_agent(case_id, budget_s=budget_s, observer=observer)
                self.wfile.write(_sse("result", {"report": report}))
                self.wfile.write(_sse("done", {"message": "stream complete"}))
                self.wfile.flush()
                self.close_connection = True
                return
            self._send_json({"status": "error", "error": "not found"}, status=404)
        except Exception as exc:
            self._send_json(
                {"status": "error", "error": str(exc), "traceback": traceback.format_exc()},
                status=500,
            )

    def log_message(self, format: str, *args: object) -> None:
        print(f"[web-agent] {self.address_string()} - {format % args}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local AutoSolver Agent web demo.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    server = ThreadingHTTPServer((args.host, args.port), AgentRequestHandler)
    print(f"AutoSolver Agent System running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
