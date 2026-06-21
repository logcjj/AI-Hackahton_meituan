#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def _node_id(text: str) -> str:
    return "n_" + re.sub(r"[^A-Za-z0-9_]", "_", text).strip("_")


def trace_to_dot(trace: dict[str, Any]) -> str:
    events = trace.get("events", [])
    lines = [
        "digraph autosolver_trace {",
        "  rankdir=LR;",
        "  node [shape=box, style=rounded];",
        '  start [label="Input"];',
        f'  regime [label="Perception\\nregime={trace.get("regime", "unknown")}"];',
        '  start -> regime;',
    ]
    previous = "regime"
    if not events:
        lines.append('  output [label="Output"];')
        lines.append("  regime -> output;")
    for index, event in enumerate(events[:80]):
        label = f"{event.get('category')}\\n{event.get('name')}\\n{event.get('elapsed_ms')}ms"
        node = _node_id(f"{index}_{event.get('name')}")
        lines.append(f'  {node} [label="{label}"];')
        lines.append(f"  {previous} -> {node};")
        previous = node
    lines.append('  output [label="Best-so-far output"];')
    lines.append(f"  {previous} -> output;")
    lines.append("}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render an AutoSolver trace JSON as Graphviz DOT.")
    parser.add_argument("trace_json")
    parser.add_argument("--output", "-o")
    args = parser.parse_args(argv)
    trace = json.loads(Path(args.trace_json).read_text(encoding="utf-8"))
    dot = trace_to_dot(trace)
    if args.output:
        Path(args.output).write_text(dot, encoding="utf-8")
    else:
        print(dot, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
