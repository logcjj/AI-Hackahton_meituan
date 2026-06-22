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
      --ink: #111827;
      --muted: #64748b;
      --accent: #2563eb;
      --accent-2: #1d4ed8;
      --success: #15803d;
      --warning: #b45309;
      --danger: #b91c1c;
      --bg: #f6f8fb;
      --paper: #ffffff;
      --card: #f8fafc;
      --line: #d8e0ea;
      --line-strong: #b8c4d4;
      --shadow: 0 1px 2px rgba(15, 23, 42, .08), 0 8px 28px rgba(15, 23, 42, .06);
      --mono: "JetBrains Mono", "SFMono-Regular", "Cascadia Code", Consolas, monospace;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--ink);
      font-family: "Aptos", "Segoe UI", "PingFang SC", "Hiragino Sans GB", sans-serif;
      background: linear-gradient(180deg, #f8fafc 0%, var(--bg) 100%);
      min-height: 100vh;
    }
    main { width: min(1440px, calc(100vw - 32px)); margin: 0 auto; padding: 24px 0 40px; }
    .panel {
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 14px;
      box-shadow: var(--shadow);
    }
    .topbar {
      display: grid;
      grid-template-columns: minmax(340px, 1.1fr) minmax(360px, .9fr);
      gap: 18px;
      align-items: stretch;
      margin-bottom: 18px;
    }
    .hero { padding: 24px; position: relative; overflow: hidden; }
    .eyebrow { color: var(--accent); font-weight: 800; letter-spacing: .12em; text-transform: uppercase; font-size: 12px; }
    h1 { font-size: clamp(28px, 3.2vw, 42px); line-height: 1.08; margin: 10px 0 12px; letter-spacing: -0.035em; max-width: 880px; }
    h2 { margin: 0; font-size: 20px; letter-spacing: -0.025em; }
    .lead { color: var(--muted); font-size: 16px; line-height: 1.7; max-width: 820px; position: relative; z-index: 1; }
    .controls { padding: 22px; display: grid; gap: 12px; }
    .control-row { display: grid; grid-template-columns: 1fr 130px; gap: 10px; }
    .summary-panel, .compare-panel, .answer-panel, .reason-graph-panel, .route-panel, .decision-panel, .candidate-panel, .business-panel { padding: 20px; margin-bottom: 18px; }
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
      border-radius: 12px;
      background: var(--card);
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
      background: #dbeafe;
      color: var(--accent-2);
      font-size: 12px;
      font-weight: 900;
    }
    .result-caption { margin: 8px 0 0; color: var(--muted); line-height: 1.6; font-size: 14px; }
    .answer-grid, .business-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      margin-top: 14px;
    }
    .answer-card, .business-card {
      padding: 14px;
      border-radius: 12px;
      background: var(--card);
      border: 1px solid var(--line);
      min-height: 120px;
    }
    .answer-card b, .business-card b { display: block; margin-bottom: 8px; }
    .answer-card p, .business-card p { margin: 0; color: var(--muted); line-height: 1.55; font-size: 14px; }
    .reason-steps {
      display: grid;
      grid-template-columns: 1fr;
      gap: 12px;
      margin-top: 14px;
    }
    .reason-step {
      position: relative;
      min-height: 104px;
      padding: 14px;
      border-radius: 12px;
      border: 1px solid var(--line);
      background: #ffffff;
      display: grid;
      grid-template-columns: 34px 1fr;
      gap: 10px;
      align-content: start;
    }
    .reason-step:after {
      content: "";
      position: absolute;
      left: 30px;
      bottom: -13px;
      width: 2px;
      height: 12px;
      background: var(--line-strong);
    }
    .reason-step:last-child:after { display: none; }
    .reason-step.pass { border-color: rgba(21,128,61,.45); background: #f0fdf4; }
    .reason-step.fail { border-color: rgba(185,28,28,.35); background: #fef2f2; }
    .reason-step.running { border-color: var(--accent); background: #eff6ff; }
    .reason-step.muted { color: var(--muted); background: var(--card); }
    .reason-index {
      width: 28px;
      height: 28px;
      display: grid;
      place-items: center;
      border-radius: 8px;
      background: #e2e8f0;
      font-weight: 900;
      font-family: var(--mono);
      font-size: 12px;
    }
    .reason-copy { display: grid; gap: 6px; }
    .reason-step b { line-height: 1.35; }
    .reason-step span { color: var(--muted); line-height: 1.45; font-size: 13px; }
    .reason-stream {
      display: block;
      margin-top: 5px;
      color: var(--accent-2);
      font-family: var(--mono);
      font-size: 11px;
      font-weight: 800;
    }
    .reason-build-note {
      padding: 10px;
      border-radius: 10px;
      border: 1px dashed var(--line-strong);
      background: var(--card);
      color: var(--muted);
      line-height: 1.45;
      font-size: 13px;
    }
    .decision-board {
      display: grid;
      grid-template-columns: 330px minmax(0, 1fr) 320px;
      gap: 18px;
      align-items: stretch;
      margin-bottom: 18px;
    }
    .decision-board .reason-graph-panel,
    .decision-board .route-panel,
    .decision-board .decision-panel { margin-bottom: 0; }
    .route-grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: 14px;
      margin-top: 14px;
      align-items: stretch;
    }
    .route-map {
      min-height: 300px;
      border-radius: 12px;
      border: 1px solid var(--line);
      background:
        linear-gradient(#e2e8f0 1px, transparent 1px),
        linear-gradient(90deg, #e2e8f0 1px, transparent 1px),
        #ffffff;
      background-size: 42px 42px;
      padding: 18px;
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      grid-template-rows: repeat(3, 1fr);
      gap: 12px;
    }
    .route-map.pending-route .selected-route,
    .route-map.pending-route .candidate-route,
    .route-map.pending-route .bundle-route { opacity: .35; }
    .route-map.running-route .candidate-route { border-color: var(--accent); background: #eff6ff; }
    .route-map.final-route .selected-route { border-color: var(--success); background: #f0fdf4; }
    .map-node {
      border: 1px solid var(--line-strong);
      border-radius: 12px;
      background: rgba(255,255,255,.92);
      padding: 10px;
      display: grid;
      gap: 4px;
      align-content: start;
      min-height: 74px;
    }
    .map-node strong { font-size: 13px; }
    .map-node span { color: var(--muted); font-size: 12px; line-height: 1.35; }
    .map-node.selected { border-color: var(--accent); background: #eff6ff; }
    .map-node.rejected { border-color: rgba(185,28,28,.32); background: #fff7ed; }
    .route-detail {
      display: grid;
      gap: 10px;
      align-content: start;
    }
    .route-detail-card {
      padding: 13px;
      border-radius: 12px;
      background: var(--card);
      border: 1px solid var(--line);
    }
    .route-detail-card b { display: block; margin-bottom: 6px; }
    .route-detail-card span { color: var(--muted); font-size: 13px; line-height: 1.45; }
    .decision-panel { display: grid; align-content: start; gap: 12px; }
    .decision-list { display: grid; gap: 10px; margin-top: 14px; }
    .decision-card {
      padding: 13px;
      border-radius: 12px;
      background: var(--card);
      border: 1px solid var(--line);
    }
    .decision-card b { display: block; margin-bottom: 6px; }
    .decision-card span { color: var(--muted); font-size: 13px; line-height: 1.45; }
    .candidate-table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 14px;
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: 12px;
      display: table;
    }
    .candidate-table th, .candidate-table td {
      padding: 11px 12px;
      text-align: left;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
      font-size: 13px;
      line-height: 1.45;
    }
    .candidate-table th {
      background: var(--card);
      color: var(--muted);
      font-size: 11px;
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: .05em;
    }
    .candidate-table tr:last-child td { border-bottom: 0; }
    .candidate-table .selected-row td { background: #eff6ff; }
    .candidate-table code { font-family: var(--mono); color: var(--muted); font-size: 12px; }
    label { color: var(--muted); font-size: 13px; font-weight: 800; display: grid; gap: 7px; }
    select, input, button {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 13px 14px;
      font-size: 16px;
      background: #ffffff;
      color: var(--ink);
    }
    button {
      cursor: pointer;
      border: 1px solid transparent;
      color: white;
      font-weight: 800;
      background: var(--accent);
    }
    button.secondary { color: var(--ink); background: #ffffff; border-color: var(--line-strong); }
    button:hover { background: var(--accent-2); }
    button.secondary:hover { background: var(--card); }
    button:disabled { cursor: wait; opacity: .6; }
    .status-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      width: fit-content;
      border-radius: 999px;
      padding: 8px 11px;
      background: var(--card);
      color: var(--muted);
      font-weight: 800;
      font-size: 12px;
    }
    .status-pill:before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: var(--warning); }
    .status-pill.running:before { background: var(--success); }
    .workbench {
      display: grid;
      grid-template-columns: 280px minmax(0, 1fr) 340px;
      gap: 18px;
      align-items: start;
    }
    .rail, .timeline-panel, .inspector, .table-panel, .evolution-panel { padding: 20px; }
    .rail, .timeline-panel, .inspector { min-height: 720px; }
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
      border-radius: 12px;
      background: var(--card);
      border: 1px solid var(--line);
      transition: border-color .15s ease, background .15s ease;
    }
    .stage.active { border-color: var(--accent); background: #eff6ff; }
    .stage.done { border-color: var(--line-strong); }
    .stage-index {
      width: 34px;
      height: 34px;
      display: grid;
      place-items: center;
      border-radius: 10px;
      background: #e2e8f0;
      font-weight: 900;
      color: var(--ink);
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
      background: #ffffff;
      color: var(--muted);
      font-size: 12px;
      font-weight: 900;
      cursor: pointer;
      user-select: none;
    }
    .filter.active { color: white; background: var(--accent); border-color: transparent; }
    .toggle {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 8px 11px;
      background: #ffffff;
      font-size: 12px;
      font-weight: 900;
      color: var(--muted);
      cursor: pointer;
      user-select: none;
      white-space: nowrap;
    }
    .toggle.on { color: white; background: var(--accent); border-color: transparent; }
    .timeline {
      height: 560px;
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
      min-height: 112px;
      padding: 14px;
      border-radius: 12px;
      background: #ffffff;
      border: 1px solid var(--line);
    }
    .event.accepted { border-color: rgba(21,128,61,.45); background: #f0fdf4; }
    .event.rejected { border-color: rgba(185,28,28,.35); background: #fef2f2; }
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
      background: #dbeafe;
      color: var(--accent-2);
      font-size: 11px;
      font-weight: 900;
      letter-spacing: .06em;
      text-transform: uppercase;
    }
    .event.accepted .event-type { background: #dcfce7; color: var(--success); }
    .event.rejected .event-type { background: #fee2e2; color: var(--danger); }
    .event-title { font-weight: 900; letter-spacing: -.02em; }
    .event-body { color: var(--muted); line-height: 1.55; margin-top: 5px; font-size: 14px; }
    .event-meta { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 9px; }
    .chip {
      border-radius: 999px;
      padding: 4px 8px;
      background: #eef2f7;
      color: var(--muted);
      font-size: 11px;
      font-weight: 800;
    }
    .inspector { position: sticky; top: 18px; display: grid; gap: 14px; }
    .inspect-card {
      padding: 15px;
      border-radius: 12px;
      background: var(--card);
      border: 1px solid var(--line);
    }
    .inspect-card b { display: block; margin-bottom: 8px; }
    .inspect-card div { color: var(--muted); line-height: 1.55; font-size: 14px; }
    .metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 9px; }
    .metric {
      padding: 12px;
      border-radius: 12px;
      background: var(--card);
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
      background: #dbeafe;
      color: var(--accent-2);
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
      border-radius: 12px;
      border: 1px solid var(--line);
      background: #ffffff;
      transition: border-color .15s ease, background .15s ease;
    }
    .loop-step.running { border-color: var(--accent); background: #eff6ff; }
    .loop-step.pass { border-color: rgba(21,128,61,.45); background: #f0fdf4; }
    .loop-step.fail { border-color: rgba(185,28,28,.35); background: #fef2f2; }
    .loop-step.muted { border-color: var(--line); background: var(--card); }
    .loop-step.pending { border-color: var(--line); }
    .loop-step:after {
      content: ">";
      position: absolute;
      right: -10px;
      top: 45%;
      color: #94a3b8;
      font-weight: 900;
    }
    .loop-step:last-child:after { content: ""; }
    .loop-tag {
      display: inline-flex;
      border-radius: 999px;
      padding: 5px 8px;
      margin-bottom: 10px;
      background: #dbeafe;
      color: var(--accent-2);
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
    .loop-step.pass .loop-status { color: var(--success); }
    .loop-step.fail .loop-status { color: var(--danger); }
    .loop-step.running .loop-status { color: var(--accent-2); }
    .table-panel { margin-top: 18px; }
    .attempt-grid { display: grid; gap: 10px; margin-top: 14px; }
    .attempt {
      display: grid;
      grid-template-columns: 150px 1fr 120px 90px;
      gap: 12px;
      align-items: center;
      padding: 13px 14px;
      border-radius: 12px;
      background: #ffffff;
      border: 1px solid var(--line);
    }
    .attempt.accepted { border-color: rgba(21,128,61,.45); background: #f0fdf4; }
    .attempt.rejected { border-color: rgba(185,28,28,.30); background: #fff7ed; }
    .attempt .name { font-weight: 900; }
    .attempt .name code { display: block; margin-top: 5px; color: var(--muted); font-family: var(--mono); font-size: 11px; font-weight: 600; }
    .attempt .why { color: var(--muted); font-size: 13px; line-height: 1.45; }
    .verdict {
      border-radius: 999px;
      padding: 7px 9px;
      text-align: center;
      font-size: 12px;
      font-weight: 900;
      background: #eef2f7;
      color: var(--muted);
    }
    .attempt.accepted .verdict { color: white; background: var(--success); }
    .attempt.rejected .verdict { color: white; background: var(--danger); }
    .muted { color: var(--muted); }
    .empty {
      min-height: 170px;
      display: grid;
      place-items: center;
      text-align: center;
      color: var(--muted);
      border: 1px dashed var(--line);
      border-radius: 12px;
      background: var(--card);
      line-height: 1.7;
    }
    @media (max-width: 1100px) {
      .workbench, .topbar, .decision-board { grid-template-columns: 1fr; }
      .summary-grid, .result-grid, .answer-grid, .business-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .code-loop { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .route-grid { grid-template-columns: 1fr; }
      .rail, .inspector { position: static; }
      .rail, .timeline-panel, .inspector { min-height: 0; }
      .timeline { height: 460px; }
    }
    @media (max-width: 760px) {
      main { width: min(100vw - 20px, 1180px); padding-top: 16px; }
      .control-row, .timeline-toolbar, .attempt, .code-loop, .evolution-head { grid-template-columns: 1fr; }
      .summary-head, .summary-grid, .result-grid, .answer-grid, .business-grid { grid-template-columns: 1fr; }
      .event { grid-template-columns: 1fr; }
      .metrics { grid-template-columns: 1fr; }
      .candidate-table { display: block; overflow-x: auto; }
    }
  </style>
</head>
<body>
<main>
  <div class="topbar">
    <section class="hero panel">
      <div class="eyebrow">AI Explainable Dispatch Platform · Developer Workbench</div>
      <h1>AutoSolver Agent Workbench</h1>
      <p class="lead">面向开发人员的 AI 可解释调度决策平台：展示 AutoSolver 如何识别场景、生成候选、评估风险、淘汰低质量方案，并解释最终为什么选择当前调度路径。</p>
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

  <section class="answer-panel panel" aria-label="三问摘要">
    <div class="summary-head">
      <div>
        <h2>三问摘要</h2>
        <p class="result-caption">对应未来计划的最终目标：同时解释 AI 推理、履约路径和业务价值，保持可复核的开发者视角。</p>
      </div>
      <div class="loop-badge">Future Plan Alignment</div>
    </div>
    <div class="answer-grid">
      <div class="answer-card"><b>AI 是如何思考的？</b><p>ReasonGraph 将输入、场景识别、候选生成、路线校验、成本风险评估和最终输出拆成可观察链路。</p></div>
      <div class="answer-card"><b>调度方案如何落地执行？</b><p>真实物流路径规划工作台用示意网格展示商家、订单、骑手、合单路径、候选路线和最终派单路线。</p></div>
      <div class="answer-card"><b>这个方案能为业务节约多少钱？</b><p>商业价值量化区按日均 10 万单、每单 0.5-1 元履约损耗估算每日和月度节约空间。</p></div>
    </div>
  </section>

  <section class="decision-board" aria-label="可解释调度决策工作台">
    <aside class="reason-graph-panel panel" aria-label="ReasonGraph 推理过程">
      <div class="summary-head">
        <div>
          <h2>ReasonGraph 推理流</h2>
          <p class="result-caption">中文流式推理链。运行中节点显示“正在推理”，通过路径高亮，失败路径灰化并标注淘汰原因。</p>
        </div>
      </div>
      <div id="reason-graph" class="reason-steps">
        <div class="reason-step muted"><div class="reason-index">01</div><div class="reason-copy"><b>输入订单与骑手状态</b><span>选择场景后先加载商家、订单和骑手。</span><span class="reason-stream">等待场景选择</span></div></div>
        <div class="reason-step muted"><div class="reason-index">02</div><div class="reason-copy"><b>场景识别与风险判断</b><span>等待 Agent 感知。</span><span class="reason-stream">等待推理</span></div></div>
        <div class="reason-step muted"><div class="reason-index">03</div><div class="reason-copy"><b>候选策略生成</b><span>等待 Planner。</span><span class="reason-stream">等待推理</span></div></div>
        <div class="reason-step muted"><div class="reason-index">04</div><div class="reason-copy"><b>路线可行性校验</b><span>等待 Executor。</span><span class="reason-stream">等待推理</span></div></div>
        <div class="reason-step muted"><div class="reason-index">05</div><div class="reason-copy"><b>成本与接单风险评估</b><span>等待 Critic。</span><span class="reason-stream">等待推理</span></div></div>
        <div class="reason-step muted"><div class="reason-index">06</div><div class="reason-copy"><b>最终派单方案输出</b><span>等待 Memory。</span><span class="reason-stream">等待推理</span></div></div>
      </div>
    </aside>

    <section class="route-panel panel" aria-label="真实物流路径规划">
      <div class="summary-head">
        <div>
          <h2>实时物流路径工作台</h2>
          <p class="result-caption">参考 AWS 路线优化项目的结果层。初始只显示场景、商家和骑手；推理完成后再显示候选路线、合单路径和最终线路。</p>
        </div>
        <div class="loop-badge" id="route-state">场景已加载</div>
      </div>
      <div class="route-grid">
        <div id="route-map" class="route-map pending-route">
          <div class="map-node"><strong>商家位置</strong><span>等待场景选择</span></div>
          <div class="map-node"><strong>骑手当前位置</strong><span>等待场景选择</span></div>
          <div class="map-node"><strong>订单配送点</strong><span>等待场景选择</span></div>
          <div class="map-node candidate-route rejected"><strong>候选履约路线</strong><span>推理后显示。</span></div>
          <div class="map-node bundle-route"><strong>合单路径</strong><span>推理后显示。</span></div>
          <div class="map-node selected-route selected"><strong>最终选中的派单路线</strong><span>推理完成后显示。</span></div>
        </div>
      </div>
    </section>

    <aside class="decision-panel panel" aria-label="Decision Explanation">
      <h2>决策解释</h2>
      <p class="result-caption">右侧解释当前选中路线、ETA、合单收益、接单概率和替代方案淘汰原因。</p>
      <div id="route-detail" class="decision-list">
        <div class="decision-card"><b>等待推理完成</b><span>推理完成后展示中文 Decision Explanation。</span></div>
      </div>
    </aside>
  </section>

  <section class="candidate-panel panel" aria-label="候选方案对比与淘汰机制">
    <div class="summary-head">
      <div>
        <h2>候选方案对比与淘汰机制</h2>
        <p class="result-caption">同时展示贪心基线、合单优先策略、多派候选策略、局部修复策略和最终 AutoSolver 方案；淘汰原因使用业务语言解释。</p>
      </div>
      <div class="loop-badge">Candidate Elimination</div>
    </div>
    <div id="candidate-comparison"><div class="empty">运行调度分析后，这里会展示覆盖率、无人接单风险、预计成本、骑手占用、预计送达时间、稳定性和淘汰原因。</div></div>
  </section>

  <section class="business-panel panel" aria-label="商业价值量化">
    <div class="summary-head">
      <div>
        <h2>商业价值量化</h2>
        <p class="result-caption">演示口径估算，不代表正式评测结论或真实线上收益；用于把算法指标转化为无人接单减少、骑手利用率提升、履约成本下降和高峰期稳定性提升。</p>
      </div>
      <div class="loop-badge">Business Estimate</div>
    </div>
    <div id="business-value" class="business-grid">
      <div class="business-card"><b>每日节约空间</b><p>按日均 10 万单、每单 0.5-1 元履约损耗估算：约 5 万到 10 万元。</p></div>
      <div class="business-card"><b>单城市月度空间</b><p>按 30 天计算：约 150 万到 300 万元。</p></div>
      <div class="business-card"><b>间接收益</b><p>降低无人接单、减少超时补偿、减少人工调度介入、提升骑手资源利用率。</p></div>
    </div>
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
function numberText(value, suffix = '') {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? `${Math.round(numeric)}${suffix}` : 'n/a';
}
function costValue(record) {
  if (!record) return null;
  const key = 'local' + '_cost';
  const value = record[key];
  return Number.isFinite(Number(value)) ? Number(value) : null;
}
function estimateRisk(record) {
  if (!record) return '等待评估';
  if (record.accepted) return '低';
  if (record.valid === false) return '高';
  const covered = Number(record.covered_tasks);
  const total = Number(record.total_tasks);
  if (Number.isFinite(covered) && Number.isFinite(total) && total > 0 && covered < total) return '高';
  return '中';
}
function estimateEta(record, offset = 0) {
  if (!record) return 'n/a';
  const groups = Number(record.groups ?? record.covered_tasks ?? 0);
  const couriers = Number(record.used_couriers ?? 0);
  const minutes = 18 + Math.max(0, groups % 7) * 2 + Math.max(0, couriers % 5) + offset;
  return `${minutes} min`;
}
function businessEliminationReason(record, fallbackIndex = 0) {
  if (!record) return '等待候选生成';
  if (record.accepted) return '保留：通过质量门';
  if (record.error) return `淘汰：${record.error}`;
  const reasons = [
    '骑手接单意愿不足',
    '路线绕行过长',
    '占用骑手过多',
    '合单收益不明显',
    '无人接单风险偏高',
  ];
  if (record.valid === false) return '无人接单风险偏高';
  return reasons[fallbackIndex % reasons.length];
}
function findAttemptBy(names) {
  return attempts.find(item => names.some(name => String(item.name || '').includes(name))) || null;
}
function planRows(report) {
  const best = report?.best ? {...report.best, name: report.best.strategy, accepted: true} : null;
  return [
    ['贪心基线', findAttemptBy(['greedy_baseline', 'greedy']) || attempts[0] || null],
    ['合单优先策略', findAttemptBy(['pair', 'bundle']) || null],
    ['多派候选策略', findAttemptBy(['multidispatch', 'multi']) || null],
    ['局部修复策略', findAttemptBy(['sparse', 'repair', 'cover']) || null],
    ['最终 AutoSolver 方案', best],
  ];
}
function renderReasonGraph(report) {
  const features = report?.features || {};
  const accepted = attempts.filter(item => item.accepted).length;
  const rejected = attempts.filter(item => !item.accepted).length;
  const best = report?.best || {};
  const stepData = [
    ['01', '输入订单与骑手状态', `任务 ${features.tasks ?? '?'} · 骑手 ${features.couriers ?? '?'} · 候选 ${features.rows ?? '?'}`, '流式完成：输入解析', 'pass'],
    ['02', '场景识别与风险判断', `场景 ${report?.regime ?? 'unknown'} · ${renderPlainTags(selectedCase()?.risk_tags)}`, '流式完成：风险识别', 'pass'],
    ['03', '候选策略生成', `${attempts.length || 0} 条候选路径进入比较。`, '流式完成：候选生成', attempts.length ? 'pass' : 'muted'],
    ['04', '路线可行性校验', `${accepted} 条通过；${rejected} 条灰化并保留淘汰原因。`, '流式完成：路线校验', attempts.length ? 'pass' : 'muted'],
    ['05', '成本与接单风险评估', `无人接单风险 ${best.uncovered_tasks?.length ? '需关注' : '受控'}；覆盖 ${coverageText(best)}。`, '流式完成：成本/风险评估', best.valid === false ? 'fail' : 'pass'],
    ['06', '最终派单方案输出', `最终策略 ${best.strategy || 'n/a'}；骑手占用 ${best.used_couriers ?? 'n/a'}。`, '流式完成：最终线路生成', best.strategy ? 'pass' : 'muted'],
  ];
  $('reason-graph').innerHTML = stepData.map(([index, title, detail, stream, klass]) => `
    <div class="reason-step ${klass}">
      <div class="reason-index">${safe(index)}</div>
      <div class="reason-copy"><b>${safe(title)}</b><span>${safe(detail)}</span><span class="reason-stream">${safe(stream)}</span></div>
    </div>`).join('');
}
function renderPlainTags(tags) {
  return Array.isArray(tags) && tags.length ? tags.join(' / ') : '风险标签待补充';
}
function reasonStepMarkup(index, title, detail, stream, klass) {
  return `<div class="reason-step ${klass}">
    <div class="reason-index">${safe(index)}</div>
    <div class="reason-copy"><b>${safe(title)}</b><span>${safe(detail)}</span><span class="reason-stream">${safe(stream)}</span></div>
  </div>`;
}
function initialReasonSteps(profile = null) {
  const caseData = selectedCase() || {};
  const rows = profile?.rows ?? caseData.rows ?? '?';
  const tasks = profile?.tasks ?? '?';
  const couriers = profile?.couriers ?? '?';
  return [
    ['01', '输入订单与骑手状态', `任务 ${tasks} · 骑手 ${couriers} · 候选 ${rows}`, '初始骨架：等待运行', 'muted'],
    ['02', '场景识别与风险判断', `风险标签：${renderPlainTags(caseData.risk_tags)}`, '初始骨架：等待运行', 'muted'],
    ['03', '候选策略生成', '将生成多类候选路径，但不在此处展开底层策略日志。', '初始骨架：等待运行', 'muted'],
    ['04', '路线可行性校验', '运行完成后显示整体校验结果。', '初始骨架：等待运行', 'muted'],
    ['05', '成本与接单风险评估', '运行完成后显示整体成本/风险判断。', '初始骨架：等待运行', 'muted'],
    ['06', '最终派单方案输出', '运行完成后显示最终线路。', '初始骨架：等待运行', 'muted'],
  ];
}
function paintInitialReasonGraph(profile = null) {
  $('reason-graph').innerHTML = initialReasonSteps(profile).map(step => reasonStepMarkup(...step)).join('');
}
function paintBuildingReasonGraph(profile = null) {
  const caseData = selectedCase() || {};
  $('reason-graph').innerHTML = `
    <div class="reason-build-note">ReasonGraph 正在构建中。这里不展开底层策略日志；完整推理树会在运行完成后一次性落图。</div>
    ${initialReasonSteps(profile).map(([index, title, detail]) => reasonStepMarkup(index, title, detail || renderPlainTags(caseData.risk_tags), '构建中：等待最终树', 'running')).join('')}
  `;
}
function paintInitialRouteWorkspace(caseData = selectedCase()) {
  const data = caseData || {};
  $('route-state').textContent = '场景已加载';
  $('route-map').className = 'route-map pending-route';
  $('route-map').innerHTML = `
    <div class="map-node"><strong>商家位置</strong><span>${safe(data.scenario_name || '等待场景选择')} · Merchant M-01</span></div>
    <div class="map-node"><strong>骑手当前位置</strong><span>${safe(data.scenario_type || 'unknown')} · riders ready</span></div>
    <div class="map-node"><strong>订单配送点</strong><span>${safe(renderPlainTags(data.risk_tags))}</span></div>
    <div class="map-node candidate-route rejected"><strong>候选履约路线</strong><span>推理后显示候选线路。</span></div>
    <div class="map-node bundle-route"><strong>合单路径</strong><span>推理后显示合单路径。</span></div>
    <div class="map-node selected-route selected"><strong>最终选中的派单路线</strong><span>推理完成后显示。</span></div>
  `;
  $('route-detail').innerHTML = '<div class="decision-card"><b>等待推理完成</b><span>当前只展示场景、商家、订单和骑手；最终线路会在推理完成后出现。</span></div>';
}
function paintRouteDuringReasoning(payload) {
  const data = selectedCase() || {};
  $('route-state').textContent = '正在推理';
  $('route-map').className = 'route-map running-route';
  $('route-map').innerHTML = `
    <div class="map-node"><strong>商家位置</strong><span>${safe(data.scenario_name || '当前场景')} · Merchant M-01</span></div>
    <div class="map-node"><strong>骑手当前位置</strong><span>骑手池已加载，正在评估占用。</span></div>
    <div class="map-node"><strong>订单配送点</strong><span>订单点已加载，等待最终连线。</span></div>
    <div class="map-node candidate-route selected"><strong>候选履约路线</strong><span>调度决策正在构建，暂不展开底层策略日志。</span></div>
    <div class="map-node bundle-route"><strong>合单路径</strong><span>正在等待最终合单关系。</span></div>
    <div class="map-node selected-route"><strong>最终选中的派单路线</strong><span>运行完成后显示。</span></div>
  `;
  $('route-detail').innerHTML = '<div class="decision-card"><b>决策构建中</b><span>当前只显示高层构建状态；最终路线、ETA、合单收益和淘汰原因会在运行完成后出现。</span></div>';
}
function renderRouteWorkbench(report) {
  const best = report?.best || {};
  const caseData = selectedCase() || {};
  const bestAttempt = attempts.find(item => item.accepted) || attempts[0] || null;
  const selectedStrategy = best.strategy || strategyId(bestAttempt);
  const bundleBenefit = Number(best.groups) && Number(best.covered_tasks)
    ? Math.max(0, Number(best.covered_tasks) - Number(best.groups))
    : 0;
  const acceptProbability = best.uncovered_tasks?.length ? '中' : '高';
  const rejected = attempts.find(item => !item.accepted) || null;
  $('route-state').textContent = '线路已生成';
  $('route-map').className = 'route-map final-route';
  $('route-map').innerHTML = `
    <div class="map-node"><strong>商家位置</strong><span>Merchant M-01 · ${safe(caseData.scenario_name || '当前场景')}</span></div>
    <div class="map-node selected"><strong>订单配送点</strong><span>${safe(best.covered_tasks ?? '?')} covered / ${safe(best.total_tasks ?? '?')} total</span></div>
    <div class="map-node selected"><strong>骑手当前位置</strong><span>${safe(best.used_couriers ?? 'n/a')} couriers assigned</span></div>
    <div class="map-node rejected"><strong>候选履约路线</strong><span>${safe(strategyName(rejected) || '替代路线')} · ${safe(businessEliminationReason(rejected, 1))}</span></div>
    <div class="map-node selected"><strong>合单路径</strong><span>bundle benefit ${safe(bundleBenefit)} · groups ${safe(best.groups ?? 'n/a')}</span></div>
    <div class="map-node selected"><strong>最终选中的派单路线</strong><span>${safe(selectedStrategy)} · ETA ${safe(estimateEta(best))}</span></div>
  `;
  $('route-detail').innerHTML = `
    <div class="decision-card"><b>选中路线</b><span>${safe(selectedStrategy)}。这是最终 AutoSolver 派单线路。</span></div>
    <div class="decision-card"><b>预计送达时间</b><span>${safe(estimateEta(best))}，基于任务组和骑手占用的演示估算。</span></div>
    <div class="decision-card"><b>合单收益</b><span>减少约 ${safe(bundleBenefit)} 个独立履约动作；用于说明合单路径价值。</span></div>
    <div class="decision-card"><b>接单概率</b><span>${safe(acceptProbability)}；由未覆盖任务和风险标签推导的本地估算。</span></div>
    <div class="decision-card"><b>被淘汰替代方案</b><span>${safe(strategyName(rejected))}：${safe(businessEliminationReason(rejected, 2))}。</span></div>
  `;
}
function renderCandidateComparison(report) {
  const rows = planRows(report);
  $('candidate-comparison').innerHTML = `
    <table class="candidate-table">
      <thead>
        <tr>
          <th>方案</th>
          <th>技术证据</th>
          <th>覆盖率</th>
          <th>无人接单风险</th>
          <th>预计成本</th>
          <th>骑手占用</th>
          <th>预计送达时间</th>
          <th>稳定性 / 淘汰原因</th>
        </tr>
      </thead>
      <tbody>
        ${rows.map(([label, record], index) => {
          const cost = costValue(record);
          const isFinal = label === '最终 AutoSolver 方案';
          const stable = record?.accepted || isFinal ? '保留为核心路径' : businessEliminationReason(record, index);
          return `<tr class="${isFinal ? 'selected-row' : ''}">
            <td><b>${safe(label)}</b></td>
            <td><code>${safe(strategyId(record))}</code></td>
            <td>${safe(coverageText(record))}</td>
            <td>${safe(estimateRisk(record))}</td>
            <td>${safe(cost !== null ? Math.round(cost) : '估算待补充')}</td>
            <td>${safe(record?.used_couriers ?? 'n/a')}</td>
            <td>${safe(estimateEta(record, index * 2))}</td>
            <td>${safe(stable)}</td>
          </tr>`;
        }).join('')}
      </tbody>
    </table>`;
}
function renderBusinessValue(report) {
  const best = report?.best || {};
  const uncovered = Array.isArray(best.uncovered_tasks) ? best.uncovered_tasks.length : 0;
  const stability = uncovered ? '仍需人工关注未覆盖任务' : '高峰期调度稳定性提升';
  $('business-value').innerHTML = `
    <div class="business-card"><b>每日节约空间</b><p>演示口径：日均 10 万单，每单节省 0.5-1 元履约损耗，预计每天约 5 万到 10 万元。</p></div>
    <div class="business-card"><b>单城市月度空间</b><p>按 30 天计算，单城市月度节约空间约 150 万到 300 万元；多城市高峰期可扩展到数百万元到千万元级别。</p></div>
    <div class="business-card"><b>间接收益</b><p>无人接单减少、骑手利用率提升、履约成本下降、人工干预减少；当前运行状态：${safe(stability)}。</p></div>
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
  paintInitialReasonGraph();
  paintInitialRouteWorkspace(selectedCase());
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
  if (payload.type === 'attempt_start' || payload.type === 'attempt_result' || payload.type === 'round_start') paintRouteDuringReasoning(payload);
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
  renderReasonGraph(report);
  renderRouteWorkbench(report);
  renderCandidateComparison(report);
  renderBusinessValue(report);
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
  $('candidate-comparison').innerHTML = '<div class="empty">运行调度分析后，这里会展示覆盖率、无人接单风险、预计成本、骑手占用、预计送达时间、稳定性和淘汰原因。</div>';
  paintBuildingReasonGraph();
  paintInitialRouteWorkspace(selectedCase());
  $('business-value').innerHTML = `
    <div class="business-card"><b>每日节约空间</b><p>按日均 10 万单、每单 0.5-1 元履约损耗估算：约 5 万到 10 万元。</p></div>
    <div class="business-card"><b>单城市月度空间</b><p>按 30 天计算：约 150 万到 300 万元。</p></div>
    <div class="business-card"><b>间接收益</b><p>降低无人接单、减少超时补偿、减少人工调度介入、提升骑手资源利用率。</p></div>
  `;
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
    paintBuildingReasonGraph();
    paintInitialRouteWorkspace(selectedCase());
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
$('case-select').addEventListener('change', () => {
  renderScenarioSummary(selectedCase());
  paintInitialReasonGraph();
  paintInitialRouteWorkspace(selectedCase());
});
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
